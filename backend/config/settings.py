from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
import os


class Settings(BaseSettings):
    # Database Configuration
    database_url: str = "postgresql://username:password@localhost:5432/cogni_db"
    
    # MinIO Configuration
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "COGNIACCESS"
    minio_secret_key: str = "COGNISECRET"
    minio_bucket_name: str = "cogni-resumes"
    minio_secure: bool = False
    
    # OpenAI Configuration
    openai_api_key: str = ""
    openai_assistant_id: str = ""
    
    # JWT Configuration
    jwt_secret_key: str = "your_jwt_secret_key_here"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    
    # Application Configuration
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    
    # Authentication
    admin_username: str = "admin"
    admin_password: str = "admin"
    
    # File Upload Configuration
    max_file_size: int = 10485760  # 10MB
    allowed_extensions: List[str] = ["pdf", "docx", "txt"]
    
    @field_validator('allowed_extensions', mode='before')
    @classmethod
    def parse_allowed_extensions(cls, v):
        if isinstance(v, str):
            # Remove any trailing characters, comments, and split by comma
            v = v.strip()
            # Remove trailing % and any comments
            if '%' in v:
                v = v.split('%')[0].strip()
            return [ext.strip() for ext in v.split(',') if ext.strip()]
        elif isinstance(v, list):
            # If it's already a list, return as is
            return v
        return v
    
    # Schema Configuration
    db_schema: str = "cogni"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings() 