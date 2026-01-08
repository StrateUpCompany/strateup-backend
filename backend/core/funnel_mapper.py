import asyncio
import re
from urllib.parse import urljoin, urlparse
from backend.core.browser import BrowserManager
from backend.utils.logger import logger

class FunnelMapper:
    """
    Engenharia Reserva de Funis:
    Navega página por página, identifica botões de compra/próximo e mapeia o fluxo.
    """
    def __init__(self, start_url, max_steps=5):
        self.start_url = start_url
        self.max_steps = max_steps
        self.browser_manager = BrowserManager(headless=True)
        self.funnel_map = []
        self.visited_urls = set()

    async def map_funnel(self):
        """Executa o mapeamento do funil"""
        logger.info(f"Iniciando mapeamento de funil: {self.start_url}")
        await self.browser_manager.start()
        
        try:
            current_url = self.start_url
            for step in range(1, self.max_steps + 1):
                if current_url in self.visited_urls:
                    logger.info(f"Ciclo detectado ou URL já visitada: {current_url}")
                    break
                
                self.visited_urls.add(current_url)
                logger.info(f"Analisando passo {step}: {current_url}")
                
                page_data = await self._analyze_page(current_url, step)
                self.funnel_map.append(page_data)
                
                # Tenta encontrar o próximo passo (URL do botão de compra)
                next_url = page_data.get('next_step_url')
                if next_url:
                    current_url = next_url
                else:
                    logger.info("Fim do funil ou link não encontrado.")
                    break
                    
        except Exception as e:
            logger.error(f"Erro no mapeamento de funil: {e}")
        finally:
            await self.browser_manager.stop()
            
        return self.funnel_map

    async def _analyze_page(self, url, step_number):
        """Analisa uma única página do funil"""
        page = await self.browser_manager.new_page()
        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000) # Espera scripts carregarem
            
            # 1. Extrai Título
            title = await page.title()
            
            # 2. Tech Stack Spy
            content = await page.content()
            tech_stack = self._analyze_tech_stack(content)
            
            # 3. Price Discovery
            prices_found = self._extract_prices(content)
            
            # 3. Busca botões de CTA (Call to Action)
            # Procura links que parecem ser "Próximo Passo" ou "Comprar"
            # Estratégia: Pegar links dentro de botões ou com classes/textos específicos
            next_url = None
            
            # Seletores comuns de checkout/próximo
            selectors = [
                "a[href*='checkout']", "a[href*='cart']", "a[href*='pay']",
                "a:has-text('Comprar')", "a:has-text('Buy')", 
                "a:has-text('Sim')", "a:has-text('Yes')",
                "button:has-text('Comprar')", "#submit-button" # Botões as vezes tem onclick, mais complexo
            ]
            
            found_ctas = []
            
            for sel in selectors:
                elements = await page.query_selector_all(sel)
                for el in elements:
                    href = await el.get_attribute('href')
                    text = await el.inner_text()
                    if href and href not in ['#', '', 'javascript:void(0)']:
                        full_url = urljoin(url, href)
                        # Filtra links internos de navegação (ex: #about)
                        if urlparse(full_url).path != urlparse(url).path:
                            found_ctas.append({'text': text.strip(), 'url': full_url})
            
            # Heurística: O primeiro link de checkout encontrado costuma ser o principal
            if found_ctas:
                # Prioriza links que saem do domínio atual (ex: ir para hotmart/stripe) 
                # OU que mudam significativamente o path
                next_url = found_ctas[0]['url']
                logger.info(f"CTA detectado: {found_ctas[0]['text']} -> {next_url}")

            return {
                "step": step_number,
                "url": url,
                "title": title,
                "tech_stack": tech_stack,
                "prices_detected": prices_found,
                "ctas_found": found_ctas,
                "next_step_url": next_url
            }

        except Exception as e:
            logger.error(f"Erro ao analisar página {url}: {e}")
            return {"step": step_number, "url": url, "error": str(e)}
        finally:
            await page.close()

    def _analyze_tech_stack(self, html_content):
        """Detecta tecnologias usadas na página"""
        stack = {
            "platform": "Custom/Unknown",
            "pixels": [],
            "video_player": "None",
            "builders": []
        }
        
        lower_html = html_content.lower()
        
        # Platforms / CMS
        if "wp-content" in lower_html: stack['platform'] = "WordPress"
        elif "shopify" in lower_html: stack['platform'] = "Shopify"
        elif "clickfunnels" in lower_html: stack['platform'] = "ClickFunnels"
        elif "hotmart" in lower_html: stack['platform'] = "Hotmart"
        elif "kiwify" in lower_html: stack['platform'] = "Kiwify"
        elif "ticto" in lower_html: stack['platform'] = "Ticto"
        elif "nuvemshop" in lower_html: stack['platform'] = "Nuvemshop"
        elif "wix" in lower_html: stack['platform'] = "Wix"
        
        # Builders
        if "elementor" in lower_html: stack['builders'].append("Elementor")
        if "divi" in lower_html: stack['builders'].append("Divi")
        if "gutenberg" in lower_html: stack['builders'].append("Gutenberg")
        
        # Pixels
        if "fbevents.js" in lower_html: stack['pixels'].append("Meta Pixel")
        if "googletagmanager" in lower_html: stack['pixels'].append("GTM")
        if "analytics.js" in lower_html or "gtag" in lower_html: stack['pixels'].append("Google Analytics")
        if "tiktok" in lower_html and "pixel" in lower_html: stack['pixels'].append("TikTok Pixel")
        if "clarity" in lower_html: stack['pixels'].append("MS Clarity")
        if "hotjar" in lower_html: stack['pixels'].append("Hotjar")
        
        # Video Players
        if "vturb" in lower_html: stack['video_player'] = "Vturb"
        elif "pandavideo" in lower_html: stack['video_player'] = "PandaVideo"
        elif "vimeo" in lower_html: stack['video_player'] = "Vimeo"
        elif "youtube" in lower_html: stack['video_player'] = "YouTube"
        elif "wistia" in lower_html: stack['video_player'] = "Wistia"
        
        return stack

    def _extract_prices(self, text):
        """Extrai possíveis preços usando Regex"""
        # Procura padrões como R$ 97,00 ou 12x R$ 9,90
        prices = set()
        # Regex para moeda BRL
        brl_matches = re.findall(r'R\$\s?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)', text)
        for p in brl_matches:
            prices.add(f"R$ {p}")
            
        return list(prices)[:3]
