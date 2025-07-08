import os
import tempfile
from typing import List
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Query
from sqlalchemy.orm import Session
from backend.models.database import get_db
from backend.models.resume import Resume, ResumeChunk
from backend.schemas.resume import (
    ResumeUploadResponse, ResumeProcessingResponse, ResumeResponse,
    ResumeListResponse, ResumeSearchRequest, ResumeSearchResponse, CandidateMatch
)
from backend.schemas.chat import ChatMessageRequest, ChatMessageResponse
from backend.services.minio_service import minio_service
# # from backend.services.resume_parser import resume_parser  # Commented out due to dependency issues
from backend.services.openai_service import openai_service
from backend.services.auth_service import get_current_user_jwt
from backend.config.settings import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resumes", tags=["Resumes"])


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user_jwt),
    db: Session = Depends(get_db)
):
    """Upload a resume file"""
    try:
        logger.info(f"🚀 Starting resume upload for file: {file.filename} (size: {file.size} bytes)")
        
        # Validate file type
        file_extension = file.filename.split('.')[-1].lower()
        logger.info(f"📄 File extension detected: {file_extension}")
        
        if file_extension not in settings.allowed_extensions:
            logger.error(f"❌ Invalid file type: {file_extension}. Allowed: {settings.allowed_extensions}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {file_extension} not allowed. Allowed types: {settings.allowed_extensions}"
            )
        
        # Validate file size
        if file.size > settings.max_file_size:
            logger.error(f"❌ File too large: {file.size} bytes. Max: {settings.max_file_size}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size {file.size} exceeds maximum allowed size {settings.max_file_size}"
            )
        
        logger.info(f"✅ File validation passed - proceeding with upload")
        
        # Upload to MinIO
        logger.info(f"📤 Uploading file to MinIO storage...")
        file_path = minio_service.upload_file(
            file.file,
            file.filename,
            content_type=file.content_type
        )
        logger.info(f"✅ File uploaded to MinIO: {file_path}")
        
        # Create database record
        logger.info(f"💾 Creating database record...")
        resume = Resume(
            filename=file_path,
            original_filename=file.filename,
            file_path=file_path,
            file_size=file.size,
            file_type=file_extension
        )
        
        db.add(resume)
        db.commit()
        db.refresh(resume)
        logger.info(f"✅ Database record created with ID: {resume.id}")
        
        # Trigger processing (in production, this would be async)
        logger.info(f"🔄 Starting resume processing pipeline for ID: {resume.id}")
        await process_resume(resume.id, db)
        
        logger.info(f"🎉 Resume upload completed successfully for ID: {resume.id}")
        
        return ResumeUploadResponse(
            id=resume.id,
            filename=resume.filename,
            original_filename=resume.original_filename,
            file_size=resume.file_size,
            file_type=resume.file_type
        )
        
    except Exception as e:
        logger.error(f"❌ Error uploading resume: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error uploading resume"
        )


@router.get("/", response_model=ResumeListResponse)
async def list_resumes(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user_jwt),
    db: Session = Depends(get_db)
):
    """List all resumes with pagination"""
    try:
        offset = (page - 1) * size
        
        # Get total count
        total = db.query(Resume).count()
        
        # Get resumes
        resumes = db.query(Resume).offset(offset).limit(size).all()
        
        # Convert to response format
        resume_responses = []
        for resume in resumes:
            metadata = {
                "name": resume.candidate_name,
                "email": resume.email,
                "phone": resume.phone,
                "current_role": resume.current_role,
                "current_company": resume.current_company,
                "years_experience": resume.years_experience,
                "domain": resume.domain,
                "skills": resume.skills or [],
                "technologies": resume.technologies or [],
                "experience": resume.experience or [],
                "education": resume.education or []
            }
            
            resume_responses.append(ResumeResponse(
                id=resume.id,
                filename=resume.filename,
                original_filename=resume.original_filename,
                file_size=resume.file_size,
                file_type=resume.file_type,
                metadata=metadata,
                is_processed=resume.is_processed,
                is_indexed=resume.is_indexed,
                chunks_count=resume.chunks_count,
                created_at=resume.created_at,
                processed_at=resume.processed_at
            ))
        
        return ResumeListResponse(
            resumes=resume_responses,
            total=total,
            page=page,
            size=size
        )
        
    except Exception as e:
        logger.error(f"Error listing resumes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing resumes"
        )


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: int,
    current_user: dict = Depends(get_current_user_jwt),
    db: Session = Depends(get_db)
):
    """Get a specific resume by ID"""
    try:
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )
        
        metadata = {
            "name": resume.candidate_name,
            "email": resume.email,
            "phone": resume.phone,
            "current_role": resume.current_role,
            "current_company": resume.current_company,
            "years_experience": resume.years_experience,
            "domain": resume.domain,
            "skills": resume.skills or [],
            "technologies": resume.technologies or [],
            "experience": resume.experience or [],
            "education": resume.education or []
        }
        
        return ResumeResponse(
            id=resume.id,
            filename=resume.filename,
            original_filename=resume.original_filename,
            file_size=resume.file_size,
            file_type=resume.file_type,
            metadata=metadata,
            is_processed=resume.is_processed,
            is_indexed=resume.is_indexed,
            chunks_count=resume.chunks_count,
            created_at=resume.created_at,
            processed_at=resume.processed_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting resume {resume_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting resume"
        )


@router.post("/search", response_model=ResumeSearchResponse)
async def search_resumes(
    search_request: ResumeSearchRequest,
    current_user: dict = Depends(get_current_user_jwt),
    db: Session = Depends(get_db)
):
    """Search resumes using semantic search"""
    try:
        import time
        start_time = time.time()
        
        # For now, implement a simple keyword-based search
        # In production, this would use vector search
        query = search_request.query.lower()
        
        # Build filter conditions
        filters = []
        if search_request.skills:
            # Filter by skills (simplified)
            pass
        
        if search_request.domain:
            filters.append(Resume.domain == search_request.domain)
        
        if search_request.min_experience is not None:
            filters.append(Resume.years_experience >= search_request.min_experience)
        
        if search_request.max_experience is not None:
            filters.append(Resume.years_experience <= search_request.max_experience)
        
        # Query resumes
        query_builder = db.query(Resume).filter(Resume.is_processed == True)
        
        for filter_condition in filters:
            query_builder = query_builder.filter(filter_condition)
        
        resumes = query_builder.limit(search_request.limit).all()
        
        # Simple scoring based on keyword matching
        candidates = []
        for resume in resumes:
            score = 0
            skills_match = []
            
            # Check skills match
            if resume.skills:
                for skill in search_request.skills or []:
                    if skill.lower() in [s.lower() for s in resume.skills]:
                        score += 10
                        skills_match.append(skill)
            
            # Check query keywords in text
            resume_text = f"{resume.candidate_name} {resume.current_role} {resume.current_company}"
            if resume.skills:
                resume_text += " " + " ".join(resume.skills)
            
            for word in query.split():
                if word in resume_text.lower():
                    score += 5
            
            # Calculate match percentage
            match_percentage = min(100, score)
            
            # Determine relevance score
            if match_percentage >= 70:
                relevance_score = "High"
            elif match_percentage >= 40:
                relevance_score = "Medium"
            else:
                relevance_score = "Low"
            
            candidates.append(CandidateMatch(
                resume_id=resume.id,
                candidate_name=resume.candidate_name or "Unknown",
                current_role=resume.current_role or "Unknown",
                current_company=resume.current_company or "Unknown",
                match_percentage=match_percentage,
                relevance_score=relevance_score,
                skills_match=skills_match,
                justification=f"Found {len(skills_match)} matching skills and relevant experience",
                highlights=resume.skills[:3] if resume.skills else []
            ))
        
        # Sort by match percentage
        candidates.sort(key=lambda x: x.match_percentage, reverse=True)
        
        search_time = time.time() - start_time
        
        return ResumeSearchResponse(
            query=search_request.query,
            candidates=candidates,
            total_found=len(candidates),
            search_time=search_time
        )
        
    except Exception as e:
        logger.error(f"Error searching resumes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error searching resumes"
        )


@router.post("/chat")
async def chat_with_assistant(
    chat_request: ChatMessageRequest,
    current_user: dict = Depends(get_current_user_jwt),
    db: Session = Depends(get_db)
):
    """Chat with OpenAI Assistant for intelligent resume search"""
    try:
        logger.info(f"💬 Chat request received: '{chat_request.message}'")
        logger.info(f"👤 User: {current_user.get('username', 'unknown')}")
        
        # Use OpenAI Assistant to search through resumes
        logger.info(f"🔍 Starting OpenAI Assistant search...")
        assistant_result = openai_service.search_with_assistant(chat_request.message)
        
        logger.info(f"✅ Assistant search completed")
        logger.info(f"📊 Response length: {len(assistant_result.get('response', ''))} characters")
        logger.info(f"🧵 Thread ID: {assistant_result.get('thread_id', 'N/A')}")
        logger.info(f"📈 Status: {assistant_result.get('status', 'N/A')}")
        
        return {
            "message": chat_request.message,
            "response": assistant_result["response"],
            "thread_id": assistant_result["thread_id"],
            "status": assistant_result["status"]
        }
        
    except Exception as e:
        logger.error(f"❌ Error in chat with assistant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat request: {str(e)}"
        )


async def process_resume(resume_id: int, db: Session):
    """Process a resume (parse, extract metadata, create embeddings)"""
    try:
        logger.info(f"🔄 Starting resume processing for ID: {resume_id}")
        
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            logger.error(f"❌ Resume not found with ID: {resume_id}")
            return
        
        logger.info(f"📋 Processing resume: {resume.original_filename} (ID: {resume_id})")
        
        # Download file from MinIO
        logger.info(f"📥 Downloading file from MinIO: {resume.filename}")
        file_data = minio_service.download_file(resume.filename)
        if not file_data:
            logger.error(f"❌ Could not download file from MinIO: {resume.filename}")
            raise Exception("Could not download file from MinIO")
        
        logger.info(f"✅ File downloaded successfully from MinIO")
        
        # Save to temporary file
        logger.info(f"💾 Creating temporary file for processing...")
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{resume.file_type}") as temp_file:
            temp_file.write(file_data.read())
            temp_file_path = temp_file.name
        
        logger.info(f"✅ Temporary file created: {temp_file_path}")
        
        try:
            # Parse resume
            logger.info(f"🔍 Starting resume parsing...")
            from backend.services.simple_resume_parser import simple_resume_parser
            parse_result = simple_resume_parser.parse_resume(temp_file_path, resume.file_type)
            
            if parse_result["success"]:
                logger.info(f"✅ Resume parsing successful")
                parsed_data = parse_result["parsed_data"]
                
                # Log extracted information
                logger.info(f"📝 Extracted candidate name: {parsed_data.get('name', 'Not found')}")
                logger.info(f"📧 Extracted email: {parsed_data.get('email', 'Not found')}")
                logger.info(f"📱 Extracted phone: {parsed_data.get('phone', 'Not found')}")
                logger.info(f"💼 Extracted current role: {parsed_data.get('current_role', 'Not found')}")
                logger.info(f"🏢 Extracted company: {parsed_data.get('current_company', 'Not found')}")
                logger.info(f"📊 Extracted years experience: {parsed_data.get('years_experience', 'Not found')}")
                logger.info(f"🎯 Extracted domain: {parsed_data.get('domain', 'Not found')}")
                logger.info(f"🛠️ Extracted skills count: {len(parsed_data.get('skills', []))}")
                logger.info(f"⚙️ Extracted technologies count: {len(parsed_data.get('technologies', []))}")
                
                # Update resume with extracted metadata
                logger.info(f"💾 Updating database with extracted metadata...")
                resume.candidate_name = parsed_data.get("name")
                resume.email = parsed_data.get("email")
                resume.phone = parsed_data.get("phone")
                resume.current_role = parsed_data.get("current_role")
                resume.current_company = parsed_data.get("current_company")
                resume.years_experience = parsed_data.get("years_experience")
                resume.domain = parsed_data.get("domain")
                resume.skills = parsed_data.get("skills", [])
                resume.technologies = parsed_data.get("technologies", [])
                resume.experience = parsed_data.get("experience", [])
                resume.education = parsed_data.get("education", [])
                resume.is_processed = True
                
                logger.info(f"✅ Database metadata updated")
                
                # Create chunks
                logger.info(f"✂️ Creating text chunks for vector processing...")
                chunks = openai_service.chunk_text(parse_result["raw_text"])
                resume.chunks_count = len(chunks)
                logger.info(f"✅ Created {len(chunks)} text chunks")
                
                # Save chunks to database
                logger.info(f"💾 Saving chunks to database...")
                for i, chunk in enumerate(chunks):
                    chunk_record = ResumeChunk(
                        resume_id=resume.id,
                        chunk_index=i,
                        content=chunk,
                        chunk_size=len(chunk)
                    )
                    db.add(chunk_record)
                
                logger.info(f"✅ Chunks saved to database")
                
                # Create embeddings (simplified - in production, this would be async)
                logger.info(f"🧠 Creating embeddings for chunks...")
                try:
                    embeddings = openai_service.create_embeddings(chunks)
                    logger.info(f"✅ Created embeddings for {len(embeddings)} chunks")
                    # Store embeddings in vector store (simplified)
                    resume.is_indexed = True
                except Exception as e:
                    logger.warning(f"⚠️ Could not create embeddings: {e}")
                
                # Upload to OpenAI Vector Store
                logger.info(f"☁️ Uploading to OpenAI Vector Store...")
                try:
                    file_id = openai_service.upload_file_to_vector_store(temp_file_path, resume.original_filename)
                    logger.info(f"✅ Resume {resume.id} uploaded to vector store with file_id: {file_id}")
                    resume.openai_file_id = file_id
                except Exception as e:
                    logger.warning(f"⚠️ Could not upload to vector store: {e}")
                
                db.commit()
                logger.info(f"✅ Database committed successfully")
                
            else:
                logger.error(f"❌ Resume parsing failed: {parse_result.get('error', 'Unknown error')}")
                resume.processing_error = parse_result.get("error", "Unknown error")
                db.commit()
                
        finally:
            # Clean up temporary file
            logger.info(f"🧹 Cleaning up temporary file: {temp_file_path}")
            os.unlink(temp_file_path)
            logger.info(f"✅ Temporary file cleaned up")
            
        logger.info(f"🎉 Resume processing completed for ID: {resume_id}")
            
    except Exception as e:
        logger.error(f"❌ Error processing resume {resume_id}: {e}")
        resume.processing_error = str(e)
        db.commit() 