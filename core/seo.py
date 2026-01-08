import json
import re
import os
import time
from urllib.parse import urljoin, urlparse
from collections import Counter
from jinja2 import Environment, FileSystemLoader

from backend.utils.logger import logger

class SEOAnalyzer:
    """
    Classe responsável por analisar e extrair informações de SEO de uma página web.
    """
    def __init__(self, soup, url):
        self.soup = soup
        self.url = url
        self.base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        self.seo_data = {}
        
    def analyze_all(self):
        """Executa todas as análises de SEO disponíveis"""
        self._extract_basic_meta()
        self._extract_advanced_meta()
        self._analyze_headings()
        self._analyze_links()
        self._analyze_images()
        self._extract_structured_data()
        self._analyze_keyword_density()
        self._analyze_page_speed_factors()
        self._generate_recommendations()
        return self.seo_data
        
    def _extract_basic_meta(self):
        self.seo_data["title"] = self.soup.title.string.strip() if self.soup.title else "N/A"
        self.seo_data["meta"] = {
            "description": "N/A", "keywords": "N/A", "robots": "N/A",
            "viewport": "N/A", "author": "N/A", "language": "N/A"
        }
        
        for meta in self.soup.find_all("meta"):
            name = meta.get("name", "").lower()
            property_attr = meta.get("property", "").lower()
            content = meta.get("content", "N/A")
            
            if name == "description" or property_attr == "og:description":
                self.seo_data["meta"]["description"] = content
            elif name == "keywords":
                self.seo_data["meta"]["keywords"] = content
            elif name == "robots":
                self.seo_data["meta"]["robots"] = content
            elif name == "viewport":
                self.seo_data["meta"]["viewport"] = content
    
    def _extract_advanced_meta(self):
        self.seo_data["canonical"] = "N/A"
        canonical = self.soup.find("link", rel="canonical")
        if canonical:
            self.seo_data["canonical"] = canonical.get("href", "N/A")

    def _analyze_headings(self):
        self.seo_data["headings"] = {f"h{i}": [] for i in range(1, 7)}
        for level in range(1, 7):
            tag = f"h{level}"
            for heading in self.soup.find_all(tag):
                text = heading.get_text().strip()
                if text:
                    self.seo_data["headings"][tag].append(text)

    def _analyze_links(self):
        self.seo_data["links"] = {"internal": [], "external": [], "total": 0, "nofollow": 0}
        for link in self.soup.find_all("a", href=True):
            href = link.get("href", "").strip()
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue
                
            if not href.startswith(("http://", "https://")):
                href = urljoin(self.url, href)
            
            is_internal = href.startswith(self.base_url)
            link_type = "internal" if is_internal else "external"
            anchor_text = link.get_text().strip() or (link.find("img").get("alt", "[Img]") if link.find("img") else "[Sem texto]")
            is_nofollow = "nofollow" in (link.get("rel", "") or "")
            
            self.seo_data["links"][link_type].append({"url": href, "anchor_text": anchor_text, "nofollow": is_nofollow})
            self.seo_data["links"]["total"] += 1
            if is_nofollow: self.seo_data["links"]["nofollow"] += 1

    def _analyze_images(self):
        self.seo_data["images"] = {"total": 0, "with_alt": 0, "without_alt": 0, "details": []}
        for img in self.soup.find_all("img"):
            src = img.get("src", "")
            if not src: continue
            if not src.startswith(("http", "https")): src = urljoin(self.url, src)
            
            alt = img.get("alt", "")
            self.seo_data["images"]["details"].append({"src": src, "alt": alt})
            self.seo_data["images"]["total"] += 1
            if alt: self.seo_data["images"]["with_alt"] += 1
            else: self.seo_data["images"]["without_alt"] += 1

    def _extract_structured_data(self):
        self.seo_data["structured_data"] = [] # Simplificado para brevidade
        
    def _analyze_keyword_density(self, top_n=20):
        text = self.soup.get_text()
        words = re.findall(r'\b\w+\b', text.lower())
        stopwords = {'a', 'o', 'e', 'de', 'do', 'da', 'em', 'um', 'para', 'com', 'não', 'uma', 'os', 'no', 'se', 'na', 'por', 'mais', 'as', 'dos', 'como', 'mas', 'foi', 'ao', 'ele', 'das', 'tem', 'à', 'seu', 'sua', 'ou', 'ser', 'quando', 'muito', 'nos', 'já', 'está', 'eu', 'também', 'só', 'pelo', 'pela', 'até', 'isso', 'ela', 'entre', 'era', 'depois', 'sem', 'mesmo', 'aos', 'seus', 'quem', 'nas', 'me', 'esse', 'eles', 'estão', 'você', 'tinha', 'foram', 'essa', 'num', 'nem', 'suas', 'meu', 'às', 'minha', 'têm', 'numa', 'pelos', 'elas', 'havia', 'seja', 'qual', 'será', 'nós', 'tenho', 'lhe', 'deles', 'essas', 'esses', 'pelas', 'este', 'fosse', 'dele', 'tu', 'te', 'vocês', 'vos', 'lhes', 'meus', 'minhas', 'teu', 'tua', 'teus', 'tuas', 'nosso', 'nossa', 'nossos', 'nossas', 'dela', 'delas', 'esta', 'estes', 'estas', 'aquele', 'aquela', 'aqueles', 'aquelas', 'isto', 'aquilo', 'estou', 'está', 'estamos', 'estão', 'estive', 'esteve', 'estivemos', 'estiveram', 'estava', 'estávamos', 'estavam', 'estivera', 'estivéramos', 'esteja', 'ejamos', 'estejam', 'estivesse', 'estivéssemos', 'estivessem', 'estiver', 'estivermos', 'estiverem', 'hei', 'há', 'havemos', 'hão', 'houve', 'houvemos', 'houveram', 'houvera', 'houvéramos', 'haja', 'hajamos', 'hajam', 'houvesse', 'houvéssemos', 'houvessem', 'houver', 'houvermos', 'houverem', 'houverei', 'houverá', 'houveremos', 'houverão', 'houveria', 'houveríamos', 'houveriam', 'sou', 'somos', 'são', 'era', 'éramos', 'eram', 'fui', 'foi', 'fomos', 'foram', 'fora', 'fôramos', 'seja', 'sejamos', 'sejam', 'fosse', 'fôssemos', 'fossem', 'for', 'formos', 'forem', 'serei', 'será', 'seremos', 'serão', 'seria', 'seríamos', 'seriam', 'tenho', 'tem', 'temos', 'tém', 'tinha', 'tínhamos', 'tinham', 'tive', 'teve', 'tivemos', 'tiveram', 'tivera', 'tivéramos', 'tenha', 'tenhamos', 'tenham', 'tivesse', 'tivéssemos', 'tivessem', 'tiver', 'tivermos', 'tiverem', 'terei', 'terá', 'teremos', 'terão', 'teria', 'teríamos', 'teriam'}
        filtered_words = [w for w in words if w not in stopwords and len(w) > 2]
        
        counter = Counter(filtered_words)
        total_words = len(filtered_words)
        
        density = {}
        for w, c in counter.most_common(top_n):
            density[w] = {"contagem": c, "densidade": round((c / total_words * 100), 2) if total_words else 0}
            
        self.seo_data["keyword_analysis"] = {
            "total_words": len(words),
            "single_keywords": density
        }

    def _analyze_page_speed_factors(self):
        # Simplificado
        self.seo_data["page_speed_factors"] = {}

    def _generate_recommendations(self):
        recs = []
        if len(self.seo_data.get("title", "")) < 30: recs.append("Título muito curto (<30 chars).")
        if not self.seo_data.get("meta", {}).get("description"): recs.append("Meta descrição ausente.")
        if not self.seo_data.get("headings", {}).get("h1"): recs.append("H1 ausente.")
        if self.seo_data.get("images", {}).get("without_alt", 0) > 0: recs.append("Imagens sem Alt Text encontradas.")
        
        self.seo_data["recommendations"] = recs

    def generate_seo_report(self, output_path):
        """Gera relatório usando Jinja2"""
        try:
            # Caminho absoluto para templates
            template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
            env = Environment(loader=FileSystemLoader(template_dir))
            template = env.get_template('seo_report.html')
            
            html = template.render(
                seo_data=self.seo_data,
                url=self.url,
                timestamp=time.strftime("%d/%m/%Y %H:%M:%S"),
                recommendations=self.seo_data.get("recommendations", [])
            )
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            logger.info(f"Relatório de SEO gerado: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Erro ao gerar relatório Jinja2: {str(e)}")
            return False
