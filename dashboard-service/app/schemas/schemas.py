from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SearchSummary(BaseModel):
    id: int
    query: str
    result_count: int
    created_at: datetime

class ImageSummary(BaseModel):
    id: int
    prompt: str
    image_url: str
    created_at: datetime

class UserStats(BaseModel):
    total_searches: int
    total_images: int
    last_activity: str
