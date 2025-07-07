# CogniScan Testing Guide

This guide helps you verify that CogniScan is working correctly after file uploads and processing.

## 🚀 Quick Status Check

### 1. Service Status
```bash
# Check if all services are running
docker-compose ps

# Expected output:
# - cogni_postgres: Up (healthy)
# - cogni_backend: Up (healthy)
```

### 2. API Health Check
```bash
# Test if the API is responding
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","service":"CogniScan API","version":"1.0.0"}
```

## 📊 Database Verification

### 1. Check Uploaded Resumes
```bash
# Connect to PostgreSQL and check uploaded files
docker exec cogni_postgres psql -U postgres -d cogni_db -c "
SELECT 
    id,
    original_filename,
    file_size,
    file_type,
    is_processed,
    chunks_count,
    created_at
FROM cogni.resumes 
ORDER BY created_at DESC;"
```

### 2. Check Extracted Metadata
```bash
# Verify that resume parsing extracted information correctly
docker exec cogni_postgres psql -U postgres -d cogni_db -c "
SELECT 
    id,
    original_filename,
    candidate_name,
    email,
    current_role,
    current_company,
    years_experience,
    domain,
    skills,
    technologies
FROM cogni.resumes 
ORDER BY created_at DESC;"
```

### 3. Check Resume Chunks
```bash
# Verify that resumes were chunked for vector search
docker exec cogni_postgres psql -U postgres -d cogni_db -c "
SELECT 
    resume_id,
    chunk_index,
    section_type,
    chunk_size,
    LEFT(content, 100) as content_preview
FROM cogni.resume_chunks 
ORDER BY resume_id, chunk_index 
LIMIT 10;"
```

### 4. Database Schema Verification
```bash
# Check if all required tables exist
docker exec cogni_postgres psql -U postgres -d cogni_db -c "\dt cogni.*"

# Check table structure
docker exec cogni_postgres psql -U postgres -d cogni_db -c "\d cogni.resumes"
docker exec cogni_postgres psql -U postgres -d cogni_db -c "\d cogni.resume_chunks"
```

## 📁 File Storage Verification

### 1. Check MinIO Bucket (if using MinIO)
```bash
# If you have MinIO client installed
mc alias set myminio http://localhost:9000 minioadmin minioadmin
mc ls myminio/cogni-resumes

# Or check via API
curl -u minioadmin:minioadmin http://localhost:9000/cogni-resumes
```

### 2. Check File Paths in Database
```bash
# Verify file paths are stored correctly
docker exec cogni_postgres psql -U postgres -d cogni_db -c "
SELECT 
    original_filename,
    filename,
    file_path,
    file_size
FROM cogni.resumes;"
```

## 🔐 Authentication Testing

### 1. Get JWT Token
```bash
# Login to get access token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'

# Save the token from response
TOKEN="your_jwt_token_here"
```

### 2. Test Protected Endpoints
```bash
# List all resumes
curl -X GET "http://localhost:8000/api/v1/resumes/" \
  -H "Authorization: Bearer $TOKEN"

# Get specific resume
curl -X GET "http://localhost:8000/api/v1/resumes/1" \
  -H "Authorization: Bearer $TOKEN"
```

## 📈 Processing Verification

### 1. Check Processing Status
```bash
# Verify all resumes are processed
docker exec cogni_postgres psql -U postgres -d cogni_db -c "
SELECT 
    COUNT(*) as total_resumes,
    COUNT(CASE WHEN is_processed = true THEN 1 END) as processed_resumes,
    COUNT(CASE WHEN is_indexed = true THEN 1 END) as indexed_resumes,
    AVG(chunks_count) as avg_chunks_per_resume
FROM cogni.resumes;"
```

### 2. Check Extracted Skills
```bash
# See what skills were extracted
docker exec cogni_postgres psql -U postgres -d cogni_db -c "
SELECT 
    original_filename,
    skills,
    technologies
FROM cogni.resumes 
WHERE skills IS NOT NULL;"
```

## 🔍 Search Functionality Testing

### 1. Test Resume Search
```bash
# Search for resumes with specific skills
curl -X POST "http://localhost:8000/api/v1/resumes/search" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Python developer",
    "filters": {
      "skills": ["Python", "React"],
      "domain": "tech"
    },
    "limit": 10
  }'
```

### 2. Test Semantic Search
```bash
# Test semantic search capabilities
curl -X POST "http://localhost:8000/api/v1/resumes/search" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "experienced software engineer with cloud expertise",
    "limit": 5
  }'
```

## 🐛 Troubleshooting

### 1. Check Backend Logs
```bash
# View recent backend logs
docker-compose logs --tail=50 backend

# Look for specific errors
docker-compose logs backend | grep -i "error\|exception\|failed"
```

### 2. Check Database Connection
```bash
# Test database connectivity
docker exec cogni_postgres psql -U postgres -d cogni_db -c "SELECT version();"
```

### 3. Check File Upload Issues
```bash
# Verify file size limits
docker exec cogni_postgres psql -U postgres -d cogni_db -c "
SELECT 
    original_filename,
    file_size,
    CASE 
        WHEN file_size > 10485760 THEN 'TOO LARGE'
        ELSE 'OK'
    END as size_status
FROM cogni.resumes;"
```

## 📋 Expected Results

### After Successful Upload:
- ✅ Files appear in `cogni.resumes` table
- ✅ `is_processed` = true for all uploaded files
- ✅ `chunks_count` > 0 (typically 6-10 chunks per resume)
- ✅ Metadata fields populated (name, email, skills, etc.)
- ✅ Chunks created in `cogni.resume_chunks` table

### Common Issues:
- ❌ `is_processed` = false: Resume parsing failed
- ❌ `chunks_count` = 0: Chunking failed
- ❌ Empty metadata: spaCy model or parsing failed
- ❌ File not in storage: MinIO upload failed

## 🧪 API Testing with Swagger UI

1. Open `http://localhost:8000/docs` in your browser
2. Click "Authorize" and enter: `Bearer your_jwt_token`
3. Test endpoints:
   - `GET /api/v1/resumes/` - List all resumes
   - `GET /api/v1/resumes/{id}` - Get specific resume
   - `POST /api/v1/resumes/search` - Search resumes
   - `POST /api/v1/resumes/upload` - Upload new resume

## 📊 Performance Metrics

### Check Processing Times
```bash
# See how long processing took
docker exec cogni_postgres psql -U postgres -d cogni_db -c "
SELECT 
    original_filename,
    created_at,
    processed_at,
    EXTRACT(EPOCH FROM (processed_at - created_at)) as processing_time_seconds
FROM cogni.resumes 
WHERE processed_at IS NOT NULL;"
```

### Check File Sizes
```bash
# Analyze file size distribution
docker exec cogni_postgres psql -U postgres -d cogni_db -c "
SELECT 
    file_type,
    COUNT(*) as count,
    AVG(file_size) as avg_size,
    MIN(file_size) as min_size,
    MAX(file_size) as max_size
FROM cogni.resumes 
GROUP BY file_type;"
```

---

## 🎯 Quick Verification Checklist

- [ ] Services running (`docker-compose ps`)
- [ ] API responding (`curl /health`)
- [ ] Files in database (`SELECT FROM cogni.resumes`)
- [ ] Processing complete (`is_processed = true`)
- [ ] Chunks created (`chunks_count > 0`)
- [ ] Metadata extracted (name, email, skills)
- [ ] Authentication working (JWT token)
- [ ] Search functional (API calls return results)

If all items are checked, your CogniScan installation is working correctly! 🎉 