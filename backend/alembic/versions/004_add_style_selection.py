"""Add selected_style column for Phase 7 style selection feature.

Revision ID: 004
Revises: 003
Create Date: 2025-11-16 14:00:00.000000

Phase 7: User-Selectable Video Styles
- Adds selected_style column to store which style was chosen
- Enables querying projects by style
- Complements JSONB storage with direct column access

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add selected_style column to projects table."""
    op.add_column(
        'projects',
        sa.Column(
            'selected_style',
            sa.String(50),
            nullable=True,
            comment='Selected video style: cinematic, dark_premium, minimal_studio, lifestyle, 2d_animated, or NULL'
        )
    )
    
    # Add index for querying by style
    op.create_index(
        'idx_projects_selected_style',
        'projects',
        ['selected_style']
    )


def downgrade() -> None:
    """Remove selected_style column from projects table."""
    op.drop_index('idx_projects_selected_style', table_name='projects')
    op.drop_column('projects', 'selected_style')

