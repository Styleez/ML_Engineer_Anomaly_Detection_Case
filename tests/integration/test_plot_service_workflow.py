"""
Integration test for Plot Service workflow
Tests training multiple model versions and retrieving training data via Plot Service
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
    PLOT_SERVICE_URL,
    TRAINING_TIMEOUT
)


class TestPlotServiceWorkflow:
    """Test Plot Service with multiple model versions and training data persistence"""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment"""
        cls.loader = DatasetLoader()
        cls.base_series_id = f"plot_test_series_{int(time.time())}"
        cls.dataset_name = "machine_temperature"  # Using machine temperature dataset
        cls.config = get_dataset_config(cls.dataset_name)
        cls.trained_versions = []  # Store all trained versions
        
        print(f"\n🧪 Starting Plot Service integration test")
        print(f"📊 Dataset: {cls.config['description']}")
        print(f"🔖 Series ID: {cls.base_series_id}")
        
        # Verify core services are available
        cls._wait_for_services()
    
    @classmethod
    def _wait_for_services(cls, timeout: int = 30):
        """Wait for required services to be available"""
        services = [
            ("Training", f"{TRAINING_SERVICE_URL}/healthcheck"),
            ("Plot", f"{PLOT_SERVICE_URL}/healthcheck")
        ]
        
        print("⏳ Waiting for services to be ready...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            all_ready = True
            
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
                print("🎉 Services are ready!")
                return
            
            time.sleep(2)
        
        raise Exception(f"❌ Services failed to become ready within {timeout}s")
    
    def test_01_train_initial_model_version(self):
        """Test training the first version of the model"""
        print(f"\n🎯 Step 1: Training initial model version...")
        
        # Load training data (smaller sample for first version)
        training_data = self.loader.load_training_sample(
            self.config['file'], 
            100  # First version with 100 points
        )
        
        # Prepare training request
        api_data = {
            "timestamps": training_data["timestamps"],
            "values": training_data["values"], 
            "threshold": 3.0  # 3-sigma threshold
        }
        
        # Send training request
        print(f"📤 Training version 1 with {len(api_data['timestamps'])} data points...")
        response = requests.post(
            f"{TRAINING_SERVICE_URL}/fit/{self.base_series_id}",
            json=api_data,
            timeout=TRAINING_TIMEOUT
        )
        
        # Validate response
        assert response.status_code == 200, f"Training failed: {response.text}"
        
        result = response.json()
        assert result["series_id"] == self.base_series_id
        assert "model_version" in result
        assert result["points_used"] == 100
        
        # Store version info
        version_info = {
            "version": result["model_version"],  # Use model_version, not version
            "points_used": result["points_used"],
            "training_data": training_data,
            "timestamp": result["timestamp"]
        }
        self.__class__.trained_versions.append(version_info)
        
        print(f"✅ Version 1 trained successfully:")
        print(f"   🏷️  Model Version: {result['model_version']}")
        print(f"   📊 Points: {result['points_used']}")
        print(f"   ⏰ Timestamp: {result['timestamp']}")
        
    def test_02_verify_version_1_in_plot_service(self):
        """Test retrieving version 1 data via Plot Service"""
        print(f"\n📊 Step 2: Verifying version 1 via Plot Service...")
        
        version_1 = self.trained_versions[0]
        
        # Query training data via Plot Service (without version - should get latest)
        response = requests.get(
            f"{PLOT_SERVICE_URL}/plot",
            params={"series_id": self.base_series_id},
            timeout=10
        )
        
        assert response.status_code == 200, f"Plot service failed: {response.text}"
        
        plot_data = response.json()
        assert plot_data["series_id"] == self.base_series_id
        assert plot_data["version"] == version_1["version"]
        assert plot_data["data_points_count"] == 100
        assert len(plot_data["timestamps"]) == 100
        assert len(plot_data["values"]) == 100
        
        # Verify data integrity (first few points)
        for i in range(min(5, len(plot_data["timestamps"]))):
            assert plot_data["timestamps"][i] == version_1["training_data"]["timestamps"][i]
            assert abs(plot_data["values"][i] - version_1["training_data"]["values"][i]) < 1e-10
        
        print(f"✅ Version 1 verified in Plot Service:")
        print(f"   📊 {plot_data['data_points_count']} data points retrieved")
        print(f"   🏷️  Version: {plot_data['version']}")
        print(f"   ⏰ Timestamp: {plot_data['timestamp']}")
        
    def test_03_train_second_model_version(self):
        """Test training a second version with more data"""
        print(f"\n🎯 Step 3: Training second model version with more data...")
        
        # Load more training data for second version
        training_data = self.loader.load_training_sample(
            self.config['file'], 
            200  # Second version with 200 points
        )
        
        # Prepare training request
        api_data = {
            "timestamps": training_data["timestamps"],
            "values": training_data["values"], 
            "threshold": 2.5  # Different threshold for second version
        }
        
        # Send training request
        print(f"📤 Training version 2 with {len(api_data['timestamps'])} data points...")
        response = requests.post(
            f"{TRAINING_SERVICE_URL}/fit/{self.base_series_id}",
            json=api_data,
            timeout=TRAINING_TIMEOUT
        )
        
        # Validate response
        assert response.status_code == 200, f"Training failed: {response.text}"
        
        result = response.json()
        assert result["series_id"] == self.base_series_id
        assert "model_version" in result
        assert result["points_used"] == 200
        
        # Store version info
        version_info = {
            "version": result["model_version"],  # Use model_version, not version
            "points_used": result["points_used"],
            "training_data": training_data,
            "timestamp": result["timestamp"]
        }
        self.__class__.trained_versions.append(version_info)
        
        # Version should be different from first one
        assert result["model_version"] != self.trained_versions[0]["version"]
        
        print(f"✅ Version 2 trained successfully:")
        print(f"   🏷️  Model Version: {result['model_version']} (was: {self.trained_versions[0]['version']})")
        print(f"   📊 Points: {result['points_used']} (was: {self.trained_versions[0]['points_used']})")
        print(f"   ⏰ Timestamp: {result['timestamp']}")
        
    def test_04_verify_latest_version_default(self):
        """Test that Plot Service returns latest version by default"""
        print(f"\n📊 Step 4: Verifying latest version is returned by default...")
        
        version_2 = self.trained_versions[1]
        
        # Query without specific version (should get latest)
        response = requests.get(
            f"{PLOT_SERVICE_URL}/plot",
            params={"series_id": self.base_series_id},
            timeout=10
        )
        
        assert response.status_code == 200, f"Plot service failed: {response.text}"
        
        plot_data = response.json()
        assert plot_data["series_id"] == self.base_series_id
        assert plot_data["version"] == version_2["version"]  # Should be latest (version 2)
        assert plot_data["data_points_count"] == 200
        
        print(f"✅ Latest version returned by default:")
        print(f"   🏷️  Version: {plot_data['version']} (latest)")
        print(f"   📊 Points: {plot_data['data_points_count']}")
        
    def test_05_retrieve_specific_version_1(self):
        """Test retrieving specific version 1 data"""
        print(f"\n📊 Step 5: Retrieving specific version 1...")
        
        version_1 = self.trained_versions[0]
        
        # Query specific version 1
        response = requests.get(
            f"{PLOT_SERVICE_URL}/plot",
            params={
                "series_id": self.base_series_id,
                "version": version_1["version"]
            },
            timeout=10
        )
        
        assert response.status_code == 200, f"Plot service failed: {response.text}"
        
        plot_data = response.json()
        assert plot_data["series_id"] == self.base_series_id
        assert plot_data["version"] == version_1["version"]
        assert plot_data["data_points_count"] == 100  # Should be 100, not 200
        
        print(f"✅ Specific version 1 retrieved:")
        print(f"   🏷️  Version: {plot_data['version']}")
        print(f"   📊 Points: {plot_data['data_points_count']}")
        
    def test_06_retrieve_specific_version_2(self):
        """Test retrieving specific version 2 data"""
        print(f"\n📊 Step 6: Retrieving specific version 2...")
        
        version_2 = self.trained_versions[1]
        
        # Query specific version 2
        response = requests.get(
            f"{PLOT_SERVICE_URL}/plot",
            params={
                "series_id": self.base_series_id,
                "version": version_2["version"]
            },
            timeout=10
        )
        
        assert response.status_code == 200, f"Plot service failed: {response.text}"
        
        plot_data = response.json()
        assert plot_data["series_id"] == self.base_series_id
        assert plot_data["version"] == version_2["version"]
        assert plot_data["data_points_count"] == 200  # Should be 200
        
        print(f"✅ Specific version 2 retrieved:")
        print(f"   🏷️  Version: {plot_data['version']}")
        print(f"   📊 Points: {plot_data['data_points_count']}")
        
    def test_07_train_third_model_version(self):
        """Test training a third version to confirm version management"""
        print(f"\n🎯 Step 7: Training third model version...")
        
        # Load different subset for third version
        training_data = self.loader.load_training_sample(
            self.config['file'], 
            150  # Third version with 150 points
        )
        
        # Use different starting point to get different data
        # Simulate retraining with updated data
        offset_data = {
            "timestamps": training_data["timestamps"][50:],  # Skip first 50 points
            "values": training_data["values"][50:],          # Skip first 50 points
            "threshold": 3.5  # Different threshold again
        }
        
        # Send training request
        print(f"📤 Training version 3 with {len(offset_data['timestamps'])} data points...")
        response = requests.post(
            f"{TRAINING_SERVICE_URL}/fit/{self.base_series_id}",
            json=offset_data,
            timeout=TRAINING_TIMEOUT
        )
        
        # Validate response
        assert response.status_code == 200, f"Training failed: {response.text}"
        
        result = response.json()
        assert result["series_id"] == self.base_series_id
        assert "model_version" in result
        assert result["points_used"] == 100  # 150 - 50 = 100
        
        # Store version info
        version_info = {
            "version": result["model_version"],  # Use model_version, not version
            "points_used": result["points_used"],
            "training_data": offset_data,
            "timestamp": result["timestamp"]
        }
        self.__class__.trained_versions.append(version_info)
        
        print(f"✅ Version 3 trained successfully:")
        print(f"   🏷️  Model Version: {result['model_version']}")
        print(f"   📊 Points: {result['points_used']}")
        print(f"   ⏰ Timestamp: {result['timestamp']}")
        
    def test_08_verify_version_management(self):
        """Test that all versions are properly managed"""
        print(f"\n🔍 Step 8: Verifying version management...")
        
        print(f"📋 Total versions trained: {len(self.trained_versions)}")
        
        # Test that each version can be retrieved individually
        for i, version_info in enumerate(self.trained_versions):
            response = requests.get(
                f"{PLOT_SERVICE_URL}/plot",
                params={
                    "series_id": self.base_series_id,
                    "version": version_info["version"]
                },
                timeout=10
            )
            
            assert response.status_code == 200, f"Failed to retrieve version {version_info['version']}"
            
            plot_data = response.json()
            assert plot_data["version"] == version_info["version"]
            assert plot_data["data_points_count"] == version_info["points_used"]
            
            print(f"   ✅ Version {i+1}: {version_info['version']} ({version_info['points_used']} points)")
        
        # Test that default query returns latest version (version 3)
        response = requests.get(
            f"{PLOT_SERVICE_URL}/plot",
            params={"series_id": self.base_series_id},
            timeout=10
        )
        
        assert response.status_code == 200
        plot_data = response.json()
        latest_version = self.trained_versions[-1]  # Last trained version
        assert plot_data["version"] == latest_version["version"]
        
        print(f"   ✅ Default query returns latest: {plot_data['version']}")
        
    def test_09_data_integrity_verification(self):
        """Test data integrity across versions"""
        print(f"\n🔒 Step 9: Verifying data integrity...")
        
        for i, version_info in enumerate(self.trained_versions):
            # Retrieve data from Plot Service
            response = requests.get(
                f"{PLOT_SERVICE_URL}/plot",
                params={
                    "series_id": self.base_series_id,
                    "version": version_info["version"]
                },
                timeout=10
            )
            
            assert response.status_code == 200
            plot_data = response.json()
            
            # Verify data matches what was sent for training
            expected_timestamps = version_info["training_data"]["timestamps"]
            expected_values = version_info["training_data"]["values"]
            
            assert len(plot_data["timestamps"]) == len(expected_timestamps)
            assert len(plot_data["values"]) == len(expected_values)
            
            # Check first 3 and last 3 points for integrity
            check_indices = [0, 1, 2, -3, -2, -1]
            for idx in check_indices:
                if abs(idx) <= len(expected_timestamps):
                    assert plot_data["timestamps"][idx] == expected_timestamps[idx]
                    assert abs(plot_data["values"][idx] - expected_values[idx]) < 1e-10
            
            print(f"   ✅ Version {i+1} data integrity verified")
        
    def test_10_error_handling(self):
        """Test error handling for invalid requests"""
        print(f"\n🚨 Step 10: Testing error handling...")
        
        # Test non-existent series
        response = requests.get(
            f"{PLOT_SERVICE_URL}/plot",
            params={"series_id": "non_existent_series"},
            timeout=10
        )
        assert response.status_code == 404
        print("   ✅ Non-existent series error handling: OK")
        
        # Test non-existent version
        response = requests.get(
            f"{PLOT_SERVICE_URL}/plot",
            params={
                "series_id": self.base_series_id,
                "version": "99.99"  # Non-existent version
            },
            timeout=10
        )
        assert response.status_code == 404
        print("   ✅ Non-existent version error handling: OK")
        
        # Test missing series_id parameter
        response = requests.get(
            f"{PLOT_SERVICE_URL}/plot",
            params={},  # Missing series_id
            timeout=10
        )
        assert response.status_code == 422  # Validation error
        print("   ✅ Missing parameter error handling: OK")
    
    @classmethod
    def teardown_class(cls):
        """Cleanup after tests"""
        print(f"\n🧹 Plot Service test cleanup completed")
        print(f"📋 Test series '{cls.base_series_id}' with {len(cls.trained_versions)} versions")
        print("📊 Summary of trained versions:")
        for i, version in enumerate(cls.trained_versions):
            print(f"   Version {i+1}: {version['version']} ({version['points_used']} points)")


def run_plot_service_test():
    """Run the plot service integration test"""
    print("🧪 Starting Plot Service Integration Test")
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
    success = run_plot_service_test()
    if success:
        print("\n🎉 Plot Service integration test PASSED!")
    else:
        print("\n❌ Plot Service integration test FAILED!")
    exit(0 if success else 1)
