import os
import time
import requests
import urllib.parse
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from backend.utils.logger import logger
from urllib.parse import urljoin, urlparse

class RecursiveCrawler:
    def __init__(self, start_url, max_depth=3, save_dir="clones", update_callback=None):
        self.start_url = start_url
        self.max_depth = max_depth
        self.save_dir = save_dir
        self.update_callback = update_callback
        
        self.visited = set()
        self.to_visit = [(start_url, 0)]  # (url, depth)
        self.domain = urlparse(start_url).netloc
        self.session = requests.Session()
        from backend.utils.config import Config
        self.session.headers.update(Config.get_headers())

    def run(self):
        """Executa o crawling recursivo BFS"""
        if self.update_callback:
            self.update_callback("Iniciando modo recursivo...", 0)
            
        while self.to_visit:
            current_url, depth = self.to_visit.pop(0)
            
            if current_url in self.visited:
                continue
            
            if depth > self.max_depth:
                continue
                
            self.visited.add(current_url)
            
            try:
                self._process_page(current_url, depth)
            except Exception as e:
                logger.error(f"Erro ao processar {current_url}: {e}")
                
            # Atualiza progresso visual (estimado)
            if self.update_callback:
                self.update_callback(f"Clonando (Profundidade {depth}): {current_url}", 0)

    def _process_page(self, url, depth):
        logger.info(f"Baixando: {url}")
        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Salvar HTML
        self._save_html(url, soup)
        
        # Se atingiu limite, não busca mais links
        if depth >= self.max_depth:
            return

        # Encontrar links internos
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            full_url = urljoin(url, href)
            
            # Remove fragmentos (#)
            full_url = full_url.split('#')[0]
            
            # Verifica se é interno e não visitado
            if self._is_internal(full_url) and full_url not in self.visited:
                 self.to_visit.append((full_url, depth + 1))

    def _is_internal(self, url):
        return urlparse(url).netloc == self.domain

    def _save_html(self, url, soup):
        parsed = urlparse(url)
        path = parsed.path
        
        if path.endswith('/'):
            path += 'index.html'
        elif not os.path.splitext(path)[1]:
            path += '/index.html'
            
        # Remove barra inicial para os.path.join funcionar
        if path.startswith('/'):
            path = path[1:]
            
        local_path = os.path.join(self.save_dir, path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        # Reescrever links para funcionar localmente
        self._rewrite_links(soup, url)
        
        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(soup.prettify())

    def _rewrite_links(self, soup, current_url):
        # Reescreve <a> hrefs
        for tag in soup.find_all(['a', 'link', 'script', 'img'], href=True) + soup.find_all(['script', 'img'], src=True):
            attr = 'href' if tag.has_attr('href') else 'src'
            val = tag.get(attr)
            
            if not val or val.startswith(('http', 'https', '#', 'javascript:', 'mailto:')):
                # Se for http interno, poderia reescrever, mas vamos simplificar
                if val.startswith(('http', 'https')) and self._is_internal(val):
                     # TODO: Lógica complexa de caminho relativo
                     pass
                continue
            
            # Lógica simples: se é relativo, mantém. Se precisar de assets, o crawler anterior baixava.
            # No modo recursivo, o foco é a navegação entre páginas HTML.
            
            # Para links de páginas internas, idealmente converteríamos para relativo
            # Ex: /sobre -> ../sobre/index.html
            # Isso é complexo de fazer perfeito em pouco tempo, mas vamos tentar o básico:
            # Se for link interno absoluto (/sobre), virar relativo.
