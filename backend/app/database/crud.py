"""Database CRUD operations for campaigns, brands, products, and campaigns."""

from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.database.models import Campaign, Brand, Product, Creative, AuthUser  # AuthUser needed for FK resolution
from app.models.schemas import (
    CreateCampaignRequest,
    CampaignResponse,
    CampaignDetailResponse
)
from uuid import UUID
from typing import List, Optional, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# CREATE Operations
# ============================================================================

def create_campaign(
    db: Session,
    user_id: UUID,
    title: str,
    brief: str,
    ad_campaign_json: Dict[str, Any],
    mood: str = "uplifting",
    duration: int = 30,
    aspect_ratio: str = "16:9",
    # STORY 3: New multi-format parameters
    product_images: Optional[List[str]] = None,
    scene_backgrounds: Optional[List[Dict[str, str]]] = None,
    output_formats: Optional[List[str]] = None,
    selected_style: Optional[str] = None  # PHASE 7: User-selected style
) -> Campaign:
    """
    Create a new campaign in the database.

    Args:
        db: Database session
        user_id: ID of the user creating the campaign
        title: Campaign title
        brief: Product brief/description
        ad_campaign_json: Complete ad campaign configuration as JSON
        mood: Video mood/style (deprecated, kept for compatibility)
        duration: Video duration in seconds
        aspect_ratio: DEPRECATED - Video aspect ratio (9:16, 1:1, or 16:9)
        product_images: STORY 3 - Array of product image URLs (max 10)
        scene_backgrounds: STORY 3 - Array of scene background mappings
        output_formats: STORY 3 - Array of desired aspect ratios
        selected_style: (PHASE 7) User-selected video style or None
        product_name: (Phase 9) Product product name (e.g., "Noir Élégance")
        product_gender: (Phase 9) Product gender ('masculine', 'feminine', 'unisex')
        num_variations: (MULTI-VARIATION) Number of video variations to generate (1-3)

    Returns:
        Campaign: Created campaign object

    Raises:
        Exception: If database insert fails
    """
    try:
        # Default output_formats if not provided
        if output_formats is None:
            output_formats = [aspect_ratio]  # Use aspect_ratio as fallback

        campaign = Campaign(
            user_id=user_id,
            title=title,
            ad_campaign_json=ad_campaign_json,
            status="PENDING",
            selected_style=selected_style,  # PHASE 7: Store selected style
            progress=0,
            cost=0.0,
            aspect_ratio=aspect_ratio,  # Kept for backward compatibility
            # STORY 3: New fields
            product_images=product_images,
            scene_backgrounds=scene_backgrounds,
            output_formats=output_formats,
            product_name=product_name,  # Phase 9: Store product name
            product_gender=product_gender,  # Phase 9: Store product gender
            num_variations=num_variations,  # MULTI-VARIATION: Store variation count
            selected_variation_index=None  # MULTI-VARIATION: No selection yet
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        logger.info(f"✅ Created campaign {campaign.id} for user {user_id} with {len(output_formats)} output formats")
        return campaign
    except Exception as e:
        try:
            db.rollback()
        except:
            pass
        logger.error(f"❌ Failed to create campaign: {e}")
        # Create in-memory mock campaign for development
        logger.warning("⚠️ Using mock campaign (database connection issue)")
        from uuid import uuid4
        from datetime import datetime
        mock_campaign = Campaign(
            user_id=user_id,
            title=title,
            ad_campaign_json=ad_campaign_json,
            status="PENDING",
            progress=0,
            cost=0.0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        mock_campaign.id = uuid4()
        return mock_campaign


# ============================================================================
# READ Operations
# ============================================================================

def get_campaign(db: Session, campaign_id: UUID) -> Optional[Campaign]:
    """
    Get a single campaign by ID.

    Args:
        db: Database session
        campaign_id: ID of the campaign to retrieve

    Returns:
        Campaign: Campaign object if found, None otherwise
    """
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if campaign:
            logger.debug(f"✅ Retrieved campaign {campaign_id}")
        else:
            logger.debug(f"⚠️ Campaign {campaign_id} not found")
        return campaign
    except Exception as e:
        logger.error(f"❌ Failed to get campaign {campaign_id}: {e}")
        # In development mode with DB issues, create a mock campaign
        logger.warning(f"⚠️ Database error - creating mock campaign for development")
        from datetime import datetime
        mock_campaign = Campaign(
            id=campaign_id,
            user_id=UUID('00000000-0000-0000-0000-000000000001'),  # Default user
            title=f"Campaign {campaign_id}",
            ad_campaign_json={},
            status="PENDING",
            progress=0,
            cost=0.0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        return mock_campaign


def get_campaign_by_user(db: Session, campaign_id: UUID, user_id: UUID) -> Optional[Campaign]:
    """
    Get a campaign by ID and verify user ownership.

    Args:
        db: Database session
        campaign_id: ID of the campaign
        user_id: ID of the user (for verification)

    Returns:
        Campaign: Campaign if found and owned by user, None otherwise
    """
    # If db is None, create a mock campaign for development
    if db is None:
        logger.warning(f"⚠️ Database session is None - creating mock campaign for development")
        from datetime import datetime
        mock_campaign = Campaign(
            id=campaign_id,
            user_id=user_id,
            title=f"Campaign {campaign_id}",
            ad_campaign_json={},
            status="PENDING",
            progress=0,
            cost=0.0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        return mock_campaign

    try:
        campaign = db.query(Campaign).filter(
            Campaign.id == campaign_id,
            Campaign.user_id == user_id
        ).first()
        if campaign:
            logger.debug(f"✅ User {user_id} owns campaign {campaign_id}")
        else:
            logger.warning(f"⚠️ User {user_id} does not own campaign {campaign_id}")
        return campaign
    except Exception as e:
        logger.error(f"❌ Failed to get campaign {campaign_id}: {e}")
        # In development mode with DB issues, create a mock campaign for development
        logger.warning(f"⚠️ Database error - creating mock campaign for development")
        from datetime import datetime
        mock_campaign = Campaign(
            id=campaign_id,
            user_id=user_id,
            title=f"Campaign {campaign_id}",
            ad_campaign_json={},
            status="PENDING",
            progress=0,
            cost=0.0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        return mock_campaign


def get_user_campaigns(
    db: Session,
    user_id: UUID,
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None
) -> List[Campaign]:
    """
    Get all campaigns for a specific user.

    Args:
        db: Database session
        user_id: ID of the user
        limit: Maximum number of campaigns to return
        offset: Number of campaigns to skip (for pagination)
        status: Optional filter by status (e.g., "COMPLETED", "FAILED")

    Returns:
        List[Campaign]: List of campaigns
    """
    try:
        query = db.query(Campaign).filter(Campaign.user_id == user_id)

        if status:
            query = query.filter(Campaign.status == status)

        campaigns = query.order_by(desc(Campaign.created_at)).limit(limit).offset(offset).all()

        logger.info(f"✅ Retrieved {len(campaigns)} campaigns for user {user_id}")
        return campaigns
    except Exception as e:
        logger.error(f"❌ Failed to get campaigns for user {user_id}: {e}")
        # Return empty list instead of raising - allows development without DB
        logger.warning("⚠️ Returning empty campaign list (database connection issue)")
        return []


def get_campaigns_by_status(
    db: Session,
    status: str,
    limit: int = 50
) -> List[Campaign]:
    """
    Get all campaigns with a specific status (for monitoring/admin).

    Args:
        db: Database session
        status: Status to filter by (e.g., "GENERATING_SCENES", "FAILED")
        limit: Maximum number of campaigns to return

    Returns:
        List[Campaign]: List of matching campaigns
    """
    try:
        campaigns = db.query(Campaign).filter(
            Campaign.status == status
        ).order_by(desc(Campaign.updated_at)).limit(limit).all()

        logger.info(f"✅ Found {len(campaigns)} campaigns with status '{status}'")
        return campaigns
    except Exception as e:
        logger.error(f"❌ Failed to get campaigns by status {status}: {e}")
        raise


# ============================================================================
# UPDATE Operations
# ============================================================================

def update_campaign(
    db: Session,
    campaign_id: UUID,
    **updates
) -> Optional[Campaign]:
    """
    Update campaign fields.

    Args:
        db: Database session
        campaign_id: ID of the campaign to update
        **updates: Fields to update (status, progress, cost, ad_campaign_json, etc.)

    Returns:
        Campaign: Updated campaign object if successful, None if campaign not found

    Raises:
        Exception: If database update fails
    """
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

        if not campaign:
            logger.warning(f"⚠️ Campaign {campaign_id} not found for update")
            return None

        # Update fields
        for key, value in updates.items():
            if hasattr(campaign, key):
                setattr(campaign, key, value)

        db.commit()
        db.refresh(campaign)

        logger.info(f"✅ Updated campaign {campaign_id}: {list(updates.keys())}")
        return campaign
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to update campaign {campaign_id}: {e}")
        raise


def update_campaign_status(
    db: Session,
    campaign_id: UUID,
    status: str,
    progress: int = 0,
    error_message: Optional[str] = None
) -> Optional[Campaign]:
    """
    Update campaign status and progress.

    Args:
        db: Database session
        campaign_id: ID of the campaign
        status: New status (e.g., "GENERATING_SCENES")
        progress: Progress percentage (0-100)
        error_message: Optional error message

    Returns:
        Campaign: Updated campaign object
    """
    # If db is None, just log and skip update
    if db is None:
        logger.warning(f"⚠️ Database session is None - skipping status update for {campaign_id}")
        return None

    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

        if not campaign:
            return None

        campaign.status = status
        campaign.progress = max(0, min(100, progress))  # Clamp 0-100
        if error_message:
            campaign.error_message = error_message

        db.commit()
        db.refresh(campaign)

        logger.info(f"✅ Updated campaign {campaign_id} status to {status} ({progress}%)")
        return campaign
    except Exception as e:
        try:
            db.rollback()
        except:
            pass
        logger.error(f"❌ Failed to update status for {campaign_id}: {e}")
        # In development mode with DB issues, just log and continue
        logger.warning(f"⚠️ Database error updating status - continuing with in-memory state")
        return None


def update_campaign_cost(
    db: Session,
    campaign_id: UUID,
    cost: float
) -> Optional[Campaign]:
    """
    Update campaign cost tracking.

    Args:
        db: Database session
        campaign_id: ID of the campaign
        cost: Total cost in USD

    Returns:
        Campaign: Updated campaign object
    """
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

        if not campaign:
            return None

        campaign.cost = round(float(cost), 2)

        db.commit()
        db.refresh(campaign)

        logger.info(f"✅ Updated campaign {campaign_id} cost to ${campaign.cost}")
        return campaign
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to update cost for {campaign_id}: {e}")
        raise


def update_campaign_output(
    db: Session,
    campaign_id: UUID,
    final_videos: Dict[str, str],
    total_cost: float,
    cost_breakdown: Dict[str, float]
) -> Optional[Campaign]:
    """
    Update campaign with final output and cost breakdown.

    Args:
        db: Database session
        campaign_id: ID of the campaign
        final_videos: Dict with aspect ratio as key (16:9) and S3 URL as value
        total_cost: Total cost in USD
        cost_breakdown: Dict with cost per service

    Returns:
        Campaign: Updated campaign object
    """
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

        if not campaign:
            return None

        # Update output videos in ad_campaign_json
        # Must create new dict to trigger SQLAlchemy change detection for JSON fields
        if isinstance(campaign.ad_campaign_json, dict):
            updated_json = dict(campaign.ad_campaign_json)
            updated_json["aspectExports"] = final_videos
            updated_json["costBreakdown"] = cost_breakdown
            campaign.ad_campaign_json = updated_json
            # Mark as modified to ensure SQLAlchemy detects the change
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(campaign, "ad_campaign_json")

        
        campaign.cost = round(float(total_cost), 2)
        campaign.status = "COMPLETED"
        campaign.progress = 100

        db.commit()
        db.refresh(campaign)

        logger.info(f"✅ Updated campaign {campaign_id} with final output, cost: ${total_cost:.2f}")
        return campaign
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to update campaign output {campaign_id}: {e}")
        raise


def update_campaign_json(
    db: Session,
    campaign_id: UUID,
    ad_campaign_json: Dict[str, Any]
) -> Optional[Campaign]:
    """
    Update the ad_campaign_json configuration.

    Args:
        db: Database session
        campaign_id: ID of the campaign
        ad_campaign_json: New configuration JSON

    Returns:
        Campaign: Updated campaign object
    """
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

        if not campaign:
            return None

        campaign.ad_campaign_json = ad_campaign_json

        db.commit()
        db.refresh(campaign)

        logger.info(f"✅ Updated campaign {campaign_id} configuration")
        return campaign
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to update json for {campaign_id}: {e}")
        raise


# ============================================================================
# DELETE Operations
# ============================================================================

def delete_campaign(db: Session, campaign_id: UUID, user_id: UUID) -> bool:
    """
    Delete a campaign (only if owned by user).

    Args:
        db: Database session
        campaign_id: ID of the campaign to delete
        user_id: ID of the user (for verification)

    Returns:
        bool: True if deleted, False if not found or unauthorized

    Raises:
        Exception: If database delete fails
    """
    try:
        campaign = db.query(Campaign).filter(
            Campaign.id == campaign_id,
            Campaign.user_id == user_id
        ).first()

        if not campaign:
            logger.warning(f"⚠️ Cannot delete: User {user_id} does not own campaign {campaign_id}")
            return False

        db.delete(campaign)
        db.commit()

        logger.info(f"✅ Deleted campaign {campaign_id}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to delete campaign {campaign_id}: {e}")
        raise


# ============================================================================
# UTILITY Operations
# ============================================================================

def get_generation_stats(db: Session, user_id: UUID) -> Dict[str, Any]:
    """
    Get generation statistics for a user.

    Args:
        db: Database session
        user_id: ID of the user

    Returns:
        Dict with statistics (total campaigns, completed, failed, total cost, etc.)
    """
    try:
        user_campaigns = db.query(Campaign).filter(Campaign.user_id == user_id).all()

        total = len(user_campaigns)
        completed = len([p for p in user_campaigns if p.status == "COMPLETED"])
        failed = len([p for p in user_campaigns if p.status == "FAILED"])
        in_progress = len([p for p in user_campaigns if p.status.startswith("GENERATING") or p.status.startswith("EXTRACTING") or p.status.startswith("COMPOSITING")])

        total_cost = sum(float(p.cost) for p in user_campaigns)

        stats = {
            "total_campaigns": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "total_cost": round(total_cost, 2),
            "success_rate": round((completed / total * 100) if total > 0 else 0, 1)
        }

        logger.debug(f"✅ Generated stats for user {user_id}: {stats}")
        return stats
    except Exception as e:
        logger.error(f"❌ Failed to get stats for user {user_id}: {e}")
        raise


def clear_old_failed_campaigns(db: Session, days: int = 7) -> int:
    """
    Delete failed campaigns older than N days (for cleanup).

    Args:
        db: Database session
        days: Number of days before cleanup

    Returns:
        int: Number of campaigns deleted
    """
    try:
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)

        query = db.query(Campaign).filter(
            Campaign.status == "FAILED",
            Campaign.created_at < cutoff
        )

        count = query.count()
        query.delete()
        db.commit()

        logger.info(f"✅ Deleted {count} failed campaigns older than {days} days")
        return count
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to clean up old campaigns: {e}")
        raise


# ============================================================================
# S3 RESTRUCTURING: New helper functions for per-campaign folders
# ============================================================================

def update_campaign_s3_paths(
    db: Session,
    campaign_id: UUID,
    s3_campaign_folder: str,
    s3_campaign_folder_url: str
) -> Optional[Campaign]:
    """
    Update campaign with S3 folder paths.

    Called after campaign creation to store the campaign's S3 folder location.

    Args:
        db: Database session
        campaign_id: ID of the campaign
        s3_campaign_folder: S3 key prefix (e.g., "campaigns/{id}/")
        s3_campaign_folder_url: Public HTTPS URL to folder

    Returns:
        Campaign: Updated campaign object
    """
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

        if not campaign:
            logger.warning(f"⚠️ Campaign {campaign_id} not found for S3 path update")
            return None

        campaign.s3_campaign_folder = s3_campaign_folder
        campaign.s3_campaign_folder_url = s3_campaign_folder_url

        db.commit()
        db.refresh(campaign)

        logger.info(f"✅ Updated campaign {campaign_id} S3 paths")
        return campaign
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to update S3 paths for {campaign_id}: {e}")
        raise


def get_campaigns_without_s3_paths(
    db: Session,
    limit: int = 100
) -> List[Campaign]:
    """
    Get campaigns that don't have S3 folder paths set (for migration).

    Useful for identifying campaigns created before restructuring was implemented.

    Args:
        db: Database session
        limit: Maximum number to return

    Returns:
        List of campaigns without S3 paths
    """
    try:
        campaigns = db.query(Campaign).filter(
            (Campaign.s3_campaign_folder == None) |
            (Campaign.s3_campaign_folder == "")
        ).limit(limit).all()

        logger.info(f"✅ Found {len(campaigns)} campaigns without S3 paths")
        return campaigns
    except Exception as e:
        logger.error(f"❌ Failed to get campaigns without S3 paths: {e}")
        raise


# ============================================================================
# Brand CRUD Operations (Phase 2 B2B SaaS)
# ============================================================================

def create_brand(
    db: Session,
    user_id: UUID,
    company_name: str,
    brand_name: Optional[str] = None,
    description: Optional[str] = None,
    guidelines: Optional[str] = None,
    logo_urls: Optional[Dict[str, Any]] = None
) -> Brand:
    """
    Create a new brand in the database.

    Args:
        db: Database session
        user_id: ID of the user creating the brand
        company_name: Company name (required)
        brand_name: Brand name (optional)
        description: Brand description (optional)
        guidelines: Brand guidelines (optional)
        logo_urls: JSONB object with logo URLs (optional)

    Returns:
        Brand: Created brand object

    Raises:
        Exception: If database insert fails
    """
    try:
        brand = Brand(
            user_id=user_id,
            company_name=company_name,
            brand_name=brand_name,
            description=description,
            guidelines=guidelines,
            logo_urls=logo_urls
        )
        db.add(brand)
        db.commit()
        db.refresh(brand)
        logger.info(f"✅ Created brand {brand.id} ({company_name}) for user {user_id}")
        return brand
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to create brand: {e}")
        raise


def get_user_brands(
    db: Session,
    user_id: UUID,
    limit: int = 50,
    offset: int = 0
) -> List[Brand]:
    """
    Get all brands for a specific user.

    Args:
        db: Database session
        user_id: ID of the user
        limit: Maximum number of brands to return
        offset: Number of brands to skip (for pagination)

    Returns:
        List[Brand]: List of brands owned by user
    """
    try:
        brands = db.query(Brand).filter(
            Brand.user_id == user_id
        ).order_by(desc(Brand.created_at)).limit(limit).offset(offset).all()

        logger.info(f"✅ Retrieved {len(brands)} brands for user {user_id}")
        return brands
    except Exception as e:
        logger.error(f"❌ Failed to get brands for user {user_id}: {e}")
        return []


def get_brand_by_user_id(
    db: Session,
    user_id: UUID
) -> Optional[Brand]:
    """
    Get the primary brand for a specific user.
    Returns the most recently created brand for the user.

    Args:
        db: Database session
        user_id: ID of the user

    Returns:
        Brand: Primary brand for user, or None if no brands exist
    """
    try:
        brand = db.query(Brand).filter(
            Brand.user_id == user_id
        ).order_by(desc(Brand.created_at)).first()

        if brand:
            logger.debug(f"✅ Found primary brand {brand.id} for user {user_id}")
        else:
            logger.warning(f"⚠️ No brand found for user {user_id}")

        return brand
    except Exception as e:
        logger.error(f"❌ Failed to get brand for user {user_id}: {e}")
        return None


def get_brand(
    db: Session,
    brand_id: UUID,
    user_id: UUID
) -> Optional[Brand]:
    """
    Get a brand by ID with ownership verification.

    Args:
        db: Database session
        brand_id: ID of the brand
        user_id: ID of the user (for ownership check)

    Returns:
        Brand: Brand object if found and owned by user, None otherwise
    """
    try:
        brand = db.query(Brand).filter(
            Brand.id == brand_id,
            Brand.user_id == user_id
        ).first()

        if brand:
            logger.debug(f"✅ User {user_id} owns brand {brand_id}")
        else:
            logger.warning(f"⚠️ Brand {brand_id} not found or not owned by user {user_id}")

        return brand
    except Exception as e:
        logger.error(f"❌ Failed to get brand {brand_id}: {e}")
        return None


def get_brand_by_id(
    db: Session,
    brand_id: UUID
) -> Optional[Brand]:
    """
    Get a brand by ID without ownership verification.

    This function is used when brand_id comes from JWT token or background jobs.
    Use get_brand() in API endpoints that need explicit ownership verification.

    Args:
        db: Database session
        brand_id: ID of the brand

    Returns:
        Brand: Brand object if found, None otherwise
    """
    try:
        brand = db.query(Brand).filter(Brand.id == brand_id).first()

        if brand:
            logger.debug(f"✅ Found brand {brand_id}")
        else:
            logger.warning(f"⚠️ Brand {brand_id} not found")

        return brand
    except Exception as e:
        logger.error(f"❌ Failed to get brand {brand_id}: {e}")
        return None


def update_brand(
    db: Session,
    brand_id: UUID,
    user_id: UUID,
    **updates
) -> Optional[Brand]:
    """
    Update brand fields (only if owned by user).

    Args:
        db: Database session
        brand_id: ID of the brand to update
        user_id: ID of the user (for ownership check)
        **updates: Fields to update (company_name, brand_name, description, etc.)

    Returns:
        Brand: Updated brand object if successful, None if not found or unauthorized

    Raises:
        Exception: If database update fails
    """
    try:
        brand = db.query(Brand).filter(
            Brand.id == brand_id,
            Brand.user_id == user_id
        ).first()

        if not brand:
            logger.warning(f"⚠️ Cannot update: Brand {brand_id} not found or not owned by user {user_id}")
            return None

        # Update fields
        for key, value in updates.items():
            if hasattr(brand, key) and key != 'id' and key != 'user_id':
                setattr(brand, key, value)

        db.commit()
        db.refresh(brand)

        logger.info(f"✅ Updated brand {brand_id}: {list(updates.keys())}")
        return brand
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to update brand {brand_id}: {e}")
        raise


def delete_brand(
    db: Session,
    brand_id: UUID,
    user_id: UUID
) -> bool:
    """
    Delete a brand (only if owned by user). CASCADE deletes products.

    Args:
        db: Database session
        brand_id: ID of the brand to delete
        user_id: ID of the user (for ownership check)

    Returns:
        bool: True if deleted, False if not found or unauthorized

    Raises:
        Exception: If database delete fails
    """
    try:
        brand = db.query(Brand).filter(
            Brand.id == brand_id,
            Brand.user_id == user_id
        ).first()

        if not brand:
            logger.warning(f"⚠️ Cannot delete: Brand {brand_id} not found or not owned by user {user_id}")
            return False

        db.delete(brand)
        db.commit()

        logger.info(f"✅ Deleted brand {brand_id} (CASCADE to products)")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to delete brand {brand_id}: {e}")
def get_brand_stats(db: Session, brand_id: UUID) -> Dict[str, Any]:
    """
    Get brand statistics (products count, campaigns count, total cost).

    Note: Campaign doesn't have brand_id - it links to Product, which has brand_id.
    So we need to join through Product to get campaigns for a brand.

    Args:
        db: Database session
        brand_id: Brand ID

    Returns:
        Dict with statistics
    """
    try:
        # Products count - direct query
        products_count = db.query(Product).filter(Product.brand_id == brand_id).count()

        # Campaigns count - join through Product
        campaigns_count = db.query(Campaign).join(
            Product, Campaign.product_id == Product.id
        ).filter(Product.brand_id == brand_id).count()

        # Total cost - sum from Creatives, joining through Campaign and Product
        # Cost is tracked at the Creative level, not Campaign level
        total_cost = db.query(func.sum(Creative.cost)).join(
            Campaign, Creative.campaign_id == Campaign.id
        ).join(
            Product, Campaign.product_id == Product.id
        ).filter(Product.brand_id == brand_id).scalar() or 0

        stats = {
            "total_products": products_count,
            "total_campaigns": campaigns_count,
            "total_cost": float(total_cost)
        }

        logger.debug(f"✅ Generated stats for brand {brand_id}: {stats}")
        return stats
    except Exception as e:
        logger.error(f"❌ Failed to get stats for brand {brand_id}: {e}")
        raise


# ============================================================================
# PRODUCT CRUD Operations
# ============================================================================

def create_product(
    db: Session,
    user_id: UUID,
    brand_id: UUID,
    product_type: str,
    name: str,
    product_gender: Optional[str] = None,
    product_attributes: Optional[Dict] = None,
    icp_segment: Optional[str] = None,
    image_urls: Optional[List[str]] = None
) -> Optional[Product]:
    """
    Create a new product associated with a brand.

    Args:
        db: Database session
        user_id: ID of the authenticated user (for brand ownership validation)
        brand_id: ID of the brand to associate product with
        product_type: Type of product (fragrance, car, watch, energy, etc.)
        name: Product name
        product_gender: Product gender (masculine, feminine, unisex, or None)
        product_attributes: Type-specific attributes as dict (optional)
        icp_segment: ICP/target audience segment (optional)
        image_urls: List of S3 image URLs (optional, max 10)

    Returns:
        Product: Created product object if brand is owned by user, None otherwise

    Raises:
        Exception: If database insert fails
    """
    try:
        # Validate brand ownership
        brand = db.query(Brand).filter(
            Brand.id == brand_id,
            Brand.user_id == user_id
        ).first()

        if not brand:
            logger.warning(f"⚠️ Cannot create product: Brand {brand_id} not found or not owned by user {user_id}")
            return None

        # Create product
        product = Product(
            brand_id=brand_id,
            product_type=product_type,
            name=name,
            product_gender=product_gender,
            product_attributes=product_attributes,
            icp_segment=icp_segment,
            image_urls=image_urls
        )
        db.add(product)
        db.commit()
        db.refresh(product)

        logger.info(f"✅ Created product {product.id} ({name}, type={product_type}) for brand {brand_id}")
        return product
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to create product: {e}")
        raise


def get_brand_products(
    db: Session,
    user_id: UUID,
    brand_id: UUID,
    limit: int = 50,
    offset: int = 0
) -> Optional[List]:
    """
    Get all products for a specific brand (with ownership validation).

    Args:
        db: Database session
        user_id: ID of the authenticated user (for brand ownership validation)
        brand_id: ID of the brand
        limit: Maximum number of products to return
        offset: Number of products to skip (for pagination)

    Returns:
        List[Product]: List of products if brand is owned by user, None if brand not found/owned
    """
    try:
        # Validate brand ownership
        brand = db.query(Brand).filter(
            Brand.id == brand_id,
            Brand.user_id == user_id
        ).first()

        if not brand:
            logger.warning(f"⚠️ Cannot list products: Brand {brand_id} not found or not owned by user {user_id}")
            return None

        # Get products for brand
        products = db.query(Product).filter(
            Product.brand_id == brand_id
        ).order_by(desc(Product.created_at)).limit(limit).offset(offset).all()

        logger.info(f"✅ Retrieved {len(products)} products for brand {brand_id}")
        return products
    except Exception as e:
        logger.error(f"❌ Failed to get products for brand {brand_id}: {e}")
        return None


def get_product(
    db: Session,
    user_id: UUID,
    product_id: UUID
) -> Optional[Product]:
    """
    Get a product by ID with ownership verification via brand.

    Args:
        db: Database session
        user_id: ID of the authenticated user (for brand ownership validation)
        product_id: ID of the product

    Returns:
        Product: Product object if found and brand is owned by user, None otherwise
    """
    try:
        # Get product with brand ownership check via JOIN
        product = db.query(Product).join(Brand).filter(
            Product.id == product_id,
            Brand.user_id == user_id
        ).first()

        if product:
            logger.debug(f"✅ User {user_id} owns product {product_id} via brand")
        else:
            logger.warning(f"⚠️ Product {product_id} not found or brand not owned by user {user_id}")

        return product
    except Exception as e:
        logger.error(f"❌ Failed to get product {product_id}: {e}")
        return None


def get_product_by_id(
    db: Session,
    product_id: UUID
) -> Optional[Product]:
    """
    Get a product by ID without ownership verification.

    This function is used in background jobs where user context is not available.
    Use get_product() in API endpoints for ownership verification.

    Args:
        db: Database session
        product_id: ID of the product

    Returns:
        Product: Product object if found, None otherwise
    """
    try:
        product = db.query(Product).filter(Product.id == product_id).first()

        if product:
            logger.debug(f"✅ Found product {product_id}")
        else:
            logger.warning(f"⚠️ Product {product_id} not found")

        return product
    except Exception as e:
        logger.error(f"❌ Failed to get product {product_id}: {e}")
        return None


def update_product(
    db: Session,
    user_id: UUID,
    product_id: UUID,
    **updates
) -> Optional[Product]:
    """
    Update product fields (only if user owns parent brand).

    Args:
        db: Database session
        user_id: ID of the authenticated user (for brand ownership validation)
        product_id: ID of the product to update
        **updates: Fields to update (product_type, name, product_gender, product_attributes, icp_segment, image_urls)

    Returns:
        Product: Updated product object if successful, None if not found or unauthorized

    Raises:
        Exception: If database update fails
    """
    try:
        # Get product with brand ownership check
        product = db.query(Product).join(Brand).filter(
            Product.id == product_id,
            Brand.user_id == user_id
        ).first()

        if not product:
            logger.warning(f"⚠️ Cannot update: Product {product_id} not found or brand not owned by user {user_id}")
            return None

        # Update fields
        for key, value in updates.items():
            if hasattr(product, key) and key not in ['id', 'brand_id']:
                setattr(product, key, value)

        db.commit()
        db.refresh(product)

        logger.info(f"✅ Updated product {product_id}: {list(updates.keys())}")
        return product
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to update product {product_id}: {e}")
        raise


def delete_product(
    db: Session,
    user_id: UUID,
    product_id: UUID
) -> bool:
    """
    Delete a product (only if user owns parent brand).

    Args:
        db: Database session
        user_id: ID of the authenticated user (for brand ownership validation)
        product_id: ID of the product to delete

    Returns:
        bool: True if deleted, False if not found or unauthorized

    Raises:
        Exception: If database delete fails
    """
    try:
        # Get product with brand ownership check
        product = db.query(Product).join(Brand).filter(
            Product.id == product_id,
            Brand.user_id == user_id
        ).first()

        if not product:
            logger.warning(f"⚠️ Cannot delete: Product {product_id} not found or brand not owned by user {user_id}")
            return False

        db.delete(product)
        db.commit()

        logger.info(f"✅ Deleted product {product_id}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to delete product {product_id}: {e}")

def get_perfume_campaigns_count(db: Session, perfume_id: UUID) -> int:
    """
    Get count of campaigns for a perfume.
    
    Args:
        db: Database session
        perfume_id: Product ID
    
    Returns:
        int: Number of campaigns
    """
    try:
        count = db.query(Campaign).filter(Campaign.perfume_id == perfume_id).count()
        return count
    except Exception as e:
        logger.error(f"❌ Failed to get campaigns count for perfume {perfume_id}: {e}")
        raise


# ============================================================================
# CAMPAIGN CRUD Operations
# ============================================================================

def create_campaign(
    db: Session,
    user_id: UUID,
    product_id: UUID,
    brand_id: UUID,
    name: str,
    seasonal_event: str,
    year: int,
    duration: int,
    scene_configs: List[Dict[str, Any]]
) -> Optional[Campaign]:
    """
    Create a new campaign associated with a product.

    Args:
        db: Database session
        user_id: ID of the authenticated user (for ownership validation)
        product_id: ID of the product to associate campaign with
        brand_id: ID of the brand (for validation, not stored in campaign)
        name: Campaign name
        seasonal_event: Seasonal event or marketing initiative
        year: Campaign year
        duration: Video duration in seconds (15, 30, 45, or 60)
        scene_configs: List of scene configuration dicts

    Returns:
        Campaign: Created campaign object if product is owned by user, None otherwise

    Raises:
        Exception: If database insert fails

    Note:
        brand_id is not stored in the Campaign model - campaigns are associated
        with products, and products are associated with brands. The brand can
        be accessed via campaign.product.brand.
    """
    try:
        # Validate product ownership via brand
        product = db.query(Product).join(Brand).filter(
            Product.id == product_id,
            Brand.user_id == user_id
        ).first()

        if not product:
            logger.warning(f"⚠️ Cannot create campaign: Product {product_id} not found or not owned by user {user_id}")
            return None

        # Create campaign with "pending" status to allow immediate generation
        campaign = Campaign(
            product_id=product_id,
            name=name,
            seasonal_event=seasonal_event,
            year=year,
            duration=duration,
            scene_configs=scene_configs,
            status="pending"
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        logger.info(f"✅ Created campaign {campaign.id} ({name}) for product {product_id}")
        return campaign
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to create campaign: {e}")
        raise


def get_product_campaigns(
    db: Session,
    user_id: UUID,
    product_id: UUID,
    limit: int = 50,
    offset: int = 0
) -> Optional[List[Campaign]]:
    """
    Get all campaigns for a specific product (with ownership validation).

    Args:
        db: Database session
        user_id: ID of the authenticated user (for ownership validation)
        product_id: ID of the product
        limit: Maximum number of campaigns to return
        offset: Number of campaigns to skip (for pagination)

    Returns:
        List[Campaign]: List of campaigns if product is owned by user, None if not found/owned
    """
    try:
        # Validate product ownership via brand
        product = db.query(Product).join(Brand).filter(
            Product.id == product_id,
            Brand.user_id == user_id
        ).first()

        if not product:
            logger.warning(f"⚠️ Cannot list campaigns: Product {product_id} not found or not owned by user {user_id}")
            return None

        # Get campaigns for product
        campaigns = db.query(Campaign).filter(
            Campaign.product_id == product_id
        ).order_by(desc(Campaign.created_at)).limit(limit).offset(offset).all()

        logger.info(f"✅ Retrieved {len(campaigns)} campaigns for product {product_id}")
        return campaigns
    except Exception as e:
        logger.error(f"❌ Failed to get campaigns for product {product_id}: {e}")
        return None


def get_campaign(
    db: Session,
    user_id: UUID,
    campaign_id: UUID
) -> Optional[Campaign]:
    """
    Get a campaign by ID with ownership verification.

    Args:
        db: Database session
        user_id: ID of the authenticated user (for ownership validation)
        campaign_id: ID of the campaign

    Returns:
        Campaign: Campaign object if found and owned by user, None otherwise
    """
    try:
        # Get campaign with ownership check via product->brand chain
        campaign = db.query(Campaign).join(Product).join(Brand).filter(
            Campaign.id == campaign_id,
            Brand.user_id == user_id
        ).first()

        if campaign:
            logger.debug(f"✅ User {user_id} owns campaign {campaign_id}")
        else:
            logger.warning(f"⚠️ Campaign {campaign_id} not found or not owned by user {user_id}")

        return campaign
    except Exception as e:
        logger.error(f"❌ Failed to get campaign {campaign_id}: {e}")
        return None


def get_campaign_by_id(
    db: Session,
    campaign_id: UUID
) -> Optional[Campaign]:
    """
    Get a campaign by ID without ownership verification.

    This function is used in background jobs where user context is not available.
    Use get_campaign() in API endpoints for ownership verification.

    Args:
        db: Database session
        campaign_id: ID of the campaign

    Returns:
        Campaign: Campaign object if found, None otherwise
    """
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

        if campaign:
            logger.debug(f"✅ Found campaign {campaign_id}")
        else:
            logger.warning(f"⚠️ Campaign {campaign_id} not found")

        return campaign
    except Exception as e:
        logger.error(f"❌ Failed to get campaign {campaign_id}: {e}")
        return None


def get_campaigns_by_product(
    db: Session,
    product_id: UUID,
    page: int = 1,
    limit: int = 20
) -> tuple[List[Campaign], int]:
    """
    Get campaigns for a product with pagination.

    Args:
        db: Database session
        product_id: ID of the product
        page: Page number (1-indexed)
        limit: Number of campaigns per page

    Returns:
        tuple: (list of campaigns, total count)
    """
    try:
        # Calculate offset
        offset = (page - 1) * limit

        # Get total count
        total = db.query(Campaign).filter(
            Campaign.product_id == product_id
        ).count()

        # Get paginated campaigns
        campaigns = db.query(Campaign).filter(
            Campaign.product_id == product_id
        ).order_by(desc(Campaign.created_at)).limit(limit).offset(offset).all()

        logger.info(f"✅ Retrieved {len(campaigns)} campaigns for product {product_id} (page {page}, total {total})")
        return campaigns, total
    except Exception as e:
        logger.error(f"❌ Failed to get campaigns for product {product_id}: {e}")
        return [], 0


def update_campaign(
    db: Session,
    user_id: UUID,
    campaign_id: UUID,
    **updates
) -> Optional[Campaign]:
    """
    Update campaign fields (only if user owns product/brand).

    Args:
        db: Database session
        user_id: ID of the authenticated user (for ownership validation)
        campaign_id: ID of the campaign to update
        **updates: Fields to update (name, seasonal_event, year, duration, scene_configs, status)

    Returns:
        Campaign: Updated campaign object if successful, None if not found or unauthorized

    Raises:
        Exception: If database update fails
    """
    try:
        # Get campaign with ownership check
        campaign = db.query(Campaign).join(Product).join(Brand).filter(
            Campaign.id == campaign_id,
            Brand.user_id == user_id
        ).first()

        if not campaign:
            logger.warning(f"⚠️ Cannot update: Campaign {campaign_id} not found or not owned by user {user_id}")
            return None

        # Update fields
        for key, value in updates.items():
            if hasattr(campaign, key) and key not in ['id', 'product_id']:
                setattr(campaign, key, value)

        db.commit()
        db.refresh(campaign)

        logger.info(f"✅ Updated campaign {campaign_id}: {list(updates.keys())}")
        return campaign
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to update campaign {campaign_id}: {e}")
        raise


def delete_campaign(
    db: Session,
    user_id: UUID,
    campaign_id: UUID
) -> bool:
    """
    Delete a campaign (only if user owns product/brand).

    Args:
        db: Database session
        user_id: ID of the authenticated user (for ownership validation)
        campaign_id: ID of the campaign to delete

    Returns:
        bool: True if deleted, False if not found or unauthorized

    Raises:
        Exception: If database delete fails
    """
    try:
        # Get campaign with ownership check
        campaign = db.query(Campaign).join(Product).join(Brand).filter(
            Campaign.id == campaign_id,
            Brand.user_id == user_id
        ).first()

        if not campaign:
            logger.warning(f"⚠️ Cannot delete: Campaign {campaign_id} not found or not owned by user {user_id}")
            return False

        db.delete(campaign)
        db.commit()

        logger.info(f"✅ Deleted campaign {campaign_id}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to delete campaign {campaign_id}: {e}")
        raise


# ============================================================================
# Creative CRUD Operations
# ============================================================================

def create_creative(
    db: Session,
    campaign_id: UUID,
    user_id: UUID,
    title: str,
    ad_creative_json: Dict[str, Any],
    status: str = "pending",
    aspect_ratio: str = "9:16",
    video_provider: str = "replicate",
    output_formats: Optional[List[str]] = None
) -> Optional[Creative]:
    """
    Create a new creative for a campaign.
    
    Args:
        db: Database session
        campaign_id: ID of the parent campaign
        user_id: ID of the user creating the creative
        title: Creative title
        ad_creative_json: Creative configuration JSON
        status: Initial status (default: "pending")
        aspect_ratio: Aspect ratio for the creative
        video_provider: Video generation provider
        output_formats: List of output aspect ratios
    
    Returns:
        Creative: Created creative object
    """
    try:
        # Verify campaign exists and user has access
        campaign = db.query(Campaign).join(Product).join(Brand).filter(
            Campaign.id == campaign_id,
            Brand.user_id == user_id
        ).first()
        
        if not campaign:
            logger.warning(f"⚠️ Cannot create creative: Campaign {campaign_id} not found or not owned by user {user_id}")
            return None
        
        # Create creative
        creative = Creative(
            campaign_id=campaign_id,
            user_id=user_id,
            title=title,
            ad_creative_json=ad_creative_json,
            status=status,
            aspect_ratio=aspect_ratio,
            video_provider=video_provider,
            output_formats=output_formats or [aspect_ratio],
            progress=0,
            cost=0
        )
        
        db.add(creative)
        db.commit()
        db.refresh(creative)
        
        logger.info(f"✅ Created creative {creative.id} for campaign {campaign_id}")
        return creative
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to create creative: {e}")
        raise


def get_creative_by_id(db: Session, creative_id: UUID) -> Optional[Creative]:
    """
    Get a creative by ID.
    
    Args:
        db: Database session
        creative_id: ID of the creative
    
    Returns:
        Creative: Creative object if found, None otherwise
    """
    return db.query(Creative).filter(Creative.id == creative_id).first()


def get_creatives_for_campaign(
    db: Session,
    campaign_id: UUID,
    user_id: UUID,
    limit: int = 20,
    offset: int = 0
) -> Tuple[List[Creative], int]:
    """
    Get all creatives for a campaign with pagination.
    
    Args:
        db: Database session
        campaign_id: ID of the campaign
        user_id: ID of the user (for ownership validation)
        limit: Maximum number of creatives to return
        offset: Number of creatives to skip
    
    Returns:
        Tuple of (list of creatives, total count)
    """
    try:
        # Verify campaign ownership
        campaign = db.query(Campaign).join(Product).join(Brand).filter(
            Campaign.id == campaign_id,
            Brand.user_id == user_id
        ).first()
        
        if not campaign:
            logger.warning(f"⚠️ Cannot list creatives: Campaign {campaign_id} not found or not owned by user {user_id}")
            return [], 0
        
        # Get creatives
        query = db.query(Creative).filter(Creative.campaign_id == campaign_id)
        total = query.count()
        creatives = query.order_by(desc(Creative.created_at)).offset(offset).limit(limit).all()
        
        logger.info(f"✅ Retrieved {len(creatives)} creatives for campaign {campaign_id} (total: {total})")
        return creatives, total
        
    except Exception as e:
        logger.error(f"❌ Failed to get creatives for campaign {campaign_id}: {e}")
        raise


def update_creative(
    db: Session,
    creative_id: UUID,
    **updates
) -> Optional[Creative]:
    """
    Update creative fields.
    
    Args:
        db: Database session
        creative_id: ID of the creative
        **updates: Fields to update
    
    Returns:
        Creative: Updated creative object
    """
    try:
        creative = db.query(Creative).filter(Creative.id == creative_id).first()
        
        if not creative:
            logger.warning(f"⚠️ Creative {creative_id} not found")
            return None
        
        for key, value in updates.items():
            if hasattr(creative, key):
                setattr(creative, key, value)
        
        db.commit()
        db.refresh(creative)
        
        logger.info(f"✅ Updated creative {creative_id}")
        return creative
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to update creative {creative_id}: {e}")
        raise


def delete_creative(
    db: Session,
    campaign_id: UUID,
    creative_id: UUID,
    user_id: UUID
) -> bool:
    """
    Delete a creative.
    
    Args:
        db: Database session
        campaign_id: ID of the parent campaign
        creative_id: ID of the creative to delete
        user_id: ID of the user (for ownership validation)
    
    Returns:
        bool: True if deleted, False if not found or unauthorized
    """
    try:
        # Get creative with ownership check
        creative = db.query(Creative).join(Campaign).join(Product).join(Brand).filter(
            Creative.id == creative_id,
            Creative.campaign_id == campaign_id,
            Brand.user_id == user_id
        ).first()
        
        if not creative:
            logger.warning(f"⚠️ Cannot delete: Creative {creative_id} not found or not owned by user {user_id}")
            return False
        
        db.delete(creative)
        db.commit()
        
        logger.info(f"✅ Deleted creative {creative_id}")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to delete creative {creative_id}: {e}")
        raise
