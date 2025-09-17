#!/bin/bash

# Start Redis in background
redis-server --daemonize yes --maxmemory 256mb --maxmemory-policy allkeys-lru

# Wait a bit for Redis to start
sleep 2

# Start the FastAPI service
exec uvicorn main:app --host 0.0.0.0 --port 8000
