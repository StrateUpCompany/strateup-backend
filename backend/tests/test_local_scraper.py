"""
Local Scraper Tests
LeadHunter AI - Testing local data collection

Tests for:
- Playwright integration (mocked)
- Parsing logic
- Error handling
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from backend.core.local_scraper import LocalScraper

# =============================================================================
# LOCAL SCRAPER TESTS
# =============================================================================

class TestLocalScraper:
    """Tests for LocalScraper class."""
    
    @pytest.mark.asyncio
    async def test_init(self):
        """Should initialize with options."""
        scraper = LocalScraper(headless=True)
        assert scraper.headless is True
        
        scraper_visible = LocalScraper(headless=False)
        assert scraper_visible.headless is False

    @pytest.mark.asyncio
    async def test_scrape_instagram_profile_success(self):
        """Should scrape instagram profile successfully."""
        scraper = LocalScraper()
        
        # Mock playwright
        with patch("backend.core.local_scraper.async_playwright") as mock_playwright:
            # Setup mock chain
            mock_context = AsyncMock()
            mock_playwright.return_value.__aenter__.return_value = mock_context
            
            mock_browser = AsyncMock()
            mock_context.chromium.launch.return_value = mock_browser
            
            mock_page = AsyncMock()
            mock_browser_context = AsyncMock()
            mock_browser.new_context.return_value = mock_browser_context
            mock_browser_context.new_page.return_value = mock_page
            
            # Mock page actions
            mock_page.title.return_value = "Nike (@nike) • Instagram photos and videos"
            mock_page.evaluate.return_value = {
                "title": "Nike (@nike)",
                "description": "300M Followers, 100 Following, 5000 Posts - See Instagram photos and videos from Nike (@nike)",
                "image": "https://example.com/pic.jpg",
                "url": "https://instagram.com/nike",
                "stats": "300M Followers, 100 Following, 5000 Posts"
            }
            
            result = await scraper.scrape_instagram_profile("nike")
            
            assert result is not None
            assert result["username"] == "nike"
            assert result["followersCount"] == "300M" # Raw parsing
            assert result["profilePicUrl"] == "https://example.com/pic.jpg"

    @pytest.mark.asyncio
    async def test_scrape_instagram_login_wall(self):
        """Should detect login wall."""
        scraper = LocalScraper()
        
        with patch("backend.core.local_scraper.async_playwright") as mock_playwright:
            mock_context = AsyncMock()
            mock_playwright.return_value.__aenter__.return_value = mock_context
            mock_browser = AsyncMock()
            mock_context.chromium.launch.return_value = mock_browser
            mock_page = AsyncMock()
            mock_browser.new_context.return_value.new_page.return_value = mock_page
            
            # Mock login wall
            mock_page.title.return_value = "Login • Instagram"
            
            result = await scraper.scrape_instagram_profile("nike")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_search_google_maps_success(self):
        """Should search google maps successfully."""
        scraper = LocalScraper()
        
        with patch("backend.core.local_scraper.async_playwright") as mock_playwright:
            mock_context = AsyncMock()
            mock_playwright.return_value.__aenter__.return_value = mock_context
            mock_browser = AsyncMock()
            mock_context.chromium.launch.return_value = mock_browser
            mock_page = AsyncMock()
            mock_browser.new_context.return_value.new_page.return_value = mock_page
            
            # Mock evaluate returning list
            mock_page.evaluate.return_value = [
                {
                    "title": "Pizza Place",
                    "address": "Main St, 123",
                    "phone": "(11) 9999-9999",
                    "url": "https://maps.google.com/..."
                }
            ]
            
            results = await scraper.search_google_maps("pizza", "sp")
            
            assert len(results) == 1
            assert results[0]["title"] == "Pizza Place"
