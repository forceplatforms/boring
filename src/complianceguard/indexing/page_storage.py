"""S3 storage utilities for PDF page images.

This module handles uploading and managing PDF page images in S3 for the indexing system.
Each page image is stored with a structured key and optionally made public for easy access.
"""

import hashlib
import io
import logging
import time
from pathlib import Path
from typing import Optional

import aioboto3
from botocore.exceptions import ClientError
from PIL import Image

from complianceguard.config import get_settings

logger = logging.getLogger(__name__)


async def get_s3_client():
    """Get configured S3 client for page image storage.

    Returns:
        Async S3 client context manager
    """
    settings = get_settings()
    session = aioboto3.Session()

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


async def ensure_page_images_bucket_exists() -> None:
    """Ensure the page images S3 bucket exists, create if it doesn't.

    Also sets up bucket policy for public read access if configured.
    """
    settings = get_settings()
    bucket_name = settings.indexing_s3_bucket_name

    logger.info(f"[S3] Checking if bucket '{bucket_name}' exists")

    async with await get_s3_client() as s3:
        try:
            await s3.head_bucket(Bucket=bucket_name)
            logger.info(f"[S3] Bucket '{bucket_name}' exists")
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "404":
                logger.info(f"[S3] Bucket not found - creating S3 bucket: {bucket_name}")
                # Create bucket
                try:
                    if settings.s3_region != "us-east-1":
                        await s3.create_bucket(
                            Bucket=bucket_name,
                            CreateBucketConfiguration={"LocationConstraint": settings.s3_region}
                        )
                    else:
                        await s3.create_bucket(Bucket=bucket_name)
                    logger.info(f"[S3] Created bucket '{bucket_name}'")
                except ClientError as create_error:
                    logger.error(f"[S3] Could not create bucket: {create_error}")
                    return

                # Set bucket policy for public read if configured
                if settings.indexing_s3_make_public:
                    try:
                        logger.info(f"[S3] Setting public read policy on '{bucket_name}'")
                        policy = {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Sid": "PublicReadGetObject",
                                    "Effect": "Allow",
                                    "Principal": "*",
                                    "Action": "s3:GetObject",
                                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                                }
                            ]
                        }
                        import json
                        await s3.put_bucket_policy(
                            Bucket=bucket_name,
                            Policy=json.dumps(policy)
                        )
                        logger.info(f"[S3] Set public read policy on '{bucket_name}'")
                    except ClientError as policy_error:
                        logger.warning(f"[S3] Could not set bucket policy: {policy_error}")
            else:
                raise


def generate_page_image_key(
    pdf_filepath: str,
    page_number: int,
    doc_hash: Optional[str] = None,
    index_name: Optional[str] = None
) -> str:
    """Generate S3 key for a page image.

    Structure:
    - With index_name: pages/{index_name}/{doc_hash}/{filename_stem}/page_{page_number}.png
    - Without index_name: pages/{doc_hash}/{filename_stem}/page_{page_number}.png (backward compatible)

    Args:
        pdf_filepath: Path to the original PDF file
        page_number: Page number (1-indexed)
        doc_hash: Optional document hash (computed if not provided)
        index_name: Optional Milvus collection name for namespacing

    Returns:
        S3 key for the page image
    """
    # Get filename without extension
    pdf_path = Path(pdf_filepath)
    filename_stem = pdf_path.stem

    # Compute document hash if not provided
    if doc_hash is None:
        doc_hash = hashlib.sha256(pdf_filepath.encode()).hexdigest()[:16]

    # Generate key with index_name prefix if provided
    if index_name:
        return f"pages/{index_name}/{doc_hash}/{filename_stem}/page_{page_number:04d}.png"
    else:
        # Backward compatible: no index_name prefix
        return f"pages/{doc_hash}/{filename_stem}/page_{page_number:04d}.png"


async def upload_page_image_to_s3(
    page_image: Image.Image,
    pdf_filepath: str,
    page_number: int,
    doc_hash: Optional[str] = None,
    index_name: Optional[str] = None
) -> Optional[str]:
    """Upload a single page image to S3.

    Args:
        page_image: PIL Image object of the page
        pdf_filepath: Path to the original PDF file
        page_number: Page number (1-indexed)
        doc_hash: Optional document hash for key generation
        index_name: Optional Milvus collection name for S3 path namespacing

    Returns:
        S3 URL of the uploaded image, or None if upload failed
    """
    upload_start = time.time()
    settings = get_settings()

    if not settings.indexing_s3_enabled:
        return None

    # Generate S3 key with index_name
    s3_key = generate_page_image_key(pdf_filepath, page_number, doc_hash, index_name)
    bucket_name = settings.indexing_s3_bucket_name

    try:
        # Convert PIL Image to bytes
        convert_start = time.time()
        img_byte_arr = io.BytesIO()
        page_image.save(img_byte_arr, format='PNG', optimize=True)
        img_byte_arr.seek(0)
        img_size = len(img_byte_arr.getvalue())
        img_size_kb = img_size / 1024
        convert_time = time.time() - convert_start

        async with await get_s3_client() as s3:
            # Check if image already exists
            try:
                await s3.head_object(Bucket=bucket_name, Key=s3_key)
                # Image already exists, return URL
                logger.info(f"[S3] Page {page_number} already in S3: {s3_key}")
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code")
                if error_code == "404":
                    # Upload the image
                    put_start = time.time()
                    await s3.put_object(
                        Bucket=bucket_name,
                        Key=s3_key,
                        Body=img_byte_arr.getvalue(),
                        ContentType="image/png",
                        Metadata={
                            "original-pdf": Path(pdf_filepath).name,
                            "page-number": str(page_number),
                        }
                    )
                    put_time = time.time() - put_start
                    logger.info(f"[S3] Uploaded page {page_number} ({img_size_kb:.1f} KB) in {put_time:.3f}s: {s3_key}")
                else:
                    raise

        # Generate public URL
        if settings.indexing_s3_make_public:
            # Public URL format
            if settings.s3_endpoint_url:
                # LocalStack/MinIO format
                base_url = settings.s3_endpoint_url.rstrip('/')
                s3_url = f"{base_url}/{bucket_name}/{s3_key}"
            else:
                # AWS S3 format
                s3_url = f"https://{bucket_name}.s3.{settings.s3_region}.amazonaws.com/{s3_key}"
        else:
            # Generate presigned URL (valid for 7 days)
            async with await get_s3_client() as s3:
                s3_url = await s3.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket_name, 'Key': s3_key},
                    ExpiresIn=7 * 24 * 3600  # 7 days
                )

        upload_total_time = time.time() - upload_start
        return s3_url

    except Exception as e:
        upload_error_time = time.time() - upload_start
        logger.error(f"[S3] Failed to upload page {page_number} after {upload_error_time:.3f}s: {type(e).__name__}: {e}")
        if settings.indexing_local_fallback:
            logger.warning(f"[S3] Continuing without S3 storage (local fallback enabled)")
        return None


async def save_page_locally(
    page_image: Image.Image,
    pdf_filepath: str,
    page_number: int,
    output_dir: str = "./artifacts/page_images"
) -> str:
    """Save page image locally as fallback.

    Args:
        page_image: PIL Image object
        pdf_filepath: Path to the original PDF
        page_number: Page number (1-indexed)
        output_dir: Directory to save images

    Returns:
        Local file path
    """
    import os

    # Create output directory
    pdf_name = Path(pdf_filepath).stem
    page_dir = Path(output_dir) / pdf_name
    page_dir.mkdir(parents=True, exist_ok=True)

    # Save image
    output_path = page_dir / f"page_{page_number:04d}.png"
    page_image.save(output_path, format='PNG', optimize=True)

    return str(output_path)


async def batch_upload_pages_to_s3(
    page_images: list[Image.Image],
    pdf_filepath: str,
    start_page: int = 1,
    doc_hash: Optional[str] = None,
    index_name: Optional[str] = None
) -> list[Optional[str]]:
    """Upload multiple page images to S3 in batch (in parallel).

    Args:
        page_images: List of PIL Image objects
        pdf_filepath: Path to the original PDF file
        start_page: Starting page number (1-indexed)
        doc_hash: Optional document hash
        index_name: Optional Milvus collection name for S3 path namespacing

    Returns:
        List of S3 URLs (or None for failed uploads)
    """
    import asyncio

    batch_start = time.time()
    settings = get_settings()

    logger.info(f"[S3-BATCH] Starting batch upload of {len(page_images)} page images")
    logger.info(f"[S3-BATCH] PDF: {pdf_filepath}")
    logger.info(f"[S3-BATCH] Starting page: {start_page}")
    if index_name:
        logger.info(f"[S3-BATCH] Index namespace: {index_name}")

    # Ensure bucket exists
    bucket_check_start = time.time()
    await ensure_page_images_bucket_exists()
    bucket_check_time = time.time() - bucket_check_start
    logger.info(f"[S3-BATCH] Bucket check completed in {bucket_check_time:.3f}s")

    # Helper function to upload a single page with fallback
    async def upload_single_page(page_image: Image.Image, page_number: int) -> Optional[str]:
        # Upload to S3 with index_name
        s3_url = await upload_page_image_to_s3(
            page_image,
            pdf_filepath,
            page_number,
            doc_hash,
            index_name
        )

        # Fallback to local storage if S3 fails and fallback is enabled
        if s3_url is None and settings.indexing_local_fallback:
            logger.info(f"[S3-BATCH] Using local fallback for page {page_number}")
            local_path = await save_page_locally(page_image, pdf_filepath, page_number)
            return f"file://{local_path}"
        return s3_url

    # Upload all pages in parallel
    logger.info(f"[S3-BATCH] Uploading {len(page_images)} pages in parallel")
    upload_start = time.time()
    upload_tasks = [
        upload_single_page(page_image, start_page + i)
        for i, page_image in enumerate(page_images)
    ]
    urls = await asyncio.gather(*upload_tasks)
    upload_time = time.time() - upload_start

    successful_uploads = len([u for u in urls if u])
    failed_uploads = len([u for u in urls if not u])

    batch_total_time = time.time() - batch_start
    logger.info(f"[S3-BATCH] Batch upload completed in {batch_total_time:.3f}s")
    logger.info(f"[S3-BATCH] Successful: {successful_uploads}/{len(page_images)}")
    logger.info(f"[S3-BATCH] Failed: {failed_uploads}/{len(page_images)}")
    logger.info(f"[S3-BATCH] Average time per page: {upload_time/len(page_images):.3f}s")

    return list(urls)


async def delete_page_images_from_s3(
    pdf_filepath: str,
    num_pages: int,
    doc_hash: Optional[str] = None,
    index_name: Optional[str] = None
) -> int:
    """Delete all page images for a document from S3.

    Args:
        pdf_filepath: Path to the PDF file
        num_pages: Number of pages in the document
        doc_hash: Optional document hash
        index_name: Optional Milvus collection name for S3 path namespacing

    Returns:
        Number of images deleted
    """
    delete_start = time.time()
    settings = get_settings()
    bucket_name = settings.indexing_s3_bucket_name
    deleted_count = 0

    logger.info(f"[S3-DELETE] Starting deletion of {num_pages} page images")
    logger.info(f"[S3-DELETE] PDF: {pdf_filepath}")
    if index_name:
        logger.info(f"[S3-DELETE] Index namespace: {index_name}")

    try:
        async with await get_s3_client() as s3:
            for page_number in range(1, num_pages + 1):
                s3_key = generate_page_image_key(pdf_filepath, page_number, doc_hash, index_name)
                try:
                    await s3.delete_object(Bucket=bucket_name, Key=s3_key)
                    deleted_count += 1
                except ClientError:
                    pass  # Ignore if file doesn't exist

        delete_time = time.time() - delete_start
        logger.info(f"[S3-DELETE] Deleted {deleted_count}/{num_pages} page images in {delete_time:.3f}s")
        return deleted_count

    except Exception as e:
        delete_error_time = time.time() - delete_start
        logger.error(f"[S3-DELETE] Error deleting page images after {delete_error_time:.3f}s: {e}")
        return deleted_count
