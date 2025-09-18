#!/usr/bin/env python3
"""
Teste para gerar predições e popular métricas do dashboard
"""
import sys
import os
import time
import asyncio
import httpx
from datetime import datetime

# Adicionar shared ao path
sys.path.append('../../shared')

async def test_predict_with_deployed_service():
    """Testa predições com serviço deployado para gerar métricas"""
    
    # URLs dos serviços (ajustar conforme necessário)
    TRAINING_URL = "https://anomaly-training-9266052327.us-central1.run.app"
    INFERENCE_URL = "https://anomaly-inference-9266052327.us-central1.run.app"
    
    print(f"🔗 Training URL: {TRAINING_URL}")
    print(f"🔗 Inference URL: {INFERENCE_URL}")
    
    print("🔍 Testing predictions with deployed services...")
    print("===========================================\n")
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=30.0)) as client:
        # 0. Verificar se serviços estão disponíveis
        print("0️⃣ Checking service health...")
        
        try:
            training_health = await client.get(f"{TRAINING_URL}/healthcheck")
            inference_health = await client.get(f"{INFERENCE_URL}/healthcheck")
            
            if training_health.status_code != 200:
                print(f"   ❌ Training service unhealthy: {training_health.status_code}")
                return False
                
            if inference_health.status_code != 200:
                print(f"   ❌ Inference service unhealthy: {inference_health.status_code}")
                return False
                
            print(f"   ✅ Both services are healthy")
            
        except Exception as e:
            print(f"   ❌ Health check failed: {e}")
            return False
        
        # 1. Primeiro treinar um modelo
        print("\n1️⃣ Training a model...")
        
        train_data = {
            "timestamps": [
                int(time.time()) - 300,  # 5 min atrás
                int(time.time()) - 240,  # 4 min atrás
                int(time.time()) - 180,  # 3 min atrás
                int(time.time()) - 120,  # 2 min atrás
                int(time.time()) - 60,   # 1 min atrás
                int(time.time()),        # agora
            ],
            "values": [23.5, 24.1, 23.8, 24.2, 23.9, 24.0],
            "threshold": 3.0
        }
        
        try:
            train_response = await client.post(
                f"{TRAINING_URL}/fit/test_live_sensor",
                json=train_data
            )
            
            if train_response.status_code == 200:
                train_result = train_response.json()
                print(f"   ✅ Model trained: {train_result['series_id']} v{train_result['version']}")
                model_version = train_result['version']
            else:
                print(f"   ❌ Training failed: {train_response.status_code} - {train_response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Training error: {e}")
            return False
        
        # 2. Fazer várias predições para gerar métricas
        print("\n2️⃣ Making predictions...")
        
        # Valores normais e algumas anomalias
        test_values = [
            23.7,  # normal
            24.3,  # normal  
            23.2,  # normal
            30.0,  # anomalia!
            23.9,  # normal
            18.0,  # anomalia!
            24.1,  # normal
            35.5,  # anomalia!
            23.6,  # normal
            24.0,  # normal
        ]
        
        prediction_count = 0
        anomaly_count = 0
        
        for i, value in enumerate(test_values):
            try:
                predict_data = {
                    "timestamp": str(int(time.time()) + i),
                    "value": value
                }
                
                predict_response = await client.post(
                    f"{INFERENCE_URL}/predict/test_live_sensor",
                    json=predict_data
                )
                
                if predict_response.status_code == 200:
                    result = predict_response.json()
                    is_anomaly = result['anomaly']
                    
                    status = "🚨 ANOMALY" if is_anomaly else "✅ normal"
                    print(f"   Value {value:5.1f} → {status}")
                    
                    prediction_count += 1
                    if is_anomaly:
                        anomaly_count += 1
                        
                    # Esperar um pouco entre predições
                    await asyncio.sleep(0.5)
                    
                else:
                    print(f"   ❌ Prediction failed for {value}: {predict_response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Prediction error for {value}: {e}")
        
        print(f"\n📊 Results:")
        print(f"   • Total predictions: {prediction_count}")
        print(f"   • Anomalies detected: {anomaly_count}")
        if prediction_count > 0:
            print(f"   • Anomaly rate: {(anomaly_count/prediction_count)*100:.1f}%")
        else:
            print(f"   • Anomaly rate: N/A (no predictions)")
        
        if prediction_count > 0:
            print("\n✅ Predictions completed! Dashboard metrics should now show data.")
            print(f"💡 Check dashboard for updated metrics")
            return True
        else:
            print("\n❌ No predictions were successful")
            return False

async def main():
    """Executa teste de predições"""
    print("🧪 Prediction Generation Test")
    print("============================\n")
    
    success = await test_predict_with_deployed_service()
    
    if success:
        print("\n🎉 SUCCESS! Metrics generated.")
        print("\n📝 Next steps:")
        print("   1. Refresh the monitoring dashboard")
        print("   2. Check 'PREDICTIONS (1H)' metric")
        print("   3. Try plotting 'test_live_sensor' data")
    else:
        print("\n⚠️ Failed to generate predictions")
        print("   • Check if services are deployed")
        print("   • Verify URLs in this script")

if __name__ == "__main__":
    asyncio.run(main())
