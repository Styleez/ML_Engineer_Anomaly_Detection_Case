"""Performance tests for load and throughput validation"""

import pytest
import time
import statistics
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import os
import sys

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import professional test configuration
from tests.config import (
    TRAINING_SERVICE_URL,
    INFERENCE_SERVICE_URL,
    TEST_SERIES_PREFIX,
    TRAINING_TIMEOUT,
    INFERENCE_TIMEOUT
)


class TestLoadPerformance:
    """Test system under realistic load"""
    
    @pytest.mark.asyncio
    async def test_sustained_load(self):
        """Test sustained load at target RPS"""
        # Use professional configuration
        training_url = TRAINING_SERVICE_URL
        inference_url = INFERENCE_SERVICE_URL
        series_id = f"{TEST_SERIES_PREFIX}_sustained_load"
        
        # Train a model first
        train_data = {
            "timestamps": [1694336400 + i*60 for i in range(100)],
            "values": [42.0 + np.sin(i/10)*2 for i in range(100)]  # Realistic pattern
        }
        
        async with aiohttp.ClientSession() as session:
            # Train model
            async with session.post(
                f"{training_url}/fit/{series_id}", 
                json=train_data,
                timeout=TRAINING_TIMEOUT
            ) as resp:
                assert resp.status == 200
            
            # Prepare prediction data
            predict_data = {
                "timestamp": "1694336580",
                "value": 42.5
            }
            
            # Test sustained load for 10 seconds at 180 RPS
            duration = 10  # seconds
            target_rps = 180
            total_requests = target_rps * duration
            
            latencies = []
            errors = 0
            
            async def make_request():
                nonlocal errors
                start_time = time.time()
                try:
                    async with session.post(
                        f"{inference_url}/predict/{series_id}", 
                        json=predict_data,
                        timeout=INFERENCE_TIMEOUT
                    ) as resp:
                        if resp.status != 200:
                            errors += 1
                        latency = time.time() - start_time
                        latencies.append(latency)
                except Exception:
                    errors += 1
            
            # Execute load test
            start_time = time.time()
            
            # Create semaphore to control concurrency
            semaphore = asyncio.Semaphore(50)  # Max 50 concurrent requests
            
            async def controlled_request():
                async with semaphore:
                    await make_request()
            
            # Schedule requests with target timing
            tasks = []
            for i in range(total_requests):
                # Schedule each request at the right time
                delay = i / target_rps
                task = asyncio.create_task(asyncio.sleep(delay))
                tasks.append(task)
            
            # Wait for all delays, then execute requests
            await asyncio.gather(*tasks)
            
            request_tasks = [controlled_request() for _ in range(total_requests)]
            await asyncio.gather(*request_tasks, return_exceptions=True)
            
            total_time = time.time() - start_time
            
            # Validate results
            actual_rps = len(latencies) / total_time
            error_rate = errors / total_requests if total_requests > 0 else 0
            
            if latencies:
                p95_latency = np.percentile(latencies, 95)
                avg_latency = statistics.mean(latencies)
                
                print(f"Performance Results:")
                print(f"  RPS: {actual_rps:.1f} (target: {target_rps})")
                print(f"  P95 Latency: {p95_latency*1000:.1f}ms (target: <100ms)")
                print(f"  Avg Latency: {avg_latency*1000:.1f}ms")
                print(f"  Error Rate: {error_rate*100:.1f}%")
                
                # Assert requirements
                assert actual_rps >= target_rps * 0.9, f"RPS too low: {actual_rps:.1f}"
                assert p95_latency < 0.1, f"P95 latency too high: {p95_latency*1000:.1f}ms"
                assert error_rate < 0.01, f"Error rate too high: {error_rate*100:.1f}%"
    
    def test_memory_usage(self):
        """Test memory usage under load"""
        import psutil
        import os
        
        # Get current process
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate some load (simplified for unit test)
        from shared.models.anomaly.ml_model import AnomalyDetectionModel
        from shared.core.data_models import TimeSeries
        
        models = {}
        for i in range(100):  # Create 100 models
            timestamps = [1694336400 + j*60 for j in range(50)]
            values = [42.0 + j*0.1 for j in range(50)]
            time_series = TimeSeries(timestamps=timestamps, values=values)
            
            model = AnomalyDetectionModel()
            model.fit(time_series)
            models[f"sensor_{i}"] = model
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        print(f"Memory usage: {initial_memory:.1f}MB -> {final_memory:.1f}MB (+{memory_growth:.1f}MB)")
        
        # Memory growth should be reasonable
        assert memory_growth < 100, f"Memory growth too high: {memory_growth:.1f}MB"


class TestScenarios:
    """Test realistic usage scenarios"""
    
    def test_mixed_workload(self):
        """Test concurrent training and inference"""
        # This test needs to be updated to use the microservices architecture
        # For now, skipping as it references the old monolithic app structure
        pytest.skip("Test needs update for microservices architecture")
        
        # Simulate mixed workload
        def training_worker():
            for i in range(5):  # 5 training requests
                train_data = {
                    "timestamps": [1694336400 + j*60 for j in range(20)],
                    "values": [42.0 + j*0.1 + i for j in range(20)]
                }
                response = client.post(f"/fit/mixed_sensor_{i}", json=train_data)
                assert response.status_code == 200
                time.sleep(0.5)  # Realistic delay between training
        
        def inference_worker():
            # First train a model
            train_data = {
                "timestamps": [1694336400 + j*60 for j in range(20)],
                "values": [42.0 + j*0.1 for j in range(20)]
            }
            response = client.post("/fit/inference_sensor", json=train_data)
            assert response.status_code == 200
            
            # Then make many predictions
            for i in range(50):  # 50 inference requests
                predict_data = {
                    "timestamp": str(1694336400 + i*60),
                    "value": 42.0 + i*0.1
                }
                response = client.post("/predict/inference_sensor", json=predict_data)
                assert response.status_code == 200
                time.sleep(0.01)  # High frequency inference
        
        # Run both workloads concurrently
        with ThreadPoolExecutor(max_workers=2) as executor:
            training_future = executor.submit(training_worker)
            inference_future = executor.submit(inference_worker)
            
            # Both should complete without errors
            training_future.result()
            inference_future.result()
