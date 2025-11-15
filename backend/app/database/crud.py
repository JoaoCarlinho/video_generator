"""Database CRUD operations for projects."""

from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database.models import Project
from app.models.schemas import (
    CreateProjectRequest,
    ProjectResponse,
    ProjectDetailResponse
)
from uuid import UUID
from typing import List, Optional, Dict, Any
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
    duration: int = 30
) -> Project:
    """
    Create a new project in the database.
    
    Args:
        db: Database session
        user_id: ID of the user creating the project
        title: Project title
        brief: Product brief/description
        ad_project_json: Complete ad project configuration as JSON
        mood: Video mood/style
        duration: Video duration in seconds
    
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
            progress=0,
            cost=0.0
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        logger.info(f"✅ Created project {project.id} for user {user_id}")
        return project
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to create project: {e}")
        raise


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
        raise


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
        raise


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
        raise


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
        db.rollback()
        logger.error(f"❌ Failed to update status for {project_id}: {e}")
        raise


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
        final_videos: Dict with aspect ratios as keys (9:16, 1:1, 16:9) and S3 URLs as values
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
        if isinstance(project.ad_project_json, dict):
            project.ad_project_json["aspectExports"] = final_videos
            project.ad_project_json["costBreakdown"] = cost_breakdown
        
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


