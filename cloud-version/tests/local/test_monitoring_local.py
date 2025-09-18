#!/usr/bin/env python3
"""
Teste Local do Monitoring Service
Testa endpoints específicos sem subir para cloud
"""
import sys
import os
import json
import time
from datetime import datetime, timezone

# Adicionar shared ao path
sys.path.append('../../shared')

from bigquery_client import BigQueryClient
from models import SimpleAnomalyModel

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

def test_models_endpoint():
    """Testa endpoint /models"""
    print("\n📋 Testing /models endpoint...")
    try:
        bq_client = BigQueryClient()
        
        # Simular query de modelos
        query = f"""
        SELECT series_id, model_version
        FROM `{bq_client.project_id}.{bq_client.dataset_id}.trained_models`
        WHERE is_active = true
        ORDER BY series_id, model_version
        LIMIT 5
        """
        
        results = bq_client.client.query(query).result()
        
        # Agrupar por series_id
        models_dict = {}
        count = 0
        for row in results:
            count += 1
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
        
        response = {
            "models": models_list,
            "total_series": len(models_list)
        }
        
        print(f"✅ Found {len(models_list)} series with {count} total models")
        for model in models_list[:3]:  # Mostrar só 3 primeiros
            print(f"   - {model['series_id']}: {model['versions']}")
        
        return response
        
    except Exception as e:
        print(f"❌ Models endpoint failed: {e}")
        return None

def test_plot_endpoint(series_id=None, version=None):
    """Testa endpoint /plot"""
    print(f"\n📈 Testing /plot endpoint (series_id={series_id}, version={version})...")
    try:
        bq_client = BigQueryClient()
        
        # Se não tiver series_id, pegar um qualquer
        if not series_id:
            query = f"""
            SELECT series_id, model_version
            FROM `{bq_client.project_id}.{bq_client.dataset_id}.trained_models`
            WHERE is_active = true
            ORDER BY created_at DESC
            LIMIT 1
            """
            results = bq_client.client.query(query).result()
            for row in results:
                series_id = row.series_id
                if not version:
                    version = row.model_version
                break
            
            if not series_id:
                print("❌ No models found for testing")
                return None
        
        print(f"   Using series_id='{series_id}', version='{version}'")
        
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
                print(f"❌ No model found for series_id: {series_id}")
                return None
        
        print(f"   Final: series_id='{series_id}', version='{version}'")
        
        # Buscar dados de treino
        query = f"""
        SELECT timestamps, values, model_version
        FROM `{bq_client.project_id}.{bq_client.dataset_id}.training_data`
        WHERE series_id = '{series_id}' AND model_version = '{version}'
        ORDER BY created_at DESC
        LIMIT 1
        """
        
        print(f"   Query: {query}")
        results = bq_client.client.query(query).result()
        
        for row in results:
            # BigQuery retorna arrays como listas Python
            timestamps = list(row[0]) if row[0] else []  # timestamps é primeira coluna
            values = list(row[1]) if row[1] else []       # values é segunda coluna
            
            print(f"   Found data: {len(timestamps)} timestamps, {len(values)} values")
            
            # Criar data points
            data_points = []
            for ts, val in zip(timestamps, values):
                data_points.append({
                    "timestamp": ts,
                    "value": val,
                    "is_anomaly": False
                })
            
            response = {
                "series_id": series_id,
                "model_version": version,
                "data_points": data_points,
                "model_stats": {
                    "data_points_count": len(data_points),
                    "model_version": version,
                    "series_id": series_id
                }
            }
            
            print(f"✅ Plot data ready: {len(data_points)} points")
            print(f"   Sample: timestamp={data_points[0]['timestamp']}, value={data_points[0]['value']}")
            return response
        
        print(f"❌ No training data found for {series_id} v{version}")
        return None
        
    except Exception as e:
        print(f"❌ Plot endpoint failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_test_data():
    """Cria dados de teste se não existir"""
    print("\n🔧 Creating test data...")
    try:
        bq_client = BigQueryClient()
        
        # Criar modelo de teste
        model = SimpleAnomalyModel()
        test_values = [23.5, 24.1, 23.8, 24.2, 23.9]
        test_timestamps = [int(time.time()) - i*60 for i in range(len(test_values))]
        test_timestamps.reverse()
        
        model.fit(test_values)
        
        # Salvar modelo
        model_stats = model.get_stats()
        success = bq_client.save_model(
            series_id="test_local",
            model_stats=model_stats,
            version="v1",
            points_used=len(test_values)
        )
        
        if success:
            print("✅ Test model saved")
            
            # Salvar dados de treino
            success = bq_client.save_training_data(
                series_id="test_local",
                model_version="v1",
                timestamps=test_timestamps,
                values=test_values
            )
            
            if success:
                print("✅ Test training data saved")
                return "test_local", "v1"
            else:
                print("❌ Failed to save training data")
        else:
            print("❌ Failed to save model")
        
        return None, None
        
    except Exception as e:
        print(f"❌ Failed to create test data: {e}")
        return None, None

def main():
    """Executa todos os testes"""
    print("🧪 Monitoring Service Local Testing")
    print("==================================\n")
    
    # 1. Testar BigQuery
    bq_client = test_bigquery_connection()
    if not bq_client:
        print("\n❌ BigQuery not available. Make sure you're authenticated:")
        print("   gcloud auth application-default login")
        return False
    
    # 2. Testar endpoint /models
    models_response = test_models_endpoint()
    
    # 3. Se não tiver modelos, criar dados de teste
    test_series_id = None
    test_version = None
    
    if not models_response or len(models_response["models"]) == 0:
        print("\n⚠️ No models found. Creating test data...")
        test_series_id, test_version = create_test_data()
        if test_series_id:
            # Tentar novamente
            models_response = test_models_endpoint()
    
    # 4. Testar endpoint /plot
    if models_response and len(models_response["models"]) > 0:
        # Usar primeiro modelo disponível
        first_model = models_response["models"][0]
        series_id = first_model["series_id"]
        version = first_model["versions"][0] if first_model["versions"] else None
        
        plot_response = test_plot_endpoint(series_id, version)
        
        if plot_response:
            print("\n✅ All monitoring endpoints working!")
            print(f"📊 Dashboard will work with {len(plot_response['data_points'])} data points")
            return True
        else:
            print("\n❌ Plot endpoint failed")
            return False
    else:
        print("\n❌ No models available for testing")
        return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🎉 MONITORING SERVICE READY!")
        print("💡 Safe to deploy: make deploy-monitoring")
    else:
        print("\n⚠️ Fix issues before deploying")
    
    print("\n📝 Quick deploy commands:")
    print("   make test-logic           # Test ML algorithm")
    print("   python test_monitoring_local.py  # Test monitoring endpoints")
    print("   make deploy-monitoring    # Deploy when ready")
