"""
Inference Service - Responsible for real-time predictions (simplified without Prometheus)
"""
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
import time
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
    
    # Start timing for total latency
    import time
    start_time = time.time()
    
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
                "model_version": db_model.model_version
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
        
        # Make prediction (measure inference latency)
        inference_start = time.time()
        data_point = request.to_data_point()
        prediction_details = model.predict_with_details(data_point)
        inference_latency_ms = (time.time() - inference_start) * 1000
        
        # Create response
        response = AnomalyPredictResponse(
            anomaly=prediction_details["anomaly"],
            model_version=model_params["model_version"]
        )
        
        # Log prediction to database (measure database latency)
        db_start = time.time()
        prediction_log = PredictionLog(
            series_id=series_id,
            timestamp=int(request.timestamp),
            value=request.value,
            prediction=prediction_details["anomaly"],
            model_version=model_params["model_version"],
            inference_latency_ms=inference_latency_ms,
            database_latency_ms=None,  # Will be updated after commit
            total_latency_ms=None,     # Will be updated after commit
            created_at=int(time.time())
        )
        db.add(prediction_log)
        db.commit()
        db_latency_ms = (time.time() - db_start) * 1000
        
        # Calculate total latency and update record
        total_latency_ms = (time.time() - start_time) * 1000
        prediction_log.database_latency_ms = db_latency_ms
        prediction_log.total_latency_ms = total_latency_ms
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
    import time
    """Inference service health check endpoint"""
    redis_status = "unknown"
    database_status = "unknown"
    
    try:
        # Check Redis connection
        redis_client.ping()
        redis_status = "connected"
        
        # Get basic cache stats
        cache_keys = len(redis_client.keys("model:*"))
        
        # Check Database connection
        active_models = db.query(TrainedModel).filter(TrainedModel.is_active == True).count()
        database_status = "connected"
        
        # Recent predictions (last hour)
        import time
        hour_ago = int(time.time()) - 3600
        recent_predictions_query = db.query(PredictionLog).filter(PredictionLog.created_at >= hour_ago)
        recent_predictions = recent_predictions_query.count()
        
        # Calculate latency metrics from recent predictions
        recent_predictions_with_latency = recent_predictions_query.filter(
            PredictionLog.total_latency_ms.isnot(None)
        ).all()
        
        avg_inference_latency = 0
        avg_total_latency = 0
        p95_inference_latency = 0
        p95_total_latency = 0
        
        if recent_predictions_with_latency:
            inference_latencies = [p.inference_latency_ms for p in recent_predictions_with_latency if p.inference_latency_ms]
            total_latencies = [p.total_latency_ms for p in recent_predictions_with_latency if p.total_latency_ms]
            
            if inference_latencies:
                avg_inference_latency = sum(inference_latencies) / len(inference_latencies)
                inference_latencies.sort()
                p95_index = int(len(inference_latencies) * 0.95)
                p95_inference_latency = inference_latencies[p95_index] if p95_index < len(inference_latencies) else inference_latencies[-1]
            
            if total_latencies:
                avg_total_latency = sum(total_latencies) / len(total_latencies)
                total_latencies.sort()
                p95_index = int(len(total_latencies) * 0.95)
                p95_total_latency = total_latencies[p95_index] if p95_index < len(total_latencies) else total_latencies[-1]
        
        return {
            "service": "inference",
            "status": "healthy",
            "timestamp": int(time.time()),
            "redis_connection": redis_status,
            "database_connection": database_status,
            "metrics": {
                "active_models": active_models,
                "cached_models": cache_keys,
                "predictions_1h": recent_predictions,
                "avg_inference_latency_ms": round(avg_inference_latency, 2),
                "p95_inference_latency_ms": round(p95_inference_latency, 2),
                "avg_total_latency_ms": round(avg_total_latency, 2),
                "p95_total_latency_ms": round(p95_total_latency, 2)
            }
        }
    except redis.RedisError as e:
        redis_status = "failed"
        # Continue without Redis if database works
        try:
            active_models = db.query(TrainedModel).filter(TrainedModel.is_active == True).count()
            database_status = "connected"
            return {
                "service": "inference",
                "status": "degraded",
                "timestamp": int(time.time()),
                "redis_connection": redis_status,
                "database_connection": database_status,
                "error": f"Redis unavailable: {str(e)}",
                "metrics": {
                    "active_models": active_models,
                    "cached_models": 0
                }
            }
        except Exception as db_e:
            raise HTTPException(
                status_code=503, 
                detail={
                    "service": "inference",
                    "status": "unhealthy",
                    "redis_connection": redis_status,
                    "database_connection": "failed",
                    "errors": [str(e), str(db_e)],
                    "timestamp": int(time.time())
                }
            )
    except Exception as e:
        raise HTTPException(
            status_code=503, 
            detail={
                "service": "inference",
                "status": "unhealthy",
                "redis_connection": redis_status,
                "database_connection": database_status,
                "error": str(e),
                "timestamp": int(time.time())
            }
        )
