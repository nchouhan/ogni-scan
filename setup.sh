#!/bin/bash

# CogniScan Setup Script
echo "🚀 Setting up CogniScan System..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "📦 Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp env.example .env
    echo "✅ .env file created. Please update it with your configuration."
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
poetry install

# Start services with Docker Compose
echo "🐳 Starting services with Docker Compose..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check if services are running
echo "🔍 Checking service status..."
docker-compose ps

# Initialize database
echo "🗄️ Initializing database..."
poetry run alembic upgrade head

# Create MinIO bucket
echo "🪣 Setting up MinIO bucket..."
docker-compose exec minio mc mb minio/cogni-resumes --ignore-existing

echo "✅ CogniScan setup complete!"
echo ""
echo "📋 Service URLs:"
echo "   - Backend API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - MinIO Console: http://localhost:9001"
echo "   - PostgreSQL: localhost:5432"
echo ""
echo "🔑 Default credentials:"
echo "   - Username: admin"
echo "   - Password: admin"
echo ""
echo "📝 Next steps:"
echo "   1. Update .env file with your OpenAI API key"
echo "   2. Access the API documentation at http://localhost:8000/docs"
echo "   3. Start the frontend: cd frontend && npm install && npm run dev"
echo "   4. Access the frontend at http://localhost:5173" 