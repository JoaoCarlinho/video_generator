"""Initial schema - brands, products, campaigns, and projects tables

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-01-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create brands table
    op.create_table(
        'brands',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('website', sa.String(255), nullable=True),
        sa.Column('industry', sa.String(100), nullable=True),
        sa.Column('brand_voice_keywords', postgresql.JSONB, nullable=True),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_brands_user_id', 'brands', ['user_id'])
    op.create_index('ix_brands_created_at', 'brands', ['created_at'])

    # Create products table
    op.create_table(
        'products',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('brand_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('product_type', sa.String(50), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('icp_segment', sa.Text(), nullable=True),
        sa.Column('image_urls', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_products_brand_id', 'products', ['brand_id'])

    # Create campaigns table
    op.create_table(
        'campaigns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('seasonal_event', sa.String(100), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('duration', sa.Integer(), nullable=False),
        sa.Column('scene_configs', postgresql.JSONB, nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default=sa.text("'draft'"), index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_campaigns_product_id', 'campaigns', ['product_id'])
    op.create_index('ix_campaigns_status', 'campaigns', ['status'])
    op.create_index('ix_campaigns_created_at', 'campaigns', ['created_at'])

    # Create projects table (existing ad generation projects)
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('brand_name', sa.String(), nullable=True),
        sa.Column('brand_url', sa.String(), nullable=True),
        sa.Column('brand_tone', sa.String(), nullable=True),
        sa.Column('product_name', sa.String(), nullable=True),
        sa.Column('product_image_url', sa.String(), nullable=True),
        sa.Column('product_images', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('product_description', sa.String(), nullable=True),
        sa.Column('product_features', sa.String(), nullable=True),
        sa.Column('audience_age_range', sa.String(), nullable=True),
        sa.Column('audience_gender', sa.String(), nullable=True),
        sa.Column('audience_interests', sa.String(), nullable=True),
        sa.Column('output_formats', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('video_url', sa.String(), nullable=True),
        sa.Column('script_content', sa.String(), nullable=True),
        sa.Column('generation_status', sa.String(), nullable=True),
        sa.Column('hooks', postgresql.JSONB, nullable=True),
        sa.Column('transitions', postgresql.JSONB, nullable=True),
        sa.Column('scenes', postgresql.JSONB, nullable=True),
        sa.Column('selected_style', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_projects_user_id', 'projects', ['user_id'])


def downgrade():
    op.drop_index('ix_campaigns_created_at', table_name='campaigns')
    op.drop_index('ix_campaigns_status', table_name='campaigns')
    op.drop_index('ix_campaigns_product_id', table_name='campaigns')
    op.drop_table('campaigns')

    op.drop_index('ix_products_brand_id', table_name='products')
    op.drop_table('products')

    op.drop_index('ix_brands_created_at', table_name='brands')
    op.drop_index('ix_brands_user_id', table_name='brands')
    op.drop_table('brands')

    op.drop_index('ix_projects_user_id', table_name='projects')
    op.drop_table('projects')
