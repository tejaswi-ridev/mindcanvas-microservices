import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:1974@localhost:5432/mindcanvas_micro")
    secret_key: str = os.getenv("SECRET_KEY", "efb4be244c9357f3ddd2dd8c96480f78871aae5c528e054beb39070e86e7bfd4")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    class Config:
        env_file = ".env"

settings = Settings()
