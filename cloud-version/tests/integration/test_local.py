#!/usr/bin/env python3
"""
Teste local para a versão cloud (sem BigQuery)
"""
import requests
import json
import time

# URLs para teste local
TRAINING_URL = "http://localhost:8080"
INFERENCE_URL = "http://localhost:8081"  # Assumindo portas diferentes localmente

def test_local_services():
    """Teste dos serviços localmente"""
    
    print("🧪 Testing Local Cloud Services")
    print("=" * 50)
    
    # 1. Health checks
    print("\n1️⃣ Health Checks:")
    try:
        response = requests.get(f"{TRAINING_URL}/healthcheck", timeout=5)
        print(f"✅ Training Service: {response.json()}")
    except Exception as e:
        print(f"❌ Training Service: {e}")
    
    try:
        response = requests.get(f"{INFERENCE_URL}/healthcheck", timeout=5)
        print(f"✅ Inference Service: {response.json()}")
    except Exception as e:
        print(f"❌ Inference Service: {e}")
    
    # 2. Treinar modelo
    print("\n2️⃣ Training Model:")
    training_data = {
        "timestamps": [1609459200, 1609459260, 1609459320, 1609459380, 1609459440],
        "values": [23.5, 24.1, 23.8, 24.0, 23.9],
        "threshold": 3.0
    }
    
    try:
        response = requests.post(
            f"{TRAINING_URL}/fit/test_sensor",
            json=training_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Model trained: {result}")
            model_version = result.get("version", "v1")
        else:
            print(f"❌ Training failed: {response.status_code} - {response.text}")
            return
            
    except Exception as e:
        print(f"❌ Training error: {e}")
        return
    
    # 3. Fazer predições
    print("\n3️⃣ Making Predictions:")
    
    test_cases = [
        {"value": 24.0, "expected": "normal"},
        {"value": 30.0, "expected": "anomaly"}, 
        {"value": 15.0, "expected": "anomaly"},
        {"value": 23.8, "expected": "normal"}
    ]
    
    for i, case in enumerate(test_cases):
        prediction_data = {
            "timestamp": str(1609459500 + i * 60),
            "value": case["value"]
        }
        
        try:
            response = requests.post(
                f"{INFERENCE_URL}/predict/test_sensor",
                json=prediction_data,
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                anomaly = "anomaly" if result["anomaly"] else "normal"
                status = "✅" if (case["expected"] == "anomaly") == result["anomaly"] else "⚠️"
                print(f"{status} Value {case['value']}: {anomaly} (expected: {case['expected']})")
            else:
                print(f"❌ Prediction failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Prediction error: {e}")
    
    print("\n✅ Local testing completed!")

def run_load_test(num_requests=10):
    """Teste de carga simples"""
    print(f"\n🔥 Running Load Test ({num_requests} requests):")
    
    # Garantir que há um modelo treinado
    training_data = {
        "timestamps": [i for i in range(1609459200, 1609459200 + 3600, 60)],  # 1 hora de dados
        "values": [42.0 + (i % 10) * 0.1 for i in range(60)],  # Valores variando
        "threshold": 3.0
    }
    
    requests.post(f"{TRAINING_URL}/fit/load_test_sensor", json=training_data, timeout=10)
    
    # Fazer múltiplas predições
    start_time = time.time()
    success_count = 0
    
    for i in range(num_requests):
        prediction_data = {
            "timestamp": str(1609459500 + i),
            "value": 42.0 + (i % 20) * 0.1  # Valores variando
        }
        
        try:
            response = requests.post(
                f"{INFERENCE_URL}/predict/load_test_sensor",
                json=prediction_data,
                timeout=5
            )
            
            if response.status_code == 200:
                success_count += 1
            
        except Exception as e:
            print(f"Request {i} failed: {e}")
    
    duration = time.time() - start_time
    rps = success_count / duration if duration > 0 else 0
    
    print(f"📊 Results:")
    print(f"   • Total requests: {num_requests}")
    print(f"   • Successful: {success_count}")
    print(f"   • Duration: {duration:.2f}s")
    print(f"   • RPS: {rps:.1f}")
    print(f"   • Success rate: {success_count/num_requests*100:.1f}%")

if __name__ == "__main__":
    print("🚀 Anomaly Detection - Local Cloud Testing")
    print("Make sure both services are running:")
    print("  Training:  python training-service/main.py")
    print("  Inference: PORT=8081 python inference-service/main.py")
    print()
    
    input("Press Enter to start testing...")
    
    test_local_services()
    
    if input("\nRun load test? (y/N): ").lower() == 'y':
        run_load_test(50)
