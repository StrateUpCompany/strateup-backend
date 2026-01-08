import asyncio
from playwright.async_api import async_playwright
from backend.utils.logger import logger

class BrowserManager:
    """Gerencia a instância do navegador Playwright"""
    def __init__(self, headless=True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None

    async def start(self):
        """Inicia o navegador"""
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            logger.info("Browser iniciado com sucesso.")

    async def new_page(self):
        """Cria uma nova página/aba"""
        if not self.context:
            await self.start()
        return await self.context.new_page()

    async def stop(self):
        """Fecha o navegador com limpeza robusta"""
        try:
            if self.context:
                await self.context.close()
        except Exception as e:
            logger.warning(f"Erro fechando context: {e}")
            
        try:
            if self.browser:
                await self.browser.close()
        except Exception as e:
            logger.warning(f"Erro fechando browser: {e}")
            
        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.warning(f"Erro parando playwright: {e}")
        
        self.playwright = None
        self.browser = None
        self.context = None
        logger.info("Browser fechado.")

    async def get_page_content(self, url, wait_for_network_idle=True):
        """Navega para uma URL e retorna o conteúdo HTML renderizado"""
        page = await self.new_page()
        try:
            # Bloqueia recursos desnecessários para acelerar
            await page.route("**/*", lambda route: route.abort() 
                             if route.request.resource_type in ["image", "media", "font"] 
                             else route.continue_())
            
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
            if wait_for_network_idle:
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except:
                    pass # Timeout no networkidle é comum, segue o fluxo
            
            # Scroll para carregar lazy loading
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)
            
            content = await page.content()
            return content
        except Exception as e:
            logger.error(f"Erro ao carregar página {url}: {e}")
            raise
        finally:
            await page.close()
