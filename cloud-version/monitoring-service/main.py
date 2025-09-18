"""
Monitoring Service - Cloud Run version
Serviço de monitoramento para métricas de latência, uso de modelos e throughput
"""
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse
import sys
import os
import httpx
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

# Adicionar shared ao path
sys.path.append('/app/shared')
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from bigquery_client import BigQueryClient

app = FastAPI(title="Anomaly Detection Monitoring Service - Cloud")

# URLs dos outros serviços (definidas via env vars)
TRAINING_SERVICE_URL = os.getenv("TRAINING_SERVICE_URL", "http://localhost:8080")
INFERENCE_SERVICE_URL = os.getenv("INFERENCE_SERVICE_URL", "http://localhost:8081")

# Cliente BigQuery global
bq_client = None

@app.on_event("startup")
async def startup_event():
    """Inicializar BigQuery na startup"""
    global bq_client
    try:
        bq_client = BigQueryClient()
        print("✅ BigQuery client initialized")
    except Exception as e:
        print(f"⚠️ BigQuery initialization failed: {e}")
        bq_client = None

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "anomaly-detection-monitoring",
        "status": "healthy",
        "version": "cloud-v1",
        "bigquery_connected": bq_client is not None,
        "endpoints": {
            "dashboard": "/dashboard",
            "metrics": "/metrics",
            "health": "/healthcheck"
        }
    }

@app.get("/healthcheck")
async def healthcheck():
    """Detailed health check with system metrics"""
    try:
        if not bq_client:
            raise HTTPException(status_code=503, detail="BigQuery not available")
        
        # Métricas básicas do sistema
        total_models = len(await get_active_models())
        recent_predictions = await get_recent_predictions_count(hours=1)
        
        return {
            "service": "monitoring",
            "status": "healthy",
            "bigquery_status": "connected",
            "system_metrics": {
                "active_models": total_models,
                "predictions_last_hour": recent_predictions,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            "ready": True
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.get("/metrics/latency")
async def get_latency_metrics(hours: int = 24) -> Dict[str, Any]:
    """Métricas de latência dos serviços"""
    try:
        if not bq_client:
            raise HTTPException(status_code=503, detail="BigQuery not available")
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Query para métricas de latência
        query = f"""
        SELECT 
            AVG(inference_latency_ms) as avg_inference_latency,
            PERCENTILE_CONT(inference_latency_ms, 0.5) OVER() as p50_inference_latency,
            PERCENTILE_CONT(inference_latency_ms, 0.95) OVER() as p95_inference_latency,
            PERCENTILE_CONT(inference_latency_ms, 0.99) OVER() as p99_inference_latency,
            AVG(total_latency_ms) as avg_total_latency,
            PERCENTILE_CONT(total_latency_ms, 0.95) OVER() as p95_total_latency,
            COUNT(*) as total_requests
        FROM `{bq_client.project_id}.{bq_client.dataset_id}.predictions`
        WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours} HOUR)
        AND inference_latency_ms IS NOT NULL
        LIMIT 1
        """
        
        results = bq_client.client.query(query).result()
        
        for row in results:
            return {
                "period_hours": hours,
                "inference_latency": {
                    "avg_ms": round(row.avg_inference_latency or 0, 2),
                    "p50_ms": round(row.p50_inference_latency or 0, 2),
                    "p95_ms": round(row.p95_inference_latency or 0, 2),
                    "p99_ms": round(row.p99_inference_latency or 0, 2)
                },
                "total_latency": {
                    "avg_ms": round(row.avg_total_latency or 0, 2),
                    "p95_ms": round(row.p95_total_latency or 0, 2)
                },
                "total_requests": row.total_requests,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        return {"message": "No data available for the specified period"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get latency metrics: {str(e)}")

@app.get("/metrics/throughput")
async def get_throughput_metrics(hours: int = 24) -> Dict[str, Any]:
    """Métricas de throughput (RPS, predições por hora)"""
    try:
        if not bq_client:
            raise HTTPException(status_code=503, detail="BigQuery not available")
        
        # Query para throughput por hora
        query = f"""
        WITH hourly_stats AS (
            SELECT 
                EXTRACT(HOUR FROM TIMESTAMP_SECONDS(created_at)) as hour,
                COUNT(*) as predictions_count,
                COUNT(DISTINCT series_id) as unique_series
            FROM `{bq_client.project_id}.{bq_client.dataset_id}.predictions`
            WHERE created_at >= UNIX_SECONDS(TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours} HOUR))
            GROUP BY hour
            ORDER BY hour DESC
        )
        SELECT 
            AVG(predictions_count) as avg_predictions_per_hour,
            MAX(predictions_count) as peak_predictions_per_hour,
            SUM(predictions_count) as total_predictions,
            AVG(unique_series) as avg_unique_series_per_hour
        FROM hourly_stats
        """
        
        results = bq_client.client.query(query).result()
        
        for row in results:
            avg_rps = (row.avg_predictions_per_hour or 0) / 3600
            peak_rps = (row.peak_predictions_per_hour or 0) / 3600
            
            return {
                "period_hours": hours,
                "throughput": {
                    "total_predictions": row.total_predictions or 0,
                    "avg_predictions_per_hour": round(row.avg_predictions_per_hour or 0, 2),
                    "peak_predictions_per_hour": row.peak_predictions_per_hour or 0,
                    "avg_rps": round(avg_rps, 4),
                    "peak_rps": round(peak_rps, 4),
                    "avg_unique_series_per_hour": round(row.avg_unique_series_per_hour or 0, 2)
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        return {"message": "No data available for the specified period"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get throughput metrics: {str(e)}")

@app.get("/metrics/model-usage")
async def get_model_usage_metrics(hours: int = 24, limit: int = 10) -> Dict[str, Any]:
    """Métricas de uso de modelos"""
    try:
        if not bq_client:
            raise HTTPException(status_code=503, detail="BigQuery not available")
        
        # Query para uso de modelos
        query = f"""
        WITH model_usage AS (
            SELECT 
                series_id,
                model_version,
                COUNT(*) as usage_count,
                AVG(total_latency_ms) as avg_latency,
                COUNT(CASE WHEN prediction = true THEN 1 END) as anomalies_detected,
                MAX(created_at) as last_used_timestamp
            FROM `{bq_client.project_id}.{bq_client.dataset_id}.predictions`
            WHERE created_at >= UNIX_SECONDS(TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours} HOUR))
            GROUP BY series_id, model_version
            ORDER BY usage_count DESC
            LIMIT {limit}
        ),
        total_predictions AS (
            SELECT COUNT(*) as total
            FROM `{bq_client.project_id}.{bq_client.dataset_id}.predictions`
            WHERE created_at >= UNIX_SECONDS(TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours} HOUR))
        )
        SELECT 
            m.*,
            t.total as total_predictions,
            ROUND((m.usage_count / t.total) * 100, 2) as usage_percentage
        FROM model_usage m
        CROSS JOIN total_predictions t
        ORDER BY m.usage_count DESC
        """
        
        results = bq_client.client.query(query).result()
        
        models = []
        total_predictions = 0
        
        for row in results:
            total_predictions = row.total_predictions
            models.append({
                "series_id": row.series_id,
                "model_version": row.model_version,
                "usage_count": row.usage_count,
                "usage_percentage": row.usage_percentage,
                "avg_latency_ms": round(row.avg_latency or 0, 2),
                "anomalies_detected": row.anomalies_detected,
                "anomaly_rate": round((row.anomalies_detected / row.usage_count) * 100, 2) if row.usage_count > 0 else 0,
                "last_used": datetime.fromtimestamp(row.last_used_timestamp, tz=timezone.utc).isoformat()
            })
        
        return {
            "period_hours": hours,
            "total_predictions": total_predictions,
            "most_used_models": models,
            "summary": {
                "unique_models": len(models),
                "avg_usage_per_model": round(total_predictions / len(models), 2) if models else 0
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get model usage metrics: {str(e)}")

async def get_active_models() -> List[Dict]:
    """Helper para buscar modelos ativos"""
    if not bq_client:
        return []
    
    try:
        query = f"""
        SELECT series_id, model_version, created_at
        FROM `{bq_client.project_id}.{bq_client.dataset_id}.trained_models`
        WHERE is_active = true
        ORDER BY created_at DESC
        """
        
        results = bq_client.client.query(query).result()
        return [{"series_id": row.series_id, "model_version": row.model_version} for row in results]
    except:
        return []

async def get_recent_predictions_count(hours: int = 1) -> int:
    """Helper para contar predições recentes"""
    if not bq_client:
        return 0
    
    try:
        query = f"""
        SELECT COUNT(*) as count
        FROM `{bq_client.project_id}.{bq_client.dataset_id}.predictions`
        WHERE created_at >= UNIX_SECONDS(TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours} HOUR))
        """
        
        results = bq_client.client.query(query).result()
        for row in results:
            return row.count
        return 0
    except:
        return 0

@app.get("/models")
async def get_models() -> Dict[str, Any]:
    """Retorna lista de modelos para o dashboard"""
    if not bq_client:
        return {"models": []}
    
    try:
        query = f"""
        SELECT series_id, model_version
        FROM `{bq_client.project_id}.{bq_client.dataset_id}.trained_models`
        WHERE is_active = true
        ORDER BY series_id, model_version
        """
        
        results = bq_client.client.query(query).result()
        
        # Agrupar por series_id
        models_dict = {}
        for row in results:
            if row.series_id not in models_dict:
                models_dict[row.series_id] = []
            models_dict[row.series_id].append(row.model_version)
        
        # Converter para lista
        models_list = []
        for series_id, versions in models_dict.items():
            models_list.append({
                "series_id": series_id,
                "versions": sorted(versions, reverse=True)
            })
        
        return {
            "models": models_list,
            "total_series": len(models_list)
        }
    except Exception as e:
        return {"models": [], "error": str(e)}

@app.get("/plot")
async def get_plot_data(series_id: str, version: str = None) -> Dict[str, Any]:
    """Retorna dados para plotting"""
    if not bq_client:
        raise HTTPException(status_code=503, detail="BigQuery not available")
    
    try:
        # Se version não especificada, pegar a mais recente
        if not version:
            query = f"""
            SELECT model_version
            FROM `{bq_client.project_id}.{bq_client.dataset_id}.trained_models`
            WHERE series_id = '{series_id}' AND is_active = true
            ORDER BY created_at DESC
            LIMIT 1
            """
            results = bq_client.client.query(query).result()
            for row in results:
                version = row.model_version
                break
            
            if not version:
                raise HTTPException(status_code=404, detail=f"No model found for series_id: {series_id}")
        
        # Buscar dados de treino
        query = f"""
        SELECT timestamps, values, model_version
        FROM `{bq_client.project_id}.{bq_client.dataset_id}.training_data`
        WHERE series_id = '{series_id}' AND model_version = '{version}'
        ORDER BY created_at DESC
        LIMIT 1
        """
        
        results = bq_client.client.query(query).result()
        
        for row in results:
            # BigQuery retorna arrays como listas Python
            timestamps = list(row[0]) if row[0] else []  # timestamps é primeira coluna
            values = list(row[1]) if row[1] else []       # values é segunda coluna
            
            # Criar data points
            data_points = []
            for ts, val in zip(timestamps, values):
                data_points.append({
                    "timestamp": ts,
                    "value": val,
                    "is_anomaly": False  # Training data não é anomalia
                })
            
            return {
                "series_id": series_id,
                "model_version": version,
                "data_points": data_points,
                "model_stats": {
                    "data_points_count": len(data_points),
                    "model_version": version,
                    "series_id": series_id
                }
            }
        
        raise HTTPException(status_code=404, detail=f"No training data found for {series_id} v{version}")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching plot data: {str(e)}")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Dashboard HTML com métricas em tempo real"""
    
    # Buscar métricas para o dashboard
    try:
        active_models = await get_active_models()
        predictions_1h = await get_recent_predictions_count(1)
        predictions_24h = await get_recent_predictions_count(24)
        
        # Calcular RPS estimado
        current_rps = round(predictions_1h / 3600, 4) if predictions_1h > 0 else 0
        
    except Exception as e:
        print(f"Error getting dashboard metrics: {e}")
        active_models = []
        predictions_1h = 0
        predictions_24h = 0
        current_rps = 0
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Anomaly Detection - Cloud Monitoring</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
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
                transition: transform 0.2s;
            }}
            .metric-card:hover {{
                transform: translateY(-5px);
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
            .api-section {{
                margin-top: 40px;
                background: white;
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.08);
            }}
            .api-section h2 {{
                color: #2c3e50;
                margin-bottom: 20px;
            }}
            .api-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
            }}
            .api-card {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                border-left: 4px solid #28a745;
            }}
            .api-card h3 {{
                margin: 0 0 10px 0;
                color: #28a745;
            }}
            .api-card code {{
                background: #e9ecef;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
            }}
            .refresh-info {{
                text-align: center;
                margin-top: 30px;
                color: #7f8c8d;
                font-style: italic;
            }}
            .plot-section {{
                margin-top: 40px;
                background: white;
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.08);
            }}
            .plot-controls {{
                display: flex;
                gap: 20px;
                margin-bottom: 20px;
                align-items: end;
            }}
            .plot-controls > div {{
                flex: 1;
            }}
            .plot-controls label {{
                display: block;
                margin-bottom: 5px;
                font-weight: 600;
                color: #2c3e50;
            }}
            .plot-controls select, .plot-controls button {{
                width: 100%;
                padding: 10px;
                border: 2px solid #ecf0f1;
                border-radius: 5px;
                font-size: 16px;
            }}
            .plot-controls button {{
                background: #3498db;
                color: white;
                border: none;
                cursor: pointer;
                font-weight: 600;
            }}
            .plot-controls button:disabled {{
                background: #bdc3c7;
                cursor: not-allowed;
            }}
            .plot-container {{
                width: 100%;
                height: 400px;
                border: 2px solid #ecf0f1;
                border-radius: 5px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #f8f9fa;
                color: #7f8c8d;
                font-style: italic;
            }}
        </style>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
        <script>
            let chart = null;
            
            // Auto refresh dashboard every 30 seconds (mas não se tiver gráfico ativo)
            setTimeout(() => {{
                if (!document.getElementById('seriesSelect').value) {{
                    location.reload();
                }}
            }}, 30000);
            
            // Carregar modelos quando página carrega
            document.addEventListener('DOMContentLoaded', function() {{
                console.log('Page loaded, initializing dashboard...');
                
                // Verificar se Chart.js foi carregado
                if (typeof Chart === 'undefined') {{
                    console.error('Chart.js not loaded!');
                    document.getElementById('plotContainer').innerHTML = 
                        '<div style="color: #e74c3c;">Chart.js library failed to load</div>';
                }} else {{
                    console.log('Chart.js loaded successfully');
                }}
                
                loadModels();
                setupEventListeners();
            }});
            
            // Carregar modelos disponíveis
            async function loadModels() {{
                try {{
                    const response = await fetch('/models');
                    const data = await response.json();
                    
                    const seriesSelect = document.getElementById('seriesSelect');
                    seriesSelect.innerHTML = '<option value="">Select a series...</option>';
                    
                    data.models.forEach(model => {{
                        const option = document.createElement('option');
                        option.value = model.series_id;
                        option.textContent = model.series_id;
                        option.dataset.versions = JSON.stringify(model.versions);
                        seriesSelect.appendChild(option);
                    }});
                }} catch (error) {{
                    console.error('Error loading models:', error);
                }}
            }}
            
            // Setup event listeners
            function setupEventListeners() {{
                const seriesSelect = document.getElementById('seriesSelect');
                const versionSelect = document.getElementById('versionSelect');
                const plotButton = document.getElementById('plotButton');
                
                // Quando série muda
                seriesSelect.addEventListener('change', function() {{
                    if (this.value && this.selectedIndex > 0) {{
                        const selectedOption = this.options[this.selectedIndex];
                        const versions = JSON.parse(selectedOption.dataset.versions || '[]');
                        
                        // Preencher versões
                        versionSelect.innerHTML = '<option value="">Latest version</option>';
                        versions.forEach(version => {{
                            const option = document.createElement('option');
                            option.value = version;
                            option.textContent = version;
                            versionSelect.appendChild(option);
                        }});
                        
                        versionSelect.disabled = false;
                        plotButton.disabled = false;
                    }} else {{
                        versionSelect.innerHTML = '<option value="">Select version...</option>';
                        versionSelect.disabled = true;
                        plotButton.disabled = true;
                    }}
                }});
                
                // Quando clica em plot
                plotButton.addEventListener('click', handlePlot);
            }}
            
            // Fazer plot
            async function handlePlot() {{
                const seriesId = document.getElementById('seriesSelect').value;
                const version = document.getElementById('versionSelect').value;
                
                if (!seriesId) {{
                    alert('Please select a series ID');
                    return;
                }}
                
                try {{
                    const plotButton = document.getElementById('plotButton');
                    plotButton.disabled = true;
                    plotButton.textContent = 'Loading...';
                    
                    let url = `/plot?series_id=${{seriesId}}`;
                    if (version) {{
                        url += `&version=${{version}}`;
                    }}
                    
                    console.log('Fetching plot data from:', url);
                    const response = await fetch(url);
                    console.log('Response status:', response.status);
                    
                    if (!response.ok) {{
                        const errorText = await response.text();
                        throw new Error(`HTTP ${{response.status}}: ${{errorText}}`);
                    }}
                    
                    const data = await response.json();
                    console.log('Plot data received:', data);
                    
                    if (data.data_points && data.data_points.length > 0) {{
                        createChart(data);
                    }} else {{
                        document.getElementById('plotContainer').innerHTML = 
                            '<div style="color: #e67e22; padding: 20px; text-align: center;">No data points found for this series</div>';
                    }}
                    
                }} catch (error) {{
                    console.error('Error:', error);
                    document.getElementById('plotContainer').innerHTML = 
                        '<div style="color: #e74c3c;">Error loading plot: ' + error.message + '</div>';
                }} finally {{
                    const plotButton = document.getElementById('plotButton');
                    plotButton.disabled = false;
                    plotButton.textContent = 'Plot Data';
                }}
            }}
            
            // Criar gráfico
            function createChart(data) {{
                console.log('Creating chart with data:', data);
                const container = document.getElementById('plotContainer');
                
                // Destruir gráfico anterior
                if (chart) {{
                    chart.destroy();
                }}
                
                // Criar canvas
                container.innerHTML = '<canvas id="timeSeriesChart" width="800" height="400"></canvas>';
                const ctx = document.getElementById('timeSeriesChart').getContext('2d');
                
                console.log('Data points:', data.data_points);
                
                chart = new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        datasets: [{{
                            label: `${{data.series_id}} (${{data.model_version}})`,
                            data: data.data_points.map(point => ({{
                                x: new Date(point.timestamp * 1000),
                                y: point.value
                            }})),
                            borderColor: '#3498db',
                            backgroundColor: 'rgba(52, 152, 219, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.1
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
                                display: true
                            }}
                        }},
                        scales: {{
                            x: {{
                                type: 'time',
                                time: {{
                                    unit: 'minute',
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
                        }}
                    }}
                }});
            }}
        </script>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>☁️ Anomaly Detection - Cloud Monitoring</h1>
                <p>Real-time monitoring dashboard for Google Cloud Run</p>
                <p style="color: #7f8c8d;">Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            </div>
            
            <!-- Key Metrics -->
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{len(active_models)}</div>
                    <div class="metric-label">Active Models</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{predictions_1h}</div>
                    <div class="metric-label">Predictions (1h)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{predictions_24h}</div>
                    <div class="metric-label">Predictions (24h)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{current_rps}</div>
                    <div class="metric-label">Current RPS</div>
                </div>
            </div>
            
            <!-- API Endpoints Section -->
            <div class="api-section">
                <h2>📊 Monitoring API Endpoints</h2>
                <div class="api-grid">
                    <div class="api-card">
                        <h3>Latency Metrics</h3>
                        <p><code>GET /metrics/latency</code></p>
                        <p>P95, P99, average latency for inference and total request time</p>
                    </div>
                    <div class="api-card">
                        <h3>Throughput Metrics</h3>
                        <p><code>GET /metrics/throughput</code></p>
                        <p>RPS, predictions per hour, peak throughput</p>
                    </div>
                    <div class="api-card">
                        <h3>Model Usage</h3>
                        <p><code>GET /metrics/model-usage</code></p>
                        <p>Most used models, usage percentage, anomaly rates</p>
                    </div>
                    <div class="api-card">
                        <h3>System Health</h3>
                        <p><code>GET /healthcheck</code></p>
                        <p>Service status, BigQuery connectivity, basic metrics</p>
                    </div>
                </div>
            </div>
            
            <!-- Interactive Plot Section -->
            <div class="plot-section">
                <h2>📈 Interactive Time Series Plot</h2>
                <div class="plot-controls">
                    <div>
                        <label for="seriesSelect">Series ID:</label>
                        <select id="seriesSelect">
                            <option value="">Select a series...</option>
                        </select>
                    </div>
                    <div>
                        <label for="versionSelect">Version:</label>
                        <select id="versionSelect" disabled>
                            <option value="">Select version...</option>
                        </select>
                    </div>
                    <div>
                        <button id="plotButton" disabled>Plot Data</button>
                    </div>
                </div>
                <div id="plotContainer" class="plot-container">
                    Select a series and version to display the plot
                </div>
            </div>
            
            <div class="refresh-info">
                🔄 Dashboard auto-refreshes every 30 seconds<br>
                🌐 Running on Google Cloud Run with BigQuery backend
            </div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 Starting Monitoring Service on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
