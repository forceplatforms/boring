"""add_ingested_documents_table

Revision ID: 001_ingested_docs
Revises: fb69163fd813
Create Date: 2025-11-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_ingested_docs'
down_revision: Union[str, Sequence[str], None] = 'fb69163fd813'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create ingested_documents table."""
    op.create_table(
        'ingested_documents',
        # File Metadata
        sa.Column('filename', sa.String(length=255), nullable=False, comment='Original filename'),
        sa.Column('file_hash', sa.String(length=64), nullable=False, comment='SHA-256 hash for deduplication'),
        sa.Column('file_size', sa.BigInteger(), nullable=False, comment='File size in bytes'),
        sa.Column('mime_type', sa.String(length=100), nullable=False, comment='MIME type (e.g., application/pdf)'),

        # S3 Storage
        sa.Column('s3_key', sa.Text(), nullable=False, comment='S3 key for the PDF file (documents/YYYY/MM/DD/XX/hash.pdf)'),
        sa.Column('s3_bucket', sa.String(length=255), nullable=False, comment='S3 bucket name'),
        sa.Column('page_image_s3_prefix', sa.Text(), nullable=True, comment='S3 prefix for page images (pages/{hash}/{filename}/)'),

        # Classification & Metadata
        sa.Column('doc_type', sa.String(length=100), nullable=True, comment='Document type (contract, invoice, report, etc.)'),
        sa.Column('doc_category', sa.String(length=100), nullable=True, comment='Document category for additional classification'),
        sa.Column('doc_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}', comment='Flexible metadata in JSON format'),

        # Milvus Indexing Info
        sa.Column('index_name', sa.String(length=100), nullable=True, comment='Milvus collection/index name'),
        sa.Column('num_pages', sa.Integer(), nullable=True, comment='Number of pages in the document'),
        sa.Column('indexed_at', sa.DateTime(timezone=True), nullable=True, comment='Timestamp when document was indexed in Milvus'),
        sa.Column('indexing_status', sa.String(length=20), nullable=False, server_default='pending', comment='Indexing status: pending, processing, completed, failed'),
        sa.Column('indexing_error', sa.Text(), nullable=True, comment='Error message if indexing failed'),

        # Base Model Fields
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Primary Key and Unique Constraint
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('file_hash'),
    )

    # Create indexes for better query performance
    op.create_index('idx_ingested_docs_hash', 'ingested_documents', ['file_hash'], unique=True)
    op.create_index('idx_ingested_docs_type', 'ingested_documents', ['doc_type'], unique=False)
    op.create_index('idx_ingested_docs_category', 'ingested_documents', ['doc_category'], unique=False)
    op.create_index('idx_ingested_docs_index_name', 'ingested_documents', ['index_name'], unique=False)
    op.create_index('idx_ingested_docs_status', 'ingested_documents', ['indexing_status'], unique=False)
    op.create_index('idx_ingested_docs_created', 'ingested_documents', ['created_at'], unique=False)
    op.create_index('idx_ingested_docs_metadata_gin', 'ingested_documents', ['doc_metadata'], unique=False, postgresql_using='gin')

    # Add standard indexes from BaseModel
    op.create_index(op.f('ix_ingested_documents_filename'), 'ingested_documents', ['filename'], unique=False)
    op.create_index(op.f('ix_ingested_documents_id'), 'ingested_documents', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema - drop ingested_documents table."""
    op.drop_index(op.f('ix_ingested_documents_id'), table_name='ingested_documents')
    op.drop_index(op.f('ix_ingested_documents_filename'), table_name='ingested_documents')
    op.drop_index('idx_ingested_docs_metadata_gin', table_name='ingested_documents', postgresql_using='gin')
    op.drop_index('idx_ingested_docs_created', table_name='ingested_documents')
    op.drop_index('idx_ingested_docs_status', table_name='ingested_documents')
    op.drop_index('idx_ingested_docs_index_name', table_name='ingested_documents')
    op.drop_index('idx_ingested_docs_category', table_name='ingested_documents')
    op.drop_index('idx_ingested_docs_type', table_name='ingested_documents')
    op.drop_index('idx_ingested_docs_hash', table_name='ingested_documents')
    op.drop_table('ingested_documents')
