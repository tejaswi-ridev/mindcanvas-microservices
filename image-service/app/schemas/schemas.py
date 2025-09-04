from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any

class ImageRequest(BaseModel):
    prompt: str
    width: Optional[int] = 1024
    height: Optional[int] = 1024

class ImageResponse(BaseModel):
    image_id: int
    prompt: str
    image_url: str
    width: int
    height: int
    metadata: Dict[str, Any]
    timestamp: datetime

class ImageHistory(BaseModel):
    id: int
    prompt: str
    image_url: str
    width: int
    height: int
    created_at: datetime

    class Config:
        from_attributes = True

class ImageDetail(BaseModel):
    id: int
    prompt: str
    image_url: str
    width: int
    height: int
    metadata: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True
