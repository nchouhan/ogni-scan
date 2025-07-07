from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ResumeUploadResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    status: str = "uploaded"
    message: str = "Resume uploaded successfully"


class ResumeProcessingResponse(BaseModel):
    id: int
    status: str
    message: str
    is_processed: bool
    is_indexed: bool
    processing_error: Optional[str] = None


class ResumeMetadata(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    current_role: Optional[str] = None
    current_company: Optional[str] = None
    years_experience: Optional[float] = None
    domain: Optional[str] = None
    skills: List[str] = []
    technologies: List[str] = []
    experience: List[Dict[str, Any]] = []
    education: List[Dict[str, Any]] = []


class ResumeResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    metadata: ResumeMetadata
    is_processed: bool
    is_indexed: bool
    chunks_count: int
    created_at: datetime
    processed_at: Optional[datetime] = None


class ResumeListResponse(BaseModel):
    resumes: List[ResumeResponse]
    total: int
    page: int
    size: int


class ResumeSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    skills: Optional[List[str]] = Field(None, description="Required skills")
    domain: Optional[str] = Field(None, description="Domain filter")
    min_experience: Optional[float] = Field(None, description="Minimum years of experience")
    max_experience: Optional[float] = Field(None, description="Maximum years of experience")
    limit: int = Field(10, description="Number of results to return")


class CandidateMatch(BaseModel):
    resume_id: int
    candidate_name: str
    current_role: str
    current_company: str
    match_percentage: int
    relevance_score: str  # High, Medium, Low
    skills_match: List[str]
    justification: str
    highlights: List[str]


class ResumeSearchResponse(BaseModel):
    query: str
    candidates: List[CandidateMatch]
    total_found: int
    search_time: float 