import httpx
from typing import List, Dict, Any
import os
import traceback

class SearchServiceClient:
    def __init__(self):
        self.http_url = os.getenv("SEARCH_SERVICE_URL", "http://localhost:8003")

    async def get_search_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.http_url}/search/history",
                    headers={"X-User-ID": str(user_id)},
                    params={"limit": limit}
                )
                response.raise_for_status() # This will raise an error for 4xx/5xx responses
                return response.json()
        except Exception as e:
            print("="*80)
            print(f"DASHBOARD FAILED TO GET SEARCH HISTORY from {self.http_url}: {e}")
            traceback.print_exc()
            print("="*80)
            return []

    async def get_search_count(self, user_id: int) -> int:
        try:
            searches = await self.get_search_history(user_id, limit=10000)
            return len(searches)
        except Exception:
            return 0
            
    async def delete_search(self, user_id: int, search_id: int) -> bool:
        # This method remains unchanged
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.http_url}/search/{search_id}",
                    headers={"X-User-ID": str(user_id)}
                )
                return response.status_code == 200
        except Exception:
            return False

class ImageServiceClient:
    def __init__(self):
        self.http_url = os.getenv("IMAGE_SERVICE_URL", "http://localhost:8004")

    async def get_image_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.http_url}/image/history",
                    headers={"X-User-ID": str(user_id)},
                    params={"limit": limit}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print("="*80)
            print(f"DASHBOARD FAILED TO GET IMAGE HISTORY from {self.http_url}: {e}")
            traceback.print_exc()
            print("="*80)
            return []

    async def get_image_count(self, user_id: int) -> int:
        # This method remains unchanged
        try:
            images = await self.get_image_history(user_id, limit=10000)
            return len(images)
        except Exception:
            return 0
    
    async def delete_image(self, user_id: int, image_id: int) -> bool:
        # This method remains unchanged
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.http_url}/image/{image_id}",
                    headers={"X-User-ID": str(user_id)}
                )
                return response.status_code == 200
        except Exception:
            return False
