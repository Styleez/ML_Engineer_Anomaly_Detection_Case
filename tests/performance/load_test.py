"""
Load testing script for Inference Service
"""
import asyncio
import aiohttp
import time
import numpy as np
import json
from datetime import datetime, timedelta
import statistics
from typing import List, Dict, Any
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Service configuration
INFERENCE_URL = "http://localhost:8001"
TRAINING_URL = "http://localhost:8000"

# Test configuration
SERIES_ID = "load_test_sensor"
REQUEST_TIMEOUT = 10  # seconds
CONCURRENT_LIMIT = 50  # Maximum concurrent connections

class LoadTest:
    def __init__(self):
        self.results: Dict[str, List[float]] = {}
        self.errors: Dict[str, int] = {}
        
    async def setup_test_data(self, session: aiohttp.ClientSession):
        """Train a model for testing"""
        print("\n🔧 Setting up test data...")
        
        # Generate training data (timestamps in ascending order)
        base_time = int(time.time())
        timestamps = [base_time + i*60 for i in range(100)]  # Ascending order
        values = [42.0 + np.sin(i/10)*2 for i in range(100)]
        
        train_data = {
            "timestamps": timestamps,
            "values": values,
            "threshold": 3.0
        }
        
        print(f"\n📊 Training data:")
        print(f"   • Points: {len(timestamps)}")
        print(f"   • Time range: {min(timestamps)} to {max(timestamps)}")
        print(f"   • Value range: {min(values):.2f} to {max(values):.2f}")
        
        # Train model
        try:
            async with session.post(
                f"{TRAINING_URL}/fit/{SERIES_ID}",
                json=train_data,
                timeout=REQUEST_TIMEOUT
            ) as response:
                if response.status != 200:
                    error_detail = await response.json()
                    print(f"❌ Failed to train model: {response.status}")
                    print(f"   Error: {error_detail.get('detail', 'Unknown error')}")
                    return False
                result = await response.json()
                print(f"✅ Model trained: {result}")
                return True
        except Exception as e:
            print(f"❌ Error training model: {e}")
            return False

    async def make_prediction(self, session: aiohttp.ClientSession) -> float:
        """Make a single prediction and return latency"""
        start_time = time.time()
        
        try:
            # Generate test data
            timestamp = int(time.time())
            value = 42.0 + np.random.normal(0, 1)
            
            data = {
                "timestamp": str(timestamp),
                "value": value
            }
            
            async with session.post(
                f"{INFERENCE_URL}/predict/{SERIES_ID}",
                json=data,
                timeout=REQUEST_TIMEOUT
            ) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")
                await response.json()
                
            latency = (time.time() - start_time) * 1000  # Convert to ms
            return latency
            
        except Exception as e:
            print(f"❌ Error making prediction: {e}")
            raise

    async def run_load_test(self, concurrent_users: int, duration_seconds: int = 10):
        """Run load test with specified number of concurrent users"""
        print(f"\n🔥 Running load test with {concurrent_users} concurrent users for {duration_seconds}s...")
        
        # Initialize results for this test
        test_key = f"users_{concurrent_users}"
        self.results[test_key] = []
        self.errors[test_key] = 0
        
        # Create session
        async with aiohttp.ClientSession() as session:
            # First ensure we have test data
            if not await self.setup_test_data(session):
                print("❌ Failed to setup test data")
                return
            
            # Create semaphore to limit concurrency
            semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
            
            async def controlled_request():
                async with semaphore:
                    try:
                        latency = await self.make_prediction(session)
                        self.results[test_key].append(latency)
                    except Exception:
                        self.errors[test_key] += 1
            
            # Run test for specified duration
            end_time = time.time() + duration_seconds
            tasks = []
            
            while time.time() < end_time:
                # Create tasks for each user
                for _ in range(concurrent_users):
                    task = asyncio.create_task(controlled_request())
                    tasks.append(task)
                
                # Wait a bit before next batch
                await asyncio.sleep(1.0)
            
            # Wait for all requests to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Calculate metrics
            if self.results[test_key]:
                avg_latency = statistics.mean(self.results[test_key])
                p95_latency = np.percentile(self.results[test_key], 95)
                max_latency = max(self.results[test_key])
                total_requests = len(self.results[test_key]) + self.errors[test_key]
                error_rate = (self.errors[test_key] / total_requests) * 100 if total_requests > 0 else 0
                rps = len(self.results[test_key]) / duration_seconds
                
                print(f"\n📊 Results for {concurrent_users} users:")
                print(f"   • Requests/second: {rps:.1f}")
                print(f"   • Average latency: {avg_latency:.1f}ms")
                print(f"   • P95 latency: {p95_latency:.1f}ms")
                print(f"   • Max latency: {max_latency:.1f}ms")
                print(f"   • Error rate: {error_rate:.1f}%")
                print(f"   • Total requests: {total_requests}")
                
                # Validate against requirements
                if p95_latency > 100:
                    print(f"⚠️  P95 latency ({p95_latency:.1f}ms) exceeds target (100ms)")
                if error_rate > 1:
                    print(f"⚠️  Error rate ({error_rate:.1f}%) exceeds target (1%)")
            else:
                print("❌ No successful requests")

async def main():
    """Run load tests with increasing concurrency"""
    load_test = LoadTest()
    
    # Test with different concurrent users
    concurrent_users = [1, 10, 100, 200, 500]
    
    for users in concurrent_users:
        await load_test.run_load_test(users, duration_seconds=30)
        # Small delay between tests
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
