"""
Authentication API Routes.
Handles user signup, login, logout, and token management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import jwt
import os
import logging

from app.database.connection import get_db
from app.database.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 7 days


# ============================================================================
# Pydantic Schemas
# ============================================================================

class UserSignup(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    created_at: datetime
    is_verified: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MessageResponse(BaseModel):
    message: str


# ============================================================================
# Helper Functions
# ============================================================================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: UUID, email: str) -> str:
    """Create a JWT access token."""
    expires = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expires,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email address."""
    return db.query(User).filter(User.email == email.lower()).first()


def get_user_by_id(db: Session, user_id: UUID) -> Optional[User]:
    """Get user by ID."""
    return db.query(User).filter(User.id == user_id).first()


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    """
    Register a new user.

    - **email**: User's email address (must be unique)
    - **password**: User's password (min 6 characters recommended)

    Returns access token and user info on success.
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    # Validate password length
    if len(user_data.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters"
        )

    # Check if user already exists
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # Create new user
    try:
        new_user = User(
            email=user_data.email.lower(),
            password_hash=hash_password(user_data.password),
            is_active=True,
            is_verified=True,  # Auto-verify for now
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        logger.info(f"New user registered: {new_user.email}")

        # Generate token
        access_token = create_access_token(new_user.id, new_user.email)

        return TokenResponse(
            access_token=access_token,
            user=UserResponse(
                id=str(new_user.id),
                email=new_user.email,
                created_at=new_user.created_at,
                is_verified=new_user.is_verified,
            )
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Signup failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create user")


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate a user and return access token.

    - **email**: User's email address
    - **password**: User's password

    Returns access token and user info on success.
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    # Find user
    user = get_user_by_email(db, user_data.email)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Verify password
    if not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="Account is deactivated"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    logger.info(f"User logged in: {user.email}")

    # Generate token
    access_token = create_access_token(user.id, user.email)

    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            created_at=user.created_at,
            is_verified=user.is_verified,
        )
    )


@router.post("/logout", response_model=MessageResponse)
async def logout():
    """
    Log out the current user.

    Note: Since we use stateless JWTs, logout is handled client-side
    by removing the token from storage.
    """
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    db: Session = Depends(get_db),
    authorization: str = None
):
    """
    Get current authenticated user's information.

    Requires valid JWT token in Authorization header.
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        # Extract token
        parts = authorization.split(" ")
        if len(parts) != 2 or parts[0] != "Bearer":
            raise HTTPException(status_code=401, detail="Invalid token format")

        token = parts[1]

        # Decode token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = UUID(payload.get("sub"))

        # Get user
        user = get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return UserResponse(
            id=str(user.id),
            email=user.email,
            created_at=user.created_at,
            is_verified=user.is_verified,
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    db: Session = Depends(get_db),
    authorization: str = None
):
    """
    Refresh an access token.

    Requires valid (or recently expired) JWT token.
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        # Extract token
        parts = authorization.split(" ")
        if len(parts) != 2 or parts[0] != "Bearer":
            raise HTTPException(status_code=401, detail="Invalid token format")

        token = parts[1]

        # Decode token (allow expired)
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"verify_exp": False}
        )
        user_id = UUID(payload.get("sub"))

        # Get user
        user = get_user_by_id(db, user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Invalid user")

        # Generate new token
        access_token = create_access_token(user.id, user.email)

        return TokenResponse(
            access_token=access_token,
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                created_at=user.created_at,
                is_verified=user.is_verified,
            )
        )

    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(status_code=401, detail="Token refresh failed")
