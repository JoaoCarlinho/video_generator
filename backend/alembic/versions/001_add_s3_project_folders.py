"""Add S3 project folder columns for per-project organization.

Revision ID: 001
Revises: 
Create Date: 2025-11-15 00:00:00.000000

This migration adds two new columns to the projects table to support
the new S3 restructuring with per-project folder organization:
- s3_project_folder: The S3 key prefix (e.g., projects/{id}/)
- s3_project_folder_url: The public HTTPS URL to the project folder
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add S3 project folder columns."""
    # Add s3_project_folder column
    op.add_column(
        'projects',
        sa.Column(
            's3_project_folder',
            sa.String(),
            nullable=True,
            comment='S3 key prefix for project folder (e.g., projects/{id}/)'
        )
    )
    
    # Add s3_project_folder_url column
    op.add_column(
        'projects',
        sa.Column(
            's3_project_folder_url',
            sa.String(),
            nullable=True,
            comment='Public HTTPS URL to project folder in S3'
        )
    )


def downgrade() -> None:
    """Remove S3 project folder columns."""
    # Drop columns in reverse order
    op.drop_column('projects', 's3_project_folder_url')
    op.drop_column('projects', 's3_project_folder')

