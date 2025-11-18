"""Add perfume-specific fields and simplify video storage - Phase 9 refactor.

Revision ID: 006
Revises: 005
Create Date: 2025-11-17 16:00:00.000000

Phase 9: Update API and Database for Perfume Specialization
- Add perfume_name column (String(200), nullable)
- Add perfume_gender column (String(20), nullable) - 'masculine', 'feminine', 'unisex'
- Add local_video_path column (String(500), nullable) - single video path (TikTok vertical only)
- Keep local_video_paths column for backward compatibility (will be deprecated)
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add perfume-specific fields and single video path column."""
    # Add perfume_name column
    op.add_column(
        'projects',
        sa.Column(
            'perfume_name',
            sa.String(200),
            nullable=True,
            comment='Perfume product name (e.g., "Noir Élégance")'
        )
    )
    
    # Add perfume_gender column
    op.add_column(
        'projects',
        sa.Column(
            'perfume_gender',
            sa.String(20),
            nullable=True,
            comment='Perfume gender: masculine, feminine, or unisex'
        )
    )
    
    # Add local_video_path column (single video path for TikTok vertical)
    op.add_column(
        'projects',
        sa.Column(
            'local_video_path',
            sa.String(500),
            nullable=True,
            comment='Local path to single TikTok vertical video (9:16, 1080x1920)'
        )
    )
    
    # Add indexes for querying
    op.create_index(
        'idx_projects_perfume_name',
        'projects',
        ['perfume_name']
    )
    
    op.create_index(
        'idx_projects_perfume_gender',
        'projects',
        ['perfume_gender']
    )


def downgrade() -> None:
    """Remove perfume-specific fields and single video path column."""
    op.drop_index('idx_projects_perfume_gender', table_name='projects')
    op.drop_index('idx_projects_perfume_name', table_name='projects')
    op.drop_column('projects', 'local_video_path')
    op.drop_column('projects', 'perfume_gender')
    op.drop_column('projects', 'perfume_name')

