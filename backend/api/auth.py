"""
Authentication API endpoints
User registration and API key management
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field

from backend.database import get_db
from backend.models.user import User
from backend.models.api_key import APIKey
from backend.core.security import generate_api_key, hash_password
from backend.core.exceptions import http_400_bad_request

router = APIRouter(prefix="/auth", tags=["authentication"])


class RegisterRequest(BaseModel):
    """Request schema for user registration"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")


class RegisterResponse(BaseModel):
    """Response schema for user registration"""
    user_id: str
    email: str
    api_key: str = Field(..., description="API key (save this - only shown once!)")


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user and generate API key

    **Important**: The API key is only returned once. Save it securely!

    Args:
        request: Email and password
        db: Database session

    Returns:
        RegisterResponse: User ID, email, and API key

    Raises:
        HTTPException: 400 if email already registered
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()

    if existing_user:
        raise http_400_bad_request(f"Email '{request.email}' is already registered")

    # Create user
    user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        is_active=True,
        is_superuser=False
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate API key
    api_key, key_hash = generate_api_key()

    # Store API key
    api_key_obj = APIKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=api_key[:15],  # Store prefix for identification
        name="Default API Key",
        scopes=["documents:read", "documents:write", "retrievals:read", "chat:read"]
    )

    db.add(api_key_obj)
    db.commit()

    return RegisterResponse(
        user_id=str(user.id),
        email=user.email,
        api_key=api_key  # Only returned once!
    )
