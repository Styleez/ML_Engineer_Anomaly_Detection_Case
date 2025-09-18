"""
Inference Service - Cloud Run version  
Versão simplificada para Google Cloud Run + BigQuery
"""
from fastapi import FastAPI, HTTPException
import sys
import os
import time

# Adicionar shared ao path
sys.path.append('/app/shared')
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from models import PredictRequest, PredictResponse, SimpleAnomalyModel
from bigquery_client import BigQueryClient

app = FastAPI(title="Anomaly Detection Inference Service - Cloud")

# Cliente BigQuery global
bq_client = None

@app.on_event("startup")
async def startup_event():
    """Inicializar BigQuery na startup"""
    global bq_client
    try:
        bq_client = BigQueryClient()
        bq_client.ensure_tables_exist()
        print("✅ BigQuery tables initialized")
    except Exception as e:
        print(f"⚠️ BigQuery initialization failed: {e}")
        # Continue sem BigQuery para desenvolvimento local
        bq_client = None

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "anomaly-detection-inference",
        "status": "healthy", 
        "version": "cloud-v1",
        "bigquery_connected": bq_client is not None
    }

@app.get("/healthcheck")
async def healthcheck():
    """Detailed health check"""
    return {
        "service": "inference",
        "status": "healthy",
        "bigquery_status": "connected" if bq_client else "disconnected",
        "ready": True
    }

@app.post("/predict/{series_id}")
async def predict(series_id: str, request: PredictRequest, version: str = None) -> PredictResponse:
    """
    Fazer predição de anomalia
    
    - series_id: Identificador da série temporal
    - request: Dados para predição (timestamp, value)
    - version: Versão específica do modelo (opcional)
    """
    start_time = time.time()  # Definir start_time no início
    
    try:
        if not bq_client:
            raise HTTPException(status_code=503, detail="BigQuery not available")
        
        # Buscar modelo ativo
        model_data = bq_client.get_active_model(series_id)
        
        if not model_data:
            raise HTTPException(
                status_code=404, 
                detail=f"No trained model found for series_id: {series_id}"
            )
        
        # Recriar modelo com parâmetros salvos
        model = SimpleAnomalyModel(threshold=model_data["threshold"])
        model.mean = model_data["mean"]
        model.std = model_data["std"] 
        model.is_trained = True
        
        # Fazer predição
        is_anomaly = model.predict(request.value)
        
        # Calcular latência total
        total_latency_ms = (time.time() - start_time) * 1000
        
        # Log da predição com métricas de latência
        if bq_client:
            bq_client.log_prediction(
                series_id=series_id,
                timestamp=int(request.timestamp),
                value=request.value,
                prediction=is_anomaly,
                model_version=model_data["model_version"],
                inference_latency_ms=None,  # Será calculado dentro do método predict se necessário
                total_latency_ms=total_latency_ms
            )
        
        print(f"🔍 Prediction: {series_id} value={request.value} anomaly={is_anomaly}")
        
        return PredictResponse(
            anomaly=is_anomaly,
            model_version=model_data["model_version"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 Starting Inference Service on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
