from fastapi import FastAPI, HTTPException, Header, Depends
from sqlalchemy.orm import Session
from typing import Optional
import redis
import json
import os
from kafka import KafkaConsumer, KafkaProducer
from datetime import datetime
import threading
import asyncio

from .core.database import get_db, engine
from .models import models
from .schemas import schemas

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="User Service", version="1.0.0")

# Redis client for caching
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

# Kafka producer for events
kafka_producer = KafkaProducer(
    bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(","),
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

def kafka_consumer_worker():
    """Kafka consumer to listen for user-related events"""
    consumer = KafkaConsumer(
        'user_events',
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(","),
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        group_id='user-service-group'
    )

    for message in consumer:
        try:
            event = message.value
            event_type = event.get('event_type')

            if event_type == 'user_registered':
                # Handle user registration event
                user_data = event.get('user_data', {})
                print(f"User registered: {user_data}")

            elif event_type == 'user_login':
                # Handle user login event
                user_data = event.get('user_data', {})
                print(f"User logged in: {user_data}")

        except Exception as e:
            print(f"Error processing Kafka message: {e}")

@app.get("/user/profile", response_model=schemas.UserProfile)
async def get_user_profile(
    x_user_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")

    user_id = int(x_user_id)

    # Check cache first
    cache_key = f"user_profile:{user_id}"
    cached_profile = redis_client.get(cache_key)
    if cached_profile:
        return json.loads(cached_profile)

    # Get or create user profile
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.user_id == user_id
    ).first()

    if not profile:
        # Create default profile
        profile = models.UserProfile(
            user_id=user_id,
            preferences=json.dumps({"theme": "light", "language": "en"}),
            settings=json.dumps({"notifications": True})
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    profile_data = {
        "user_id": profile.user_id,
        "preferences": json.loads(profile.preferences or "{}"),
        "settings": json.loads(profile.settings or "{}"),
        "created_at": profile.created_at.isoformat(),
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None
    }

    # Cache for 1 hour
    redis_client.setex(cache_key, 3600, json.dumps(profile_data))

    return profile_data

@app.put("/user/profile", response_model=schemas.UserProfile)
async def update_user_profile(
    profile_update: schemas.UserProfileUpdate,
    x_user_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")

    user_id = int(x_user_id)

    # Get or create user profile
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.user_id == user_id
    ).first()

    if not profile:
        profile = models.UserProfile(
            user_id=user_id,
            preferences=json.dumps({}),
            settings=json.dumps({})
        )
        db.add(profile)

    # Update profile
    if profile_update.preferences:
        profile.preferences = json.dumps(profile_update.preferences)
    if profile_update.settings:
        profile.settings = json.dumps(profile_update.settings)

    db.commit()
    db.refresh(profile)

    # Clear cache
    redis_client.delete(f"user_profile:{user_id}")

    # Publish profile update event
    try:
        event = {
            "event_type": "profile_updated",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        kafka_producer.send("user_events", event)
    except Exception as e:
        print(f"Failed to publish profile update event: {e}")

    return {
        "user_id": profile.user_id,
        "preferences": json.loads(profile.preferences or "{}"),
        "settings": json.loads(profile.settings or "{}"),
        "created_at": profile.created_at.isoformat(),
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None
    }

@app.get("/user/activity", response_model=list[schemas.UserActivity])
async def get_user_activity(
    x_user_id: Optional[str] = Header(None),
    limit: int = 50,
    db: Session = Depends(get_db)
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")

    user_id = int(x_user_id)

    activities = db.query(models.UserActivity).filter(
        models.UserActivity.user_id == user_id
    ).order_by(models.UserActivity.created_at.desc()).limit(limit).all()

    return [
        {
            "id": activity.id,
            "activity_type": activity.activity_type,
            "description": activity.description,
            "metadata": json.loads(activity.metadata or "{}"),
            "created_at": activity.created_at
        }
        for activity in activities
    ]

@app.post("/user/activity")
async def log_user_activity(
    activity: schemas.UserActivityCreate,
    x_user_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")

    user_id = int(x_user_id)

    # Create activity log
    db_activity = models.UserActivity(
        user_id=user_id,
        activity_type=activity.activity_type,
        description=activity.description,
        metadata=json.dumps(activity.metadata or {})
    )

    db.add(db_activity)
    db.commit()

    return {"message": "Activity logged successfully"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "user-service"}

# Start Kafka consumer in background thread
def start_kafka_consumer():
    kafka_thread = threading.Thread(target=kafka_consumer_worker, daemon=True)
    kafka_thread.start()

if __name__ == "__main__":
    start_kafka_consumer()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
