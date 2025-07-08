# CogniScan - Resume Insight Assistant Platform

A GPT-like intelligent assistant platform that allows recruiters to query and understand candidate resumes naturally and smartly. The system supports semantic search, summarization, justifications, and structured output through a responsive frontend.

## 🚀 Features

- **Resume Upload & Processing**: Support for PDF, DOCX, and TXT files
- **Intelligent Parsing**: Extract structured metadata using Unstructured.io and spaCy
- **Vector Search**: OpenAI embeddings for semantic resume search
- **AI-Powered Analysis**: GPT-4 assistant for natural language queries
- **Dual Authentication**: JWT for recruiters, Basic Auth for system-to-system calls
- **Scalable Architecture**: PostgreSQL, MinIO, Redis, and FastAPI

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │   External      │
│   (React)       │◄──►│   (FastAPI)     │◄──►│   Services      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │   MinIO         │    │   OpenAI        │
│   (Metadata)    │    │   (File Store)  │    │   (Embeddings)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🛠️ Tech Stack

### Backend
- **Python 3.10+** with FastAPI
- **PostgreSQL** with SQLAlchemy ORM
- **MinIO** for object storage
- **Redis** for caching and Celery
- **OpenAI API** for embeddings and GPT-4
- **Poetry** for dependency management

### Frontend
- **React** with TypeScript
- **Tailwind CSS** for styling
- **Material-UI (MUI)** for components
- **Vite** for build tooling
- **Axios** for API communication

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.10+
- Node.js 18+ (for frontend development)
- Poetry (will be installed automatically)
- OpenAI API key
- MinIO (for file storage)
- Redis (optional, for caching)

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd cogni-scan
```

### 2. Run Setup Script
```bash
./setup.sh
```

This script will:
- Install Poetry if not present
- Create `.env` file from template
- Install Python dependencies
- Start all services with Docker Compose
- Initialize database schema
- Create MinIO bucket

### 3. Configure Environment
Edit the `.env` file and add your OpenAI API key:
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### 4. Access the Application
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Frontend**: http://localhost:5173 (after running `npm run dev` in frontend directory)
- **MinIO Console**: http://localhost:9001
- **Default Credentials**: admin/admin

## 📚 API Documentation

### Authentication

#### JWT Authentication (for recruiters)
```bash
# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'

# Use token
curl -X GET "http://localhost:8000/api/v1/resumes/" \
  -H "Authorization: Bearer <your_token>"
```

#### Basic Authentication (for system-to-system)
```bash
curl -X POST "http://localhost:8000/api/v1/auth/basic-auth" \
  -H "Authorization: Basic YWRtaW46YWRtaW4="
```

### Resume Operations

#### Upload Resume
```bash
curl -X POST "http://localhost:8000/api/v1/resumes/upload" \
  -H "Authorization: Bearer <your_token>" \
  -F "file=@resume.pdf"
```

#### List Resumes
```bash
curl -X GET "http://localhost:8000/api/v1/resumes/?page=1&size=10" \
  -H "Authorization: Bearer <your_token>"
```

#### Search Resumes
```bash
curl -X POST "http://localhost:8000/api/v1/resumes/search" \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Python developer with 5+ years experience",
    "skills": ["Python", "Django"],
    "domain": "saas",
    "min_experience": 5,
    "limit": 10
  }'
```

## 🗄️ Database Schema

### Resumes Table
- `id`: Primary key
- `filename`: MinIO file path
- `original_filename`: Original file name
- `candidate_name`: Extracted name
- `email`: Contact email
- `phone`: Contact phone
- `current_role`: Current position
- `current_company`: Current employer
- `years_experience`: Calculated experience
- `domain`: Industry classification
- `skills`: JSON array of skills
- `technologies`: JSON array of technologies
- `experience`: JSON array of work history
- `education`: JSON array of education
- `is_processed`: Processing status
- `is_indexed`: Vector indexing status

### Resume Chunks Table
- `id`: Primary key
- `resume_id`: Foreign key to resumes
- `chunk_index`: Chunk order
- `content`: Text content
- `chunk_size`: Character count
- `vector_id`: OpenAI vector ID
- `section_type`: Content classification

## 🔧 Development

### Running Locally

#### Prerequisites
- Docker and Docker Compose
- Python 3.10+
- Node.js 18+ (for frontend)
- OpenAI API key

#### Backend Setup

1. **Clone and Setup**
```bash
git clone <repository-url>
cd cogni-scan
```

2. **Create Environment File**
```bash
cp env.example .env
# Edit .env and add your OpenAI API key
```

3. **Install Python Dependencies**
```bash
poetry install
```

4. **Start Required Services**
```bash
# Start PostgreSQL and Redis (MinIO should be running separately)
docker-compose up -d postgres

# Or start all services if you have MinIO running
docker-compose up -d
```

5. **Run Database Migrations**
```bash
poetry run alembic upgrade head
```

6. **Start Backend Development Server**
```bash
# From the project root directory
poetry run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup

1. **Navigate to Frontend Directory**
```bash
cd frontend
```

2. **Install Dependencies**
```bash
npm install
```

3. **Start Development Server**
```bash
npm run dev
```

4. **Access Frontend**
- Frontend will be available at: http://localhost:5173 (or next available port)

#### External Services Setup

**MinIO Setup (Required for file uploads)**
```bash
# Start MinIO using Docker
docker run -d \
  --name minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  minio/minio server /data --console-address ":9001"

# Create the required bucket
docker exec minio mc mb minio/cogni-resumes --ignore-existing
```

**Redis Setup (Optional, for caching)**
```bash
# Start Redis using Docker
docker run -d --name redis -p 6379:6379 redis:alpine
```

#### Complete Setup Script

Alternatively, use the provided setup script:
```bash
chmod +x setup.sh
./setup.sh
```

**Note**: The setup script assumes you have MinIO and Redis running externally. If not, start them manually as shown above.

### Troubleshooting

#### Common Issues

**1. Backend Import Error: "No module named 'backend'"**
```bash
# Make sure you're running from the project root directory
cd /path/to/cogni-scan
poetry run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**2. MinIO Connection Issues**
```bash
# Check if MinIO is running
docker ps | grep minio

# If not running, start it:
docker run -d --name minio -p 9000:9000 -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  minio/minio server /data --console-address ":9001"
```

**3. Database Connection Issues**
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# If not running, start it:
docker-compose up -d postgres
```

**4. Frontend Port Already in Use**
```bash
# The frontend will automatically try the next available port
# Check the terminal output for the correct URL
```

**5. OpenAI API Key Issues**
- Make sure your OpenAI API key is set in the `.env` file
- Verify the key is valid and has sufficient credits
- Check the backend logs for API errors

#### Service URLs and Ports
- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:5173 (or next available port)
- **PostgreSQL**: localhost:5442
- **MinIO**: http://localhost:9000 (API), http://localhost:9001 (Console)
- **Redis**: localhost:6379

### Database Migrations

```bash
# Create new migration
poetry run alembic revision --autogenerate -m "Description"

# Apply migrations
poetry run alembic upgrade head

# Rollback migration
poetry run alembic downgrade -1
```

### Testing

```bash
# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=backend
```

## 🐳 Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down

# Rebuild and restart
docker-compose up -d --build

# Clean up volumes
docker-compose down -v
```

## 📁 Project Structure

```
cogni-scan/
├── backend/
│   ├── api/                 # API routes
│   ├── config/              # Configuration
│   ├── models/              # Database models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   └── main.py              # FastAPI app
├── frontend/                # React frontend
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── lib/            # Utilities and API
│   │   └── App.tsx         # Main app component
│   ├── package.json        # Frontend dependencies
│   └── vite.config.ts      # Vite configuration
├── alembic/                 # Database migrations
├── docker-compose.yml       # Docker services
├── Dockerfile               # Backend container
├── pyproject.toml           # Poetry configuration
├── setup.sh                 # Setup script
└── README.md               # This file
```

## 🔒 Security

- JWT tokens for user authentication
- Basic auth for system-to-system calls
- Environment variables for sensitive data
- Input validation with Pydantic
- File type and size restrictions

## 🚀 Deployment

### Production Checklist
- [ ] Update `.env` with production values
- [ ] Set secure JWT secret
- [ ] Configure proper CORS origins
- [ ] Set up SSL/TLS certificates
- [ ] Configure database backups
- [ ] Set up monitoring and logging
- [ ] Configure rate limiting
- [ ] Set up CI/CD pipeline

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the API documentation at `/docs`
- Review the logs in `cogni_scan.log`

---

**Built with ❤️ for better recruitment processes** 