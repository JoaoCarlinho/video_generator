"""Add local storage paths for local-first generation.

Revision ID: 002
Revises: 001
Create Date: 2025-11-16

This migration adds fields to track local storage paths and status updates
for the local-first generation flow.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add local storage tracking columns
    op.add_column('projects', sa.Column('local_project_path', sa.String(500), nullable=True))
    op.add_column('projects', sa.Column('local_video_paths', sa.JSON(), nullable=True))
    op.add_column('projects', sa.Column('local_input_files', sa.JSON(), nullable=True))
    op.add_column('projects', sa.Column('local_draft_files', sa.JSON(), nullable=True))
    
    # Add comment to help developers understand the flow
    op.execute("""
    COMMENT ON COLUMN projects.local_project_path IS 
    'Root directory for all local files: /tmp/genads/{project_id}';
    """)
    
    op.execute("""
    COMMENT ON COLUMN projects.local_video_paths IS 
    'JSON dict mapping aspect_ratio to local video path: {"16:9": "/tmp/genads/{id}/final/video_16-9.mp4"}';
    """)
    
    op.execute("""
    COMMENT ON COLUMN projects.local_input_files IS 
    'JSON dict of uploaded files: {"product_image": "/tmp/genads/{id}/input/product.png", ...}';
    """)
    
    op.execute("""
    COMMENT ON COLUMN projects.local_draft_files IS 
    'JSON dict of draft/intermediate files: {"scene_1_bg": "/tmp/genads/{id}/drafts/scene_1_bg.mp4", ...}';
    """)


def downgrade() -> None:
    # Remove columns if rolling back
    op.drop_column('projects', 'local_draft_files')
    op.drop_column('projects', 'local_input_files')
    op.drop_column('projects', 'local_video_paths')
    op.drop_column('projects', 'local_project_path')

