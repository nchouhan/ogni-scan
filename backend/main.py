from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import sys

from backend.config.settings import settings
from backend.models.database import engine, Base
from backend.api import auth, resumes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("cogni_scan.log")
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting CogniScan application...")
    
    # Create database tables
    try:
        # Create schema if it doesn't exist
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.db_schema}"))
            conn.commit()
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down CogniScan application...")


# Create FastAPI app
app = FastAPI(
    title="CogniScan API",
    description="Resume Insight Assistant Platform API",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception handler: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "CogniScan API",
        "version": "1.0.0"
    }


# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(resumes.router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to CogniScan API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug
    ) 