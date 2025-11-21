"""Create B2B SaaS schema with brands, perfumes, and campaigns.

Revision ID: 008
Revises: 007
Create Date: 2025-11-18 14:00:00.000000

Phase 2 B2B SaaS Transformation:
- Drop old projects table
- Create brands table (1 user = 1 brand)
- Create perfumes table (many perfumes per brand)
- Create campaigns table (many campaigns per perfume)
- Add all indexes, foreign keys, and constraints
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create B2B schema: brands, perfumes, campaigns."""
    
    # Drop old projects table (CASCADE to handle any dependencies)
    op.execute('DROP TABLE IF EXISTS projects CASCADE')
    
    # Create brands table
    op.create_table(
        'brands',
        sa.Column('brand_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('brand_name', sa.String(100), nullable=False),
        sa.Column('brand_logo_url', sa.String(500), nullable=False),
        sa.Column('brand_guidelines_url', sa.String(500), nullable=False),
        sa.Column('onboarding_completed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['auth.users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('brand_name', name='uq_brands_brand_name'),
        sa.UniqueConstraint('user_id', name='uq_brands_user_id')
    )
    
    # Create perfumes table
    op.create_table(
        'perfumes',
        sa.Column('perfume_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('brand_id', UUID(as_uuid=True), nullable=False),
        sa.Column('perfume_name', sa.String(200), nullable=False),
        sa.Column('perfume_gender', sa.String(20), nullable=False),
        sa.Column('front_image_url', sa.String(500), nullable=False),
        sa.Column('back_image_url', sa.String(500), nullable=True),
        sa.Column('top_image_url', sa.String(500), nullable=True),
        sa.Column('left_image_url', sa.String(500), nullable=True),
        sa.Column('right_image_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.brand_id'], ondelete='CASCADE'),
        sa.CheckConstraint("perfume_gender IN ('masculine', 'feminine', 'unisex')", name='ck_perfumes_gender'),
        sa.UniqueConstraint('brand_id', 'perfume_name', name='uq_perfumes_brand_perfume')
    )
    
    # Create campaigns table
    op.create_table(
        'campaigns',
        sa.Column('campaign_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('perfume_id', UUID(as_uuid=True), nullable=False),
        sa.Column('brand_id', UUID(as_uuid=True), nullable=False),
        sa.Column('campaign_name', sa.String(200), nullable=False),
        sa.Column('creative_prompt', sa.Text(), nullable=False),
        sa.Column('selected_style', sa.String(50), nullable=False),
        sa.Column('target_duration', sa.Integer(), nullable=False),
        sa.Column('num_variations', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('selected_variation_index', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('campaign_json', sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['perfume_id'], ['perfumes.perfume_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.brand_id'], ondelete='CASCADE'),
        sa.CheckConstraint("selected_style IN ('gold_luxe', 'dark_elegance', 'romantic_floral')", name='ck_campaigns_style'),
        sa.CheckConstraint('target_duration BETWEEN 15 AND 60', name='ck_campaigns_duration'),
        sa.CheckConstraint('num_variations BETWEEN 1 AND 3', name='ck_campaigns_variations'),
        sa.CheckConstraint('selected_variation_index IS NULL OR selected_variation_index BETWEEN 0 AND 2', name='ck_campaigns_selected_variation'),
        sa.CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", name='ck_campaigns_status'),
        sa.CheckConstraint('progress BETWEEN 0 AND 100', name='ck_campaigns_progress'),
        sa.UniqueConstraint('perfume_id', 'campaign_name', name='uq_campaigns_perfume_campaign')
    )
    
    # Create indexes for brands
    op.create_index('idx_brands_user_id', 'brands', ['user_id'])
    op.create_index('idx_brands_onboarding', 'brands', ['onboarding_completed'])
    op.create_index('idx_brands_name_lower', 'brands', [sa.text('LOWER(brand_name)')], unique=True)
    
    # Create indexes for perfumes
    op.create_index('idx_perfumes_brand_id', 'perfumes', ['brand_id'])
    op.create_index('idx_perfumes_gender', 'perfumes', ['perfume_gender'])
    
    # Create indexes for campaigns
    op.create_index('idx_campaigns_perfume_id', 'campaigns', ['perfume_id'])
    op.create_index('idx_campaigns_brand_id', 'campaigns', ['brand_id'])
    op.create_index('idx_campaigns_status', 'campaigns', ['status'])
    op.create_index('idx_campaigns_created_at', 'campaigns', ['created_at'], postgresql_using='btree', postgresql_ops={'created_at': 'DESC'})


def downgrade() -> None:
    """Revert B2B schema: drop campaigns, perfumes, brands."""
    
    # Drop indexes
    op.drop_index('idx_campaigns_created_at', table_name='campaigns')
    op.drop_index('idx_campaigns_status', table_name='campaigns')
    op.drop_index('idx_campaigns_brand_id', table_name='campaigns')
    op.drop_index('idx_campaigns_perfume_id', table_name='campaigns')
    op.drop_index('idx_perfumes_gender', table_name='perfumes')
    op.drop_index('idx_perfumes_brand_id', table_name='perfumes')
    op.drop_index('idx_brands_name_lower', table_name='brands')
    op.drop_index('idx_brands_onboarding', table_name='brands')
    op.drop_index('idx_brands_user_id', table_name='brands')
    
    # Drop tables (CASCADE handles foreign keys)
    op.drop_table('campaigns')
    op.drop_table('perfumes')
    op.drop_table('brands')
    
    # Note: We don't recreate the old projects table in downgrade
    # as that would require data migration which is not implemented

