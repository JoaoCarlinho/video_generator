"""Add multi-variation generation tracking fields.

Revision ID: 007
Revises: 006
Create Date: 2025-11-18 12:00:00.000000

Multi-Variation Generation Feature:
- Add num_variations column (INTEGER, default=1) - Number of video variations (1-3)
- Add selected_variation_index column (INTEGER, nullable) - Index of selected variation (0-2)
- Create indexes for query performance
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add variation tracking columns."""
    # Add num_variations column (default=1 for backward compatibility)
    op.add_column(
        'projects',
        sa.Column(
            'num_variations',
            sa.Integer(),
            nullable=False,
            server_default='1',
            comment='Number of video variations to generate (1-3)'
        )
    )
    
    # Add selected_variation_index column (nullable - null means not selected yet)
    op.add_column(
        'projects',
        sa.Column(
            'selected_variation_index',
            sa.Integer(),
            nullable=True,
            comment='Index of selected variation (0-2), NULL if not selected yet'
        )
    )
    
    # Create indexes for query performance
    op.create_index(
        'idx_projects_num_variations',
        'projects',
        ['num_variations']
    )
    
    op.create_index(
        'idx_projects_selected_variation',
        'projects',
        ['selected_variation_index']
    )


def downgrade() -> None:
    """Remove variation tracking columns."""
    op.drop_index('idx_projects_selected_variation', table_name='projects')
    op.drop_index('idx_projects_num_variations', table_name='projects')
    op.drop_column('projects', 'selected_variation_index')
    op.drop_column('projects', 'num_variations')

