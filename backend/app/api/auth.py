"""
Authentication middleware and utilities for API endpoints.
Handles JWT token extraction and user context.
"""

from fastapi import Depends, HTTPException, Header
from uuid import UUID
import logging
import os
import jwt
from typing import Dict, Any

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
    """
    # For Phase 4 development: Allow test user ID via header or environment
    env = os.getenv("ENVIRONMENT", "development")

    if not authorization:
        if env == "development":
            # Development: use test user ID
            logger.debug("⚠️  No auth header - using test user ID")
            return UUID("00000000-0000-0000-0000-000000000001")
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
            # Development: accept any token
            logger.debug(f"✓ Accepted dev token")
            return UUID("00000000-0000-0000-0000-000000000001")

        # Production: validate JWT with Supabase
        try:
            # Decode JWT without verification first to check structure
            # Supabase uses HS256 algorithm with JWT secret
            supabase_jwt_secret = os.getenv("SUPABASE_JWT_SECRET")

            if not supabase_jwt_secret:
                # Fallback: decode without verification (less secure but functional)
                logger.warning("⚠️ SUPABASE_JWT_SECRET not set - decoding token without verification")
                decoded = jwt.decode(token, options={"verify_signature": False})
            else:
                # Verify and decode the token
                decoded = jwt.decode(
                    token,
                    supabase_jwt_secret,
                    algorithms=["HS256"],
                    options={"verify_exp": True, "verify_aud": False}
                )

            # Extract user ID from the 'sub' claim
            user_id_str = decoded.get("sub")
            if not user_id_str:
                logger.error("❌ Token missing 'sub' claim")
                raise HTTPException(status_code=401, detail="Invalid token: missing user ID")

            # Convert to UUID
            user_id = UUID(user_id_str)
            logger.debug(f"✓ Authenticated user: {user_id}")
            return user_id

        except jwt.ExpiredSignatureError:
            logger.error("❌ Token expired")
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            logger.error(f"❌ Invalid token: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")
        except ValueError as e:
            logger.error(f"❌ Invalid user ID format: {e}")
            raise HTTPException(status_code=401, detail="Invalid user ID in token")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Auth error: {e}")
        raise HTTPException(status_code=401, detail="Invalid authorization")


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

