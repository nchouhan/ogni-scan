import os
import uuid
from typing import Optional, BinaryIO
from minio import Minio
from minio.error import S3Error
from backend.config.settings import settings
import logging

logger = logging.getLogger(__name__)


class MinIOService:
    def __init__(self):
        try:
            self.client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure
            )
            self.bucket_name = settings.minio_bucket_name
            self._ensure_bucket_exists()
            self.available = True
            logger.info("MinIO service initialized successfully")
        except Exception as e:
            logger.error(f"MinIO service initialization failed: {e}")
            self.client = None
            self.bucket_name = settings.minio_bucket_name
            self.available = False
    
    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if it doesn't"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
            else:
                logger.info(f"Bucket {self.bucket_name} already exists")
        except Exception as e:
            logger.error(f"Error ensuring bucket exists: {e}")
            # Don't raise the error to allow the application to start
            # The bucket check will be retried when needed
    
    def upload_file(self, file_data, filename: str, content_type: str = None) -> str:
        """Upload a file to MinIO"""
        try:
            logger.info(f"📤 Starting file upload to MinIO: {filename}")
            
            # Generate unique filename
            file_extension = filename.split('.')[-1] if '.' in filename else ''
            unique_filename = f"{uuid.uuid4()}.{file_extension}" if file_extension else str(uuid.uuid4())
            
            logger.info(f"🆔 Generated unique filename: {unique_filename}")
            
            # Upload file
            logger.info(f"☁️ Uploading file to MinIO bucket: {self.bucket_name}")
            self.client.put_object(
                self.bucket_name,
                unique_filename,
                file_data,
                length=-1,
                part_size=10*1024*1024
            )
            
            logger.info(f"✅ File uploaded successfully: {filename} -> {unique_filename}")
            return unique_filename
            
        except Exception as e:
            logger.error(f"❌ Error uploading file to MinIO: {e}")
            raise
    
    def download_file(self, filename: str) -> Optional[BinaryIO]:
        """Download a file from MinIO"""
        try:
            logger.info(f"📥 Starting file download from MinIO: {filename}")
            
            # Get object
            logger.info(f"🔍 Retrieving object from bucket: {self.bucket_name}")
            response = self.client.get_object(self.bucket_name, filename)
            
            logger.info(f"✅ File downloaded successfully: {filename}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Error downloading file from MinIO: {e}")
            return None
    
    def delete_file(self, file_path: str) -> bool:
        """Delete a file from MinIO"""
        try:
            self.client.remove_object(self.bucket_name, file_path)
            logger.info(f"Deleted file: {file_path}")
            return True
        except S3Error as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return False
    
    def get_file_url(self, file_path: str, expires: int = 3600) -> Optional[str]:
        """Get a presigned URL for file access"""
        try:
            url = self.client.presigned_get_object(
                self.bucket_name,
                file_path,
                expires=expires
            )
            return url
        except S3Error as e:
            logger.error(f"Error generating presigned URL for {file_path}: {e}")
            return None
    
    def list_files(self, prefix: str = "") -> list:
        """List files in the bucket with optional prefix"""
        try:
            objects = self.client.list_objects(self.bucket_name, prefix=prefix, recursive=True)
            return [obj.object_name for obj in objects]
        except S3Error as e:
            logger.error(f"Error listing files: {e}")
            return []


# Global instance
minio_service = MinIOService() 