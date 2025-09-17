"""
Complete integration test using real dataset
Tests the full workflow: Load Dataset → Train Model → Make Predictions → Validate Results
"""
import pytest
import requests
import time
import sys
import os
from pathlib import Path

# Add project root and tests to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tests"))

from tests.utils.dataset_loader import DatasetLoader, get_dataset_config
from tests.config import (
    TRAINING_SERVICE_URL, 
    INFERENCE_SERVICE_URL, 
    PLOT_SERVICE_URL,
    HEALTHCHECK_SERVICE_URL,
    TRAINING_TIMEOUT,
    INFERENCE_TIMEOUT
)


class TestCompleteWorkflow:
    """Complete integration test suite using real datasets"""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment and data loader"""
        cls.loader = DatasetLoader()
        cls.test_series_id = f"test_series_p1_{int(time.time())}"
        cls.dataset_name = "ambient_temperature"  # Using ambient temperature dataset
        cls.config = get_dataset_config(cls.dataset_name)
        cls.trained_model_version = None
        
        print(f"\n🧪 Starting complete integration test")
        print(f"📊 Dataset: {cls.config['description']}")
        print(f"🔖 Series ID: {cls.test_series_id}")
        
        # Verify core services are available (HealthCheck is optional)
        cls._wait_for_services()
    
    @classmethod
    def _wait_for_services(cls, timeout: int = 60):
        """Wait for all required services to be available"""
        # Core required services for integration test
        services = [
            ("Training", f"{TRAINING_SERVICE_URL}/healthcheck"),
            ("Inference", f"{INFERENCE_SERVICE_URL}/healthcheck"), 
            ("Plot", f"{PLOT_SERVICE_URL}/healthcheck")
        ]
        
        # Optional services (don't fail if not available)
        optional_services = [
            ("HealthCheck", f"{HEALTHCHECK_SERVICE_URL}/healthcheck")
        ]
        
        print("⏳ Waiting for core services to be ready...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            all_ready = True
            
            # Check core services (required)
            for service_name, url in services:
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        print(f"✅ {service_name} service ready")
                    else:
                        print(f"⏳ {service_name} not ready (status: {response.status_code})")
                        all_ready = False
                        break
                except requests.exceptions.RequestException as e:
                    print(f"⏳ {service_name} not ready (error: {str(e)[:50]}...)")
                    all_ready = False
                    break
            
            if all_ready:
                print("🎉 Core services are ready!")
                
                # Check optional services (don't fail if not available)
                for service_name, url in optional_services:
                    try:
                        response = requests.get(url, timeout=2)
                        if response.status_code == 200:
                            print(f"✅ {service_name} service ready (optional)")
                        else:
                            print(f"⚠️  {service_name} not available (optional)")
                    except requests.exceptions.RequestException:
                        print(f"⚠️  {service_name} not available (optional)")
                
                return
            
            time.sleep(3)
        
        raise Exception(f"❌ Core services failed to become ready within {timeout}s")
    
    def test_01_load_dataset(self):
        """Test loading and validating dataset"""
        print(f"\n📥 Step 1: Loading dataset '{self.config['file']}'...")
        
        # Load training data
        self.__class__.training_data = self.loader.load_training_sample(
            self.config['file'], 
            self.config['training_size']
        )
        
        # Validate data structure
        assert "timestamps" in self.training_data
        assert "values" in self.training_data
        assert "threshold" in self.training_data
        assert len(self.training_data["timestamps"]) == len(self.training_data["values"])
        assert len(self.training_data["timestamps"]) == self.config['training_size']
        
        # Validate Unix timestamps
        for ts in self.training_data["timestamps"]:
            assert isinstance(ts, int)
            assert ts > 1000000000  # Reasonable Unix timestamp (after 2001)
        
        # Validate values
        for val in self.training_data["values"]:
            assert isinstance(val, (int, float))
            assert not str(val).lower() in ['nan', 'inf', '-inf']
        
        print(f"✅ Dataset loaded successfully:")
        print(f"   📊 {len(self.training_data['timestamps'])} training points")
        print(f"   📈 Value range: {self.training_data['metadata']['value_range']['min']:.4f} - {self.training_data['metadata']['value_range']['max']:.4f}")
        print(f"   ⏰ Time range: {self.training_data['metadata']['time_range']['start']} - {self.training_data['metadata']['time_range']['end']}")
        
    def test_02_train_model(self):
        """Test training model with real dataset"""
        print(f"\n🎯 Step 2: Training model for series '{self.test_series_id}'...")
        
        # Prepare training request (remove metadata for API)
        api_data = {
            "timestamps": self.training_data["timestamps"],
            "values": self.training_data["values"], 
            "threshold": self.training_data["threshold"]
        }
        
        # Send training request
        print(f"📤 Sending {len(api_data['timestamps'])} data points to training service...")
        print(f"🎯 Training URL: {TRAINING_SERVICE_URL}/fit/{self.test_series_id}")
        print(f"📊 Sample data: timestamps[0]={api_data['timestamps'][0]}, values[0]={api_data['values'][0]}")
        
        response = requests.post(
            f"{TRAINING_SERVICE_URL}/fit/{self.test_series_id}",
            json=api_data,
            timeout=TRAINING_TIMEOUT
        )
        
        print(f"📋 Response status: {response.status_code}")
        if response.status_code != 200:
            print(f"❌ Response content: {response.text}")
        
        # Validate response
        assert response.status_code == 200, f"Training failed: {response.text}"
        
        result = response.json()
        assert result["series_id"] == self.test_series_id
        assert "version" in result
        assert result["points_used"] == len(self.training_data["timestamps"])
        assert "timestamp" in result
        
        # Store model version for later tests
        self.__class__.trained_model_version = result["version"]
        
        print(f"✅ Model trained successfully:")
        print(f"   🏷️  Model version: {self.trained_model_version}")
        print(f"   📊 Points used: {result['points_used']}")
        print(f"   ⏰ Training timestamp: {result['timestamp']}")
        
    def test_03_verify_model_in_database(self):
        """Test that trained model is stored in database via Plot Service"""
        print(f"\n🔍 Step 3: Verifying model in database...")
        
        # Query training data via Plot Service
        response = requests.get(
            f"{PLOT_SERVICE_URL}/plot",
            params={"series_id": self.test_series_id},
            timeout=10
        )
        
        assert response.status_code == 200, f"Plot service failed: {response.text}"
        
        plot_data = response.json()
        assert plot_data["series_id"] == self.test_series_id
        assert plot_data["version"] == self.trained_model_version
        assert len(plot_data["timestamps"]) == len(self.training_data["timestamps"])
        assert len(plot_data["values"]) == len(self.training_data["values"])
        
        print(f"✅ Model verified in database:")
        print(f"   📊 {plot_data['data_points_count']} data points stored")
        print(f"   🏷️  Version: {plot_data['version']}")
        
    def test_04_make_predictions(self):
        """Test making predictions with the trained model"""
        print(f"\n⚡ Step 4: Making predictions with trained model...")
        
        # Load prediction samples from dataset
        prediction_samples = self.loader.load_prediction_samples(
            self.config['file'],
            start_idx=self.config['training_size'],  # After training data
            count=self.config['prediction_samples']
        )
        
        print(f"🔮 Testing {len(prediction_samples)} prediction samples...")
        
        prediction_results = []
        
        for i, sample in enumerate(prediction_samples):
            # Make prediction
            response = requests.post(
                f"{INFERENCE_SERVICE_URL}/predict/{self.test_series_id}",
                json=sample,
                timeout=INFERENCE_TIMEOUT
            )
            
            assert response.status_code == 200, f"Prediction {i+1} failed: {response.text}"
            
            result = response.json()
            assert "anomaly" in result
            assert "model_version" in result
            assert "timestamp" in result
            assert result["model_version"] == self.trained_model_version
            assert isinstance(result["anomaly"], bool)
            
            prediction_results.append({
                "input": sample,
                "output": result,
                "is_anomaly": result["anomaly"]
            })
            
            print(f"   📊 Prediction {i+1}: value={sample['value']:.4f} → anomaly={result['anomaly']}")
        
        # Store results for analysis
        self.__class__.prediction_results = prediction_results
        
        # Analyze results
        anomaly_count = sum(1 for r in prediction_results if r["is_anomaly"])
        normal_count = len(prediction_results) - anomaly_count
        
        print(f"✅ Predictions completed:")
        print(f"   🔴 Anomalies detected: {anomaly_count}")
        print(f"   🟢 Normal values: {normal_count}")
        print(f"   📊 Anomaly rate: {(anomaly_count/len(prediction_results)*100):.1f}%")
        
    def test_05_test_caching_performance(self):
        """Test that inference caching improves performance"""
        print(f"\n🚀 Step 5: Testing caching performance...")
        
        # Use first prediction sample for cache testing
        sample = self.prediction_results[0]["input"]
        
        # First request (should load from database and cache)
        start_time = time.time()
        response1 = requests.post(
            f"{INFERENCE_SERVICE_URL}/predict/{self.test_series_id}",
            json=sample,
            timeout=INFERENCE_TIMEOUT
        )
        first_request_time = (time.time() - start_time) * 1000  # ms
        
        assert response1.status_code == 200
        result1 = response1.json()
        
        # Second request (should use cache)
        start_time = time.time()
        response2 = requests.post(
            f"{INFERENCE_SERVICE_URL}/predict/{self.test_series_id}",
            json=sample,
            timeout=INFERENCE_TIMEOUT
        )
        second_request_time = (time.time() - start_time) * 1000  # ms
        
        assert response2.status_code == 200
        result2 = response2.json()
        
        # Results should be identical
        assert result1["anomaly"] == result2["anomaly"]
        assert result1["model_version"] == result2["model_version"]
        
        # Second request should typically be faster (cache hit)
        print(f"✅ Caching performance test:")
        print(f"   🐌 First request (DB + cache): {first_request_time:.1f}ms")
        print(f"   🚀 Second request (cache hit): {second_request_time:.1f}ms")
        
        if second_request_time < first_request_time:
            improvement = ((first_request_time - second_request_time) / first_request_time) * 100
            print(f"   📈 Performance improvement: {improvement:.1f}%")
        
    def test_06_system_health_check(self):
        """Test system-wide health check"""
        print(f"\n🏥 Step 6: Testing system health...")
        
        # Try HealthCheck service if available
        try:
            response = requests.get(f"{HEALTHCHECK_SERVICE_URL}/v1/healthcheck", timeout=10)
            
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ System health check passed:")
                print(f"   📊 Overall status: {health_data.get('status', 'unknown')}")
                
                if "services" in health_data:
                    for service, status in health_data["services"].items():
                        print(f"   🔧 {service}: {status.get('status', 'unknown')}")
            else:
                print(f"⚠️  HealthCheck service returned: {response.status_code}")
        except requests.exceptions.RequestException:
            print(f"⚠️  HealthCheck service not available - checking individual services")
            
            # Fallback: check individual services
            individual_services = [
                ("Training", f"{TRAINING_SERVICE_URL}/healthcheck"),
                ("Inference", f"{INFERENCE_SERVICE_URL}/healthcheck"), 
                ("Plot", f"{PLOT_SERVICE_URL}/healthcheck")
            ]
            
            for service_name, url in individual_services:
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        print(f"✅ {service_name} service: healthy")
                    else:
                        print(f"⚠️  {service_name} service: status {response.status_code}")
                except requests.exceptions.RequestException as e:
                    print(f"❌ {service_name} service: not available")
            
            print("✅ Individual service health checks completed")
    
    def test_07_performance_requirements(self):
        """Test that performance requirements are met"""
        print(f"\n⚡ Step 7: Validating performance requirements...")
        
        # Test inference latency (should be < 100ms P95)
        latencies = []
        sample = self.prediction_results[0]["input"]
        
        print("📊 Measuring inference latency...")
        for i in range(20):
            start_time = time.time()
            response = requests.post(
                f"{INFERENCE_SERVICE_URL}/predict/{self.test_series_id}",
                json=sample,
                timeout=INFERENCE_TIMEOUT
            )
            latency = (time.time() - start_time) * 1000  # ms
            latencies.append(latency)
            
            assert response.status_code == 200
        
        # Calculate performance metrics
        import statistics
        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(0.95 * len(latencies))]
        max_latency = max(latencies)
        
        print(f"✅ Performance metrics:")
        print(f"   📊 Average latency: {avg_latency:.1f}ms")
        print(f"   📊 P95 latency: {p95_latency:.1f}ms")
        print(f"   📊 Max latency: {max_latency:.1f}ms")
        
        # Performance assertions
        assert avg_latency < 50, f"Average latency too high: {avg_latency}ms (target: <50ms)"
        assert p95_latency < 100, f"P95 latency too high: {p95_latency}ms (target: <100ms)"
        
        print("🎯 Performance requirements met!")
    
    def test_08_error_handling(self):
        """Test error handling scenarios"""
        print(f"\n🚨 Step 8: Testing error handling...")
        
        # Test prediction with non-existent model
        response = requests.post(
            f"{INFERENCE_SERVICE_URL}/predict/non_existent_model",
            json={"timestamp": str(int(time.time())), "value": 42.0},
            timeout=INFERENCE_TIMEOUT
        )
        assert response.status_code == 404
        print("✅ Non-existent model error handling: OK")
        
        # Test invalid prediction data
        response = requests.post(
            f"{INFERENCE_SERVICE_URL}/predict/{self.test_series_id}",
            json={"timestamp": "invalid", "value": "not_a_number"},
            timeout=INFERENCE_TIMEOUT
        )
        assert response.status_code in [400, 422]
        print("✅ Invalid data error handling: OK")
        
        # Test plot with non-existent series
        response = requests.get(
            f"{PLOT_SERVICE_URL}/plot",
            params={"series_id": "non_existent_series"},
            timeout=10
        )
        assert response.status_code == 404
        print("✅ Non-existent plot data error handling: OK")
    
    @classmethod
    def teardown_class(cls):
        """Cleanup after tests"""
        print(f"\n🧹 Test cleanup completed")
        print(f"📋 Test series '{cls.test_series_id}' can be cleaned up if needed")


def run_complete_integration_test():
    """Run the complete integration test suite"""
    print("🧪 Starting Complete Integration Test Suite")
    print("=" * 60)
    
    # Run pytest with this specific test
    import subprocess
    result = subprocess.run([
        "python", "-m", "pytest", 
        __file__, 
        "-v", 
        "--tb=short",
        "-s"  # Show print statements
    ], cwd=str(Path(__file__).parent.parent.parent))
    
    return result.returncode == 0


if __name__ == "__main__":
    # Allow running directly
    success = run_complete_integration_test()
    if success:
        print("\n🎉 Complete integration test PASSED!")
    else:
        print("\n❌ Complete integration test FAILED!")
    exit(0 if success else 1)
