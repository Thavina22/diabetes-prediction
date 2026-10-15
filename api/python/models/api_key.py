from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
import secrets
import hashlib


class ApiKeyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    scopes: List[str] = Field(default_factory=lambda: ["screening:read", "history:read"])
    rate_limit_rpm: int = Field(default=60, ge=1, le=1000)
    expires_at: Optional[datetime] = None


class ApiKeyCreate(ApiKeyBase):
    pass


class ApiKeyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    scopes: Optional[List[str]] = None
    rate_limit_rpm: Optional[int] = Field(None, ge=1, le=1000)
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class ApiKeyResponse(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    scopes: List[str]
    rate_limit_rpm: int
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ApiKeyCreateResponse(BaseModel):
    id: UUID
    name: str
    key: str  # Full key only returned once
    key_prefix: str
    scopes: List[str]
    rate_limit_rpm: int
    expires_at: Optional[datetime] = None
    created_at: datetime


class WebhookConfig(BaseModel):
    url: str
    events: List[str]
    secret: Optional[str] = None


# Utility functions
def generate_api_key() -> tuple[str, str, str]:
    """Generate API key, return (full_key, key_prefix, key_hash)"""
    # Format: drk_live_xxxxxxxxxxxxxxxx or drk_test_xxxxxxxxxxxxxxxx
    prefix = "drk_live_"
    random_part = secrets.token_urlsafe(24)
    full_key = f"{prefix}{random_part}"
    key_prefix = full_key[:12]  # drk_live_xxxx
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, key_prefix, key_hash


def verify_api_key(provided_key: str, stored_hash: str) -> bool:
    """Verify API key against stored hash"""
    provided_hash = hashlib.sha256(provided_key.encode()).hexdigest()
    return secrets.compare_digest(provided_hash, stored_hash)