import os
import requests
import time
import logging
import json
import asyncio
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from backend.core.event_bus import EventBus
from backend.core.seo import SEOAnalyzer
from backend.utils.logger import logger
from backend.utils.config import Config
from backend.core.funnel_mapper import FunnelMapper
from backend.core.supabase_manager import SupabaseManager

# Lazy imports to avoid heavy deps on Vercel
# from backend.core.browser import BrowserManager
# from backend.core.recursive_crawler import RecursiveCrawler
# from backend.core.visualizer import FunnelVisualizer
# from backend.core.form_hijacker import FormHijacker

class CloneEngine:
    """
    Motor de clonagem agnóstico a framework de UI.
    Emite eventos via EventBus.
    """
    def __init__(self, url, options=None, project_id=None):
        self.url = url
        self.options = options or {}
        self.stop_requested = False
        self.session_manager = SupabaseManager()
        self.project_id = project_id # Se fornecido, é um re-clone

        # Defaults
        defaults = {
            'baixar_imagens': True, 'baixar_css': True, 'baixar_js': True,
            'respeitar_robots': True, 'delay_entre_requisicoes': 0.5,
            'max_recursos': 100, 'timeout': 30, 'pasta_destino': '',
            'modo_funnel': False, 'modo_recursivo': False, 'depth': 3
        }
        for k, v in defaults.items():
            self.options.setdefault(k, v)

    def run(self):
        """Ponto de entrada principal (síncrono/bloqueante)"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        mode = "STATIC"
        if self.options['modo_recursivo']: mode = "RECURSIVE"
        elif self.options['modo_funnel']: mode = "FUNNEL"
        else: mode = "STATIC"
        
        if self.project_id:
            logger.info(f"Re-utilizando Project ID: {self.project_id}")
            self.current_session_id = self.project_id
        else:
            self.current_session_id = self.session_manager.create_project(self.url, mode)
        
        try:
            if self.options['modo_recursivo']:
                 self.run_recursive()
            elif self.options['modo_funnel']:
                loop.run_until_complete(self.run_funnel_hacking())
            else:
                loop.run_until_complete(self.run_static_clone())
        except Exception as e:
            logger.error(f"Erro critical na engine: {e}")
            self.session_manager.update_project(self.current_session_id, "ERROR", error=str(e))
            EventBus.emit("error", str(e))
        finally:
            loop.close()

    def run_recursive(self):
        pasta_base = self.options['pasta_destino'] or os.path.join(os.path.expanduser("~"), 'Desktop', 'clones', f"full_{urlparse(self.url).netloc}")
        
        def progress_callback(msg, val=0):
            EventBus.emit("update", {"msg": msg, "val": val})

        # Lazy Import
        from backend.core.recursive_crawler import RecursiveCrawler

        crawler = RecursiveCrawler(
            self.url, 
            max_depth=self.options['depth'], 
            save_dir=pasta_base,
            update_callback=progress_callback
        )
        crawler.run()
        
        result_data = {
            'message': f"Clonagem Completa finalizada em: {pasta_base}",
            'path': pasta_base,
            'url': self.url
        }
        EventBus.emit("cloning_success", result_data)
        self.session_manager.update_project(self.current_session_id, "COMPLETED", local_path=pasta_base)
        EventBus.emit("finished", result_data['message'])

    async def run_funnel_hacking(self):
        EventBus.emit("update", {"msg": "Iniciando Funnel Hacking (Playwright)...", "val": 5})
        mapper = FunnelMapper(self.url)
        
        EventBus.emit("update", {"msg": "Mapeando funil e passos...", "val": 20})
        funnel_map = await mapper.map_funnel()
        
        if not funnel_map:
            self.session_manager.update_project(self.current_session_id, "ERROR", error="Failed to map funnel")
            EventBus.emit("error", "Não foi possível mapear o funil.")
            return

        pasta_base = self.options['pasta_destino'] or os.path.join(os.path.expanduser("~"), 'Desktop', 'clones', f"funnel_{int(time.time())}")
        os.makedirs(pasta_base, exist_ok=True)
        
        with open(os.path.join(pasta_base, 'funnel_map.json'), 'w') as f:
            json.dump(funnel_map, f, indent=4)
        
        # Lazy Imports
        from backend.core.browser import BrowserManager
        from backend.core.visualizer import FunnelVisualizer
        from backend.core.form_hijacker import FormHijacker

        browser = BrowserManager(headless=True)
        await browser.start()
        
        try:
            total_steps = len(funnel_map)
            for i, step in enumerate(funnel_map):
                if self.stop_requested: break
                
                step_url = step['url']
                step_num = step['step']
                EventBus.emit("update", {"msg": f"Clonando passo {step_num}/{total_steps}: {step_url}", "val": 30 + int((i/total_steps)*60)})
                
                content = await browser.get_page_content(step_url)
                
                step_folder = os.path.join(pasta_base, f"step_{step_num}")
                os.makedirs(step_folder, exist_ok=True)
                
                # HACKER MODE: Form Hijacking
                if self.options.get('hijack_mode', True):
                    try:
                        api_url = os.environ.get("API_URL", "http://localhost:8000")
                        hijacker = FormHijacker(str(self.current_session_id), api_url)
                        content = hijacker.process_html(content)
                    except Exception as e:
                        logger.error(f"Hijack Error: {e}")

                with open(os.path.join(step_folder, "index.html"), "w", encoding="utf-8") as f:
                    f.write(content)
            
            # Gera Visualização
            visualizer = FunnelVisualizer(funnel_map)
            visualizer.generate_html(os.path.join(pasta_base, "funnel_graph.html"))
            
            result_data = {
                'message': f"Funnel Hacking concluído em: {pasta_base}",
                'path': pasta_base,
                'url': self.url
            }
            EventBus.emit("cloning_success", result_data)
            self.session_manager.update_project(self.current_session_id, "COMPLETED", local_path=pasta_base)
            EventBus.emit("finished", result_data['message'])
            
        finally:
            await browser.stop()

    async def run_static_clone(self):
        if self.options.get('use_headless'):
            await self._run_smart_clone()
        else:
            # Run sync method in executor to avoid blocking loop if needed, 
            # but for now we can just call it (simplification)
            # Better: wrap in run_in_executor if heavy.
            # actually _run_static_sync is blocking.
            await asyncio.to_thread(self._run_static_sync)

    async def _run_smart_clone(self):
        if not self.url.startswith(('http://', 'https://')): self.url = 'http://' + self.url
        dominio = urlparse(self.url).netloc
        pasta_base = self.options['pasta_destino'] or os.path.join(os.path.expanduser("~"), 'Desktop', 'clones', f"clone_{dominio}_smart")
        
        pastas = {k: os.path.join(pasta_base, k) if k != 'main' else pasta_base for k in ['main', 'images', 'css', 'js', 'seo']}
        for p in pastas.values(): os.makedirs(p, exist_ok=True)

        EventBus.emit("update", {"msg": "Initializing Neural Browser (Smart Clone)...", "val": 10})
        
        browser = BrowserManager(headless=True)
        await browser.start()
        
        try:
            EventBus.emit("update", {"msg": "Rendering Full DOM & Styles...", "val": 30})
            # Playwright renders the page
            content = await browser.get_page_content(self.url)
            
            # TODO: We could use specific scroll actions here to lazy load images
            
            soup = BeautifulSoup(content, 'html.parser')

            EventBus.emit("update", {"msg": "Analyzed Rendered Structure", "val": 50})
            seo = SEOAnalyzer(soup, self.url)
            EventBus.emit("seo_data", seo.analyze_all())
            seo.generate_seo_report(os.path.join(pastas['seo'], "relatorio_seo.html"))

            EventBus.emit("update", {"msg": "Extracting computed assets...", "val": 70})
            self._download_resources(soup, pastas)

            with open(os.path.join(pasta_base, "index.html"), "w", encoding="utf-8") as f:
                f.write(soup.prettify())

            result_data = {
                'message': f"Smart Clone concluído em: {pasta_base}",
                'path': pasta_base,
                'url': self.url
            }
            EventBus.emit("cloning_success", result_data)
            self.session_manager.update_project(self.current_session_id, "COMPLETED", local_path=pasta_base)
            EventBus.emit("finished", result_data['message'])

        finally:
            await browser.stop()

    def _run_static_sync(self):
        if not self.url.startswith(('http://', 'https://')): self.url = 'http://' + self.url
        dominio = urlparse(self.url).netloc
        pasta_base = self.options['pasta_destino'] or os.path.join(os.path.expanduser("~"), 'Desktop', 'clones', f"clone_{dominio}")
        
        pastas = {k: os.path.join(pasta_base, k) if k != 'main' else pasta_base for k in ['main', 'images', 'css', 'js', 'seo']}
        for p in pastas.values(): os.makedirs(p, exist_ok=True)

        EventBus.emit("update", {"msg": "Acessando site (Estático)...", "val": 10})
        resp = requests.get(self.url, headers=Config.get_headers(), timeout=self.options['timeout'])
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        EventBus.emit("update", {"msg": "Analisando SEO...", "val": 30})
        seo = SEOAnalyzer(soup, self.url)
        EventBus.emit("seo_data", seo.analyze_all())
        seo.generate_seo_report(os.path.join(pastas['seo'], "relatorio_seo.html"))

        EventBus.emit("update", {"msg": "Baixando recursos...", "val": 50})
        
        # Download Resources
        self._download_resources(soup, pastas)

        with open(os.path.join(pasta_base, "index.html"), "w", encoding="utf-8") as f:
            f.write(soup.prettify())

        result_data = {
            'message': f"Clonagem Estática concluída em: {pasta_base}",
            'path': pasta_base,
            'url': self.url
        }
        EventBus.emit("cloning_success", result_data)
        self.session_manager.update_project(self.current_session_id, "COMPLETED", local_path=pasta_base)
        EventBus.emit("finished", result_data['message'])
            
    def _download_resources(self, soup, pastas):
        """Baixa imagens, css, js, video posters e background-images."""
        from urllib.parse import urljoin, unquote
        import re

        # Helper para download
        def download_file(url, folder, tag=None, attr=None):
            """
            Baixa arquivo e retorna caminho relativo local.
            Se tag e attr forem fornecidos, atualiza o attributo da tag.
            """
            if not url or url.startswith('data:') or url.startswith('#'): return None
            
            # Clean URL (remove func calls like url('...'))
            clean_url = url.strip().strip("'").strip('"')
            
            # Resolve URL relative to base
            full_url = urljoin(self.url, clean_url)
            
            # Clean filename
            path_no_query = urlparse(full_url).path
            filename = os.path.basename(path_no_query)
            
            # Fallback
            if not filename or not re.match(r'^[\w\-. ]+$', filename): 
                ext = path_no_query.split('.')[-1] if '.' in path_no_query else 'file'
                if len(ext) > 4: ext = 'bin'
                filename = f"res_{int(time.time()*1000)}_{len(os.listdir(folder))}.{ext}"
            
            local_path = os.path.join(folder, filename)
            rel_path = os.path.relpath(local_path, pastas['main'])

            try:
                # Evita re-download
                if os.path.exists(local_path):
                    if tag and attr: tag[attr] = rel_path
                    return rel_path

                # Download
                res = requests.get(full_url, headers=Config.get_headers(), timeout=15)
                if res.status_code == 200:
                    with open(local_path, 'wb') as f:
                        f.write(res.content)
                    logger.info(f"Downloaded: {filename}")
                    
                    if tag and attr: tag[attr] = rel_path
                    return rel_path
                else:
                    logger.warning(f"Failed {res.status_code}: {full_url}")
                    return None
            except Exception as e:
                logger.warning(f"Error downloading {full_url}: {e}")
                return None

        # 1. Imagens (src)
        if self.options.get('baixar_imagens'):
            for img in soup.find_all('img'):
                download_file(img.get('src'), pastas['images'], img, 'src')
                
                # Handle srcset
                if img.get('srcset'):
                    try:
                        parts = img['srcset'].split(',')
                        new_parts = []
                        for part in parts:
                            p = part.strip().split()
                            if not p: continue
                            url = p[0]
                            desc = " ".join(p[1:]) if len(p) > 1 else ""
                            
                            local = download_file(url, pastas['images'])
                            if local:
                                new_parts.append(f"{local} {desc}")
                            else:
                                new_parts.append(part.strip()) # Keep original if fail
                        img['srcset'] = ", ".join(new_parts)
                    except Exception as e:
                        logger.warning(f"Error parsing srcset: {e}")

            # 2. Source tags (picture/video)
            for source in soup.find_all('source'):
                if source.get('srcset'):
                     # Simple download of first url if comma separated, 
                     # complex parsing for source is similar to img
                     # For brevity, treating entire srcset as one URL often fails.
                     # Let's match img logic roughly or just pick first for now? 
                     # Better: parse properly.
                     try:
                        parts = source['srcset'].split(',')
                        new_parts = []
                        for part in parts:
                            p = part.strip().split()
                            if not p: continue
                            url = p[0]
                            desc = " ".join(p[1:]) if len(p) > 1 else ""
                            local = download_file(url, pastas['images'])
                            if local: new_parts.append(f"{local} {desc}")
                            else: new_parts.append(part.strip())
                        source['srcset'] = ", ".join(new_parts)
                     except: pass

            # 3. Video Poster
            for video in soup.find_all('video'):
                download_file(video.get('poster'), pastas['images'], video, 'poster')

            # 4. Inline Background Images
            # Regex to find url('...')
            url_pattern = re.compile(r'url\([\'"]?(.*?)[\'"]?\)')
            for tag in soup.find_all(style=True):
                style = tag['style']
                if 'url(' in style:
                    def replace_url(match):
                        url = match.group(1)
                        if url.startswith('data:'): return match.group(0)
                        local = download_file(url, pastas['images'])
                        return f"url('{local}')" if local else match.group(0)
                    
                    new_style = url_pattern.sub(replace_url, style)
                    tag['style'] = new_style

        # 5. CSS
        if self.options.get('baixar_css'):
            for link in soup.find_all('link'):
                rel = link.get('rel', [])
                if isinstance(rel, str): rel = [rel]
                if 'stylesheet' in rel or ('preload' in rel and link.get('as') == 'style'):
                    download_file(link.get('href'), pastas['css'], link, 'href')

        # 6. JS
        if self.options.get('baixar_js'):
            for script in soup.find_all('script'):
                download_file(script.get('src'), pastas['js'], script, 'src')
            
            
    def stop(self):
        self.stop_requested = True
