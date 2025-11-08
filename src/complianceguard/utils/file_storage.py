"""
File storage utilities for handling document uploads to S3.
Provides secure file storage, hash calculation, and MIME type detection.
"""

import hashlib
import mimetypes
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from uuid import uuid4

import aioboto3
from botocore.exceptions import ClientError
from fastapi import UploadFile

from complianceguard.config import get_settings

settings = get_settings()


def calculate_file_hash(file_content: bytes) -> str:
    """
    Calculate SHA-256 hash of file content.

    Args:
        file_content: File content as bytes

    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(file_content).hexdigest()


def get_mime_type(filename: str) -> str:
    """
    Get MIME type from filename.

    Args:
        filename: Name of the file

    Returns:
        MIME type string
    """
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "application/octet-stream"


def generate_s3_key(file_hash: str, filename: str) -> str:
    """
    Generate S3 object key with organized structure.

    Args:
        file_hash: SHA-256 hash of the file
        filename: Original filename

    Returns:
        S3 object key path
    """
    # Get file extension
    file_extension = Path(filename).suffix.lower()

    # Organize by date and hash prefix for better distribution
    date_prefix = datetime.utcnow().strftime("%Y/%m/%d")
    hash_prefix = file_hash[:2]  # First 2 chars for sharding

    # Format: YYYY/MM/DD/XX/hash.ext
    return f"documents/{date_prefix}/{hash_prefix}/{file_hash}{file_extension}"


async def get_s3_client():
    """
    Get configured S3 client (async).

    Returns:
        Async S3 client context manager
    """
    session = aioboto3.Session()

    # Build client kwargs
    kwargs = {
        "service_name": "s3",
        "region_name": settings.s3_region,
    }

    # Add credentials if provided
    if settings.s3_access_key_id and settings.s3_secret_access_key:
        kwargs["aws_access_key_id"] = settings.s3_access_key_id
        kwargs["aws_secret_access_key"] = settings.s3_secret_access_key

    # Add endpoint URL if provided (for LocalStack/MinIO)
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
        kwargs["use_ssl"] = settings.s3_use_ssl

    return session.client(**kwargs)


async def ensure_bucket_exists() -> None:
    """
    Ensure S3 bucket exists, create if it doesn't.
    """
    async with await get_s3_client() as s3:
        try:
            await s3.head_bucket(Bucket=settings.s3_bucket_name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "404":
                # Bucket doesn't exist, create it
                await s3.create_bucket(
                    Bucket=settings.s3_bucket_name,
                    CreateBucketConfiguration={"LocationConstraint": settings.s3_region}
                    if settings.s3_region != "us-east-1"
                    else {},
                )
            else:
                raise


async def upload_file_to_s3(
    upload_file: UploadFile,
) -> tuple[str, str, int, str]:
    """
    Upload file to S3 and return file metadata.

    Args:
        upload_file: FastAPI UploadFile instance

    Returns:
        Tuple of (s3_key, file_hash, file_size, mime_type)
    """
    # Read file content
    file_content = await upload_file.read()
    file_size = len(file_content)

    # Calculate hash
    file_hash = calculate_file_hash(file_content)

    # Get MIME type
    mime_type = get_mime_type(upload_file.filename or "")

    # Generate S3 key
    s3_key = generate_s3_key(file_hash, upload_file.filename or "unknown")

    # Upload to S3
    async with await get_s3_client() as s3:
        # Check if file already exists
        try:
            await s3.head_object(Bucket=settings.s3_bucket_name, Key=s3_key)
            # File already exists, skip upload
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "404":
                # File doesn't exist, upload it
                await s3.put_object(
                    Bucket=settings.s3_bucket_name,
                    Key=s3_key,
                    Body=file_content,
                    ContentType=mime_type,
                    Metadata={
                        "original-filename": upload_file.filename or "",
                        "file-hash": file_hash,
                    },
                )
            else:
                raise

    # Reset file pointer for potential reuse
    await upload_file.seek(0)

    return s3_key, file_hash, file_size, mime_type


async def get_file_from_s3(s3_key: str) -> bytes:
    """
    Download file content from S3.

    Args:
        s3_key: S3 object key

    Returns:
        File content as bytes
    """
    async with await get_s3_client() as s3:
        response = await s3.get_object(Bucket=settings.s3_bucket_name, Key=s3_key)
        return await response["Body"].read()


async def delete_file_from_s3(s3_key: str) -> bool:
    """
    Delete file from S3.

    Args:
        s3_key: S3 object key

    Returns:
        True if file was deleted, False if file didn't exist
    """
    async with await get_s3_client() as s3:
        try:
            await s3.delete_object(Bucket=settings.s3_bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False


async def generate_presigned_url(
    s3_key: str, expiration_seconds: int = 3600
) -> str:
    """
    Generate presigned URL for temporary file access.

    Args:
        s3_key: S3 object key
        expiration_seconds: URL expiration time in seconds (default 1 hour)

    Returns:
        Presigned URL string
    """
    async with await get_s3_client() as s3:
        url = await s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket_name, "Key": s3_key},
            ExpiresIn=expiration_seconds,
        )
        return url


async def check_file_exists(s3_key: str) -> bool:
    """
    Check if file exists in S3.

    Args:
        s3_key: S3 object key

    Returns:
        True if file exists, False otherwise
    """
    async with await get_s3_client() as s3:
        try:
            await s3.head_object(Bucket=settings.s3_bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False


async def extract_text_with_landing_ai(
    file_content: bytes, filename: str
) -> tuple[str, dict]:
    """
    Extract text from file using Landing AI Document AI Engine.

    Args:
        file_content: Binary file content
        filename: Original filename

    Returns:
        Tuple of (extracted_text, extraction_metadata)
    """
    from complianceguard.services.landing_ai import parse_document_with_landing_ai

    try:
        extracted_text, metadata = await parse_document_with_landing_ai(
            file_content, filename
        )
        return extracted_text, metadata
    except Exception as e:
        # If Landing AI fails, return error info
        return (
            f"[Text extraction failed: {str(e)}]",
            {
                "extraction_method": "landing_ai_ade",
                "error": str(e),
                "file_size": len(file_content),
                "text_length": 0,
                "confidence_score": 0.0,
                "num_pages": 0,
                "tables_found": 0,
            },
        )
