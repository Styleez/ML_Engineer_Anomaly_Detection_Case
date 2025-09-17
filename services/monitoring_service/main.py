"""
Monitoring Service - Responsável por dashboards e plot de dados
"""
from fastapi import FastAPI, HTTPException, Depends, Response
from sqlalchemy.orm import Session
from shared.database.database import get_db
from shared.database.models import TrainedModel, PredictionLog, TrainingData
from shared.models.anomaly.plot_models import AnomalyPlotResponse, PlotDataPoint
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
import json
import os
import httpx
import asyncio

app = FastAPI(title="Monitoring Service")

# Service URLs from environment (for system health check)
TRAINING_SERVICE_URL = os.getenv("TRAINING_SERVICE_URL", "http://training-service:8000")
INFERENCE_SERVICE_URL = os.getenv("INFERENCE_SERVICE_URL", "http://inference-service:8000")

async def get_service_health(client: httpx.AsyncClient, service_name: str, url: str) -> Dict[str, Any]:
    """Helper to get health status of other services."""
    try:
        response = await client.get(f"{url}/healthcheck", timeout=5)
        response.raise_for_status()
        return {"service": service_name, "status": "Healthy", "details": response.json()}
    except httpx.HTTPStatusError as e:
        return {"service": service_name, "status": "Unhealthy", "details": f"HTTP error: {e.response.status_code} - {e.response.text}"}
    except httpx.RequestError as e:
        return {"service": service_name, "status": "Unhealthy", "details": f"Request error: {e}"}
    except Exception as e:
        return {"service": service_name, "status": "Unhealthy", "details": f"Unexpected error: {e}"}

@app.get("/healthcheck")
async def healthcheck(db: Session = Depends(get_db)):
    """Monitoring service health check endpoint."""
    try:
        # Check database connection
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        return {
            "status": "ok", 
            "service": "monitoring",
            "database_connection": "successful",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {e}")

@app.get("/plot", response_model=AnomalyPlotResponse)
async def get_plot(
    series_id: str,
    version: Optional[str] = None,
    db: Session = Depends(get_db)
) -> AnomalyPlotResponse:
    """
    Retrieves training data for a specific series_id and optional version.
    If version is not provided, the most recent version is returned.
    """
    query = db.query(TrainingData).filter(TrainingData.series_id == series_id)

    if version:
        query = query.filter(TrainingData.model_version == version)
    else:
        # Get the most recent model version from TrainedModel table (more authoritative)
        from shared.database.models import TrainedModel
        
        # Debug: Get all models for this series_id to understand the issue
        all_models = db.query(TrainedModel).filter(
            TrainedModel.series_id == series_id
        ).order_by(TrainedModel.id.desc()).all()
        
        print(f"🔍 DEBUG: Found {len(all_models)} models for series_id {series_id}")
        for i, model in enumerate(all_models):
            print(f"   Model {i+1}: version={model.model_version}, id={model.id}, created_at={model.created_at}")
        
        latest_model = all_models[0] if all_models else None

        if not latest_model:
            raise HTTPException(status_code=404, detail=f"No trained model found for series_id: {series_id}")

        version = latest_model.model_version
        print(f"🔍 DEBUG: Selected version {version} from model id={latest_model.id}")
        query = query.filter(TrainingData.model_version == version)

    training_data_records = query.order_by(TrainingData.created_at.desc()).all()

    if not training_data_records:
        raise HTTPException(status_code=404, detail=f"No training data found for series_id: {series_id} and version: {version}")

    # Get the first (most recent) record
    training_record = training_data_records[0]
    
    # Extract timestamps and values from JSON arrays
    timestamps = training_record.timestamps if isinstance(training_record.timestamps, list) else []
    values = training_record.values if isinstance(training_record.values, list) else []
    
    if len(timestamps) != len(values):
        raise HTTPException(status_code=500, detail="Data corruption: timestamps and values arrays have different lengths")

    plot_data_points = [
        PlotDataPoint(
            timestamp=timestamp,
            value=value,
            is_anomaly=False  # Training data itself is not marked as anomaly
        )
        for timestamp, value in zip(timestamps, values)
    ]

    return AnomalyPlotResponse(
        series_id=series_id,
        model_version=version,
        data_points=plot_data_points,
        model_stats={
            "data_points_count": len(plot_data_points),
            "model_version": version,
            "series_id": series_id
        }
    )

@app.get("/metrics/throughput")
async def get_throughput_metrics(
    hours: int = 24,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Returns throughput metrics for inference and training services.
    
    Args:
        hours: Number of hours to look back (default: 24)
    """
    try:
        import time
        cutoff_time = int(time.time()) - (hours * 3600)
        
        # Inference throughput (predictions per hour)
        predictions_query = db.query(PredictionLog).filter(
            PredictionLog.created_at >= cutoff_time
        )
        total_predictions = predictions_query.count()
        
        # Calculate predictions per hour for each hour
        hourly_predictions = []
        for h in range(hours):
            hour_start = int(time.time()) - ((h + 1) * 3600)
            hour_end = int(time.time()) - (h * 3600)
            hour_count = predictions_query.filter(
                PredictionLog.created_at >= hour_start,
                PredictionLog.created_at < hour_end
            ).count()
            hourly_predictions.append({
                "hour": f"{h}h ago",
                "predictions": hour_count,
                "timestamp": hour_start
            })
        
        # Training throughput (models trained)
        models_query = db.query(TrainedModel).filter(
            TrainedModel.created_at >= cutoff_time
        )
        total_models_trained = models_query.count()
        
        # Current throughput rates
        avg_predictions_per_hour = total_predictions / hours if hours > 0 else 0
        avg_models_per_hour = total_models_trained / hours if hours > 0 else 0
        
        return {
            "period_hours": hours,
            "timestamp": int(time.time()),
            "inference_throughput": {
                "total_predictions": total_predictions,
                "avg_predictions_per_hour": round(avg_predictions_per_hour, 2),
                "peak_hour_predictions": max([h["predictions"] for h in hourly_predictions]) if hourly_predictions else 0,
                "current_rps_estimate": round(avg_predictions_per_hour / 3600, 4),  # requests per second
                "hourly_breakdown": hourly_predictions[-12:]  # Last 12 hours
            },
            "training_throughput": {
                "total_models_trained": total_models_trained,
                "avg_models_per_hour": round(avg_models_per_hour, 2)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate throughput: {str(e)}")

@app.get("/metrics/model-usage")
async def get_model_usage_metrics(
    hours: int = 24,
    limit: int = 10,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Returns the most used models and their usage statistics.
    
    Args:
        hours: Number of hours to look back (default: 24)
        limit: Number of top models to return (default: 10)
    """
    try:
        import time
        from sqlalchemy import func
        
        cutoff_time = int(time.time()) - (hours * 3600)
        
        # Query most used models by prediction count
        most_used_models = db.query(
            PredictionLog.series_id,
            PredictionLog.model_version,
            func.count(PredictionLog.id).label('prediction_count'),
            func.avg(PredictionLog.total_latency_ms).label('avg_latency_ms'),
            func.max(PredictionLog.created_at).label('last_used_at')
        ).filter(
            PredictionLog.created_at >= cutoff_time
        ).group_by(
            PredictionLog.series_id,
            PredictionLog.model_version
        ).order_by(
            func.count(PredictionLog.id).desc()
        ).limit(limit).all()
        
        # Calculate usage statistics
        total_predictions_period = db.query(PredictionLog).filter(
            PredictionLog.created_at >= cutoff_time
        ).count()
        
        model_stats = []
        for model in most_used_models:
            usage_percentage = (model.prediction_count / total_predictions_period * 100) if total_predictions_period > 0 else 0
            last_used_dt = datetime.fromtimestamp(model.last_used_at, tz=timezone.utc)
            
            model_stats.append({
                "series_id": model.series_id,
                "model_version": model.model_version,
                "prediction_count": model.prediction_count,
                "usage_percentage": round(usage_percentage, 2),
                "avg_latency_ms": round(model.avg_latency_ms or 0, 2),
                "last_used_at": model.last_used_at,
                "last_used_formatted": last_used_dt.strftime('%Y-%m-%d %H:%M:%S UTC')
            })
        
        # Series usage summary
        series_usage = db.query(
            PredictionLog.series_id,
            func.count(PredictionLog.id).label('total_predictions'),
            func.count(func.distinct(PredictionLog.model_version)).label('version_count')
        ).filter(
            PredictionLog.created_at >= cutoff_time
        ).group_by(
            PredictionLog.series_id
        ).order_by(
            func.count(PredictionLog.id).desc()
        ).limit(limit).all()
        
        series_stats = []
        for series in series_usage:
            usage_percentage = (series.total_predictions / total_predictions_period * 100) if total_predictions_period > 0 else 0
            series_stats.append({
                "series_id": series.series_id,
                "total_predictions": series.total_predictions,
                "version_count": series.version_count,
                "usage_percentage": round(usage_percentage, 2)
            })
        
        return {
            "period_hours": hours,
            "timestamp": int(time.time()),
            "total_predictions_period": total_predictions_period,
            "most_used_models": model_stats,
            "most_used_series": series_stats,
            "summary": {
                "unique_models_used": len(model_stats),
                "unique_series_used": len(series_stats),
                "avg_predictions_per_model": round(total_predictions_period / len(model_stats), 2) if model_stats else 0
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate model usage: {str(e)}")

@app.get("/models")
async def get_models(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Returns a list of all available models grouped by series_id with their versions.
    Format: {"models": [{"series_id": "sensor_1", "versions": ["v1", "v2"]}, ...]}
    """
    try:
        # Query all active models grouped by series_id
        models_query = db.query(
            TrainedModel.series_id,
            TrainedModel.model_version
        ).filter(
            TrainedModel.is_active == True
        ).order_by(
            TrainedModel.series_id.asc(),
            TrainedModel.model_version.asc()
        ).all()
        
        # Group by series_id
        models_dict = {}
        for series_id, model_version in models_query:
            if series_id not in models_dict:
                models_dict[series_id] = []
            if model_version not in models_dict[series_id]:
                models_dict[series_id].append(model_version)
        
        # Convert to list format
        models_list = []
        for series_id, versions in models_dict.items():
            models_list.append({
                "series_id": series_id,
                "versions": sorted(versions, reverse=True)  # Most recent first
            })
        
        # Sort by series_id
        models_list.sort(key=lambda x: x["series_id"])
        
        return {
            "models": models_list,
            "total_series": len(models_list),
            "total_models": sum(len(m["versions"]) for m in models_list)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch models: {str(e)}")

@app.get("/api-docs", response_class=Response)
async def api_docs():
    """
    Swagger UI for API documentation
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Anomaly Detection API - Documentation</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css" />
        <style>
            html {
                box-sizing: border-box;
                overflow: -moz-scrollbars-vertical;
                overflow-y: scroll;
            }
            *, *:before, *:after {
                box-sizing: inherit;
            }
            body {
                margin:0;
                background: #fafafa;
            }
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
        <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-standalone-preset.js"></script>
        <script>
            window.onload = function() {
                const ui = SwaggerUIBundle({
                    url: '/openapi.yaml',
                    dom_id: '#swagger-ui',
                    deepLinking: true,
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIStandalonePreset
                    ],
                    plugins: [
                        SwaggerUIBundle.plugins.DownloadUrl
                    ],
                    layout: "StandaloneLayout"
                })
            }
        </script>
    </body>
    </html>
    """
    return Response(content=html_content, media_type="text/html")

@app.get("/openapi.yaml", response_class=Response)
async def get_openapi_yaml():
    """
    Serve the OpenAPI YAML specification
    """
    import os
    yaml_path = "/app/api_docs/openapi.yaml"
    
    # If not found in container, try relative path
    if not os.path.exists(yaml_path):
        yaml_path = "../../api_docs/openapi.yaml"
    
    try:
        with open(yaml_path, 'r', encoding='utf-8') as file:
            yaml_content = file.read()
        return Response(content=yaml_content, media_type="text/yaml")
    except FileNotFoundError:
        # Fallback: return minimal OpenAPI spec
        minimal_spec = """
openapi: 3.0.3
info:
  title: Anomaly Detection API
  version: 1.0.0
  description: High-performance anomaly detection microservices
servers:
  - url: http://localhost:8000
    description: Training Service
  - url: http://localhost:8001  
    description: Inference Service
  - url: http://localhost:8002
    description: Monitoring Service
paths:
  /fit/{series_id}:
    post:
      summary: Train anomaly detection model
      parameters:
        - name: series_id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Model trained successfully
  /predict/{series_id}:
    post:
      summary: Predict anomaly for data point
      parameters:
        - name: series_id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Prediction completed
  /plot:
    get:
      summary: Get training data for visualization
      parameters:
        - name: series_id
          in: query
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Training data retrieved
  /models:
    get:
      summary: List all available models
      responses:
        '200':
          description: Models list retrieved
  /healthcheck:
    get:
      summary: Service health check
      responses:
        '200':
          description: Service is healthy
"""
        return Response(content=minimal_spec, media_type="text/yaml")

@app.get("/dashboard", response_class=Response)
async def dashboard(db: Session = Depends(get_db)):
    """
    Generates a simple HTML dashboard displaying key monitoring metrics
    from the database.
    """
    # --- Fetch Data ---
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    one_day_ago = now - timedelta(days=1)
    
    # Convert to unix timestamps
    one_hour_ago_ts = int(one_hour_ago.timestamp())
    one_day_ago_ts = int(one_day_ago.timestamp())
    
    # Basic metrics
    total_models = db.query(TrainedModel).filter(TrainedModel.is_active == True).count()
    total_predictions_today = db.query(PredictionLog).filter(
        PredictionLog.created_at >= one_day_ago_ts
    ).count()
    total_predictions_hour = db.query(PredictionLog).filter(
        PredictionLog.created_at >= one_hour_ago_ts
    ).count()
    
    # Recent models
    recent_models = db.query(TrainedModel).filter(
        TrainedModel.is_active == True
    ).order_by(TrainedModel.created_at.desc()).limit(5).all()
    
    # Recent predictions
    recent_predictions = db.query(PredictionLog).order_by(
        PredictionLog.created_at.desc()
    ).limit(10).all()

    # System health
    try:
        async with httpx.AsyncClient() as client:
            system_health = await asyncio.gather(
                get_service_health(client, "Training", TRAINING_SERVICE_URL),
                get_service_health(client, "Inference", INFERENCE_SERVICE_URL),
                return_exceptions=True
            )
    except Exception:
        system_health = [
            {"service": "Training", "status": "Unknown", "details": "Health check failed"},
            {"service": "Inference", "status": "Unknown", "details": "Health check failed"}
        ]
    
    # Throughput metrics (last 24h)
    try:
        cutoff_time = int(one_day_ago.timestamp())
        
        # Calculate hourly throughput for last 24h
        total_predictions_24h = db.query(PredictionLog).filter(
            PredictionLog.created_at >= cutoff_time
        ).count()
        
        # Calculate current hour predictions
        current_hour_start = int(now.replace(minute=0, second=0, microsecond=0).timestamp())
        predictions_current_hour = db.query(PredictionLog).filter(
            PredictionLog.created_at >= current_hour_start
        ).count()
        
        avg_predictions_per_hour = total_predictions_24h / 24 if total_predictions_24h > 0 else 0
        current_rps_estimate = avg_predictions_per_hour / 3600 if avg_predictions_per_hour > 0 else 0
        
    except Exception:
        total_predictions_24h = 0
        predictions_current_hour = 0
        avg_predictions_per_hour = 0
        current_rps_estimate = 0
    
    # Most used models (last 24h)
    try:
        from sqlalchemy import func
        
        most_used_models = db.query(
            PredictionLog.series_id,
            PredictionLog.model_version,
            func.count(PredictionLog.id).label('usage_count')
        ).filter(
            PredictionLog.created_at >= cutoff_time
        ).group_by(
            PredictionLog.series_id,
            PredictionLog.model_version
        ).order_by(
            func.count(PredictionLog.id).desc()
        ).limit(5).all()
        
    except Exception:
        most_used_models = []

    # Generate HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Anomaly Detection System - Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: rgba(255,255,255,0.95);
                border-radius: 20px;
                padding: 30px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                backdrop-filter: blur(10px);
            }}
            .header {{
                text-align: center;
                margin-bottom: 40px;
                border-bottom: 2px solid #eee;
                padding-bottom: 20px;
            }}
            .header h1 {{
                color: #2c3e50;
                margin: 0 0 10px 0;
                font-size: 2.5em;
                font-weight: 300;
            }}
            .header p {{
                color: #7f8c8d;
                margin: 0;
                font-size: 1.1em;
            }}
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 40px;
            }}
            .metric-card {{
                background: white;
                padding: 25px;
                border-radius: 15px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.08);
                text-align: center;
                border-left: 4px solid #3498db;
                transition: transform 0.2s, box-shadow 0.2s;
            }}
            .metric-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 10px 25px rgba(0,0,0,0.15);
            }}
            .metric-value {{
                font-size: 2.5em;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 10px;
            }}
            .metric-label {{
                color: #7f8c8d;
                font-size: 1.1em;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            .section {{
                margin-bottom: 40px;
            }}
            .section h2 {{
                color: #2c3e50;
                border-bottom: 2px solid #ecf0f1;
                padding-bottom: 10px;
                margin-bottom: 20px;
                font-weight: 300;
            }}
            .service-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
            }}
            .service-card {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.08);
            }}
            .service-status {{
                display: inline-block;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 0.9em;
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            .status-healthy {{
                background: #2ecc71;
                color: white;
            }}
            .status-unhealthy {{
                background: #e74c3c;
                color: white;
            }}
            .status-unknown {{
                background: #f39c12;
                color: white;
            }}
            .table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 5px 15px rgba(0,0,0,0.08);
            }}
            .table th, .table td {{
                padding: 15px;
                text-align: left;
                border-bottom: 1px solid #ecf0f1;
            }}
            .table th {{
                background: #f8f9fa;
                font-weight: 600;
                color: #2c3e50;
                text-transform: uppercase;
                letter-spacing: 1px;
                font-size: 0.9em;
            }}
            .table tr:hover {{
                background: #f8f9fa;
            }}
            .timestamp {{
                color: #7f8c8d;
                font-size: 0.9em;
            }}
            .prediction-true {{
                color: #e74c3c;
                font-weight: bold;
            }}
            .prediction-false {{
                color: #27ae60;
                font-weight: bold;
            }}
            .refresh-info {{
                text-align: center;
                margin-top: 30px;
                color: #7f8c8d;
                font-style: italic;
            }}
            .api-links {{
                margin-top: 30px;
                text-align: center;
            }}
            .api-links a {{
                display: inline-block;
                margin: 5px 10px;
                padding: 10px 20px;
                background: #3498db;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                transition: background 0.2s;
            }}
            .api-links a:hover {{
                background: #2980b9;
            }}
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .no-data {{
                text-align: center;
                font-style: italic;
                color: #7f8c8d;
                padding: 20px;
            }}
        </style>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns"></script>
        <script>
            let chart = null;
            
            // Wait for DOM to be fully loaded
            document.addEventListener('DOMContentLoaded', function() {{
                console.log('DOM loaded, initializing dashboard...');
                
                // Load models on page load
                loadModels();
                
                // Setup event listeners
                setupEventListeners();
            }});
            
            // Load available models
            async function loadModels() {{
                try {{
                    console.log('Loading models...');
                    const response = await fetch('/models');
                    const data = await response.json();
                    
                    const seriesSelect = document.getElementById('seriesSelect');
                    if (!seriesSelect) {{
                        console.error('seriesSelect element not found!');
                        return;
                    }}
                    
                    seriesSelect.innerHTML = '<option value="">Select a series...</option>';
                    
                    console.log('Found', data.models.length, 'models');
                    data.models.forEach(model => {{
                        const option = document.createElement('option');
                        option.value = model.series_id;
                        option.textContent = model.series_id;
                        option.dataset.versions = JSON.stringify(model.versions);
                        seriesSelect.appendChild(option);
                    }});
                    
                    console.log('Models loaded successfully');
                }} catch (error) {{
                    console.error('Error loading models:', error);
                }}
            }}
            
            // Setup all event listeners
            function setupEventListeners() {{
                console.log('Setting up event listeners...');
                
                const seriesSelect = document.getElementById('seriesSelect');
                const versionSelect = document.getElementById('versionSelect');
                const plotButton = document.getElementById('plotButton');
                
                if (!seriesSelect || !versionSelect || !plotButton) {{
                    console.error('Required elements not found:', {{
                        seriesSelect: !!seriesSelect,
                        versionSelect: !!versionSelect,
                        plotButton: !!plotButton
                    }});
                    return;
                }}
                
                // Handle series selection
                seriesSelect.addEventListener('change', function() {{
                    console.log('Series changed, value:', this.value);
                    console.log('Selected index:', this.selectedIndex);
                    
                    if (this.value && this.selectedIndex > 0) {{
                        // Get selected option using options array and selectedIndex
                        const selectedOption = this.options[this.selectedIndex];
                        console.log('Selected option:', selectedOption);
                        console.log('Dataset versions:', selectedOption.dataset.versions);
                        
                        const versions = JSON.parse(selectedOption.dataset.versions || '[]');
                        
                        console.log('Selected series:', this.value);
                        console.log('Available versions:', versions);
                        
                        // Clear and populate version dropdown
                        versionSelect.innerHTML = '<option value="">Latest version</option>';
                        
                        versions.forEach(version => {{
                            const option = document.createElement('option');
                            option.value = version;
                            option.textContent = version;
                            versionSelect.appendChild(option);
                            console.log('Added version option:', version);
                        }});
                        
                        // Enable controls
                        versionSelect.disabled = false;
                        plotButton.disabled = false;
                        
                        console.log('Version select enabled, options count:', versionSelect.options.length);
                    }} else {{
                        console.log('No series selected, disabling version select');
                        versionSelect.innerHTML = '<option value="">Select version...</option>';
                        versionSelect.disabled = true;
                        plotButton.disabled = true;
                    }}
                }});
                
                // Handle plot button click
                plotButton.addEventListener('click', handlePlotButtonClick);
                
                console.log('Event listeners setup complete');
            }}
            
            // Handle plot button click function
            async function handlePlotButtonClick() {{
                const seriesId = document.getElementById('seriesSelect').value;
                const version = document.getElementById('versionSelect').value;
                
                if (!seriesId) {{
                    alert('Please select a series ID');
                    return;
                }}
                
                try {{
                    this.disabled = true;
                    this.textContent = 'Loading...';
                    
                    // Build API URL
                    let url = `/plot?series_id=${{seriesId}}`;
                    if (version) {{
                        url += `&version=${{version}}`;
                    }}
                    
                    const response = await fetch(url);
                    const data = await response.json();
                    
                    if (data.data_points && data.data_points.length > 0) {{
                        createChart(data);
                    }} else {{
                        document.getElementById('plotContainer').innerHTML = 
                            '<div style="color: #e74c3c;">No data points found for this series</div>';
                    }}
                    
                }} catch (error) {{
                    console.error('Error loading plot data:', error);
                    document.getElementById('plotContainer').innerHTML = 
                        '<div style="color: #e74c3c;">Error loading plot data: ' + error.message + '</div>';
                }} finally {{
                    this.disabled = false;
                    this.textContent = 'Plot Data';
                }}
            }}
            
            // Create chart
            function createChart(data) {{
                const container = document.getElementById('plotContainer');
                
                // Clear previous chart
                if (chart) {{
                    chart.destroy();
                }}
                
                // Create canvas
                container.innerHTML = '<canvas id="timeSeriesChart"></canvas>';
                const ctx = document.getElementById('timeSeriesChart').getContext('2d');
                
                // Prepare data
                const timestamps = data.data_points.map(point => new Date(point.timestamp * 1000));
                const values = data.data_points.map(point => point.value);
                
                chart = new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        labels: timestamps,
                        datasets: [{{
                            label: `${{data.series_id}} (${{data.model_version}})`,
                            data: values,
                            borderColor: '#3498db',
                            backgroundColor: 'rgba(52, 152, 219, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            title: {{
                                display: true,
                                text: `Time Series: ${{data.series_id}} (Version: ${{data.model_version}})`,
                                font: {{ size: 16, weight: 'bold' }}
                            }},
                            legend: {{
                                display: true,
                                position: 'top'
                            }}
                        }},
                        scales: {{
                            x: {{
                                type: 'time',
                                time: {{
                                    displayFormats: {{
                                        minute: 'HH:mm',
                                        hour: 'MM/DD HH:mm'
                                    }}
                                }},
                                title: {{
                                    display: true,
                                    text: 'Timestamp'
                                }}
                            }},
                            y: {{
                                title: {{
                                    display: true,
                                    text: 'Value'
                                }}
                            }}
                        }},
                        interaction: {{
                            intersect: false,
                            mode: 'index'
                        }}
                    }}
                }});
            }}
            
            // Auto-refresh every 30 seconds (but skip if user is interacting with plots)
            let refreshTimer = setTimeout(function() {{
                if (!document.getElementById('seriesSelect').value) {{
                    location.reload();
                }}
            }}, 30000);
        </script>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 Anomaly Detection System</h1>
                <p>Real-time Monitoring Dashboard</p>
                <p class="timestamp">Last updated: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            </div>
            
            <!-- Key Metrics -->
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{total_models}</div>
                    <div class="metric-label">Active Models</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{predictions_current_hour}</div>
                    <div class="metric-label">Current Hour</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{total_predictions_today}</div>
                    <div class="metric-label">Predictions (24h)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{avg_predictions_per_hour:.1f}</div>
                    <div class="metric-label">Avg/Hour</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{current_rps_estimate:.3f}</div>
                    <div class="metric-label">RPS Estimate</div>
                </div>
            </div>
            
            <!-- System Health -->
            <div class="section">
                <h2>🏥 System Health</h2>
                <div class="service-grid">
    """
    
    for service in system_health:
        if isinstance(service, dict):
            status_class = f"status-{service['status'].lower()}"
            html_content += f"""
                    <div class="service-card">
                        <h3>{service['service']} Service</h3>
                        <div class="service-status {status_class}">{service['status']}</div>
                        <p><small>{service.get('details', 'No details available')}</small></p>
                    </div>
            """
    
    html_content += """
                </div>
            </div>
            
            <!-- Recent Models -->
            <div class="section">
                <h2>🧠 Recent Models</h2>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Series ID</th>
                            <th>Version</th>
                            <th>Threshold</th>
                            <th>Created</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    for model in recent_models:
        created_dt = datetime.fromtimestamp(model.created_at, tz=timezone.utc)
        html_content += f"""
                        <tr>
                            <td><strong>{model.series_id}</strong></td>
                            <td>{model.model_version}</td>
                            <td>{model.threshold}</td>
                            <td class="timestamp">{created_dt.strftime('%Y-%m-%d %H:%M')}</td>
                            <td><span class="status-healthy service-status">Active</span></td>
                        </tr>
        """
    
    html_content += """
                    </tbody>
                </table>
            </div>
            
            <!-- Recent Predictions -->
            <div class="section">
                <h2>🔍 Recent Predictions</h2>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Series ID</th>
                            <th>Value</th>
                            <th>Prediction</th>
                            <th>Model Version</th>
                            <th>Timestamp</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    for pred in recent_predictions:
        prediction_class = "prediction-true" if pred.prediction else "prediction-false"
        prediction_text = "ANOMALY" if pred.prediction else "NORMAL"
        created_dt = datetime.fromtimestamp(pred.created_at, tz=timezone.utc)
        html_content += f"""
                        <tr>
                            <td><strong>{pred.series_id}</strong></td>
                            <td>{pred.value:.2f}</td>
                            <td class="{prediction_class}">{prediction_text}</td>
                            <td>{pred.model_version}</td>
                            <td class="timestamp">{created_dt.strftime('%Y-%m-%d %H:%M:%S')}</td>
                        </tr>
        """
    
    html_content += f"""
                    </tbody>
                </table>
            </div>
            
            <!-- Most Used Models Section -->
            <div class="section">
                <h2>🏆 Most Used Models (24h)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Series ID</th>
                            <th>Version</th>
                            <th>Usage Count</th>
                            <th>Usage %</th>
                        </tr>
                    </thead>
                    <tbody>"""
    
    # Add most used models to HTML
    for idx, model in enumerate(most_used_models[:5], 1):
        usage_percentage = (model.usage_count / total_predictions_today * 100) if total_predictions_today > 0 else 0
        html_content += f"""
                        <tr>
                            <td>{idx}</td>
                            <td>{model.series_id}</td>
                            <td>{model.model_version}</td>
                            <td>{model.usage_count}</td>
                            <td>{usage_percentage:.1f}%</td>
                        </tr>"""
    
    if not most_used_models:
        html_content += """
                        <tr>
                            <td colspan="5" class="no-data">No prediction data available for the last 24h</td>
                        </tr>"""
    
    html_content += """
                    </tbody>
                </table>
            </div>
            
            <!-- API Links Section -->
            <div class="section">
                <h2>🔗 Metrics API Endpoints</h2>
                <div class="api-links">
                    <a href="/metrics/throughput" target="_blank">📊 Throughput Metrics</a>
                    <a href="/metrics/model-usage" target="_blank">🏆 Model Usage</a>
                    <a href="/models" target="_blank">📋 All Models</a>
                    <a href="/api-docs" target="_blank">📖 API Documentation</a>
                </div>
            </div>
            
            <!-- Interactive Plot Section -->
            <div class="section">
                <h2>📈 Interactive Time Series Plot</h2>
                <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.08); margin-bottom: 20px;">
                    <div style="display: flex; gap: 20px; margin-bottom: 20px; align-items: end;">
                        <div style="flex: 1;">
                            <label for="seriesSelect" style="display: block; margin-bottom: 5px; font-weight: 600; color: #2c3e50;">Series ID:</label>
                            <select id="seriesSelect" style="width: 100%; padding: 10px; border: 2px solid #ecf0f1; border-radius: 5px; font-size: 16px;">
                                <option value="">Select a series...</option>
                            </select>
                        </div>
                        <div style="flex: 1;">
                            <label for="versionSelect" style="display: block; margin-bottom: 5px; font-weight: 600; color: #2c3e50;">Version:</label>
                            <select id="versionSelect" style="width: 100%; padding: 10px; border: 2px solid #ecf0f1; border-radius: 5px; font-size: 16px;" disabled>
                                <option value="">Select version...</option>
                            </select>
                        </div>
                        <div>
                            <button id="plotButton" style="padding: 10px 20px; background: #3498db; color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; font-weight: 600;" disabled>Plot Data</button>
                        </div>
                    </div>
                    <div id="plotContainer" style="width: 100%; height: 400px; border: 2px solid #ecf0f1; border-radius: 5px; display: flex; align-items: center; justify-content: center; background: #f8f9fa; color: #7f8c8d; font-style: italic;">
                        Select a series and version to display the plot
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return Response(content=html_content, media_type="text/html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)