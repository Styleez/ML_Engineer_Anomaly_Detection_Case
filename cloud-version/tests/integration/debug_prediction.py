#!/usr/bin/env python3
"""
Debug de predição individual
"""
import asyncio
import httpx
import json

async def debug_prediction():
    INFERENCE_URL = "https://anomaly-inference-9266052327.us-central1.run.app"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Testar uma predição simples
        predict_data = {
            "timestamp": "1758207000",
            "value": 23.7
        }
        
        try:
            print(f"Sending prediction to: {INFERENCE_URL}/predict/test_live_sensor")
            print(f"Data: {json.dumps(predict_data, indent=2)}")
            
            response = await client.post(
                f"{INFERENCE_URL}/predict/test_live_sensor",
                json=predict_data
            )
            
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_prediction())
