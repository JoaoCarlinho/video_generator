"""Add aspect_ratio column to projects table.

Revision ID: 003
Revises: 002_add_local_storage_paths
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add aspect_ratio column with default value
    op.add_column('projects', sa.Column('aspect_ratio', sa.String(), nullable=True))
    
    # Set default value for existing rows
    op.execute("UPDATE projects SET aspect_ratio = '16:9' WHERE aspect_ratio IS NULL")
    
    # Make it non-nullable with default
    op.alter_column('projects', 'aspect_ratio', nullable=False, existing_type=sa.String())
    
    op.execute("""
    COMMENT ON COLUMN projects.aspect_ratio IS 
    'Video aspect ratio: 9:16 (vertical/1080x1920), 1:1 (square/1080x1080), or 16:9 (horizontal/1920x1080)';
    """)


def downgrade() -> None:
    op.drop_column('projects', 'aspect_ratio')

