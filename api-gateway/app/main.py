from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
import httpx
import redis
import json
from kafka import KafkaProducer
import asyncio
import logging
from typing import Dict, Any
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MindCanvas API Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

kafka_producer = KafkaProducer(
    bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(","),
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

SERVICES = {
    "auth": os.getenv("AUTH_SERVICE_URL", "http://localhost:8001"),
    "user": os.getenv("USER_SERVICE_URL", "http://localhost:8002"), 
    "search": os.getenv("SEARCH_SERVICE_URL", "http://localhost:8003"),
    "image": os.getenv("IMAGE_SERVICE_URL", "http://localhost:8004"),
    "dashboard": os.getenv("DASHBOARD_SERVICE_URL", "http://localhost:8005")
}

security = HTTPBearer(auto_error=False)

async def get_current_user(request: Request, token = Depends(security)):
    if not token:
        return None
    cached_user = redis_client.get(f"user_token:{token.credentials}")
    if cached_user:
        return json.loads(cached_user)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{SERVICES['auth']}/auth/me",
                headers={"Authorization": f"Bearer {token.credentials}"}
            )
            if response.status_code == 200:
                user_data = response.json()
                redis_client.setex(f"user_token:{token.credentials}", 900, json.dumps(user_data))
                return user_data
        except Exception as e:
            logger.error(f"Auth validation error: {e}")
    return None

async def log_request_to_kafka(endpoint: str, user_id: str = None, request_data: Dict = None):
    try:
        event = {
            "endpoint": endpoint,
            "user_id": user_id,
            "timestamp": asyncio.get_event_loop().time(),
            "request_data": request_data
        }
        kafka_producer.send("api_requests", event)
    except Exception as e:
        logger.error(f"Kafka logging error: {e}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "services": SERVICES}

# Authentication routes
@app.post("/auth/register")
async def register(request: Request):
    data = await request.json()
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{SERVICES['auth']}/auth/register", json=data)
            await log_request_to_kafka("/auth/register", request_data={"email": data.get("email")})
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Auth service unavailable")

@app.post("/auth/login") 
async def login(request: Request):
    data = await request.json()
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{SERVICES['auth']}/auth/login", json=data)
            await log_request_to_kafka("/auth/login", request_data={"email": data.get("email")})
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Auth service unavailable")

@app.get("/auth/me")
async def get_me(current_user = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return current_user

@app.post("/auth/refresh")
async def refresh_token(request: Request):
    data = await request.json()
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{SERVICES['auth']}/auth/refresh", json=data)
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Auth service unavailable")

# Search routes
@app.post("/search/")
async def search_web(request: Request, current_user = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    data = await request.json()
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{SERVICES['search']}/search/",
                json=data,
                headers={"X-User-ID": str(current_user["id"])}
            )
            await log_request_to_kafka("/search", current_user["id"], data)
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Search service unavailable")

@app.get("/search/history")
async def get_search_history(current_user = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{SERVICES['search']}/search/history",
                headers={"X-User-ID": str(current_user["id"])}
            )
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Search service unavailable")

# Image generation routes
@app.post("/image/generate")
async def generate_image(request: Request, current_user = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    data = await request.json()
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{SERVICES['image']}/image/generate",
                json=data,
                headers={"X-User-ID": str(current_user["id"])}
            )
            await log_request_to_kafka("/image/generate", current_user["id"], data)
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Image service unavailable")

@app.get("/image/history")
async def get_image_history(current_user = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{SERVICES['image']}/image/history",
                headers={"X-User-ID": str(current_user["id"])}
            )
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Image service unavailable")

# Dashboard routes (✅ FIXED to proxy through gateway properly)
@app.get("/dashboard/search")
async def get_dashboard_search(current_user = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{SERVICES['dashboard']}/dashboard/search",
                headers={"X-User-ID": str(current_user['id'])}
            )
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Dashboard service unavailable")

@app.get("/dashboard/images")
async def get_dashboard_images(current_user = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{SERVICES['dashboard']}/dashboard/images",
                headers={"X-User-ID": str(current_user['id'])}
            )
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Dashboard service unavailable")
        
@app.get("/dashboard/stats")
async def get_dashboard_stats(current_user = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{SERVICES['dashboard']}/dashboard/stats",
                headers={"X-User-ID": str(current_user["id"])}
            )
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Dashboard service unavailable")


# other dashboard routes unchanged...

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
