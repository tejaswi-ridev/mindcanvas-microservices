from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import redis
import json
import os
from datetime import datetime
import csv
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import grpc

from .core.database import get_db, engine
from .services.grpc_client import SearchServiceClient, ImageServiceClient
from .schemas import schemas

app = FastAPI(title="Dashboard Service", version="1.0.0")

# Redis client for caching
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

# gRPC clients
search_client = SearchServiceClient()
image_client = ImageServiceClient()

@app.get("/dashboard/search", response_model=List[schemas.SearchSummary])
async def get_dashboard_search(
    x_user_id: Optional[str] = Header(None),
    limit: int = 10
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")

    user_id = int(x_user_id)

    cache_key = f"dashboard:search:{user_id}:{limit}"
    cached_result = redis_client.get(cache_key)
    if cached_result:
        return json.loads(cached_result)

    try:
        searches = await search_client.get_search_history(user_id, limit)
        # FIX: Directly dump the list of dictionaries
        redis_client.setex(cache_key, 300, json.dumps(searches))
        return searches
    except Exception as e:
        print(f"Error getting search history: {e}")
        return []

@app.get("/dashboard/images", response_model=List[schemas.ImageSummary])
async def get_dashboard_images(
    x_user_id: Optional[str] = Header(None),
    limit: int = 10
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")

    user_id = int(x_user_id)

    cache_key = f"dashboard:images:{user_id}:{limit}"
    cached_result = redis_client.get(cache_key)
    if cached_result:
        return json.loads(cached_result)

    try:
        images = await image_client.get_image_history(user_id, limit)
        # FIX: Directly dump the list of dictionaries
        redis_client.setex(cache_key, 300, json.dumps(images))
        return images
    except Exception as e:
        print(f"Error getting image history: {e}")
        return []

@app.get("/dashboard/stats", response_model=schemas.UserStats)
async def get_user_stats(
    x_user_id: Optional[str] = Header(None)
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")

    user_id = int(x_user_id)

    cache_key = f"dashboard:stats:{user_id}"
    cached_result = redis_client.get(cache_key)
    if cached_result:
        return json.loads(cached_result)

    try:
        search_count = await search_client.get_search_count(user_id)
        image_count = await image_client.get_image_count(user_id)

        stats = {
            "total_searches": search_count,
            "total_images": image_count,
            "last_activity": datetime.utcnow().isoformat()
        }

        redis_client.setex(cache_key, 600, json.dumps(stats))
        return stats
    except Exception as e:
        print(f"Error getting user stats: {e}")
        return {"total_searches": 0, "total_images": 0}

@app.delete("/dashboard/search/{search_id}")
async def delete_search(
    search_id: int,
    x_user_id: Optional[str] = Header(None)
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")

    user_id = int(x_user_id)
    try:
        success = await search_client.delete_search(user_id, search_id)
        if success:
            redis_client.delete(f"dashboard:search:{user_id}:10")
            redis_client.delete(f"dashboard:stats:{user_id}")
            return {"message": "Search deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Search not found")
    except Exception as e:
        print(f"Error deleting search: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete search")

@app.delete("/dashboard/image/{image_id}")
async def delete_image(
    image_id: int,
    x_user_id: Optional[str] = Header(None)
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    user_id = int(x_user_id)
    try:
        success = await image_client.delete_image(user_id, image_id)
        if success:
            redis_client.delete(f"dashboard:images:{user_id}:10")
            redis_client.delete(f"dashboard:stats:{user_id}")
            return {"message": "Image deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Image not found")
    except Exception as e:
        print(f"Error deleting image: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete image")

@app.get("/dashboard/export/csv")
async def export_data_csv(
    x_user_id: Optional[str] = Header(None)
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    user_id = int(x_user_id)
    try:
        searches = await search_client.get_search_history(user_id, limit=1000)
        images = await image_client.get_image_history(user_id, limit=1000)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Type", "ID", "Content", "Timestamp"])

        # FIX: Access items by key, not attribute
        for search in searches:
            writer.writerow(["Search", search['id'], search['query'], search['created_at']])
        for image in images:
            writer.writerow(["Image", image['id'], image['prompt'], image['created_at']])

        output.seek(0)
        return StreamingResponse(io.StringIO(output.getvalue()), media_type="text/csv",
                                 headers={"Content-Disposition": "attachment; filename=mindcanvas_data.csv"})
    except Exception as e:
        print(f"Error exporting CSV: {e}")
        raise HTTPException(status_code=500, detail="Failed to export data")

@app.get("/dashboard/export/pdf")
async def export_data_pdf(
    x_user_id: Optional[str] = Header(None)
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    user_id = int(x_user_id)
    try:
        searches = await search_client.get_search_history(user_id, limit=100)
        images = await image_client.get_image_history(user_id, limit=100)

        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(50, height - 50, "MindCanvas User Data Export")
        y_position = height - 100

        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, y_position, f"Search History ({len(searches)} items)")
        y_position -= 30
        pdf.setFont("Helvetica", 10)
        
        # FIX: Access items by key, not attribute
        for search in searches[:20]:
            if y_position < 100:
                pdf.showPage()
                y_position = height - 50
            pdf.drawString(70, y_position, f"• {search['query']}")
            y_position -= 15

        y_position -= 20
        if y_position < 100:
            pdf.showPage()
            y_position = height - 50

        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, y_position, f"Generated Images ({len(images)} items)")
        y_position -= 30
        pdf.setFont("Helvetica", 10)

        # FIX: Access items by key, not attribute
        for image in images[:20]:
            if y_position < 100:
                pdf.showPage()
                y_position = height - 50
            pdf.drawString(70, y_position, f"• {image['prompt'][:60]}...")
            y_position -= 15

        pdf.save()
        buffer.seek(0)
        return StreamingResponse(io.BytesIO(buffer.getvalue()), media_type="application/pdf",
                                 headers={"Content-Disposition": "attachment; filename=mindcanvas_data.pdf"})
    except Exception as e:
        print(f"Error exporting PDF: {e}")
        raise HTTPException(status_code=500, detail="Failed to export PDF")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "dashboard-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
