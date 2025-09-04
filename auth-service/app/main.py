from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import redis
import json
import os
from kafka import KafkaProducer
import grpc
from concurrent import futures
import asyncio
import threading

from .core.database import get_db, engine
from .models import models
from .schemas import schemas
from .services.auth_service import AuthServiceImplementation
from .core.config import settings

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auth Service", version="1.0.0")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "efb4be244c9357f3ddd2dd8c96480f78871aae5c528e054beb39070e86e7bfd4")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Redis client
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

# Kafka producer
kafka_producer = KafkaProducer(
    bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(","),
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str, db: Session):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None

        # Check Redis cache first
        cached_user = redis_client.get(f"user:{user_id}")
        if cached_user:
            return json.loads(cached_user)

        # Get from database
        user = db.query(models.User).filter(models.User.id == int(user_id)).first()
        if user:
            user_data = {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "created_at": user.created_at.isoformat()
            }
            # Cache for 15 minutes
            redis_client.setex(f"user:{user_id}", 900, json.dumps(user_data))
            return user_data
    except JWTError:
        return None

    return None

async def publish_user_event(event_type: str, user_data: dict):
    """Publish user events to Kafka"""
    try:
        event = {
            "event_type": event_type,
            "user_data": user_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        kafka_producer.send("user_events", event)
    except Exception as e:
        print(f"Failed to publish event: {e}")

@app.post("/auth/register", response_model=schemas.UserResponse)
async def register_user(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    hashed_password = hash_password(user_data.password)
    db_user = models.User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Create access token
    access_token = create_access_token(data={"sub": str(db_user.id)})

    # Publish user registration event
    await publish_user_event("user_registered", {
        "user_id": db_user.id,
        "email": db_user.email,
        "full_name": db_user.full_name
    })

    return {
        "user": {
            "id": db_user.id,
            "email": db_user.email,
            "full_name": db_user.full_name,
            "created_at": db_user.created_at
        },
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.post("/auth/login", response_model=schemas.LoginResponse)
async def login_user(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_credentials.email).first()

    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": str(user.id)})

    # Publish login event
    await publish_user_event("user_login", {
        "user_id": user.id,
        "email": user.email
    })

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "created_at": user.created_at
        }
    }

@app.get("/auth/me", response_model=schemas.User)
async def get_current_user_info(token: str = Depends(security), db: Session = Depends(get_db)):
    user = get_current_user(token.credentials, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

@app.post("/auth/refresh", response_model=schemas.TokenResponse)
async def refresh_access_token(refresh_data: schemas.RefreshToken, db: Session = Depends(get_db)):
    user = get_current_user(refresh_data.refresh_token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    new_access_token = create_access_token(data={"sub": str(user["id"])})

    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }

def start_grpc_server():
    """Start gRPC server in a separate thread"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Add AuthService to server
    from . import auth_pb2_grpc
    auth_service = AuthServiceImplementation()
    auth_pb2_grpc.add_AuthServiceServicer_to_server(auth_service, server)

    server.add_insecure_port('[::]:50051')
    server.start()
    print("gRPC server started on port 50051")
    server.wait_for_termination()

if __name__ == "__main__":
    # Start gRPC server in background thread
    grpc_thread = threading.Thread(target=start_grpc_server, daemon=True)
    grpc_thread.start()

    # Start FastAPI server
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
