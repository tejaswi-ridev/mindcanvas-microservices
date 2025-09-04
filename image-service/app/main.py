from fastapi import FastAPI, HTTPException, Header, Depends
from sqlalchemy.orm import Session
from typing import Optional
import redis
import json
import os
from kafka import KafkaProducer
from datetime import datetime
import base64

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from urllib.parse import urlencode

from .core.database import get_db, engine
from .models import models
from .schemas import schemas

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Image Service", version="1.0.0")

# Redis client for caching
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

# Kafka producer for events
kafka_producer = KafkaProducer(
    bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(","),
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

# Flux MCP configuration
FLUX_API_KEY = os.getenv("FLUX_API_KEY", "54945398-acdb-4b35-975e-595c7fa33ed1")
FLUX_BASE_URL = "https://server.smithery.ai/@falahgs/flux-imagegen-mcp-server/mcp"

async def generate_image_with_flux(prompt: str, width: int = 1024, height: int = 1024):
    try:
        cache_key = f"image:{hash(prompt)}:{width}:{height}"
        cached_result = redis_client.get(cache_key)
        if cached_result:
            return json.loads(cached_result)

        params = {"api_key": FLUX_API_KEY}
        url = f"{FLUX_BASE_URL}?{urlencode(params)}"

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "generate_image",
                    arguments={
                        "prompt": prompt,
                        "width": width,
                        "height": height,
                        "steps": 20,
                        "guidance": 3.5
                    }
                )
                redis_client.setex(cache_key, 86400, json.dumps(result.content))
                return result.content

    except Exception as e:
        print(f"Flux image generation error: {e}")
        return {
            "image_url": "https://picsum.photos/1024/1024",
            "image_data": None,
            "metadata": {
                "prompt": prompt,
                "width": width,
                "height": height,
                "model": "flux-dev"
            }
        }

async def publish_image_event(user_id: int, prompt: str, image_url: str):
    try:
        event = {
            "event_type": "image_generated",
            "user_id": user_id,
            "prompt": prompt,
            "image_url": image_url,
            "timestamp": datetime.utcnow().isoformat()
        }
        kafka_producer.send("image_events", event)
    except Exception as e:
        print(f"Failed to publish image event: {e}")

@app.post("/image/generate", response_model=schemas.ImageResponse)
async def generate_image(
    image_request: schemas.ImageRequest,
    x_user_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")

    user_id = int(x_user_id)

    image_result = await generate_image_with_flux(
        image_request.prompt,
        image_request.width or 1024,
        image_request.height or 1024
    )

    if isinstance(image_result, list) and len(image_result) > 0:
        image_url = image_result[0].get("url") or image_result[0].get("image_url", "https://picsum.photos/1024/1024")
        metadata = image_result[0].get("metadata", {})
    elif isinstance(image_result, dict):
        image_url = image_result.get("image_url", "https://picsum.photos/1024/1024")
        metadata = image_result.get("metadata", {})
    else:
        image_url = "https://picsum.photos/1024/1024"
        metadata = {}

    db_image = models.GeneratedImage(
        user_id=user_id,
        prompt=image_request.prompt,
        image_url=image_url,
        width=image_request.width or 1024,
        height=image_request.height or 1024,
        metadata=json.dumps(metadata)
    )

    db.add(db_image)
    db.commit()
    db.refresh(db_image)

    # Invalidate dashboard caches
    redis_client.delete(f"dashboard:images:{user_id}:10")
    redis_client.delete(f"dashboard:stats:{user_id}")

    await publish_image_event(user_id, image_request.prompt, image_url)

    return {
        "image_id": db_image.id,
        "prompt": image_request.prompt,
        "image_url": image_url,
        "width": db_image.width,
        "height": db_image.height,
        "metadata": metadata,
        "timestamp": db_image.created_at
    }

@app.get("/image/history", response_model=list[schemas.ImageHistory])
async def get_image_history(
    x_user_id: Optional[str] = Header(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")

    user_id = int(x_user_id)

    images = db.query(models.GeneratedImage).filter(
        models.GeneratedImage.user_id == user_id
    ).order_by(models.GeneratedImage.created_at.desc()).offset(skip).limit(limit).all()

    return [
        {
            "id": image.id,
            "prompt": image.prompt,
            "image_url": image.image_url,
            "width": image.width,
            "height": image.height,
            "created_at": image.created_at
        }
        for image in images
    ]

@app.get("/image/{image_id}", response_model=schemas.ImageDetail)
async def get_image_detail(
    image_id: int,
    x_user_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")

    user_id = int(x_user_id)

    image = db.query(models.GeneratedImage).filter(
        models.GeneratedImage.id == image_id,
        models.GeneratedImage.user_id == user_id
    ).first()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    return {
        "id": image.id,
        "prompt": image.prompt,
        "image_url": image.image_url,
        "width": image.width,
        "height": image.height,
        "metadata": json.loads(image.metadata) if image.metadata else {},
        "created_at": image.created_at
    }

@app.delete("/image/{image_id}")
async def delete_image(
    image_id: int,
    x_user_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")

    user_id = int(x_user_id)

    image = db.query(models.GeneratedImage).filter(
        models.GeneratedImage.id == image_id,
        models.GeneratedImage.user_id == user_id
    ).first()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    db.delete(image)
    db.commit()

    # Invalidate dashboard caches
    redis_client.delete(f"dashboard:images:{user_id}:10")
    redis_client.delete(f"dashboard:stats:{user_id}")

    return {"message": "Image deleted successfully"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "image-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
