from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any

class SearchRequest(BaseModel):
    query: str
    max_results: Optional[int] = 10

class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    published_date: Optional[str] = None

class SearchResponse(BaseModel):
    search_id: int
    query: str
    results: List[Dict[str, Any]]
    result_count: int
    timestamp: datetime

class SearchHistory(BaseModel):
    id: int
    query: str
    result_count: int
    created_at: datetime

    class Config:
        from_attributes = True

class SearchDetail(BaseModel):
    id: int
    query: str
    results: List[Dict[str, Any]]
    result_count: int
    created_at: datetime

    class Config:
        from_attributes = True
