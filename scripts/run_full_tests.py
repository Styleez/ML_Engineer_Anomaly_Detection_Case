#!/usr/bin/env python3
"""
Complete test pipeline script for local development
Mirrors the CI/CD pipeline but runs locally
"""
import subprocess
import sys
import time
import requests
import os
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_step(message):
    print(f"\n{Colors.BLUE}{Colors.BOLD}=== {message} ==={Colors.ENDC}")

def print_success(message):
    print(f"{Colors.GREEN}✅ {message}{Colors.ENDC}")

def print_error(message):
    print(f"{Colors.RED}❌ {message}{Colors.ENDC}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.ENDC}")

def run_command(cmd, cwd=None, check=True):
    """Run a command and return the result"""
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            cwd=cwd, 
            check=check,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr and result.returncode != 0:
            print(result.stderr)
        return result
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        raise

def wait_for_service(url, timeout=300, interval=5):
    """Wait for a service to be ready"""
    print(f"Waiting for {url} to be ready...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print_success(f"Service {url} is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(interval)
    
    print_error(f"Service {url} did not become ready within {timeout} seconds")
    return False

def cleanup_docker():
    """Clean up Docker containers and volumes"""
    print_step("Cleaning up Docker environment")
    try:
        run_command("docker-compose -f docker-compose.test.yml down -v", check=False)
        run_command("docker system prune -f", check=False)
        print_success("Docker cleanup completed")
    except Exception as e:
        print_warning(f"Docker cleanup had issues: {e}")

def setup_environment():
    """Set up test environment"""
    print_step("Setting up test environment")
    
    # Set environment variables
    os.environ["DATABASE_URL"] = "postgresql://anomaly_user:test_password@localhost:5432/anomaly_detection"
    os.environ["REDIS_HOST"] = "localhost"
    os.environ["REDIS_PORT"] = "6379"
    os.environ["ENVIRONMENT"] = "test"
    
    print_success("Environment variables set")

def install_dependencies():
    """Install Python dependencies"""
    print_step("Installing dependencies")
    
    try:
        run_command("python -m pip install --upgrade pip")
        
        if Path("requirements.txt").exists():
            run_command("pip install -r requirements.txt")
        
        if Path("requirements-dev.txt").exists():
            run_command("pip install -r requirements-dev.txt")
        else:
            # Install test dependencies
            run_command("pip install pytest pytest-cov pytest-asyncio httpx")
            
        print_success("Dependencies installed successfully")
    except Exception as e:
        print_error(f"Failed to install dependencies: {e}")
        return False
    return True

def run_unit_tests():
    """Run unit tests"""
    print_step("Running unit tests")
    
    try:
        if Path("tests/unit").exists():
            result = run_command("python -m pytest tests/unit/ -v --tb=short", check=False)
            if result.returncode == 0:
                print_success("Unit tests passed!")
                return True
            else:
                print_error("Unit tests failed!")
                return False
        else:
            print_warning("No unit tests directory found")
            return True
    except Exception as e:
        print_error(f"Failed to run unit tests: {e}")
        return False

def start_docker_services():
    """Start Docker services"""
    print_step("Starting Docker services")
    
    try:
        cleanup_docker()
        
        print("Building and starting services...")
        run_command("docker-compose -f docker-compose.test.yml up -d --build")
        
        print("Waiting for services to be ready...")
        services = [
            "http://localhost:8000/healthcheck",  # Training
            "http://localhost:8001/healthcheck",  # Inference  
            "http://localhost:8002/healthcheck",  # Monitoring
        ]
        
        all_ready = True
        for service_url in services:
            if not wait_for_service(service_url, timeout=120):
                all_ready = False
                
        if all_ready:
            print_success("All Docker services are ready!")
            return True
        else:
            print_error("Some services failed to start")
            return False
            
    except Exception as e:
        print_error(f"Failed to start Docker services: {e}")
        return False

def run_integration_tests():
    """Run integration tests"""
    print_step("Running integration tests")
    
    try:
        success = True
        
        if Path("tests/integration").exists():
            # Run integration test files
            test_files = [
                "tests/integration/test_complete_workflow.py",
                "tests/integration/test_plot_service_workflow.py"
            ]
            
            for test_file in test_files:
                if Path(test_file).exists():
                    print(f"Running {test_file}...")
                    result = run_command(f"python -m pytest {test_file} -v", check=False)
                    if result.returncode != 0:
                        success = False
                        print_error(f"Integration test {test_file} failed!")
                    else:
                        print_success(f"Integration test {test_file} passed!")
                else:
                    print_warning(f"Test file {test_file} not found")
        else:
            print_warning("No integration tests directory found")
            
        return success
    except Exception as e:
        print_error(f"Failed to run integration tests: {e}")
        return False

def run_performance_tests():
    """Run performance/load tests"""
    print_step("Running performance tests")
    
    try:
        success = True
        perf_dir = Path("tests/performance")
        
        if perf_dir.exists():
            test_scripts = [
                "inference_load_test.py",
                "training_load_test.py"
            ]
            
            for script in test_scripts:
                script_path = perf_dir / script
                if script_path.exists():
                    print(f"Running {script}...")
                    result = run_command(f"python {script}", cwd=perf_dir, check=False)
                    if result.returncode != 0:
                        success = False
                        print_error(f"Performance test {script} failed!")
                    else:
                        print_success(f"Performance test {script} completed!")
                else:
                    print_warning(f"Performance test {script} not found")
        else:
            print_warning("No performance tests directory found")
            
        return success
    except Exception as e:
        print_error(f"Failed to run performance tests: {e}")
        return False

def test_dashboard():
    """Test the monitoring dashboard"""
    print_step("Testing monitoring dashboard")
    
    try:
        # Test dashboard endpoint
        dashboard_url = "http://localhost:8002/dashboard"
        response = requests.get(dashboard_url, timeout=10)
        
        if response.status_code == 200 and "Anomaly Detection System" in response.text:
            print_success("Dashboard is working!")
            return True
        else:
            print_error(f"Dashboard test failed. Status: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Failed to test dashboard: {e}")
        return False

def main():
    """Main test pipeline"""
    print_step("Starting Full Test Pipeline")
    
    # Track results
    results = {
        "setup": False,
        "dependencies": False,
        "unit_tests": False,
        "docker_services": False,
        "integration_tests": False,
        "performance_tests": False,
        "dashboard_test": False
    }
    
    try:
        # 1. Setup environment
        setup_environment()
        results["setup"] = True
        
        # 2. Install dependencies
        results["dependencies"] = install_dependencies()
        if not results["dependencies"]:
            print_error("Stopping pipeline due to dependency installation failure")
            return False
        
        # 3. Run unit tests
        results["unit_tests"] = run_unit_tests()
        
        # 4. Start Docker services
        results["docker_services"] = start_docker_services()
        if not results["docker_services"]:
            print_error("Stopping pipeline due to Docker services failure")
            return False
            
        # 5. Run integration tests
        results["integration_tests"] = run_integration_tests()
        
        # 6. Run performance tests
        results["performance_tests"] = run_performance_tests()
        
        # 7. Test dashboard
        results["dashboard_test"] = test_dashboard()
        
    finally:
        # Always cleanup
        cleanup_docker()
    
    # Print summary
    print_step("Test Pipeline Summary")
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print_success("\n🎉 All tests passed! Pipeline successful!")
        return True
    else:
        print_error("\n💥 Some tests failed! Check the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
