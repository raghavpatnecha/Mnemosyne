"""Type definitions for Auth API"""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Schema for user registration"""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")


class RegisterResponse(BaseModel):
    """Schema for registration response"""

    user_id: str
    email: str
    api_key: str = Field(..., description="API key (save this - only shown once!)")
