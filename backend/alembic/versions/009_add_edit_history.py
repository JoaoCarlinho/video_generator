"""Add edit history tracking to campaigns

Revision ID: 009
Revises: 008
Create Date: 2025-01-20 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    # Add edit_history column to campaigns table
    op.add_column(
        'campaigns',
        sa.Column('edit_history', postgresql.JSONB, nullable=True, comment='Edit history tracking')
    )
    
    # Create GIN index for efficient JSONB queries
    op.create_index(
        'idx_campaigns_edit_history',
        'campaigns',
        ['edit_history'],
        postgresql_using='gin',
        unique=False
    )
    
    # Initialize existing campaigns with empty edit history
    op.execute("""
        UPDATE campaigns 
        SET edit_history = '{"edits": [], "total_edit_cost": 0.0, "edit_count": 0}'::jsonb
        WHERE edit_history IS NULL
    """)


def downgrade():
    # Drop index first
    op.drop_index('idx_campaigns_edit_history', table_name='campaigns')
    
    # Drop column
    op.drop_column('campaigns', 'edit_history')

