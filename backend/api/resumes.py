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
from backend.services.minio_service import minio_service
from backend.services.resume_parser import resume_parser
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
        # Validate file type
        file_extension = file.filename.split('.')[-1].lower()
        if file_extension not in settings.allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {file_extension} not allowed. Allowed types: {settings.allowed_extensions}"
            )
        
        # Validate file size
        if file.size > settings.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size {file.size} exceeds maximum allowed size {settings.max_file_size}"
            )
        
        # Upload to MinIO
        file_path = minio_service.upload_file(
            file.file,
            file.filename,
            content_type=file.content_type
        )
        
        # Create database record
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
        
        # Trigger processing (in production, this would be async)
        # For now, we'll process synchronously
        await process_resume(resume.id, db)
        
        return ResumeUploadResponse(
            id=resume.id,
            filename=resume.filename,
            original_filename=resume.original_filename,
            file_size=resume.file_size,
            file_type=resume.file_type
        )
        
    except Exception as e:
        logger.error(f"Error uploading resume: {e}")
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


async def process_resume(resume_id: int, db: Session):
    """Process a resume (parse, extract metadata, create embeddings)"""
    try:
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            return
        
        # Download file from MinIO
        file_data = minio_service.download_file(resume.filename)
        if not file_data:
            raise Exception("Could not download file from MinIO")
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{resume.file_type}") as temp_file:
            temp_file.write(file_data.read())
            temp_file_path = temp_file.name
        
        try:
            # Parse resume
            parse_result = resume_parser.parse_resume(temp_file_path, resume.file_type)
            
            if parse_result["success"]:
                parsed_data = parse_result["parsed_data"]
                
                # Update resume with extracted metadata
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
                
                # Create chunks
                chunks = openai_service.chunk_text(parse_result["raw_text"])
                resume.chunks_count = len(chunks)
                
                # Save chunks to database
                for i, chunk in enumerate(chunks):
                    chunk_record = ResumeChunk(
                        resume_id=resume.id,
                        chunk_index=i,
                        content=chunk,
                        chunk_size=len(chunk)
                    )
                    db.add(chunk_record)
                
                # Create embeddings (simplified - in production, this would be async)
                try:
                    embeddings = openai_service.create_embeddings(chunks)
                    # Store embeddings in vector store (simplified)
                    resume.is_indexed = True
                except Exception as e:
                    logger.warning(f"Could not create embeddings: {e}")
                
                db.commit()
                
            else:
                resume.processing_error = parse_result.get("error", "Unknown error")
                db.commit()
                
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
            
    except Exception as e:
        logger.error(f"Error processing resume {resume_id}: {e}")
        resume.processing_error = str(e)
        db.commit() 