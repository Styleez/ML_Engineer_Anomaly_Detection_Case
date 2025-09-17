"""
Inference Service - Responsible for real-time predictions (simplified without Prometheus)
"""
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from shared.models.anomaly import (
    AnomalyPredictRequest,
    AnomalyPredictResponse,
    AnomalyDetectionModel
)
from shared.database.database import get_db
from shared.database.models import TrainedModel, PredictionLog
import redis
import json
import os
import time
from datetime import datetime, timezone

# FastAPI app
app = FastAPI(title="Inference Service")

# Redis Configuration
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB", 0))
)

@app.post("/predict/{series_id}")
async def predict(
    series_id: str, 
    request: AnomalyPredictRequest,
    version: str = None,
    db: Session = Depends(get_db)
) -> AnomalyPredictResponse:
    """Make prediction using cached model with database fallback"""
    try:
        # Check prediction cache first
        cache_key = f"prediction:{series_id}:{request.timestamp}"
        cached_prediction = redis_client.get(cache_key)
        
        if cached_prediction:
            prediction_data = json.loads(cached_prediction)
            return AnomalyPredictResponse(**prediction_data)
        
        # Get model parameters from cache
        model_key = f"model:{series_id}"
        cached_model = redis_client.get(model_key)
        
        model_params = None
        if cached_model:
            model_params = json.loads(cached_model)
        else:
            # Fallback to database if not in cache
            db_model = db.query(TrainedModel).filter(
                TrainedModel.series_id == series_id,
                TrainedModel.is_active == True
            ).first()
            
            if not db_model:
                raise HTTPException(
                    status_code=404,
                    detail=f"Model for series {series_id} not found. Train model first."
                )
            
            # Load model parameters from database
            model_params = {
                "mean": db_model.mean,
                "std": db_model.std,
                "threshold": db_model.threshold,
                "version": db_model.model_version
            }
            
            # Cache model parameters for future use
            redis_client.setex(
                model_key,
                3600,  # 1 hour TTL
                json.dumps(model_params)
            )
        
        # Create model from parameters
        model = AnomalyDetectionModel(threshold=model_params["threshold"])
        model.mean = model_params["mean"]
        model.std = model_params["std"]
        model._mark_as_trained()
        
        # Make prediction
        data_point = request.to_data_point()
        prediction_details = model.predict_with_details(data_point)
        
        # Create response
        response = AnomalyPredictResponse(
            anomaly=prediction_details["anomaly"],
            model_version=model_params["version"]
        )
        
        # Log prediction to database
        prediction_log = PredictionLog(
            series_id=series_id,
            timestamp=int(request.timestamp),
            value=request.value,
            is_anomaly=prediction_details["anomaly"],
            confidence=prediction_details["confidence"],
            deviation=prediction_details["deviation"],
            model_version=model_params["version"]
        )
        db.add(prediction_log)
        db.commit()
        
        # Cache prediction
        redis_client.setex(
            cache_key,
            300,  # 5 minutes TTL
            json.dumps(response.model_dump())
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/healthcheck")
async def healthcheck(db: Session = Depends(get_db)):
    """Inference service health check endpoint"""
    try:
        # Check Redis connection
        redis_client.ping()
        
        # Check Database connection
        series_trained = db.query(TrainedModel).filter(TrainedModel.is_active == True).count()
        
        return {
            "series_trained": series_trained,
            "inference_latency_ms": {"avg": 0, "p95": 0},  # Simplified
            "prediction_latency_ms": {"avg": 0, "p95": 0},  # Simplified
            "cache_stats": {"hits": 0, "misses": 0}  # Simplified
        }
    except redis.RedisError as e:
        raise HTTPException(
            status_code=503, 
            detail=f"Redis connection failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=503, 
            detail=f"Service unhealthy: {str(e)}"
        )
