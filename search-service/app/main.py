from fastapi import FastAPI, HTTPException, Header, Depends
from sqlalchemy.orm import Session
from typing import Optional
import redis
import json
import os
from kafka import KafkaProducer
from datetime import datetime
import grpc
from concurrent import futures
import threading

# --- START OF CHANGES ---
# The mcp imports are no longer needed, so they are replaced with the TavilyClient
from tavily import TavilyClient
# --- END OF CHANGES ---

from .core.database import get_db, engine
from .models import models
from .schemas import schemas

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Search Service", version="1.0.0")

# Redis client for caching
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

# Kafka producer for events
kafka_producer = KafkaProducer(
    bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(","),
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

# --- START OF CHANGES ---
# This part is simplified as the profile and complex URL are no longer needed
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

async def search_with_tavily(query: str, max_results: int = 10):
    """Search using the official Tavily Python client"""
    try:
        # Check cache first (this logic is preserved)
        cache_key = f"search:{hash(query)}"
        cached_result = redis_client.get(cache_key)
        if cached_result:
            return json.loads(cached_result)

        # Ensure the API key is available
        if not TAVILY_API_KEY:
            raise ValueError("TAVILY_API_KEY environment variable not set")

        # Initialize the Tavily client with your API key
        client = TavilyClient(api_key=TAVILY_API_KEY)

        # Perform the search
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results
        )

        # The client directly returns the list of results
        search_results = response.get("results", [])

        # Cache result for 1 hour (this logic is preserved)
        redis_client.setex(cache_key, 3600, json.dumps(search_results))

        return search_results

    except Exception as e:
        # The detailed error logging is preserved
        import traceback
        print("="*80)
        print("TAVILY SEARCH FAILED - DETAILED TRACEBACK:")
        traceback.print_exc()
        print("="*80)

        # The mock data fallback is preserved
        return [{
            "title": f"Search result for '{query}'",
            "url": "https://example.com",
            "snippet": f"This is a mock search result for the query: {query}",
            "published_date": datetime.now().isoformat()
        }]
# --- END OF CHANGES ---

async def publish_search_event(user_id: int, query: str, results: list):
    """Publish search events to Kafka"""
    try:
        event = {
            "event_type": "search_performed",
            "user_id": user_id,
            "query": query,
            "result_count": len(results),
            "timestamp": datetime.utcnow().isoformat()
        }
        kafka_producer.send("search_events", event)
    except Exception as e:
        print(f"Failed to publish search event: {e}")


@app.post("/search/", response_model=schemas.SearchResponse)
async def perform_search(
    search_request: schemas.SearchRequest,
    x_user_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")

    user_id = int(x_user_id)

    # Perform search using Tavily
    search_results = await search_with_tavily(
        search_request.query,
        search_request.max_results or 10
    )

    # Save search to database
    db_search = models.Search(
        user_id=user_id,
        query=search_request.query,
        results=json.dumps(search_results),
        result_count=len(search_results)
    )

    db.add(db_search)
    db.commit()
    db.refresh(db_search)

    # Invalidate dashboard caches so it fetches fresh data
    redis_client.delete(f"dashboard:search:{user_id}:10")
    redis_client.delete(f"dashboard:stats:{user_id}")

    # Publish search event
    await publish_search_event(user_id, search_request.query, search_results)

    return {
        "search_id": db_search.id,
        "query": search_request.query,
        "results": search_results,
        "result_count": len(search_results),
        "timestamp": db_search.created_at
    }

@app.get("/search/history", response_model=list[schemas.SearchHistory])
async def get_search_history(
    x_user_id: Optional[str] = Header(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")

    user_id = int(x_user_id)

    searches = db.query(models.Search).filter(
        models.Search.user_id == user_id
    ).order_by(models.Search.created_at.desc()).offset(skip).limit(limit).all()

    return [
        {
            "id": search.id,
            "query": search.query,
            "result_count": search.result_count,
            "created_at": search.created_at
        }
        for search in searches
    ]


@app.get("/search/{search_id}", response_model=schemas.SearchDetail)
async def get_search_detail(
    search_id: int,
    x_user_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")

    user_id = int(x_user_id)

    search = db.query(models.Search).filter(
        models.Search.id == search_id,
        models.Search.user_id == user_id
    ).first()

    if not search:
        raise HTTPException(status_code=404, detail="Search not found")

    return {
        "id": search.id,
        "query": search.query,
        "results": json.loads(search.results),
        "result_count": search.result_count,
        "created_at": search.created_at
    }


@app.delete("/search/{search_id}")
async def delete_search(
    search_id: int,
    x_user_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")

    user_id = int(x_user_id)

    search = db.query(models.Search).filter(
        models.Search.id == search_id,
        models.Search.user_id == user_id
    ).first()

    if not search:
        raise HTTPException(status_code=404, detail="Search not found")

    db.delete(search)
    db.commit()

    return {"message": "Search deleted successfully"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "search-service"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
