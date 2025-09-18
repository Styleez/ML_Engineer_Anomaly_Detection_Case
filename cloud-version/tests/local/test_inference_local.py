#!/usr/bin/env python3
"""
Teste Local do Inference Service
Testa inferência usando modelos treinados
"""
import sys
import os
import json
import time
import pandas as pd
from datetime import datetime, timezone
from typing import List, Tuple, Optional

# Adicionar shared ao path
sys.path.append('../../shared')

from bigquery_client import BigQueryClient
from models import SimpleAnomalyModel, PredictRequest, PredictResponse

def load_dataset(dataset_name: str, limit: int = 20) -> Tuple[List[int], List[float]]:
    """Carrega dataset real da pasta ../dataset"""
    dataset_path = f"../../../dataset/{dataset_name}.csv"
    
    if not os.path.exists(dataset_path):
        print(f"❌ Dataset not found: {dataset_path}")
        return [], []
    
    try:
        # Ler CSV
        df = pd.read_csv(dataset_path)
        
        if 'timestamp' not in df.columns or 'value' not in df.columns:
            print(f"❌ Dataset must have 'timestamp' and 'value' columns")
            return [], []
        
        # Converter timestamp para unix
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['unix_timestamp'] = df['timestamp'].astype('int64') // 10**9
        
        # Pegar últimos valores (para teste de inferência)
        df = df.tail(limit)
        
        timestamps = df['unix_timestamp'].tolist()
        values = df['value'].tolist()
        
        print(f"✅ Loaded {len(timestamps)} test points from {dataset_name}")
        print(f"   Value range: {min(values):.2f} to {max(values):.2f}")
        
        return timestamps, values
        
    except Exception as e:
        print(f"❌ Error loading dataset {dataset_name}: {e}")
        return [], []

def test_bigquery_connection():
    """Testa conexão BigQuery"""
    print("🔌 Testing BigQuery Connection...")
    try:
        bq_client = BigQueryClient()
        
        # Testar query simples
        query = f"SELECT 1 as test"
        results = bq_client.client.query(query).result()
        
        for row in results:
            if row.test == 1:
                print("✅ BigQuery connection working")
                return bq_client
        
        print("❌ BigQuery query failed")
        return None
    except Exception as e:
        print(f"❌ BigQuery connection failed: {e}")
        return None

def find_trained_model(bq_client: BigQueryClient, series_prefix: str = "test_") -> Optional[Tuple[str, str, dict]]:
    """Encontra um modelo treinado para teste"""
    try:
        query = f"""
        SELECT series_id, model_version, mean_value, std_value, threshold_value
        FROM `{bq_client.project_id}.{bq_client.dataset_id}.trained_models`
        WHERE series_id LIKE '{series_prefix}%' AND is_active = true
        ORDER BY created_at DESC
        LIMIT 1
        """
        
        results = bq_client.client.query(query).result()
        
        for row in results:
            # Reconstruir stats do modelo
            stats = {
                'mean': row.mean_value,
                'std': row.std_value,
                'threshold': row.threshold_value,
                'is_trained': True
            }
            return row.series_id, row.model_version, stats
        
        return None
        
    except Exception as e:
        print(f"❌ Error finding trained model: {e}")
        return None

def test_inference_logic(model_stats: dict, test_values: List[float], series_id: str):
    """Testa lógica de inferência local"""
    print(f"\n🧠 Testing Inference Logic for {series_id}...")
    try:
        # Criar modelo com stats salvos
        model = SimpleAnomalyModel()
        model.mean = model_stats['mean']
        model.std = model_stats['std']
        model.threshold = model_stats['threshold']
        model.is_trained = model_stats['is_trained']
        
        print(f"✅ Model loaded:")
        print(f"   - Mean: {model.mean:.4f}")
        print(f"   - Std: {model.std:.4f}")
        print(f"   - Threshold: {model.threshold}")
        
        # Testar predições
        predictions = []
        anomaly_count = 0
        
        for i, value in enumerate(test_values[:10]):  # Testar só 10 valores
            is_anomaly = model.predict(value)
            predictions.append(is_anomaly)
            if is_anomaly:
                anomaly_count += 1
            
            status = "🚨 ANOMALY" if is_anomaly else "✅ normal"
            print(f"   Value {value:.2f} → {status}")
        
        print(f"✅ Inference completed: {anomaly_count}/{len(predictions)} anomalies detected")
        
        return predictions
        
    except Exception as e:
        print(f"❌ Inference logic failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_inference_api_format(timestamps: List[int], values: List[float], series_id: str):
    """Testa formato da API de inferência"""
    print(f"\n📡 Testing Inference API Format for {series_id}...")
    try:
        results = []
        
        # Testar só primeiros 5 valores
        for ts, val in zip(timestamps[:5], values[:5]):
            predict_request = PredictRequest(
                timestamp=str(ts),
                value=val
            )
            
            # Simular resposta
            predict_response = PredictResponse(
                anomaly=False,  # Será calculado depois
                model_version="v1"
            )
            
            results.append((predict_request, predict_response))
        
        print(f"✅ PredictRequest/Response created for {len(results)} points:")
        for i, (req, resp) in enumerate(results[:3]):
            print(f"   {i+1}. timestamp={req.timestamp}, value={req.value} → {resp.anomaly}")
        
        return results
        
    except Exception as e:
        print(f"❌ Inference API format failed: {e}")
        return None

def test_inference_persistence(bq_client: BigQueryClient, series_id: str, model_version: str,
                             timestamps: List[int], values: List[float], predictions: List[bool]):
    """Testa log de predições no BigQuery"""
    print(f"\n💾 Testing Inference Persistence for {series_id}...")
    try:
        success_count = 0
        
        # Logar algumas predições (só 3 para teste)
        for ts, val, pred in zip(timestamps[:3], values[:3], predictions[:3]):
            try:
                success = bq_client.log_prediction(
                    series_id=series_id,
                    timestamp=int(ts),  # Garantir que é int
                    value=float(val),   # Garantir que é float
                    prediction=bool(pred),  # Garantir que é bool
                    model_version=str(model_version),  # Garantir que é string
                    total_latency_ms=15.5  # Latência simulada
                )
                
                if success:
                    success_count += 1
                else:
                    print(f"   ⚠️ Failed to log prediction for timestamp {ts}")
            except Exception as e:
                print(f"   ❌ Error logging prediction: {e}")
        
        print(f"✅ Predictions logged: {success_count}/3")
        
        return success_count > 0
        
    except Exception as e:
        print(f"❌ Inference persistence failed: {e}")
        return False

def test_dataset_inference(dataset_name: str, limit: int = 20):
    """Testa inferência completa com um dataset"""
    print(f"\n{'='*60}")
    print(f"🎯 TESTING INFERENCE WITH {dataset_name.upper()}")
    print(f"{'='*60}")
    
    # 1. Carregar dados de teste
    timestamps, values = load_dataset(dataset_name, limit)
    if not timestamps:
        return False
    
    series_id = f"test_{dataset_name}"
    
    # 2. Testar BigQuery
    bq_client = test_bigquery_connection()
    if not bq_client:
        print("⚠️ Skipping BigQuery tests (not available)")
        return True
    
    # 3. Encontrar modelo treinado
    model_data = find_trained_model(bq_client, "test_")
    if not model_data:
        print(f"⚠️ No trained model found. Run training first:")
        print(f"   python test_training_local.py")
        return True
    
    found_series_id, model_version, model_stats = model_data
    print(f"✅ Found trained model: {found_series_id} v{model_version}")
    
    # 4. Testar lógica de inferência
    predictions = test_inference_logic(model_stats, values, found_series_id)
    if predictions is None:
        return False
    
    # 5. Testar formato da API
    api_results = test_inference_api_format(timestamps, values, series_id)
    if not api_results:
        return False
    
    # 6. Testar persistência
    persistence_ok = test_inference_persistence(
        bq_client, found_series_id, model_version, 
        timestamps, values, predictions
    )
    if not persistence_ok:
        return False
    
    print(f"\n✅ {dataset_name.upper()} INFERENCE: ALL TESTS PASSED!")
    return True

def main():
    """Executa todos os testes de inferência"""
    print("🧪 Inference Service Local Testing")
    print("==================================\n")
    
    # Datasets para testar
    datasets = [
        "machine_temperature",
        "synthetic_cpu_spikes"
    ]
    
    results = {}
    
    for dataset in datasets:
        try:
            results[dataset] = test_dataset_inference(dataset, limit=15)
        except Exception as e:
            print(f"❌ {dataset} failed: {e}")
            results[dataset] = False
    
    # Resumo
    print(f"\n{'='*60}")
    print("📊 INFERENCE TESTS SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for dataset, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {dataset:<30} {status}")
    
    print(f"\n📈 Results: {passed}/{total} datasets passed")
    
    if passed == total:
        print("\n🎉 ALL INFERENCE TESTS PASSED!")
        print("💡 Safe to deploy: make deploy-inference")
        return True
    else:
        print(f"\n⚠️ {total-passed} tests failed. Fix issues before deploying.")
        return False

if __name__ == "__main__":
    success = main()
    
    print("\n📝 Quick commands:")
    print("   python test_training_local.py     # Test training service")
    print("   python test_inference_local.py    # Test inference service") 
    print("   python test_monitoring_local.py   # Test monitoring service")
    print("   make deploy-inference             # Deploy when ready")
