"""
Load testing script for Training Service
"""
import asyncio
import aiohttp
import time
import numpy as np
import json
import statistics
import os
import sys
from datetime import datetime
from typing import List, Dict, Any

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

# Import professional test configuration
try:
    from tests.config import (
        TRAINING_SERVICE_URL,
        TRAINING_TIMEOUT,
        TEST_SERIES_PREFIX
    )
except ImportError:
    # Fallback configuration if running standalone
    TRAINING_SERVICE_URL = "http://localhost:8000"
    TRAINING_TIMEOUT = 60
    TEST_SERIES_PREFIX = "test_sensor"

# Service configuration from professional config
TRAINING_URL = TRAINING_SERVICE_URL
REQUEST_TIMEOUT = TRAINING_TIMEOUT  # seconds
CONCURRENT_LIMIT = 20  # Maximum concurrent connections

class TrainingLoadTest:
    def __init__(self):
        self.results: Dict[str, List[float]] = {}
        self.errors: Dict[str, int] = {}
        
    async def train_model(self, session: aiohttp.ClientSession, series_id: str) -> float:
        """Train a model and return latency"""
        start_time = time.time()
        
        try:
            # Generate training data
            base_time = int(time.time())
            timestamps = [base_time + i*60 for i in range(100)]  # Ascending order
            values = [42.0 + np.sin(i/10)*2 for i in range(100)]
            
            train_data = {
                "timestamps": timestamps,
                "values": values,
                "threshold": 3.0
            }
            
            async with session.post(
                f"{TRAINING_URL}/fit/{series_id}",
                json=train_data,
                timeout=REQUEST_TIMEOUT
            ) as response:
                if response.status != 200:
                    error_detail = await response.json()
                    raise Exception(f"HTTP {response.status}: {error_detail.get('detail', 'Unknown error')}")
                await response.json()
                
            latency = (time.time() - start_time) * 1000  # Convert to ms
            return latency
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error training model: {error_msg}")
            
            # Stop test if HTTP 500 errors occur
            if "HTTP 500" in error_msg:
                print(f"🛑 Stopping load test due to HTTP 500 errors")
                raise SystemExit("Load test stopped due to HTTP 500 Internal Server Error")
            
            raise

    async def run_load_test(self, concurrent_models: int, duration_seconds: int = 10):
        """Run load test training multiple models concurrently"""
        print(f"\n🔥 Running training load test with {concurrent_models} concurrent models for {duration_seconds}s...")
        
        # Initialize results for this test
        test_key = f"models_{concurrent_models}"
        self.results[test_key] = []
        self.errors[test_key] = 0
        
        # Create session
        async with aiohttp.ClientSession() as session:
            # Create semaphore to limit concurrency
            semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
            
            async def controlled_request(model_idx: int):
                async with semaphore:
                    try:
                        series_id = f"{TEST_SERIES_PREFIX}_load_training_{model_idx}"
                        latency = await self.train_model(session, series_id)
                        self.results[test_key].append(latency)
                    except Exception:
                        self.errors[test_key] += 1
            
            # Create tasks for each model
            tasks = []
            for i in range(concurrent_models):
                task = asyncio.create_task(controlled_request(i))
                tasks.append(task)
            
            # Wait for all training tasks to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Calculate metrics
            if self.results[test_key]:
                avg_latency = statistics.mean(self.results[test_key])
                p95_latency = np.percentile(self.results[test_key], 95)
                max_latency = max(self.results[test_key])
                total_requests = len(self.results[test_key]) + self.errors[test_key]
                error_rate = (self.errors[test_key] / total_requests) * 100 if total_requests > 0 else 0
                models_per_second = len(self.results[test_key]) / duration_seconds
                
                print(f"\n📊 Results for {concurrent_models} concurrent models:")
                print(f"   • Models/second: {models_per_second:.1f}")
                print(f"   • Average latency: {avg_latency:.1f}ms")
                print(f"   • P95 latency: {p95_latency:.1f}ms")
                print(f"   • Max latency: {max_latency:.1f}ms")
                print(f"   • Error rate: {error_rate:.1f}%")
                print(f"   • Total models: {total_requests}")
                print(f"   • Successful models: {len(self.results[test_key])}")
                print(f"   • Failed models: {self.errors[test_key]}")
                
                # Validate against requirements
                if error_rate > 1:
                    print(f"⚠️  Error rate ({error_rate:.1f}%) exceeds target (1%)")
            else:
                print("❌ No successful training")

async def main():
    """Run load tests with increasing concurrency"""
    load_test = TrainingLoadTest()
    
    # Test with different concurrent models
    concurrent_models = [1, 10, 100]
    
    for models in concurrent_models:
        await load_test.run_load_test(models, duration_seconds=10)
        # Longer delay between training tests
        await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
