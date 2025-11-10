"""add_compliance_frameworks_table

Revision ID: 002_compliance_frameworks
Revises: 001_ingested_docs
Create Date: 2025-11-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_compliance_frameworks'
down_revision: Union[str, Sequence[str], None] = '001_ingested_docs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create compliance_frameworks table."""
    op.create_table(
        'compliance_frameworks',
        # Basic information
        sa.Column('name', sa.String(length=200), nullable=False, comment='Framework name (e.g., SOC 2 Type II)'),
        sa.Column('description', sa.Text(), nullable=True, comment='Framework description'),
        sa.Column('version', sa.String(length=50), nullable=True, comment='Framework version (e.g., 2023.1)'),

        # Document references
        sa.Column(
            'framework_document_id',
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment='Reference to framework document in documents table'
        ),

        # Milvus index for semantic search
        sa.Column(
            'framework_index_name',
            sa.String(length=100),
            nullable=False,
            comment='Milvus collection name for framework documents'
        ),

        # Compliance requirements checklist
        sa.Column(
            'compliance_todos',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='[]',
            comment='Array of compliance requirement strings to check'
        ),

        # Additional metadata
        sa.Column(
            'framework_metadata',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='{}',
            comment='Additional framework metadata (category, jurisdiction, etc.)'
        ),

        # Status
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', comment='Whether framework is active'),

        # Audit fields
        sa.Column('created_by_email', sa.String(length=255), nullable=True, comment='Email of user who created the framework'),
        sa.Column('updated_by_email', sa.String(length=255), nullable=True, comment='Email of user who last updated the framework'),

        # Base Model Fields
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Primary Key and Unique Constraint
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),

        # Foreign Key
        sa.ForeignKeyConstraint(
            ['framework_document_id'],
            ['documents.id'],
            ondelete='CASCADE'
        ),
    )

    # Create indexes for better query performance
    op.create_index('idx_compliance_frameworks_name', 'compliance_frameworks', ['name'], unique=True)
    op.create_index('idx_compliance_frameworks_index_name', 'compliance_frameworks', ['framework_index_name'], unique=False)
    op.create_index('idx_compliance_frameworks_is_active', 'compliance_frameworks', ['is_active'], unique=False)
    op.create_index('idx_compliance_frameworks_framework_doc_id', 'compliance_frameworks', ['framework_document_id'], unique=False)

    # GIN index for JSONB queries
    op.create_index(
        'idx_compliance_frameworks_todos_gin',
        'compliance_frameworks',
        ['compliance_todos'],
        unique=False,
        postgresql_using='gin'
    )
    op.create_index(
        'idx_compliance_frameworks_metadata_gin',
        'compliance_frameworks',
        ['framework_metadata'],
        unique=False,
        postgresql_using='gin'
    )

    # Add standard indexes from BaseModel
    op.create_index(op.f('ix_compliance_frameworks_id'), 'compliance_frameworks', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema - drop compliance_frameworks table."""
    op.drop_index(op.f('ix_compliance_frameworks_id'), table_name='compliance_frameworks')
    op.drop_index('idx_compliance_frameworks_metadata_gin', table_name='compliance_frameworks', postgresql_using='gin')
    op.drop_index('idx_compliance_frameworks_todos_gin', table_name='compliance_frameworks', postgresql_using='gin')
    op.drop_index('idx_compliance_frameworks_framework_doc_id', table_name='compliance_frameworks')
    op.drop_index('idx_compliance_frameworks_is_active', table_name='compliance_frameworks')
    op.drop_index('idx_compliance_frameworks_index_name', table_name='compliance_frameworks')
    op.drop_index('idx_compliance_frameworks_name', table_name='compliance_frameworks')
    op.drop_table('compliance_frameworks')
