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
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        self.bucket_name = settings.minio_bucket_name
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if it doesn't"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
            else:
                logger.info(f"Bucket {self.bucket_name} already exists")
        except S3Error as e:
            logger.error(f"Error ensuring bucket exists: {e}")
            # Don't raise the error to allow the application to start
            # The bucket check will be retried when needed
    
    def upload_file(self, file_data: BinaryIO, filename: str, content_type: str = "application/octet-stream") -> str:
        """Upload a file to MinIO and return the file path"""
        try:
            # Generate unique filename
            file_extension = os.path.splitext(filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            # Upload file
            self.client.put_object(
                self.bucket_name,
                unique_filename,
                file_data,
                length=-1,
                part_size=10*1024*1024,  # 10MB parts
                content_type=content_type
            )
            
            logger.info(f"Uploaded file: {filename} -> {unique_filename}")
            return unique_filename
            
        except S3Error as e:
            logger.error(f"Error uploading file {filename}: {e}")
            raise
    
    def download_file(self, file_path: str) -> Optional[BinaryIO]:
        """Download a file from MinIO"""
        try:
            response = self.client.get_object(self.bucket_name, file_path)
            return response
        except S3Error as e:
            logger.error(f"Error downloading file {file_path}: {e}")
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