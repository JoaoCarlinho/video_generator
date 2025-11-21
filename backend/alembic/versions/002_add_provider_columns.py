"""Add provider columns to projects table

Revision ID: 002_add_provider_columns
Revises: 001_initial_schema
Create Date: 2025-01-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_add_provider_columns'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    """Add video provider tracking columns to projects table."""

    # Add video_provider column
    op.add_column(
        'projects',
        sa.Column(
            'video_provider',
            sa.String(20),
            nullable=False,
            server_default='replicate',
            comment='Video generation provider: replicate or ecs'
        )
    )

    # Add video_provider_metadata column for provider-specific data
    op.add_column(
        'projects',
        sa.Column(
            'video_provider_metadata',
            postgresql.JSONB,
            nullable=True,
            comment='Provider-specific metadata (endpoint version, failover events)'
        )
    )

    # Create index on video_provider for analytics queries
    op.create_index(
        'idx_projects_video_provider',
        'projects',
        ['video_provider']
    )


def downgrade():
    """Remove provider tracking columns from projects table."""

    # Drop index first
    op.drop_index('idx_projects_video_provider', table_name='projects')

    # Drop columns
    op.drop_column('projects', 'video_provider_metadata')
    op.drop_column('projects', 'video_provider')
