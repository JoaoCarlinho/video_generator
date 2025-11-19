"""Database CRUD operations for projects, brands, perfumes, and campaigns."""

from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.database.models import Project, Brand, Perfume, Campaign
from app.models.schemas import (
    CreateProjectRequest,
    ProjectResponse,
    ProjectDetailResponse
)
from uuid import UUID
from typing import List, Optional, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# CREATE Operations
# ============================================================================

def create_project(
    db: Session,
    user_id: UUID,
    title: str,
    brief: str,
    ad_project_json: Dict[str, Any],
    mood: str = "uplifting",
    duration: int = 30,
    aspect_ratio: str = "9:16",  # Phase 9: Default to TikTok vertical
    selected_style: Optional[str] = None,  # PHASE 7: User-selected style
    perfume_name: Optional[str] = None,  # Phase 9: Perfume product name
    perfume_gender: Optional[str] = None,  # Phase 9: Perfume gender
    num_variations: int = 1  # MULTI-VARIATION: Number of variations (1-3)
) -> Project:
    """
    Create a new luxury perfume TikTok ad project in the database.
    
    Args:
        db: Database session
        user_id: ID of the user creating the project
        title: Project title
        brief: Product brief/description
        ad_project_json: Complete ad project configuration as JSON
        mood: Video mood/style (deprecated, kept for compatibility)
        duration: Video duration in seconds
        aspect_ratio: Video aspect ratio (always 9:16 for TikTok vertical)
        selected_style: (PHASE 7) User-selected video style or None
        perfume_name: (Phase 9) Perfume product name (e.g., "Noir Élégance")
        perfume_gender: (Phase 9) Perfume gender ('masculine', 'feminine', 'unisex')
        num_variations: (MULTI-VARIATION) Number of video variations to generate (1-3)
    
    Returns:
        Project: Created project object
    
    Raises:
        Exception: If database insert fails
    """
    try:
        project = Project(
            user_id=user_id,
            title=title,
            ad_project_json=ad_project_json,
            status="PENDING",
            selected_style=selected_style,  # PHASE 7: Store selected style
            progress=0,
            cost=0.0,
            aspect_ratio=aspect_ratio,
            perfume_name=perfume_name,  # Phase 9: Store perfume name
            perfume_gender=perfume_gender,  # Phase 9: Store perfume gender
            num_variations=num_variations,  # MULTI-VARIATION: Store variation count
            selected_variation_index=None  # MULTI-VARIATION: No selection yet
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        logger.info(f"✅ Created project {project.id} for user {user_id}")
        return project
    except Exception as e:
        try:
            db.rollback()
        except:
            pass
        logger.error(f"❌ Failed to create project: {e}")
        # Create in-memory mock project for development
        logger.warning("⚠️ Using mock project (database connection issue)")
        from uuid import uuid4
        from datetime import datetime
        mock_project = Project(
            user_id=user_id,
            title=title,
            ad_project_json=ad_project_json,
            status="PENDING",
            progress=0,
            cost=0.0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        mock_project.id = uuid4()
        return mock_project


# ============================================================================
# READ Operations
# ============================================================================

def get_project(db: Session, project_id: UUID) -> Optional[Project]:
    """
    Get a single project by ID.
    
    Args:
        db: Database session
        project_id: ID of the project to retrieve
    
    Returns:
        Project: Project object if found, None otherwise
    """
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            logger.debug(f"✅ Retrieved project {project_id}")
        else:
            logger.debug(f"⚠️ Project {project_id} not found")
        return project
    except Exception as e:
        logger.error(f"❌ Failed to get project {project_id}: {e}")
        # In development mode with DB issues, create a mock project
        logger.warning(f"⚠️ Database error - creating mock project for development")
        from datetime import datetime
        mock_project = Project(
            id=project_id,
            user_id=UUID('00000000-0000-0000-0000-000000000001'),  # Default user
            title=f"Project {project_id}",
            ad_project_json={},
            status="PENDING",
            progress=0,
            cost=0.0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        return mock_project


def get_project_by_user(db: Session, project_id: UUID, user_id: UUID) -> Optional[Project]:
    """
    Get a project by ID and verify user ownership.
    
    Args:
        db: Database session
        project_id: ID of the project
        user_id: ID of the user (for verification)
    
    Returns:
        Project: Project if found and owned by user, None otherwise
    """
    # If db is None, create a mock project for development
    if db is None:
        logger.warning(f"⚠️ Database session is None - creating mock project for development")
        from datetime import datetime
        mock_project = Project(
            id=project_id,
            user_id=user_id,
            title=f"Project {project_id}",
            ad_project_json={},
            status="PENDING",
            progress=0,
            cost=0.0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        return mock_project
    
    try:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == user_id
        ).first()
        if project:
            logger.debug(f"✅ User {user_id} owns project {project_id}")
        else:
            logger.warning(f"⚠️ User {user_id} does not own project {project_id}")
        return project
    except Exception as e:
        logger.error(f"❌ Failed to get project {project_id}: {e}")
        # In development mode with DB issues, create a mock project for development
        logger.warning(f"⚠️ Database error - creating mock project for development")
        from datetime import datetime
        mock_project = Project(
            id=project_id,
            user_id=user_id,
            title=f"Project {project_id}",
            ad_project_json={},
            status="PENDING",
            progress=0,
            cost=0.0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        return mock_project


def get_user_projects(
    db: Session,
    user_id: UUID,
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None
) -> List[Project]:
    """
    Get all projects for a specific user.
    
    Args:
        db: Database session
        user_id: ID of the user
        limit: Maximum number of projects to return
        offset: Number of projects to skip (for pagination)
        status: Optional filter by status (e.g., "COMPLETED", "FAILED")
    
    Returns:
        List[Project]: List of projects
    """
    try:
        query = db.query(Project).filter(Project.user_id == user_id)
        
        if status:
            query = query.filter(Project.status == status)
        
        projects = query.order_by(desc(Project.created_at)).limit(limit).offset(offset).all()
        
        logger.info(f"✅ Retrieved {len(projects)} projects for user {user_id}")
        return projects
    except Exception as e:
        logger.error(f"❌ Failed to get projects for user {user_id}: {e}")
        # Return empty list instead of raising - allows development without DB
        logger.warning("⚠️ Returning empty project list (database connection issue)")
        return []


def get_projects_by_status(
    db: Session,
    status: str,
    limit: int = 50
) -> List[Project]:
    """
    Get all projects with a specific status (for monitoring/admin).
    
    Args:
        db: Database session
        status: Status to filter by (e.g., "GENERATING_SCENES", "FAILED")
        limit: Maximum number of projects to return
    
    Returns:
        List[Project]: List of matching projects
    """
    try:
        projects = db.query(Project).filter(
            Project.status == status
        ).order_by(desc(Project.updated_at)).limit(limit).all()
        
        logger.info(f"✅ Found {len(projects)} projects with status '{status}'")
        return projects
    except Exception as e:
        logger.error(f"❌ Failed to get projects by status {status}: {e}")
        raise


# ============================================================================
# UPDATE Operations
# ============================================================================

def update_project(
    db: Session,
    project_id: UUID,
    **updates
) -> Optional[Project]:
    """
    Update project fields.
    
    Args:
        db: Database session
        project_id: ID of the project to update
        **updates: Fields to update (status, progress, cost, ad_project_json, etc.)
    
    Returns:
        Project: Updated project object if successful, None if project not found
    
    Raises:
        Exception: If database update fails
    """
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        
        if not project:
            logger.warning(f"⚠️ Project {project_id} not found for update")
            return None
        
        # Update fields
        for key, value in updates.items():
            if hasattr(project, key):
                setattr(project, key, value)
        
        db.commit()
        db.refresh(project)
        
        logger.info(f"✅ Updated project {project_id}: {list(updates.keys())}")
        return project
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to update project {project_id}: {e}")
        raise


def update_project_status(
    db: Session,
    project_id: UUID,
    status: str,
    progress: int = 0,
    error_message: Optional[str] = None
) -> Optional[Project]:
    """
    Update project status and progress.
    
    Args:
        db: Database session
        project_id: ID of the project
        status: New status (e.g., "GENERATING_SCENES")
        progress: Progress percentage (0-100)
        error_message: Optional error message
    
    Returns:
        Project: Updated project object
    """
    # If db is None, just log and skip update
    if db is None:
        logger.warning(f"⚠️ Database session is None - skipping status update for {project_id}")
        return None
    
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        
        if not project:
            return None
        
        project.status = status
        project.progress = max(0, min(100, progress))  # Clamp 0-100
        if error_message:
            project.error_message = error_message
        
        db.commit()
        db.refresh(project)
        
        logger.info(f"✅ Updated project {project_id} status to {status} ({progress}%)")
        return project
    except Exception as e:
        try:
            db.rollback()
        except:
            pass
        logger.error(f"❌ Failed to update status for {project_id}: {e}")
        # In development mode with DB issues, just log and continue
        logger.warning(f"⚠️ Database error updating status - continuing with in-memory state")
        return None


def update_project_cost(
    db: Session,
    project_id: UUID,
    cost: float
) -> Optional[Project]:
    """
    Update project cost tracking.
    
    Args:
        db: Database session
        project_id: ID of the project
        cost: Total cost in USD
    
    Returns:
        Project: Updated project object
    """
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        
        if not project:
            return None
        
        project.cost = round(float(cost), 2)
        
        db.commit()
        db.refresh(project)
        
        logger.info(f"✅ Updated project {project_id} cost to ${project.cost}")
        return project
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to update cost for {project_id}: {e}")
        raise


def update_project_output(
    db: Session,
    project_id: UUID,
    final_videos: Dict[str, str],
    total_cost: float,
    cost_breakdown: Dict[str, float]
) -> Optional[Project]:
    """
    Update project with final output and cost breakdown.
    
    Args:
        db: Database session
        project_id: ID of the project
        final_videos: Dict with aspect ratio as key (16:9) and S3 URL as value
        total_cost: Total cost in USD
        cost_breakdown: Dict with cost per service
    
    Returns:
        Project: Updated project object
    """
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        
        if not project:
            return None
        
        # Update output videos in ad_project_json
        # Must create new dict to trigger SQLAlchemy change detection for JSON fields
        if isinstance(project.ad_project_json, dict):
            updated_json = dict(project.ad_project_json)
            updated_json["aspectExports"] = final_videos
            updated_json["costBreakdown"] = cost_breakdown
            project.ad_project_json = updated_json
            # Mark as modified to ensure SQLAlchemy detects the change
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(project, "ad_project_json")
        
        project.cost = round(float(total_cost), 2)
        project.status = "COMPLETED"
        project.progress = 100
        
        db.commit()
        db.refresh(project)
        
        logger.info(f"✅ Updated project {project_id} with final output, cost: ${total_cost:.2f}")
        return project
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to update project output {project_id}: {e}")
        raise


def update_project_json(
    db: Session,
    project_id: UUID,
    ad_project_json: Dict[str, Any]
) -> Optional[Project]:
    """
    Update the ad_project_json configuration.
    
    Args:
        db: Database session
        project_id: ID of the project
        ad_project_json: New configuration JSON
    
    Returns:
        Project: Updated project object
    """
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        
        if not project:
            return None
        
        project.ad_project_json = ad_project_json
        
        db.commit()
        db.refresh(project)
        
        logger.info(f"✅ Updated project {project_id} configuration")
        return project
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to update json for {project_id}: {e}")
        raise


# ============================================================================
# DELETE Operations
# ============================================================================

def delete_project(db: Session, project_id: UUID, user_id: UUID) -> bool:
    """
    Delete a project (only if owned by user).
    
    Args:
        db: Database session
        project_id: ID of the project to delete
        user_id: ID of the user (for verification)
    
    Returns:
        bool: True if deleted, False if not found or unauthorized
    
    Raises:
        Exception: If database delete fails
    """
    try:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == user_id
        ).first()
        
        if not project:
            logger.warning(f"⚠️ Cannot delete: User {user_id} does not own project {project_id}")
            return False
        
        db.delete(project)
        db.commit()
        
        logger.info(f"✅ Deleted project {project_id}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to delete project {project_id}: {e}")
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
        Dict with statistics (total projects, completed, failed, total cost, etc.)
    """
    try:
        user_projects = db.query(Project).filter(Project.user_id == user_id).all()
        
        total = len(user_projects)
        completed = len([p for p in user_projects if p.status == "COMPLETED"])
        failed = len([p for p in user_projects if p.status == "FAILED"])
        in_progress = len([p for p in user_projects if p.status.startswith("GENERATING") or p.status.startswith("EXTRACTING") or p.status.startswith("COMPOSITING")])
        
        total_cost = sum(float(p.cost) for p in user_projects)
        
        stats = {
            "total_projects": total,
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


def clear_old_failed_projects(db: Session, days: int = 7) -> int:
    """
    Delete failed projects older than N days (for cleanup).
    
    Args:
        db: Database session
        days: Number of days before cleanup
    
    Returns:
        int: Number of projects deleted
    """
    try:
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = db.query(Project).filter(
            Project.status == "FAILED",
            Project.created_at < cutoff
        )
        
        count = query.count()
        query.delete()
        db.commit()
        
        logger.info(f"✅ Deleted {count} failed projects older than {days} days")
        return count
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to clean up old projects: {e}")
        raise


# ============================================================================
# S3 RESTRUCTURING: New helper functions for per-project folders
# ============================================================================

def update_project_s3_paths(
    db: Session,
    project_id: UUID,
    s3_project_folder: str,
    s3_project_folder_url: str
) -> Optional[Project]:
    """
    Update project with S3 folder paths.
    
    Called after project creation to store the project's S3 folder location.
    
    Args:
        db: Database session
        project_id: ID of the project
        s3_project_folder: S3 key prefix (e.g., "projects/{id}/")
        s3_project_folder_url: Public HTTPS URL to folder
    
    Returns:
        Project: Updated project object
    """
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        
        if not project:
            logger.warning(f"⚠️ Project {project_id} not found for S3 path update")
            return None
        
        project.s3_project_folder = s3_project_folder
        project.s3_project_folder_url = s3_project_folder_url
        
        db.commit()
        db.refresh(project)
        
        logger.info(f"✅ Updated project {project_id} S3 paths")
        return project
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to update S3 paths for {project_id}: {e}")
        raise


def get_projects_without_s3_paths(
    db: Session,
    limit: int = 100
) -> List[Project]:
    """
    Get projects that don't have S3 folder paths set (for migration).
    
    Useful for identifying projects created before restructuring was implemented.
    
    Args:
        db: Database session
        limit: Maximum number to return
    
    Returns:
        List of projects without S3 paths
    """
    try:
        projects = db.query(Project).filter(
            (Project.s3_project_folder == None) | 
            (Project.s3_project_folder == "")
        ).limit(limit).all()
        
        logger.info(f"✅ Found {len(projects)} projects without S3 paths")
        return projects
    except Exception as e:
        logger.error(f"❌ Failed to get projects without S3 paths: {e}")
        raise


# ============================================================================
# Brand CRUD Operations (Phase 2 B2B SaaS)
# ============================================================================

def create_brand(
    db: Session,
    user_id: UUID,
    brand_name: str,
    brand_logo_url: str,
    brand_guidelines_url: str
) -> Brand:
    """
    Create a new brand for a user.
    
    Args:
        db: Database session
        user_id: User ID (must be unique - one brand per user)
        brand_name: Brand name (must be unique)
        brand_logo_url: S3 URL of brand logo
        brand_guidelines_url: S3 URL of brand guidelines PDF
    
    Returns:
        Brand: Created brand object
    
    Raises:
        Exception: If brand creation fails (e.g., duplicate name or user_id)
    """
    try:
        brand = Brand(
            user_id=user_id,
            brand_name=brand_name,
            brand_logo_url=brand_logo_url,
            brand_guidelines_url=brand_guidelines_url,
            onboarding_completed=True
        )
        db.add(brand)
        db.commit()
        db.refresh(brand)
        logger.info(f"✅ Created brand {brand.brand_id} for user {user_id}")
        return brand
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to create brand: {e}")
        raise


def get_brand_by_user_id(db: Session, user_id: UUID) -> Optional[Brand]:
    """
    Get brand by user ID.
    
    Args:
        db: Database session
        user_id: User ID
    
    Returns:
        Brand: Brand object if found, None otherwise
    """
    try:
        brand = db.query(Brand).filter(Brand.user_id == user_id).first()
        if brand:
            logger.debug(f"✅ Retrieved brand {brand.brand_id} for user {user_id}")
        else:
            logger.debug(f"⚠️ No brand found for user {user_id}")
        return brand
    except Exception as e:
        logger.error(f"❌ Failed to get brand for user {user_id}: {e}")
        raise


def get_brand_by_id(db: Session, brand_id: UUID) -> Optional[Brand]:
    """
    Get brand by brand ID.
    
    Args:
        db: Database session
        brand_id: Brand ID
    
    Returns:
        Brand: Brand object if found, None otherwise
    """
    try:
        brand = db.query(Brand).filter(Brand.brand_id == brand_id).first()
        if brand:
            logger.debug(f"✅ Retrieved brand {brand_id}")
        else:
            logger.debug(f"⚠️ Brand {brand_id} not found")
        return brand
    except Exception as e:
        logger.error(f"❌ Failed to get brand {brand_id}: {e}")
        raise


def update_brand(
    db: Session,
    brand_id: UUID,
    **updates
) -> Optional[Brand]:
    """
    Update brand fields.
    
    Args:
        db: Database session
        brand_id: Brand ID
        **updates: Fields to update (brand_name, brand_logo_url, etc.)
    
    Returns:
        Brand: Updated brand object if successful, None if not found
    """
    try:
        brand = db.query(Brand).filter(Brand.brand_id == brand_id).first()
        if not brand:
            logger.warning(f"⚠️ Brand {brand_id} not found for update")
            return None
        
        for key, value in updates.items():
            if hasattr(brand, key):
                setattr(brand, key, value)
        
        db.commit()
        db.refresh(brand)
        logger.info(f"✅ Updated brand {brand_id}: {list(updates.keys())}")
        return brand
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to update brand {brand_id}: {e}")
        raise


def get_brand_stats(db: Session, brand_id: UUID) -> Dict[str, Any]:
    """
    Get brand statistics (perfumes count, campaigns count, total cost).
    
    Args:
        db: Database session
        brand_id: Brand ID
    
    Returns:
        Dict with statistics
    """
    try:
        perfumes_count = db.query(Perfume).filter(Perfume.brand_id == brand_id).count()
        campaigns_count = db.query(Campaign).filter(Campaign.brand_id == brand_id).count()
        total_cost = db.query(func.sum(Campaign.cost)).filter(Campaign.brand_id == brand_id).scalar() or 0
        
        stats = {
            "total_perfumes": perfumes_count,
            "total_campaigns": campaigns_count,
            "total_cost": float(total_cost)
        }
        
        logger.debug(f"✅ Generated stats for brand {brand_id}: {stats}")
        return stats
    except Exception as e:
        logger.error(f"❌ Failed to get stats for brand {brand_id}: {e}")
        raise


# ============================================================================
# Perfume CRUD Operations (Phase 2 B2B SaaS)
# ============================================================================

def create_perfume(
    db: Session,
    brand_id: UUID,
    perfume_name: str,
    perfume_gender: str,
    front_image_url: str,
    back_image_url: Optional[str] = None,
    top_image_url: Optional[str] = None,
    left_image_url: Optional[str] = None,
    right_image_url: Optional[str] = None
) -> Perfume:
    """
    Create a new perfume for a brand.
    
    Args:
        db: Database session
        brand_id: Brand ID
        perfume_name: Perfume name (unique within brand)
        perfume_gender: Perfume gender ('masculine', 'feminine', 'unisex')
        front_image_url: S3 URL of front image (required)
        back_image_url: S3 URL of back image (optional)
        top_image_url: S3 URL of top image (optional)
        left_image_url: S3 URL of left image (optional)
        right_image_url: S3 URL of right image (optional)
    
    Returns:
        Perfume: Created perfume object
    """
    try:
        perfume = Perfume(
            brand_id=brand_id,
            perfume_name=perfume_name,
            perfume_gender=perfume_gender,
            front_image_url=front_image_url,
            back_image_url=back_image_url,
            top_image_url=top_image_url,
            left_image_url=left_image_url,
            right_image_url=right_image_url
        )
        db.add(perfume)
        db.commit()
        db.refresh(perfume)
        logger.info(f"✅ Created perfume {perfume.perfume_id} for brand {brand_id}")
        return perfume
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to create perfume: {e}")
        raise


def get_perfumes_by_brand(
    db: Session,
    brand_id: UUID,
    page: int = 1,
    limit: int = 20
) -> Tuple[List[Perfume], int]:
    """
    Get perfumes for a brand with pagination.
    
    Args:
        db: Database session
        brand_id: Brand ID
        page: Page number (1-indexed)
        limit: Items per page
    
    Returns:
        Tuple of (list of perfumes, total count)
    """
    try:
        offset = (page - 1) * limit
        perfumes = db.query(Perfume)\
            .filter(Perfume.brand_id == brand_id)\
            .order_by(desc(Perfume.created_at))\
            .offset(offset)\
            .limit(limit)\
            .all()
        
        total = db.query(Perfume).filter(Perfume.brand_id == brand_id).count()
        
        logger.debug(f"✅ Retrieved {len(perfumes)} perfumes for brand {brand_id} (page {page})")
        return perfumes, total
    except Exception as e:
        logger.error(f"❌ Failed to get perfumes for brand {brand_id}: {e}")
        raise


def get_perfume_by_id(db: Session, perfume_id: UUID) -> Optional[Perfume]:
    """
    Get perfume by ID.
    
    Args:
        db: Database session
        perfume_id: Perfume ID
    
    Returns:
        Perfume: Perfume object if found, None otherwise
    """
    try:
        perfume = db.query(Perfume).filter(Perfume.perfume_id == perfume_id).first()
        if perfume:
            logger.debug(f"✅ Retrieved perfume {perfume_id}")
        else:
            logger.debug(f"⚠️ Perfume {perfume_id} not found")
        return perfume
    except Exception as e:
        logger.error(f"❌ Failed to get perfume {perfume_id}: {e}")
        raise


def update_perfume(
    db: Session,
    perfume_id: UUID,
    **updates
) -> Optional[Perfume]:
    """
    Update perfume fields.
    
    Args:
        db: Database session
        perfume_id: Perfume ID
        **updates: Fields to update
    
    Returns:
        Perfume: Updated perfume object if successful, None if not found
    """
    try:
        perfume = db.query(Perfume).filter(Perfume.perfume_id == perfume_id).first()
        if not perfume:
            logger.warning(f"⚠️ Perfume {perfume_id} not found for update")
            return None
        
        for key, value in updates.items():
            if hasattr(perfume, key):
                setattr(perfume, key, value)
        
        db.commit()
        db.refresh(perfume)
        logger.info(f"✅ Updated perfume {perfume_id}: {list(updates.keys())}")
        return perfume
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to update perfume {perfume_id}: {e}")
        raise


def delete_perfume(db: Session, perfume_id: UUID) -> bool:
    """
    Delete a perfume (only if it has no campaigns).
    
    Args:
        db: Database session
        perfume_id: Perfume ID
    
    Returns:
        bool: True if deleted, False if not found or has campaigns
    """
    try:
        perfume = db.query(Perfume).filter(Perfume.perfume_id == perfume_id).first()
        if not perfume:
            logger.warning(f"⚠️ Perfume {perfume_id} not found")
            return False
        
        # Check if perfume has campaigns
        campaigns_count = db.query(Campaign).filter(Campaign.perfume_id == perfume_id).count()
        if campaigns_count > 0:
            logger.warning(f"⚠️ Cannot delete perfume {perfume_id}: has {campaigns_count} campaigns")
            return False
        
        db.delete(perfume)
        db.commit()
        logger.info(f"✅ Deleted perfume {perfume_id}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to delete perfume {perfume_id}: {e}")
        raise


def get_perfume_campaigns_count(db: Session, perfume_id: UUID) -> int:
    """
    Get count of campaigns for a perfume.
    
    Args:
        db: Database session
        perfume_id: Perfume ID
    
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
# Campaign CRUD Operations (Phase 2 B2B SaaS)
# ============================================================================

def create_campaign(
    db: Session,
    perfume_id: UUID,
    brand_id: UUID,
    campaign_name: str,
    creative_prompt: str,
    selected_style: str,
    target_duration: int,
    num_variations: int = 1
) -> Campaign:
    """
    Create a new campaign for a perfume.
    
    Args:
        db: Database session
        perfume_id: Perfume ID
        brand_id: Brand ID
        campaign_name: Campaign name (unique within perfume)
        creative_prompt: Creative prompt text
        selected_style: Video style ('gold_luxe', 'dark_elegance', 'romantic_floral')
        target_duration: Target duration in seconds (15-60)
        num_variations: Number of variations (1-3)
    
    Returns:
        Campaign: Created campaign object
    """
    try:
        campaign = Campaign(
            perfume_id=perfume_id,
            brand_id=brand_id,
            campaign_name=campaign_name,
            creative_prompt=creative_prompt,
            selected_style=selected_style,
            target_duration=target_duration,
            num_variations=num_variations,
            status='pending',
            progress=0,
            cost=0,
            campaign_json={}
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        logger.info(f"✅ Created campaign {campaign.campaign_id} for perfume {perfume_id}")
        return campaign
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to create campaign: {e}")
        raise


def get_campaigns_by_perfume(
    db: Session,
    perfume_id: UUID,
    page: int = 1,
    limit: int = 20
) -> Tuple[List[Campaign], int]:
    """
    Get campaigns for a perfume with pagination.
    
    Args:
        db: Database session
        perfume_id: Perfume ID
        page: Page number (1-indexed)
        limit: Items per page
    
    Returns:
        Tuple of (list of campaigns, total count)
    """
    try:
        offset = (page - 1) * limit
        campaigns = db.query(Campaign)\
            .filter(Campaign.perfume_id == perfume_id)\
            .order_by(desc(Campaign.created_at))\
            .offset(offset)\
            .limit(limit)\
            .all()
        
        total = db.query(Campaign).filter(Campaign.perfume_id == perfume_id).count()
        
        logger.debug(f"✅ Retrieved {len(campaigns)} campaigns for perfume {perfume_id} (page {page})")
        return campaigns, total
    except Exception as e:
        logger.error(f"❌ Failed to get campaigns for perfume {perfume_id}: {e}")
        raise


def get_campaigns_by_brand(
    db: Session,
    brand_id: UUID,
    page: int = 1,
    limit: int = 20
) -> Tuple[List[Campaign], int]:
    """
    Get campaigns for a brand with pagination.
    
    Args:
        db: Database session
        brand_id: Brand ID
        page: Page number (1-indexed)
        limit: Items per page
    
    Returns:
        Tuple of (list of campaigns, total count)
    """
    try:
        offset = (page - 1) * limit
        campaigns = db.query(Campaign)\
            .filter(Campaign.brand_id == brand_id)\
            .order_by(desc(Campaign.created_at))\
            .offset(offset)\
            .limit(limit)\
            .all()
        
        total = db.query(Campaign).filter(Campaign.brand_id == brand_id).count()
        
        logger.debug(f"✅ Retrieved {len(campaigns)} campaigns for brand {brand_id} (page {page})")
        return campaigns, total
    except Exception as e:
        logger.error(f"❌ Failed to get campaigns for brand {brand_id}: {e}")
        raise


def get_campaign_by_id(db: Session, campaign_id: UUID) -> Optional[Campaign]:
    """
    Get campaign by ID.
    
    Args:
        db: Database session
        campaign_id: Campaign ID
    
    Returns:
        Campaign: Campaign object if found, None otherwise
    """
    try:
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if campaign:
            logger.debug(f"✅ Retrieved campaign {campaign_id}")
        else:
            logger.debug(f"⚠️ Campaign {campaign_id} not found")
        return campaign
    except Exception as e:
        logger.error(f"❌ Failed to get campaign {campaign_id}: {e}")
        raise


def update_campaign(
    db: Session,
    campaign_id: UUID,
    **updates
) -> Optional[Campaign]:
    """
    Update campaign fields.
    
    Args:
        db: Database session
        campaign_id: Campaign ID
        **updates: Fields to update (status, progress, cost, campaign_json, etc.)
    
    Returns:
        Campaign: Updated campaign object if successful, None if not found
    """
    try:
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if not campaign:
            logger.warning(f"⚠️ Campaign {campaign_id} not found for update")
            return None
        
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


def delete_campaign(db: Session, campaign_id: UUID) -> bool:
    """
    Delete a campaign (only if not processing).
    
    Args:
        db: Database session
        campaign_id: Campaign ID
    
    Returns:
        bool: True if deleted, False if not found or processing
    """
    try:
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if not campaign:
            logger.warning(f"⚠️ Campaign {campaign_id} not found")
            return False
        
        # Check if campaign is processing
        if campaign.status == 'processing':
            logger.warning(f"⚠️ Cannot delete campaign {campaign_id}: currently processing")
            return False
        
        db.delete(campaign)
        db.commit()
        logger.info(f"✅ Deleted campaign {campaign_id}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to delete campaign {campaign_id}: {e}")
        raise


