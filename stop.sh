#!/bin/bash

echo "�� Stopping CogniScan services..."

# Stop backend and frontend dev servers (if running in background)
pkill -f "uvicorn backend.main:app" 2>/dev/null
pkill -f "vite" 2>/dev/null

# Stop Docker containers
docker stop minio redis cogni_postgres 2>/dev/null
docker rm minio redis cogni_postgres 2>/dev/null

echo "✅ All CogniScan services stopped."