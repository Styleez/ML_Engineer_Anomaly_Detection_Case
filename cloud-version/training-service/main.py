"""
Training Service - Cloud Run version
Versão simplificada para Google Cloud Run + BigQuery
"""
from fastapi import FastAPI, HTTPException
import sys
import os

# Adicionar shared ao path
sys.path.append('/app/shared')
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from models import TrainRequest, TrainResponse, SimpleAnomalyModel
from bigquery_client import BigQueryClient

app = FastAPI(title="Anomaly Detection Training Service - Cloud")

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
        "service": "anomaly-detection-training",
        "status": "healthy",
        "version": "cloud-v1",
        "bigquery_connected": bq_client is not None
    }

@app.get("/healthcheck")
async def healthcheck():
    """Detailed health check"""
    return {
        "service": "training",
        "status": "healthy",
        "bigquery_status": "connected" if bq_client else "disconnected",
        "ready": True
    }

@app.post("/fit/{series_id}")
async def fit_model(series_id: str, request: TrainRequest) -> TrainResponse:
    """
    Treinar modelo de detecção de anomalias
    
    - series_id: Identificador único da série temporal
    - request: Dados de treinamento (timestamps, values, threshold)
    """
    try:
        # Validar dados
        request.validate_data()
        
        # Criar e treinar modelo
        model = SimpleAnomalyModel(threshold=request.threshold)
        model.fit(request.values)
        
        # Gerar versão
        if bq_client:
            version = bq_client.get_next_version(series_id)
        else:
            version = "v1"  # Fallback para desenvolvimento local
        
        # Estatísticas do modelo
        model_stats = model.get_stats()
        model_stats["training_points"] = len(request.values)
        
        # Salvar no BigQuery
        if bq_client:
            success = bq_client.save_model(
                series_id=series_id,
                model_stats=model_stats,
                version=version,
                points_used=len(request.values)
            )
            
            if not success:
                raise HTTPException(status_code=500, detail="Failed to save model")
            
            # Salvar dados de treino
            bq_client.save_training_data(
                series_id=series_id,
                model_version=version,
                timestamps=request.timestamps,
                values=request.values
            )
        
        print(f"✅ Model trained: {series_id} {version}")
        
        return TrainResponse(
            series_id=series_id,
            version=version,
            points_used=len(request.values),
            model_stats=model_stats
        )
        
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        print(f"❌ Training error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 Starting Training Service on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
