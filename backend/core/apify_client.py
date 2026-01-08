"""
Apify Client - Wrapper for Apify API
LeadHunter AI - Data Collection Module

Allows running pre-built Actors for:
- Instagram Profile Scraping
- Instagram Post Scraping
- Google Maps / Business Data
- Generic Web Scraping
"""

import os
import httpx
import asyncio
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime
from backend.utils.logger import logger
from backend.core.cache_manager import cache

class ApifyClient:
    """
    Client for Apify API.
    
    Usage:
        client = ApifyClient()  # Uses APIFY_TOKEN from env
        
        # Scrape Instagram profile
        result = await client.scrape_instagram_profile("nike")
        
        # Scrape Instagram posts
        posts = await client.scrape_instagram_posts("nike", limit=12)
        
        # Search businesses on Google Maps
        businesses = await client.search_google_maps("pizzaria", "São Paulo")
    """
    
    BASE_URL = "https://api.apify.com/v2"
    
    # Popular Actors for our use cases
    ACTORS = {
        "instagram_profile": "apify/instagram-profile-scraper", # Updated from legacy
        "instagram_posts": "apify/instagram-scraper",          # General scraper covers posts well
        "google_maps": "apify/google-maps-scraper",
        "web_scraper": "apify/web-scraper",
        "facebook_pages": "apify/facebook-pages-scraper",
    }
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("APIFY_TOKEN")
        if not self.token:
            logger.warning("APIFY_TOKEN not set. Apify features will be disabled.")
        
        self.client = httpx.AsyncClient(
            timeout=120.0,  # Apify runs can take time
            headers={"Authorization": f"Bearer {self.token}"} if self.token else {}
        )
    
    async def _run_actor(
        self, 
        actor_id: str, 
        input_data: Dict[str, Any],
        wait_secs: int = 60,
        memory_mbytes: int = 256
    ) -> Dict[str, Any]:
        """
        Run an Apify Actor and wait for results.
        
        Args:
            actor_id: The Actor to run (e.g., 'apify/instagram-scraper')
            input_data: Input configuration for the Actor
            wait_secs: Max seconds to wait for completion
            memory_mbytes: Memory allocation (affects speed & cost)
        
        Returns:
            Dictionary with run status and dataset items
        """
        if not self.token:
            return {"error": "APIFY_TOKEN not configured", "items": []}
        
        try:
            # Start the Actor run
            run_url = f"{self.BASE_URL}/acts/{actor_id}/runs"
            
            response = await self.client.post(
                run_url,
                json=input_data,
                params={"waitForFinish": wait_secs, "memory": memory_mbytes}
            )
            
            if response.status_code != 201:
                logger.error(f"Apify run failed: {response.status_code} - {response.text}")
                return {"error": f"Actor run failed: {response.status_code}", "items": []}
            
            run_data = response.json()["data"]
            run_id = run_data["id"]
            status = run_data["status"]
            
            logger.info(f"Apify run started: {run_id} (status: {status})")
            
            # If still running, poll for completion
            if status == "RUNNING":
                run_data = await self._wait_for_run(run_id, timeout=wait_secs)
            
            # Get dataset items
            dataset_id = run_data.get("defaultDatasetId")
            if dataset_id:
                items = await self._get_dataset_items(dataset_id)
                return {
                    "run_id": run_id,
                    "status": run_data.get("status", "UNKNOWN"),
                    "items": items,
                    "stats": run_data.get("stats", {})
                }
            
            return {"run_id": run_id, "status": status, "items": []}
            
        except httpx.TimeoutException:
            logger.error("Apify request timed out")
            return {"error": "Request timed out", "items": []}
        except Exception as e:
            logger.error(f"Apify error: {e}")
            return {"error": str(e), "items": []}
    
    async def _wait_for_run(self, run_id: str, timeout: int = 60) -> Dict:
        """Poll for Actor run completion."""
        start = datetime.now()
        while (datetime.now() - start).seconds < timeout:
            response = await self.client.get(f"{self.BASE_URL}/actor-runs/{run_id}")
            if response.status_code == 200:
                data = response.json()["data"]
                if data["status"] in ["SUCCEEDED", "FAILED", "ABORTED"]:
                    return data
            await asyncio.sleep(2)
        return {"status": "TIMEOUT"}
    
    async def _get_dataset_items(self, dataset_id: str, limit: int = 100) -> List[Dict]:
        """Fetch items from a dataset."""
        url = f"{self.BASE_URL}/datasets/{dataset_id}/items"
        response = await self.client.get(url, params={"limit": limit})
        if response.status_code == 200:
            return response.json()
        return []
    
    # ============================================================
    # HIGH-LEVEL METHODS FOR SPECIFIC USE CASES
    # ============================================================
    
    async def scrape_instagram_profile(self, username: str) -> Dict[str, Any]:
        """
        Scrape an Instagram profile's public data.
        
        Returns:
            {
                "username": "nike",
                "fullName": "Nike",
                "biography": "Just Do It",
                "followersCount": 123456789,
                "followsCount": 123,
                "postsCount": 5000,
                "profilePicUrl": "https://...",
                "isVerified": true,
                "externalUrl": "https://nike.com",
                "email": "contact@nike.com" (if in bio)
            }
        """
        # Check cache first
        cache_key = f"instagram_profile:{username.lower()}"
        cached = cache.get(cache_key, cache_type="apify")
        if cached:
            logger.info(f"Cache HIT for Instagram profile: {username}")
            return cached
        
        input_data = {
            "usernames": [username],
            "resultsLimit": 1,
            "resultsType": "details"
        }
        
        result = await self._run_actor(
            self.ACTORS["instagram_profile"],
            input_data,
            wait_secs=30
        )
        
        if result.get("items"):
            profile = result["items"][0]
            return {
                "success": True,
                "profile": {
                    "username": profile.get("username"),
                    "fullName": profile.get("fullName"),
                    "biography": profile.get("biography"),
                    "followersCount": profile.get("followersCount"),
                    "followsCount": profile.get("followsCount"),
                    "postsCount": profile.get("postsCount"),
                    "profilePicUrl": profile.get("profilePicUrl"),
                    "isVerified": profile.get("isVerified", False),
                    "externalUrl": profile.get("externalUrl"),
                    "email": self._extract_email(profile.get("biography", "")),
                    "phone": self._extract_phone(profile.get("biography", ""))
                }
            }
            # Cache successful result
            cache.set(cache_key, result, cache_type="apify")
            return result
        
        return {"success": False, "error": result.get("error", "Profile not found")}
    
    async def scrape_instagram_posts(
        self, 
        username: str, 
        limit: int = 12
    ) -> Dict[str, Any]:
        """
        Scrape recent posts from an Instagram profile.
        
        Returns list of posts with:
            - imageUrl, caption, likesCount, commentsCount, timestamp
        """
        input_data = {
            "username": username,
            "resultsLimit": limit
        }
        
        result = await self._run_actor(
            self.ACTORS["instagram_posts"],
            input_data,
            wait_secs=45
        )
        
        posts = []
        for item in result.get("items", []):
            posts.append({
                "id": item.get("id"),
                "shortCode": item.get("shortCode"),
                "imageUrl": item.get("displayUrl"),
                "caption": item.get("caption", "")[:500],  # Limit caption length
                "likesCount": item.get("likesCount", 0),
                "commentsCount": item.get("commentsCount", 0),
                "timestamp": item.get("timestamp"),
                "isVideo": item.get("isVideo", False)
            })
        
        return {"success": True, "posts": posts}
    
    async def search_google_maps(
        self, 
        query: str, 
        location: str = "Brazil",
        limit: int = 20,
        min_rating: float = 0.0,
        min_reviews: int = 0
    ) -> Dict[str, Any]:
        """
        Search businesses on Google Maps.
        Great for finding companies with:
            - Name, address, phone, website
            - Reviews, ratings
            - Business hours
        
        Example:
            await client.search_google_maps("agência de marketing", "São Paulo", min_rating=4.5)
        """
        # Build cache key from parameters
        cache_key_str = f"gmaps:{query}:{location}:{limit}:{min_rating}:{min_reviews}"
        cache_key = hashlib.md5(cache_key_str.encode()).hexdigest()
        
        # Check cache first
        cached = cache.get(cache_key, cache_type="apify")
        if cached:
            logger.info(f"Cache HIT for Google Maps: {query} in {location}")
            return cached
        
        input_data = {
            "searchStringsArray": [f"{query} em {location}"],
            "maxCrawledPlacesPerSearch": limit + 10, # Request extra to account for filtering
            "language": "pt-BR",
            "includeReviews": False,  # Faster without reviews
            "maxImages": 0,
            "onlyDataFromSearchPage": True  # Faster
        }
        
        result = await self._run_actor(
            self.ACTORS["google_maps"],
            input_data,
            wait_secs=90,  # Maps scraping takes longer
            memory_mbytes=512
        )
        
        businesses = []
        for item in result.get("items", []):
            rating = item.get("totalScore") or 0
            reviews = item.get("reviewsCount") or 0
            
            # Filter Logic
            if rating < min_rating:
                continue
            if reviews < min_reviews:
                continue
                
            businesses.append({
                "name": item.get("title"),
                "address": item.get("address"),
                "phone": item.get("phone"),
                "website": item.get("website"),
                "rating": rating,
                "reviewsCount": reviews,
                "category": item.get("categoryName"),
                "placeId": item.get("placeId"),
                "url": item.get("url")
            })
        
        # Trim to requested limit after filtering
        result = {"success": True, "businesses": businesses[:limit]}
        
        # Cache successful result
        cache.set(cache_key, result, cache_type="apify")
        return result
    
    async def scrape_website(
        self, 
        url: str,
        selectors: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Generic web scraper for any URL.
        
        Args:
            url: The page to scrape
            selectors: CSS selectors to extract (optional)
        """
        input_data = {
            "startUrls": [{"url": url}],
            "pageFunction": """
                async function pageFunction(context) {
                    const $ = context.jQuery;
                    return {
                        title: $('title').text(),
                        h1: $('h1').first().text(),
                        description: $('meta[name="description"]').attr('content'),
                        html: $('body').html().substring(0, 50000)
                    };
                }
            """
        }
        
        result = await self._run_actor(
            self.ACTORS["web_scraper"],
            input_data,
            wait_secs=30
        )
        
        if result.get("items"):
            return {"success": True, "data": result["items"][0]}
        
        return {"success": False, "error": result.get("error", "Scrape failed")}
    
    # ============================================================
    # UTILITY METHODS
    # ============================================================
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email from text (bio)."""
        import re
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        match = re.search(pattern, text or "")
        return match.group(0) if match else None
    
    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract Brazilian phone from text."""
        import re
        # Padrão BR: (11) 99999-9999 ou 11999999999
        patterns = [
            r'\(\d{2}\)\s*\d{4,5}-?\d{4}',
            r'\d{2}\s*\d{4,5}-?\d{4}',
            r'\+55\s*\d{2}\s*\d{4,5}-?\d{4}'
        ]
        for pattern in patterns:
            match = re.search(pattern, text or "")
            if match:
                return match.group(0)
        return None
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get Apify account info and usage stats."""
        if not self.token:
            return {"error": "APIFY_TOKEN not configured"}
        
        response = await self.client.get(f"{self.BASE_URL}/users/me")
        if response.status_code == 200:
            data = response.json()["data"]
            return {
                "success": True,
                "username": data.get("username"),
                "email": data.get("email"),
                "plan": data.get("plan"),
                "usedCredits": data.get("usedCredits"),
                "monthlyUsage": data.get("monthlyUsage", {})
            }
        return {"success": False, "error": "Failed to fetch account info"}
        
    async def is_healthy(self) -> bool:
        """Check if Apify service is reachable and quota is available."""
        try:
            # Check user info (lightweight call)
            result = await self.get_account_info()
            return result.get("success", False)
        except Exception as e:
            logger.error(f"Apify health check failed: {e}")
            return False
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton instance
_apify_client: Optional[ApifyClient] = None

def get_apify_client() -> ApifyClient:
    """Get or create the Apify client singleton."""
    global _apify_client
    if _apify_client is None:
        _apify_client = ApifyClient()
    return _apify_client
