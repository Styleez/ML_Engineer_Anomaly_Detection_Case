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
        db.execute("SELECT 1")
        return {
            "status": "ok", 
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
        query = query.filter(TrainingData.version == version)
    else:
        # Get the most recent version for the series_id
        latest_version_subquery = db.query(
            TrainingData.version,
            TrainingData.created_at
        ).filter(
            TrainingData.series_id == series_id
        ).order_by(
            TrainingData.created_at.desc()
        ).limit(1).subquery()

        latest_version_data = db.query(latest_version_subquery).first()

        if not latest_version_data:
            raise HTTPException(status_code=404, detail=f"No training data found for series_id: {series_id}")

        version = latest_version_data.version
        query = query.filter(TrainingData.version == version)

    training_data_records = query.order_by(TrainingData.timestamp.asc()).all()

    if not training_data_records:
        raise HTTPException(status_code=404, detail=f"No training data found for series_id: {series_id} and version: {version}")

    plot_data_points = [
        PlotDataPoint(
            timestamp=record.timestamp,
            value=record.value,
            is_anomaly=False  # Training data itself is not marked as anomaly
        )
        for record in training_data_records
    ]

    return AnomalyPlotResponse(
        series_id=series_id,
        model_version=version,
        data=plot_data_points
    )

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
        </style>
        <script>
            // Auto-refresh every 30 seconds
            setTimeout(function() {{
                location.reload();
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
                    <div class="metric-value">{total_predictions_hour}</div>
                    <div class="metric-label">Predictions (1h)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{total_predictions_today}</div>
                    <div class="metric-label">Predictions (24h)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{len(system_health)}</div>
                    <div class="metric-label">Services</div>
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
            
            <!-- API Links -->
            <div class="api-links">
                <h2>🔗 API Endpoints</h2>
                <a href="/plot?series_id=test_sensor">📊 Sample Plot</a>
                <a href="/healthcheck">🏥 Health Check</a>
                <a href="{TRAINING_SERVICE_URL}/docs" target="_blank">📚 Training API Docs</a>
                <a href="{INFERENCE_SERVICE_URL}/docs" target="_blank">⚡ Inference API Docs</a>
            </div>
            
            <div class="refresh-info">
                <p>⏱️ Dashboard auto-refreshes every 30 seconds</p>
                <p>📊 Monitoring {total_models} active models across {len(system_health)} services</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return Response(content=html_content, media_type="text/html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)