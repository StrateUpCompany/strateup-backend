"""
Scraper Manager
LeadHunter AI - Data Collection Orchestrator

Unified interface for scraping data from multiple sources (Local, Apify, BrightData).
Implements fallback logic and circuit breaking.
"""
import asyncio
from typing import Optional, Dict, Any, List
from backend.utils.logger import logger
from backend.core.apify_client import get_apify_client
# Will import LocalScraper and BrightDataClient later to avoid circular imports if needed

class ScraperManager:
    """
    Orchestrates data collection across multiple providers.
    
    Priority:
    1. Local Scraper (Free, Fast, Playwright)
    2. Apify (Paid, API-based, Reliable)
    3. BrightData (Backup, Enterprise)
    """
    
    def __init__(self):
        self.apify = get_apify_client()
        self.local = None # Lazy load
        self.bright_data = None # Lazy load
        
        # Stats
        self.stats = {
            "local_hits": 0,
            "apify_hits": 0,
            "failed": 0
        }

    async def _get_local_scraper(self):
        """Lazy load local scraper to avoid heavy startup if not needed."""
        if not self.local:
            try:
                from backend.core.local_scraper import LocalScraper
                self.local = LocalScraper()
            except ImportError as e:
                logger.warning(f"Could not import LocalScraper: {e}")
                return None
        return self.local

    async def scrape_instagram_profile(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Scrape Instagram profile using fallback chain.
        """
        # 1. Try Local First (Zero Cost)
        local = await self._get_local_scraper()
        if local:
            try:
                logger.info(f"Attempting local scrape for {username}")
                result = await local.scrape_instagram_profile(username)
                if result:
                    self.stats["local_hits"] += 1
                    return result
            except Exception as e:
                logger.warning(f"Local scrape failed for {username}: {e}")
        
        # 2. Fallback to Apify
        try:
            logger.info(f"Fallback to Apify for {username}")
            if self.apify:
                result = await self.apify.scrape_instagram_profile(username)
                if result:
                    self.stats["apify_hits"] += 1
                    return result
        except Exception as e:
            logger.error(f"Apify scrape failed for {username}: {e}")
            
        self.stats["failed"] += 1
        return None

    async def search_google_maps(self, query: str, location: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search Google Maps using fallback chain.
        """
        # 1. Try Local
        local = await self._get_local_scraper()
        if local:
            try:
                logger.info(f"Attempting local maps search for {query} in {location}")
                result = await local.search_google_maps(query, location, limit)
                if result:
                    self.stats["local_hits"] += 1
                    return result
            except Exception as e:
                logger.warning(f"Local maps search failed: {e}")

        # 2. Fallback to Apify
        try:
            logger.info(f"Fallback to Apify maps search")
            if self.apify:
                result = await self.apify.search_google_maps(query, location, limit)
                if result:
                    self.stats["apify_hits"] += 1
                    return result
        except Exception as e:
            logger.error(f"Apify maps search failed: {e}")

        self.stats["failed"] += 1
        return []

# Singleton instance
scraper_manager = ScraperManager()
