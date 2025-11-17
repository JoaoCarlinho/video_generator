"""Hardcode TikTok vertical (9:16) aspect ratio - Phase 3 refactor.

Revision ID: 005
Revises: 004
Create Date: 2025-11-17 14:00:00.000000

Phase 3: Simplify to TikTok Vertical Only
- Update default aspect_ratio to '9:16' (TikTok vertical)
- Update existing projects to use 9:16 if they have null or 16:9
- Remove multi-aspect support, hardcode vertical only
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Update aspect_ratio default to 9:16 and migrate existing projects."""
    # Update existing projects to 9:16 if they have null or 16:9
    op.execute("""
        UPDATE projects 
        SET aspect_ratio = '9:16' 
        WHERE aspect_ratio IS NULL OR aspect_ratio = '16:9'
    """)
    
    # Change default for new projects (via ALTER COLUMN)
    op.alter_column(
        'projects',
        'aspect_ratio',
        existing_type=sa.String(),
        server_default='9:16',
        existing_nullable=True,
        comment='TikTok vertical aspect ratio (hardcoded)'
    )


def downgrade() -> None:
    """Revert to 16:9 default (multi-aspect support)."""
    # Revert existing projects back to 16:9
    op.execute("""
        UPDATE projects 
        SET aspect_ratio = '16:9' 
        WHERE aspect_ratio = '9:16'
    """)
    
    # Change default back to 16:9
    op.alter_column(
        'projects',
        'aspect_ratio',
        existing_type=sa.String(),
        server_default='16:9',
        existing_nullable=True,
        comment='Video aspect ratio: 9:16, 1:1, or 16:9'
    )

