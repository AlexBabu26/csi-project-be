"""Generic file URL endpoint for generating pre-signed URLs."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.common.storage import get_file_url
from app.common.security import get_current_user
from app.auth.models import CustomUser

router = APIRouter()


@router.get("/url")
async def get_presigned_url(
    key: str = Query(..., description="Object key/path from storage"),
    expires_in: int = Query(3600, ge=60, le=86400, description="URL expiration in seconds (1min-24hrs)"),
    current_user: CustomUser = Depends(get_current_user),
):
    """
    Generate a pre-signed URL for accessing a file in cloud storage.
    
    The URL is temporary and expires after the specified duration.
    Requires authentication.
    
    Args:
        key: The object key/path stored in the database (e.g., "csi_youth_kalamela/payments/abc123.png")
        expires_in: URL expiration time in seconds (default: 1 hour, min: 1 min, max: 24 hrs)
    
    Returns:
        Pre-signed URL and expiration info
    """
    if not key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Object key is required"
        )
    
    try:
        url = get_file_url(key, expires_in=expires_in)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate file URL"
        )
    
    return {
        "url": url,
        "key": key,
        "expires_in": expires_in,
    }


