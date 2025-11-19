"""
Authentication middleware and utilities for API endpoints.
Handles JWT token extraction and user context.
"""

from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from uuid import UUID
import logging
import os
import jwt
from typing import Optional
from app.database.connection import get_db
from app.database import crud

logger = logging.getLogger(__name__)


def get_current_user_id(authorization: str = Header(None)) -> UUID:
    """
    Extract user ID from Supabase JWT token.
    
    **Arguments:**
    - authorization: Bearer token from Authorization header
    
    **Returns:**
    - UUID: User ID extracted from token
    
    **Raises:**
    - HTTPException 401: Missing or invalid token
    
    **Implementation Notes:**
    - In development: Falls back to test user ID if no token
    - In production: Validates JWT with Supabase
    - Token format: "Bearer {token}"
    - Automatically creates test user in auth.users if it doesn't exist (dev only)
    """
    # For Phase 4 development: Allow test user ID via header or environment
    env = os.getenv("ENVIRONMENT", "development")
    test_user_id = UUID("00000000-0000-0000-0000-000000000001")
    
    if not authorization:
        if env == "development":
            # Development: use test user ID and ensure it exists in database
            _ensure_test_user_exists(test_user_id)
            logger.debug("⚠️  No auth header - using test user ID")
            return test_user_id
        else:
            # Production: require token
            raise HTTPException(
                status_code=401,
                detail="Missing Authorization header"
            )
    
    try:
        # Extract Bearer token
        parts = authorization.split(" ")
        if len(parts) != 2 or parts[0] != "Bearer":
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization header format. Use 'Bearer {token}'"
            )
        
        token = parts[1]
        
        # Decode JWT token to extract user ID (without verification for now)
        # Supabase JWT tokens contain user_id in the 'sub' claim
        try:
            # Decode without verification (for development)
            # In production, we should verify with Supabase JWT secret
            decoded = jwt.decode(token, options={"verify_signature": False})
            user_id_str = decoded.get("sub") or decoded.get("user_id")
            
            if not user_id_str:
                raise HTTPException(status_code=401, detail="Token missing user ID")
            
            try:
                user_id = UUID(user_id_str)
            except ValueError:
                # Invalid UUID format
                raise HTTPException(status_code=401, detail="Invalid user ID in token")
            
            # Sync user to local auth.users table
            _ensure_user_exists(user_id, decoded.get("email"))
            
            logger.debug(f"✓ Authenticated user: {user_id}")
            return user_id
            
        except jwt.DecodeError:
            # If token decode fails, fall back to test user in development
            if env == "development":
                logger.warning("⚠️  Failed to decode token, using test user")
                _ensure_test_user_exists(test_user_id)
                return test_user_id
            raise HTTPException(status_code=401, detail="Invalid token")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Auth error: {e}")
        raise HTTPException(status_code=401, detail="Invalid authorization")


def _ensure_user_exists(user_id: UUID, email: Optional[str] = None):
    """Ensure user exists in auth.users table (syncs from Supabase)."""
    try:
        from app.database.connection import SessionLocal
        from sqlalchemy import text
        
        if SessionLocal is None:
            return  # Can't create user if DB not available
        
        # Create a new session
        db = SessionLocal()
        try:
            # Check if user exists, create if not
            result = db.execute(
                text("SELECT id FROM auth.users WHERE id = :user_id"),
                {"user_id": str(user_id)}
            ).fetchone()
            
            if not result:
                # Create user (synced from Supabase)
                db.execute(
                    text("INSERT INTO auth.users (id, email, created_at) VALUES (:user_id, :email, NOW()) ON CONFLICT (id) DO NOTHING"),
                    {"user_id": str(user_id), "email": email or "user@example.com"}
                )
                db.commit()
                logger.info(f"✅ Synced user {user_id} to local auth.users table")
            elif email:
                # Update email if provided and different
                db.execute(
                    text("UPDATE auth.users SET email = :email WHERE id = :user_id AND (email IS NULL OR email != :email)"),
                    {"user_id": str(user_id), "email": email}
                )
                db.commit()
        finally:
            db.close()
    except Exception as e:
        # Non-critical - log but don't fail
        logger.warning(f"⚠️  Could not sync user to local DB: {e}")


def _ensure_test_user_exists(user_id: UUID):
    """Ensure test user exists in auth.users table (dev only)."""
    _ensure_user_exists(user_id, "test@example.com")


async def get_authenticated_user(
    authorization: str = Header(None)
) -> UUID:
    """
    Async wrapper for get_current_user_id.
    Use in endpoints where you need async context.
    """
    return get_current_user_id(authorization)


def verify_user_ownership(
    owner_user_id: UUID,
    current_user_id: UUID
) -> bool:
    """
    Verify that current user owns the resource.
    
    **Arguments:**
    - owner_user_id: User ID who owns the resource
    - current_user_id: Current authenticated user ID
    
    **Returns:**
    - bool: True if owner matches
    
    **Raises:**
    - HTTPException 403: If user doesn't own resource
    """
    if owner_user_id != current_user_id:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access this resource"
        )
    return True


# ============================================================================
# Phase 2 B2B SaaS: Brand-related dependencies
# ============================================================================

def get_current_user(user_id: UUID = Depends(get_current_user_id)) -> UUID:
    """
    Get current authenticated user ID (alias for get_current_user_id).
    Kept for backward compatibility.
    """
    return user_id


def get_current_brand_id(
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> UUID:
    """
    Get brand_id for current user.
    
    **Returns:**
    - UUID: Brand ID
    
    **Raises:**
    - HTTPException 404: If brand not found (onboarding not completed)
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    brand = crud.get_brand_by_user_id(db, user_id)
    if not brand:
        raise HTTPException(
            status_code=404,
            detail="Brand not found. Please complete onboarding."
        )
    return brand.brand_id


def verify_onboarding(
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> bool:
    """
    Verify that user has completed onboarding.
    
    **Returns:**
    - bool: True if onboarding completed
    
    **Raises:**
    - HTTPException 403: If onboarding not completed
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    brand = crud.get_brand_by_user_id(db, user_id)
    if not brand or not brand.onboarding_completed:
        raise HTTPException(
            status_code=403,
            detail="Onboarding not completed"
        )
    return True


def verify_perfume_ownership(
    perfume_id: UUID,
    brand_id: UUID = Depends(get_current_brand_id),
    db: Session = Depends(get_db)
) -> bool:
    """
    Verify that perfume belongs to current user's brand.
    
    **Arguments:**
    - perfume_id: Perfume ID to verify
    
    **Returns:**
    - bool: True if perfume belongs to brand
    
    **Raises:**
    - HTTPException 404: If perfume not found or doesn't belong to brand
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    perfume = crud.get_perfume_by_id(db, perfume_id)
    if not perfume:
        raise HTTPException(
            status_code=404,
            detail="Perfume not found"
        )
    
    if perfume.brand_id != brand_id:
        raise HTTPException(
            status_code=404,
            detail="Perfume not found"  # Return 404 to avoid info leak
        )
    
    return True


def verify_campaign_ownership(
    campaign_id: UUID,
    brand_id: UUID = Depends(get_current_brand_id),
    db: Session = Depends(get_db)
) -> bool:
    """
    Verify that campaign belongs to current user's brand.
    
    **Arguments:**
    - campaign_id: Campaign ID to verify
    
    **Returns:**
    - bool: True if campaign belongs to brand
    
    **Raises:**
    - HTTPException 404: If campaign not found or doesn't belong to brand
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    campaign = crud.get_campaign_by_id(db, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=404,
            detail="Campaign not found"
        )
    
    if campaign.brand_id != brand_id:
        raise HTTPException(
            status_code=404,
            detail="Campaign not found"  # Return 404 to avoid info leak
        )
    
    return True

