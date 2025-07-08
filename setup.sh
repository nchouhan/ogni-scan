#!/bin/bash

echo "🚀 CogniScan: Complete Auto Setup..."

# Check for required tools
for tool in docker docker-compose node npm poetry; do
  if ! command -v $tool &> /dev/null; then
    echo "❌ $tool is not installed. Please install $tool first."
    exit 1
  fi
done

# Create .env if missing
if [ ! -f .env ]; then
  echo "📝 Creating .env file..."
  cp env.example .env
  echo "✅ .env file created. Please update it with your OpenAI API key."
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
poetry install

# Stop any existing containers to avoid conflicts
echo "🛑 Stopping any existing containers..."
docker stop minio redis cogni_postgres 2>/dev/null || true
docker rm minio redis cogni_postgres 2>/dev/null || true

# Start PostgreSQL
echo "🐘 Starting PostgreSQL..."
docker-compose up -d postgres

# Start MinIO if not already running
if ! docker ps | grep -q minio; then
  echo "🪣 Starting MinIO..."
  docker run -d \
    --name minio \
    -p 9000:9000 \
    -p 9001:9001 \
    -e "MINIO_ROOT_USER=minioadmin" \
    -e "MINIO_ROOT_PASSWORD=minioadmin" \
    minio/minio server /data --console-address ":9001"
fi

# Start Redis if not already running
if ! docker ps | grep -q redis; then
  echo "🔴 Starting Redis..."
  docker run -d --name redis -p 6379:6379 redis:alpine
fi

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check if services are running
echo "🔍 Checking service status..."
docker ps | grep -E "(postgres|minio|redis)"

# Initialize database
echo "🗄️ Initializing database..."
poetry run alembic upgrade head

# Create MinIO bucket
echo "🪣 Setting up MinIO bucket..."
docker exec minio mc mb minio/cogni-resumes --ignore-existing

# Setup frontend
echo "🎨 Setting up frontend..."
cd frontend
if [ ! -d "node_modules" ]; then
  echo "📦 Installing frontend dependencies..."
  npm install
fi
cd ..

# Start backend server in background
echo "🔧 Starting backend server..."
poetry run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 10

# Start frontend in background
echo "🎨 Starting frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ CogniScan setup complete and all services started!"
echo ""
echo "📋 Service URLs:"
echo "   - Frontend: http://localhost:5173 (or next available port)"
echo "   - Backend API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - MinIO Console: http://localhost:9001"
echo "   - PostgreSQL: localhost:5442"
echo "   - Redis: localhost:6379"
echo ""
echo "🔑 Default credentials:"
echo "   - Username: admin"
echo "   - Password: admin"
echo ""
echo "📝 Important:"
echo "   1. Update .env file with your OpenAI API key"
echo "   2. All services are now running automatically"
echo "   3. To stop all services: kill $BACKEND_PID $FRONTEND_PID; docker stop minio redis cogni_postgres"
echo ""
echo "🚀 CogniScan is ready to use!"
echo "   Open http://localhost:5173 in your browser"