#!/usr/bin/env python3
"""
Script para testar todos os endpoints localmente
"""
import requests
import json
import time
from datetime import datetime

# URLs dos serviços
SERVICES = {
    "training": "http://localhost:8001",
    "inference": "http://localhost:8002", 
    "plot": "http://localhost:8003",
    "healthcheck": "http://localhost:8004"
}

# URLs base para endpoints da spec
BASE_URL = "http://localhost:8001"  # Training service para fit
INFERENCE_URL = "http://localhost:8002"  # Inference service para predict

def wait_for_services(max_retries=30):
    """Aguarda todos os serviços estarem disponíveis"""
    print("🔍 Checking service availability...")
    
    for service, url in SERVICES.items():
        for i in range(max_retries):
            try:
                if service == "healthcheck":
                    endpoint = f"{url}/health"
                else:
                    endpoint = f"{url}/healthcheck"
                
                response = requests.get(endpoint, timeout=5)
                if response.status_code == 200:
                    print(f"✅ {service.title()} service is ready!")
                    break
            except:
                print(f"⏳ Waiting for {service} service... attempt {i+1}/{max_retries}")
                time.sleep(2)
        else:
            raise Exception(f"❌ {service.title()} service not available")

def test_health_checks():
    """Testa todos os health checks"""
    print("\n🏥 Testing health checks...")
    
    # Test individual services
    for service, url in SERVICES.items():
        if service == "healthcheck":
            endpoint = f"{url}/health"
        else:
            endpoint = f"{url}/healthcheck"
        
        response = requests.get(endpoint)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {service.title()}: {data.get('status', 'unknown')}")
        else:
            print(f"❌ {service.title()}: Failed ({response.status_code})")
    
    # Test system health check (conforme spec)
    response = requests.get(f"{BASE_URL}/healthcheck")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ System Health: {data.get('series_trained', 0)} series trained")
    else:
        print(f"❌ System Health: Failed ({response.status_code})")

def test_training_workflow():
    """Testa o fluxo de treinamento"""
    print("\n🎯 Testing training workflow...")
    
    # Sample training data
    training_data = {
        "timestamps": [
            int(datetime.utcnow().timestamp()) - 3600 + i * 60  # Last hour, every minute
            for i in range(30)
        ],
        "values": [
            42.5 + i * 0.1 + (i % 3) * 0.5  # Varying values
            for i in range(30)
        ],
        "threshold": 3.0
    }
    
    # Train model (conforme spec: /fit/{series_id})
    response = requests.post(
        f"{BASE_URL}/fit/test_sensor_001",
        json=training_data
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Training successful: {data['points_used']} points used")
        
        # Test retrieving training data via plot endpoint
        plot_response = requests.get(f"{SERVICES['plot']}/plot?series_id=test_sensor_001")
        if plot_response.status_code == 200:
            plot_data = plot_response.json()
            print(f"✅ Plot data retrieved: {plot_data['data_points_count']} points, version {plot_data['version']}")
        
        return True
    else:
        print(f"❌ Training failed: {response.status_code} - {response.text}")
        return False

def test_inference_workflow():
    """Testa o fluxo de inferência"""
    print("\n🔮 Testing inference workflow...")
    
    # Make prediction
    prediction_data = {
        "timestamp": str(int(datetime.utcnow().timestamp())),
        "value": 50.5  # Likely anomaly
    }
    
    response = requests.post(
        f"{INFERENCE_URL}/predict/test_sensor_001",
        json=prediction_data
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Prediction successful: anomaly={data['anomaly']}, model_version={data['model_version']}")
        return True
    else:
        print(f"❌ Prediction failed: {response.status_code} - {response.text}")
        return False

def test_plot_workflow():
    """Testa o fluxo de plotting"""
    print("\n📊 Testing plot workflow...")
    
    # Get plot data (training series)
    response = requests.get(f"{SERVICES['plot']}/plot?series_id=sensor_001")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Plot data retrieved: {data['data_points_count']} training points, version {data['version']}")
        return True
    
    print(f"❌ Plot workflow failed: {response.status_code} - {response.text}")
    return False

def test_integration():
    """Teste de integração end-to-end"""
    print("\n🔄 Testing end-to-end integration...")
    
    series_id = f"integration_test_{int(time.time())}"
    
    # 1. Train model
    training_data = {
        "timestamps": [int(time.time()) - 1800 + i * 30 for i in range(60)],  # 30 minutes, every 30s
        "values": [42.0 + i * 0.01 + (i % 10) * 0.1 for i in range(60)],
        "threshold": 2.5
    }
    
    train_response = requests.post(f"{BASE_URL}/fit/{series_id}", json=training_data)
    if train_response.status_code != 200:
        print("❌ Integration test failed at training step")
        return False
    
    # 2. Make prediction
    prediction_data = {"timestamp": str(int(time.time())), "value": 50.0}
    pred_response = requests.post(f"{INFERENCE_URL}/predict/{series_id}", json=prediction_data)
    if pred_response.status_code != 200:
        print("❌ Integration test failed at prediction step")
        return False
    
    # Wait a bit for data to be available
    time.sleep(2)
    
    # 3. Get plot data
    plot_response = requests.get(f"{SERVICES['plot']}/plot?series_id={series_id}")
    if plot_response.status_code == 200:
        plot_data = plot_response.json()
        print(f"✅ End-to-end integration test successful! Plot has {plot_data['data_points_count']} points")
        return True
    else:
        print("❌ Integration test failed at plot step")
        return False

def main():
    """Função principal de teste"""
    print("🧪 Starting local testing...")
    
    try:
        # Aguarda serviços
        wait_for_services()
        
        # Testa health checks
        test_health_checks()
        
        # Testa workflows individuais
        training_ok = test_training_workflow()
        if training_ok:
            inference_ok = test_inference_workflow()
            plot_ok = test_plot_workflow()
            
            if training_ok and inference_ok and plot_ok:
                # Teste de integração
                integration_ok = test_integration()
                
                if integration_ok:
                    print("\n🎉 All tests passed! System is working correctly!")
                else:
                    print("\n⚠️ Integration test failed")
            else:
                print("\n⚠️ Some individual tests failed")
        else:
            print("\n⚠️ Training failed, skipping other tests")
    
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")

if __name__ == "__main__":
    main()
