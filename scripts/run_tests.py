#!/usr/bin/env python3
"""
Test runner script for all services
"""
import subprocess
import sys
import os
import time
import requests
from typing import List, Dict

# Add tests directory to Python path for config import
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tests'))

try:
    from config import (
        TRAINING_SERVICE_URL, 
        INFERENCE_SERVICE_URL, 
        PLOT_SERVICE_URL, 
        HEALTHCHECK_SERVICE_URL,
        DEFAULT_TIMEOUT
    )
except ImportError:
    # Fallback URLs if config not available
    TRAINING_SERVICE_URL = "http://localhost:8000"
    INFERENCE_SERVICE_URL = "http://localhost:8001"
    PLOT_SERVICE_URL = "http://localhost:8002"
    HEALTHCHECK_SERVICE_URL = "http://localhost:8003"
    DEFAULT_TIMEOUT = 30

class TestRunner:
    def __init__(self):
        self.services = {
            "training": TRAINING_SERVICE_URL,
            "inference": INFERENCE_SERVICE_URL,
            "plot": PLOT_SERVICE_URL,
            "healthcheck": HEALTHCHECK_SERVICE_URL
        }
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def wait_for_services(self, timeout: int = 60) -> bool:
        """Wait for all services to be ready"""
        print("🔍 Waiting for services to be ready...")
        
        for service_name, url in self.services.items():
            print(f"  Checking {service_name}...")
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    response = requests.get(f"{url}/healthcheck", timeout=2)
                    if response.status_code == 200:
                        print(f"  ✅ {service_name} is ready")
                        break
                except:
                    pass
                time.sleep(2)
            else:
                print(f"  ❌ {service_name} not ready after {timeout}s")
                return False
        
        return True
    
    def run_unit_tests(self) -> bool:
        """Run unit tests for all services"""
        print("\n🧪 Running unit tests...")
        
        cmd = [
            sys.executable, "-m", "pytest", 
            "tests/unit/", 
            "-v", 
            "-m", "not integration"
        ]
        
        result = subprocess.run(cmd, cwd=self.base_dir)
        return result.returncode == 0
    
    def run_integration_tests(self) -> bool:
        """Run integration tests"""
        print("\n🔗 Running integration tests...")
        
        if not self.wait_for_services():
            print("❌ Services not ready, skipping integration tests")
            return False
        
        cmd = [
            sys.executable, "-m", "pytest", 
            "tests/integration/", 
            "-v"
        ]
        
        result = subprocess.run(cmd, cwd=self.base_dir)
        return result.returncode == 0
    
    def run_all_tests(self) -> bool:
        """Run all tests"""
        print("🚀 Running all tests...\n")
        
        unit_passed = self.run_unit_tests()
        integration_passed = self.run_integration_tests()
        
        print("\n📊 Test Summary:")
        print(f"  Unit tests: {'✅ PASSED' if unit_passed else '❌ FAILED'}")
        print(f"  Integration tests: {'✅ PASSED' if integration_passed else '❌ FAILED'}")
        
        if unit_passed and integration_passed:
            print("\n🎉 All tests passed!")
            return True
        else:
            print("\n💥 Some tests failed!")
            return False

def main():
    """Main function"""
    runner = TestRunner()
    
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
        if test_type == "unit":
            success = runner.run_unit_tests()
        elif test_type == "integration":
            success = runner.run_integration_tests()
        else:
            print("Usage: python run_tests.py [unit|integration]")
            sys.exit(1)
    else:
        success = runner.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
