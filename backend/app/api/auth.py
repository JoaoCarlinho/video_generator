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

# JWT configuration (same as auth_routes.py)
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"

# Test user ID for development mode
TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


def get_current_user_id(authorization: str = Header(None)) -> UUID:
    """
    Extract user ID from JWT token.

    **Arguments:**
    - authorization: Bearer token from Authorization header

    **Returns:**
    - UUID: User ID extracted from token

    **Raises:**
    - HTTPException 401: Missing or invalid token

    **Implementation Notes:**
    - In development: Falls back to test user ID if no token
    - In production: Validates JWT signature and expiration
    - Token format: "Bearer {token}"
    """
    env = os.getenv("ENVIRONMENT", "development")

    if not authorization:
        if env == "development":
            # Development: use test user ID and ensure it exists in database
            _ensure_test_user_exists(TEST_USER_ID)
            logger.debug("No auth header - using test user ID")
            return TEST_USER_ID
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

        if env == "development":
            # Development: try to decode, fall back to test user
            try:
                decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                user_id = UUID(decoded.get("sub"))
                logger.debug(f"Authenticated user: {user_id}")
                return user_id
            except Exception:
                logger.debug("Dev mode: token decode failed, using test user")
                return TEST_USER_ID

        # Production: validate JWT
        try:
            decoded = jwt.decode(
                token,
                JWT_SECRET,
                algorithms=[JWT_ALGORITHM],
                options={"verify_exp": True}
            )

            # Extract user ID from the 'sub' claim
            user_id_str = decoded.get("sub")
            if not user_id_str:
                logger.error("Token missing 'sub' claim")
                raise HTTPException(status_code=401, detail="Invalid token: missing user ID")

            user_id = UUID(user_id_str)
            logger.debug(f"Authenticated user: {user_id}")
            return user_id

        except jwt.ExpiredSignatureError:
            logger.error("Token expired")
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")
        except ValueError as e:
            logger.error(f"Invalid user ID format: {e}")
            raise HTTPException(status_code=401, detail="Invalid user ID in token")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(status_code=401, detail="Invalid authorization")


def _ensure_test_user_exists(user_id: UUID):
    """Ensure test user exists in users table (dev only)."""
    try:
        from app.database.connection import SessionLocal
        from app.database.models import User

        if SessionLocal is None:
            return

        db = SessionLocal()
        try:
            # Check if user exists
            user = db.query(User).filter(User.id == user_id).first()

            if not user:
                # Create test user
                from passlib.context import CryptContext
                pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

                test_user = User(
                    id=user_id,
                    email="test@example.com",
                    password_hash=pwd_context.hash("testpassword"),
                    is_active=True,
                    is_verified=True,
                )
                db.add(test_user)
                db.commit()
                logger.info(f"Created test user: {user_id}")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Could not ensure test user exists: {e}")


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
    return brand.id


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
    Verify that product belongs to current user's brand.

    **Arguments:**
    - perfume_id: Product ID to verify

    **Returns:**
    - bool: True if product belongs to brand

    **Raises:**
    - HTTPException 404: If product not found or doesn't belong to brand
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    product = crud.get_product_by_id(db, perfume_id)
    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    if product.brand_id != brand_id:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
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

    if campaign.product.brand_id != brand_id:
        raise HTTPException(
            status_code=404,
            detail="Campaign not found"
        )

    return True
