from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any

class UserProfile(BaseModel):
    user_id: int
    preferences: Dict[str, Any]
    settings: Dict[str, Any]
    created_at: str
    updated_at: Optional[str] = None

class UserProfileUpdate(BaseModel):
    preferences: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None

class UserActivity(BaseModel):
    id: int
    activity_type: str
    description: str
    meta_data: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True

class UserActivityCreate(BaseModel):
    activity_type: str
    description: str
    meta_data: Optional[Dict[str, Any]] = None
