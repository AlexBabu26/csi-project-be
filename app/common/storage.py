"""File storage using Backblaze B2 (S3-compatible API)."""

import uuid
import logging
from pathlib import Path
from typing import Tuple
from functools import lru_cache

import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, UploadFile, status

from app.common.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


@lru_cache
def get_s3_client():
    """Get or create S3 client for Backblaze B2."""
    if not settings.b2_key_id or not settings.b2_application_key:
        raise ValueError("B2 credentials not configured. Set B2_KEY_ID and B2_APPLICATION_KEY in environment.")
    
    return boto3.client(
        's3',
        endpoint_url=settings.b2_endpoint,
        aws_access_key_id=settings.b2_key_id,
        aws_secret_access_key=settings.b2_application_key,
        region_name=settings.b2_region,
    )


def _validate_upload(file: UploadFile) -> None:
    """Validate uploaded file before saving."""
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename")
    
    suffix = Path(file.filename).suffix.lower()
    if settings.allowed_upload_extensions and suffix not in settings.allowed_upload_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Unsupported file type: {suffix or 'unknown'}"
        )
    
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB"
        )


def save_upload_file(file: UploadFile, subdir: str = "") -> Tuple[str, str]:
    """
    Upload file to Backblaze B2 storage.
    
    Args:
        file: FastAPI UploadFile object
        subdir: Subdirectory path within bucket (e.g., "units/proofs", "kalamela/payments")
    
    Returns:
        Tuple of (object_key, object_key) - key is the B2 object identifier
    
    Raises:
        HTTPException: If validation fails or upload fails
    """
    _validate_upload(file)
    
    # Generate unique object key
    suffix = Path(file.filename or "").suffix
    filename = f"{uuid.uuid4().hex}{suffix}"
    
    # Build full object key with subdirectory and required prefix
    # B2 application key may require a specific prefix for all uploads
    prefix = settings.b2_key_prefix or ""
    if subdir:
        object_key = f"{prefix}{subdir}/{filename}"
    else:
        object_key = f"{prefix}{filename}"
    
    try:
        # Read file content
        file.file.seek(0)
        file_content = file.file.read()
        
        # Upload to B2
        s3_client = get_s3_client()
        s3_client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=object_key,
            Body=file_content,
            ContentType=file.content_type or 'application/octet-stream',
        )
        
        logger.info(f"Successfully uploaded file to B2: {object_key}")
        
        # Return object key twice (for backward compatibility with code expecting (key, path))
        return object_key, object_key
        
    except ClientError as e:
        logger.error(f"Failed to upload file to B2: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file to cloud storage"
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error uploading file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save file"
        ) from e
    finally:
        file.file.close()


def delete_file(object_key: str) -> bool:
    """
    Delete file from Backblaze B2 storage.
    
    Args:
        object_key: B2 object key to delete (should already include prefix if saved via save_upload_file)
    
    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        s3_client = get_s3_client()
        # Object key should already include prefix from save_upload_file
        s3_client.delete_object(
            Bucket=settings.b2_bucket_name,
            Key=object_key,
        )
        logger.info(f"Successfully deleted file from B2: {object_key}")
        return True
    except ClientError as e:
        logger.error(f"Failed to delete file from B2: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting file: {e}")
        return False


def get_file_url(object_key: str, expires_in: int = 3600) -> str:
    """
    Generate a pre-signed URL for accessing a private file in B2.
    
    Args:
        object_key: B2 object key
        expires_in: URL expiration time in seconds (default: 1 hour)
    
    Returns:
        Pre-signed URL string
    """
    try:
        s3_client = get_s3_client()
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.b2_bucket_name,
                'Key': object_key,
            },
            ExpiresIn=expires_in,
        )
        return url
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate file access URL"
        ) from e


def ensure_dir(path: Path) -> Path:
    """
    Legacy function for local storage compatibility.
    Not used with B2, but kept for backward compatibility with exporter.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path
