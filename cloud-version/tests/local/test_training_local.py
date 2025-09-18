#!/usr/bin/env python3
"""
Teste Local do Training Service
Testa treinamento usando datasets reais
"""
import sys
import os
import json
import time
import pandas as pd
from datetime import datetime, timezone
from typing import List, Tuple

# Adicionar shared ao path
sys.path.append('../../shared')

from bigquery_client import BigQueryClient
from models import SimpleAnomalyModel, TrainRequest

def load_dataset(dataset_name: str, limit: int = 100) -> Tuple[List[int], List[float]]:
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
        
        # Limitar dados
        df = df.head(limit)
        
        timestamps = df['unix_timestamp'].tolist()
        values = df['value'].tolist()
        
        print(f"✅ Loaded {len(timestamps)} points from {dataset_name}")
        print(f"   Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
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
        bq_client.ensure_dataset_exists()
        print("✅ BigQuery connection working")
        return bq_client
    except Exception as e:
        print(f"❌ BigQuery connection failed: {e}")
        return None

def test_training_logic(timestamps: List[int], values: List[float], series_id: str):
    """Testa lógica de treinamento local"""
    print(f"\n🧠 Testing Training Logic for {series_id}...")
    try:
        # Criar modelo
        model = SimpleAnomalyModel()
        
        # Treinar
        model.fit(values)
        
        # Verificar stats
        stats = model.get_stats()
        
        print(f"✅ Model trained successfully:")
        print(f"   - Mean: {stats['mean']:.4f}")
        print(f"   - Std: {stats['std']:.4f}")
        print(f"   - Threshold: {stats['threshold']}")
        print(f"   - Data points: {len(values)}")
        
        # Testar algumas predições
        test_values = values[:5]  # Primeiros 5 valores
        anomalies = [model.predict(val) for val in test_values]
        
        print(f"   - Test predictions: {sum(anomalies)}/{len(anomalies)} anomalies")
        
        return model, stats
        
    except Exception as e:
        print(f"❌ Training logic failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def test_training_persistence(bq_client: BigQueryClient, series_id: str, 
                            model_stats: dict, timestamps: List[int], values: List[float]):
    """Testa persistência no BigQuery"""
    print(f"\n💾 Testing Training Persistence for {series_id}...")
    try:
        version = f"v{int(time.time())}"
        
        # Salvar modelo
        success = bq_client.save_model(
            series_id=series_id,
            model_stats=model_stats,
            version=version,
            points_used=len(values)
        )
        
        if not success:
            print("❌ Failed to save model")
            return None
        
        # Salvar dados de treino
        success = bq_client.save_training_data(
            series_id=series_id,
            model_version=version,
            timestamps=timestamps,
            values=values
        )
        
        if not success:
            print("❌ Failed to save training data")
            return None
        
        print(f"✅ Model and training data saved:")
        print(f"   - Series: {series_id}")
        print(f"   - Version: {version}")
        print(f"   - Points: {len(values)}")
        
        return version
        
    except Exception as e:
        print(f"❌ Training persistence failed: {e}")
        return None

def test_training_api_format(timestamps: List[int], values: List[float], series_id: str):
    """Testa formato da API de treinamento"""
    print(f"\n📡 Testing Training API Format for {series_id}...")
    try:
        # Criar request
        train_request = TrainRequest(
            timestamps=timestamps,
            values=values,
            threshold=3.0
        )
        
        # Validar dados
        train_request.validate_data()
        
        print(f"✅ TrainRequest created:")
        print(f"   - Data points: {len(train_request.timestamps)}")
        print(f"   - Timestamps: {train_request.timestamps[:3]}")
        print(f"   - Values: {train_request.values[:3]}")
        print(f"   - Threshold: {train_request.threshold}")
        
        return train_request
        
    except Exception as e:
        print(f"❌ Training API format failed: {e}")
        return None

def test_dataset_training(dataset_name: str, limit: int = 50):
    """Testa treinamento completo com um dataset"""
    print(f"\n{'='*60}")
    print(f"🎯 TESTING TRAINING WITH {dataset_name.upper()}")
    print(f"{'='*60}")
    
    # 1. Carregar dataset
    timestamps, values = load_dataset(dataset_name, limit)
    if not timestamps:
        return False
    
    series_id = f"test_{dataset_name}"
    
    # 2. Testar lógica de treinamento
    model, stats = test_training_logic(timestamps, values, series_id)
    if not model:
        return False
    
    # 3. Testar formato da API
    train_request = test_training_api_format(timestamps, values, series_id)
    if not train_request:
        return False
    
    # 4. Testar BigQuery
    bq_client = test_bigquery_connection()
    if not bq_client:
        print("⚠️ Skipping BigQuery tests (not available)")
        return True
    
    # 5. Testar persistência
    version = test_training_persistence(bq_client, series_id, stats, timestamps, values)
    if not version:
        return False
    
    print(f"\n✅ {dataset_name.upper()} TRAINING: ALL TESTS PASSED!")
    return True

def main():
    """Executa todos os testes de treinamento"""
    print("🧪 Training Service Local Testing")
    print("=================================\n")
    
    # Datasets para testar
    datasets = [
        "machine_temperature",
        "synthetic_cpu_spikes", 
        "ambient_temperature_system_failure"
    ]
    
    results = {}
    
    for dataset in datasets:
        try:
            results[dataset] = test_dataset_training(dataset, limit=30)
        except Exception as e:
            print(f"❌ {dataset} failed: {e}")
            results[dataset] = False
    
    # Resumo
    print(f"\n{'='*60}")
    print("📊 TRAINING TESTS SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for dataset, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {dataset:<30} {status}")
    
    print(f"\n📈 Results: {passed}/{total} datasets passed")
    
    if passed == total:
        print("\n🎉 ALL TRAINING TESTS PASSED!")
        print("💡 Safe to deploy: make deploy-training")
        return True
    else:
        print(f"\n⚠️ {total-passed} tests failed. Fix issues before deploying.")
        return False

if __name__ == "__main__":
    success = main()
    
    print("\n📝 Quick commands:")
    print("   python test_training_local.py    # Test training service")
    print("   python test_inference_local.py   # Test inference service") 
    print("   python test_monitoring_local.py  # Test monitoring service")
    print("   make deploy-training             # Deploy when ready")
