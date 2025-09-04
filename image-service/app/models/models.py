from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class GeneratedImage(Base):
    __tablename__ = "generated_images"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    prompt = Column(Text, nullable=False)
    image_url = Column(String, nullable=False)
    width = Column(Integer, default=1024)
    height = Column(Integer, default=1024)
    meta_data = Column(Text)  # JSON string of generation metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
