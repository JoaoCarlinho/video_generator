"""Add multi-format output fields

Revision ID: 004
Revises: 003
Create Date: 2025-11-16

This migration adds support for:
- Multiple product images (array of URLs)
- Scene-specific custom backgrounds (JSONB)
- Multiple output format aspect ratios (array)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add columns for multi-format video generation."""
    # Add product_images array column (TEXT[] for URL array)
    op.add_column('projects', sa.Column(
        'product_images',
        sa.ARRAY(sa.Text),
        nullable=True,
        comment='Array of product image URLs (max 10). First is primary.'
    ))

    # Add scene_backgrounds JSON column (stores {sceneId: backgroundUrl} mappings)
    op.add_column('projects', sa.Column(
        'scene_backgrounds',
        JSONB,
        nullable=True,
        comment='JSON array of scene background mappings [{sceneId, backgroundUrl}]'
    ))

    # Add output_formats array column (TEXT[] for aspect ratio strings)
    op.add_column('projects', sa.Column(
        'output_formats',
        sa.ARRAY(sa.Text),
        nullable=True,
        server_default=sa.text("ARRAY['16:9']"),
        comment='Array of desired aspect ratios (9:16, 16:9, 1:1)'
    ))


def downgrade() -> None:
    """Remove multi-format columns."""
    op.drop_column('projects', 'output_formats')
    op.drop_column('projects', 'scene_backgrounds')
    op.drop_column('projects', 'product_images')
