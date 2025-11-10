"""S3 storage utilities for PDF page images.

This module handles uploading and managing PDF page images in S3 for the indexing system.
Each page image is stored with a structured key and optionally made public for easy access.
"""

import hashlib
import io
from pathlib import Path
from typing import Optional

import aioboto3
from botocore.exceptions import ClientError
from PIL import Image

from complianceguard.config import get_settings


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

    async with await get_s3_client() as s3:
        try:
            await s3.head_bucket(Bucket=bucket_name)
            print(f"✓ S3 bucket '{bucket_name}' exists")
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "404":
                print(f"Creating S3 bucket: {bucket_name}")
                # Create bucket
                try:
                    if settings.s3_region != "us-east-1":
                        await s3.create_bucket(
                            Bucket=bucket_name,
                            CreateBucketConfiguration={"LocationConstraint": settings.s3_region}
                        )
                    else:
                        await s3.create_bucket(Bucket=bucket_name)
                    print(f"✓ Created bucket '{bucket_name}'")
                except ClientError as create_error:
                    print(f"Warning: Could not create bucket: {create_error}")
                    return

                # Set bucket policy for public read if configured
                if settings.indexing_s3_make_public:
                    try:
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
                        print(f"✓ Set public read policy on '{bucket_name}'")
                    except ClientError as policy_error:
                        print(f"Warning: Could not set bucket policy: {policy_error}")
            else:
                raise


def generate_page_image_key(
    pdf_filepath: str,
    page_number: int,
    doc_hash: Optional[str] = None
) -> str:
    """Generate S3 key for a page image.

    Structure: pages/{doc_hash}/{filename_stem}/page_{page_number}.png

    Args:
        pdf_filepath: Path to the original PDF file
        page_number: Page number (1-indexed)
        doc_hash: Optional document hash (computed if not provided)

    Returns:
        S3 key for the page image
    """
    # Get filename without extension
    pdf_path = Path(pdf_filepath)
    filename_stem = pdf_path.stem

    # Compute document hash if not provided
    if doc_hash is None:
        doc_hash = hashlib.sha256(pdf_filepath.encode()).hexdigest()[:16]

    # Generate key: pages/{doc_hash}/{filename}/page_001.png
    return f"pages/{doc_hash}/{filename_stem}/page_{page_number:04d}.png"


async def upload_page_image_to_s3(
    page_image: Image.Image,
    pdf_filepath: str,
    page_number: int,
    doc_hash: Optional[str] = None
) -> Optional[str]:
    """Upload a single page image to S3.

    Args:
        page_image: PIL Image object of the page
        pdf_filepath: Path to the original PDF file
        page_number: Page number (1-indexed)
        doc_hash: Optional document hash for key generation

    Returns:
        S3 URL of the uploaded image, or None if upload failed
    """
    settings = get_settings()

    if not settings.indexing_s3_enabled:
        return None

    # Generate S3 key
    s3_key = generate_page_image_key(pdf_filepath, page_number, doc_hash)
    bucket_name = settings.indexing_s3_bucket_name

    try:
        # Convert PIL Image to bytes
        img_byte_arr = io.BytesIO()
        page_image.save(img_byte_arr, format='PNG', optimize=True)
        img_byte_arr.seek(0)

        async with await get_s3_client() as s3:
            # Check if image already exists
            try:
                await s3.head_object(Bucket=bucket_name, Key=s3_key)
                # Image already exists, return URL
                print(f"⏭️  Page {page_number} already in S3: {s3_key}")
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code")
                if error_code == "404":
                    # Upload the image
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
                    print(f"✓ Uploaded page {page_number} to S3: {s3_key}")
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

        return s3_url

    except Exception as e:
        print(f"❌ Failed to upload page {page_number} to S3: {e}")
        if settings.indexing_local_fallback:
            print("   Continuing without S3 storage (local fallback enabled)")
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
    doc_hash: Optional[str] = None
) -> list[Optional[str]]:
    """Upload multiple page images to S3 in batch (in parallel).

    Args:
        page_images: List of PIL Image objects
        pdf_filepath: Path to the original PDF file
        start_page: Starting page number (1-indexed)
        doc_hash: Optional document hash

    Returns:
        List of S3 URLs (or None for failed uploads)
    """
    import asyncio

    settings = get_settings()

    # Ensure bucket exists
    await ensure_page_images_bucket_exists()

    # Helper function to upload a single page with fallback
    async def upload_single_page(page_image: Image.Image, page_number: int) -> Optional[str]:
        # Upload to S3
        s3_url = await upload_page_image_to_s3(
            page_image,
            pdf_filepath,
            page_number,
            doc_hash
        )

        # Fallback to local storage if S3 fails and fallback is enabled
        if s3_url is None and settings.indexing_local_fallback:
            local_path = await save_page_locally(page_image, pdf_filepath, page_number)
            return f"file://{local_path}"
        return s3_url

    # Upload all pages in parallel
    upload_tasks = [
        upload_single_page(page_image, start_page + i)
        for i, page_image in enumerate(page_images)
    ]
    urls = await asyncio.gather(*upload_tasks)

    return list(urls)


async def delete_page_images_from_s3(
    pdf_filepath: str,
    num_pages: int,
    doc_hash: Optional[str] = None
) -> int:
    """Delete all page images for a document from S3.

    Args:
        pdf_filepath: Path to the PDF file
        num_pages: Number of pages in the document
        doc_hash: Optional document hash

    Returns:
        Number of images deleted
    """
    settings = get_settings()
    bucket_name = settings.indexing_s3_bucket_name
    deleted_count = 0

    try:
        async with await get_s3_client() as s3:
            for page_number in range(1, num_pages + 1):
                s3_key = generate_page_image_key(pdf_filepath, page_number, doc_hash)
                try:
                    await s3.delete_object(Bucket=bucket_name, Key=s3_key)
                    deleted_count += 1
                except ClientError:
                    pass  # Ignore if file doesn't exist

        print(f"🗑️  Deleted {deleted_count} page images from S3")
        return deleted_count

    except Exception as e:
        print(f"❌ Error deleting page images: {e}")
        return deleted_count
