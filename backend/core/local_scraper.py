"""
Local Scraper
LeadHunter AI - Zero Cost Data Collection

Uses Playwright to scrape data directly from the browser.
This is the primary fallback when Apify is unavailable or to save costs.
"""
import asyncio
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Page, Browser
from backend.utils.logger import logger
import urllib.parse

class LocalScraper:
    """
    Scraper running locally via Playwright.
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        
    async def _get_browser(self, p):
        """Configure browser with stealth settings."""
        browser = await p.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )
        return browser
        
    async def scrape_instagram_profile(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Scrape public Instagram profile data.
        Note: Instagram has strict anti-scraping. This is a best-effort implementation.
        """
        url = f"https://www.instagram.com/{username}/"
        
        async with async_playwright() as p:
            browser = await self._get_browser(p)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = await context.new_page()
            
            try:
                logger.info(f"Navigating to {url}")
                await page.goto(url, wait_until="networkidle", timeout=15000)
                
                # Check for login wall or error
                if "Login" in await page.title():
                    logger.warning("Instagram login wall detected")
                    return None
                    
                # Extract meta tags (OpenGraph)
                data = await page.evaluate("""() => {
                    const getMeta = (name) => {
                        const meta = document.querySelector(`meta[property='og:${name}']`);
                        return meta ? meta.content : null;
                    };
                    
                    const desc = getMeta('description') || '';
                    // Format: "100 Followers, 50 Following, 10 Posts - ..."
                    const stats = desc.split('-')[0].trim(); 
                    
                    return {
                        title: getMeta('title'),
                        description: getMeta('description'),
                        image: getMeta('image'),
                        url: getMeta('url'),
                        stats: stats
                    };
                }""")
                
                # Parse stats if possible
                followers = 0
                following = 0
                
                if data['stats']:
                    parts = data['stats'].split(',')
                    for part in parts:
                        if 'Followers' in part:
                            # Basic parsing, likely needs regex for K/M suffixes
                            followers = part.replace('Followers', '').strip()
                        elif 'Following' in part:
                            following = part.replace('Following', '').strip()
                            
                return {
                    "username": username,
                    "fullName": data.get('title', '').split('(@')[0].strip(),
                    "biography": data.get('description'),
                    "followersCount": followers, # Raw string for now
                    "followingCount": following, # Raw string for now
                    "profilePicUrl": data.get('image'),
                    "externalUrl": data.get('url'),
                    "isPrivate": False, # Assumption
                    "isVerified": False # Hard to tell from meta
                }
                
            except Exception as e:
                logger.error(f"Error scraping Instagram {username}: {e}")
                return None
            finally:
                await browser.close()
                
    async def search_google_maps(self, query: str, location: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search Google Maps via direct scraping.
        """
        search_query = f"{query} in {location}"
        encoded_query = urllib.parse.quote(search_query)
        url = f"https://www.google.com/maps/search/{encoded_query}"
        
        results = []
        
        async with async_playwright() as p:
            browser = await self._get_browser(p)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="pt-BR"
            )
            page = await context.new_page()
            
            try:
                logger.info(f"Navigating to {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                
                # Wait for results to load (scroll panel)
                try:
                    await page.wait_for_selector('div[role="feed"]', timeout=5000)
                except:
                    logger.warning("Could not find results feed")
                    
                # Scroll to load more items
                # ... (Simplified for this version)
                
                # Extract items
                # Note: Google Maps classes are obfuscated and change often. 
                # This is a fragile implementation that might need constant updates.
                # Relying on aria-labels or roles is safer.
                
                items = await page.evaluate("""() => {
                    const results = [];
                    const articles = document.querySelectorAll('div[role="article"]');
                    
                    articles.forEach(article => {
                        if (!article.ariaLabel) return;
                        
                        const text = article.innerText;
                        const phone = (text.match(/\\(?\\d{2}\\)?\\s?\\d{4,5}-?\\d{4}/) || [])[0];
                        const website = null; // Hard to extract easily without clicking
                        
                        results.push({
                            title: article.ariaLabel,
                            address: text.split('\\n')[1] || '', // Heuristic
                            phone: phone,
                            website: website,
                            url: article.querySelector('a')?.href
                        });
                    });
                    
                    return results;
                }""")
                
                # Filter and limit
                for item in items[:limit]:
                    results.append(item)
                    
            except Exception as e:
                logger.error(f"Error searching maps: {e}")
            finally:
                await browser.close()
                
        return results
