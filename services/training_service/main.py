"""
Training Service - Responsible for model training and persistence
"""
from fastapi import FastAPI, HTTPException, Depends
from datetime import datetime, timezone
from shared.models.anomaly import (
    AnomalyTrainRequest, 
    AnomalyTrainResponse,
    AnomalyDetectionModel
)
from shared.database.database import get_db
from shared.database.models import TrainedModel, TrainingData
from sqlalchemy.orm import Session
import json
import os

app = FastAPI(title="Training Service")


@app.post("/fit/{series_id}")
async def fit_model(
    series_id: str, 
    request: AnomalyTrainRequest,
    db: Session = Depends(get_db)
) -> AnomalyTrainResponse:
    """Train a new model or update existing one"""
    
    # Start timing for training latency
    import time
    training_start = time.time()
    
    try:
        # Convert request to TimeSeries
        time_series = request.to_time_series()
        
        # Create and train model (measure actual training time)
        model = AnomalyDetectionModel(threshold=request.threshold)
        model_training_start = time.time()
        model.fit(time_series)
        training_latency_ms = (time.time() - training_start) * 1000
        
        # Determine next version number for this series by finding the highest version
        all_versions = db.query(TrainedModel).filter(
            TrainedModel.series_id == series_id
        ).all()
        
        max_version_num = 0
        for model in all_versions:
            if model.model_version.startswith('v'):
                try:
                    version_num = int(model.model_version[1:])
                    max_version_num = max(max_version_num, version_num)
                except ValueError:
                    continue
        
        next_version_num = max_version_num + 1
        model_version = f"v{next_version_num}"
        
        # 1. Save model parameters to database
        # Create statistics dictionary manually
        training_stats = {
            "count": len(request.timestamps),
            "mean": model.mean,
            "std": model.std,
            "min": min(request.values),
            "max": max(request.values),
            "start_time": min(request.timestamps),
            "end_time": max(request.timestamps)
        }
        
        db_model = TrainedModel(
            series_id=series_id,
            model_type="anomaly_detection",
            mean=model.mean,
            std=model.std,
            threshold=model.threshold,
            model_version=model_version,
            training_points=len(request.timestamps),
            training_data_stats=training_stats,
            training_latency_ms=training_latency_ms
        )
        
        # Mark previous models as inactive for inference (but keep for history)
        if all_versions:
            db.query(TrainedModel).filter(
                TrainedModel.series_id == series_id,
                TrainedModel.is_active == True
            ).update({"is_active": False})
        
        db.add(db_model)
        
        # 2. Save training data to database
        training_data = TrainingData(
            series_id=series_id,
            model_version=model_version,
            timestamps=request.timestamps,
            values=request.values,
            data_points_count=len(request.timestamps)
        )
        
        db.add(training_data)
        db.commit()
        
        # Model parameters saved to database only
        # Inference service will cache them when needed
        
        return AnomalyTrainResponse(
            series_id=series_id,
            model_version=model_version,
            points_used=len(request.timestamps)
        )
        
    except ValueError as e:
        db.rollback()
        # Validation errors should return 422
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        db.rollback()
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/healthcheck")
async def healthcheck(db: Session = Depends(get_db)):
    import time
    """Training service health check endpoint"""
    try:
        # Database connectivity check
        total_models = db.query(TrainedModel).count()
        active_models = db.query(TrainedModel).filter(TrainedModel.is_active == True).count()
        
        # Recent training activity (last 24h)
        import time
        yesterday = int(time.time()) - 86400
        recent_models_query = db.query(TrainedModel).filter(TrainedModel.created_at >= yesterday)
        recent_models = recent_models_query.count()
        
        # Calculate training latency metrics from recent models
        recent_models_with_latency = recent_models_query.filter(
            TrainedModel.training_latency_ms.isnot(None)
        ).all()
        
        avg_training_latency = 0
        p95_training_latency = 0
        
        if recent_models_with_latency:
            training_latencies = [m.training_latency_ms for m in recent_models_with_latency if m.training_latency_ms]
            
            if training_latencies:
                avg_training_latency = sum(training_latencies) / len(training_latencies)
                training_latencies.sort()
                p95_index = int(len(training_latencies) * 0.95)
                p95_training_latency = training_latencies[p95_index] if p95_index < len(training_latencies) else training_latencies[-1]
        
        return {
            "service": "training",
            "status": "healthy",
            "timestamp": int(time.time()),
            "database_connection": "successful",
            "metrics": {
                "total_models": total_models,
                "active_models": active_models,
                "models_trained_24h": recent_models,
                "avg_training_latency_ms": round(avg_training_latency, 2),
                "p95_training_latency_ms": round(p95_training_latency, 2)
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=503, 
            detail={
                "service": "training",
                "status": "unhealthy", 
                "error": str(e),
                "timestamp": int(time.time())
            }
        )
