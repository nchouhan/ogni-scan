from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ChatMessageRequest(BaseModel):
    message: str = Field(..., description="Chat message")
    session_id: Optional[str] = Field(None, description="Chat session ID")


class ChatMessageResponse(BaseModel):
    id: int
    session_id: str
    message_type: str  # user, assistant, system
    content: str
    candidates_found: int = 0
    search_query: Optional[str] = None
    filters_applied: Optional[Dict[str, Any]] = None
    created_at: datetime


class ChatSessionResponse(BaseModel):
    id: int
    session_id: str
    title: Optional[str] = None
    is_active: bool
    created_at: datetime
    last_activity: datetime
    message_count: int = 0


class ChatSessionListResponse(BaseModel):
    sessions: List[ChatSessionResponse]
    total: int


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: List[ChatMessageResponse]
    total_messages: int


class QueryResultResponse(BaseModel):
    id: int
    resume_id: int
    relevance_score: str  # High, Medium, Low
    match_percentage: int
    justification: str
    highlights: List[str]
    created_at: datetime 