import requests
from urllib.parse import urlparse
from backend.utils.logger import logger

class SecurityScanner:
    def scan(self, url: str):
        """
        Scans a URL for basic security headers and potential exposures.
        """
        results = {
            "score": 100,
            "issues": [],
            "headers": {}
        }
        
        try:
            res = requests.get(url, timeout=10, verify=False) # verify=False to detect SSL issues manually? 
            # Actually, requests throws SSLError if verify=True and cert is bad.
            # Let's try separate SSL check.
            
            headers = res.headers
            results['headers'] = dict(headers)
            
            # 1. Missing Security Headers
            if 'Content-Security-Policy' not in headers:
                results['issues'].append("Missing Content-Security-Policy")
                results['score'] -= 10
            if 'X-Frame-Options' not in headers:
                results['issues'].append("Missing X-Frame-Options (Clickjacking Risk)")
                results['score'] -= 10
            if 'X-Content-Type-Options' not in headers:
                results['issues'].append("Missing X-Content-Type-Options")
                results['score'] -= 5
                
            # 2. Server Information Leakage
            if 'Server' in headers:
                results['issues'].append(f"Server Header Leaked: {headers['Server']}")
                results['score'] -= 5
            if 'X-Powered-By' in headers:
                results['issues'].append(f"Tech Stack Leaked: {headers['X-Powered-By']}")
                results['score'] -= 5
                
            # 3. Check for Exposed Files (Basic)
            exposures = self._check_exposures(url)
            for exp in exposures:
                results['issues'].append(f"Exposed File: {exp}")
                results['score'] -= 20
                
        except Exception as e:
            logger.error(f"Security Scan Error: {e}")
            results['issues'].append(f"Scan failed: {str(e)}")
            results['score'] = 0
            
        return results

    def _check_exposures(self, base_url):
        exposures = []
        paths = ['.env', '.git/config', 'package.json', 'composer.json']
        
        for p in paths:
            try:
                target = base_url.rstrip('/') + '/' + p
                r = requests.head(target, timeout=3)
                if r.status_code == 200:
                    exposures.append(p)
            except:
                pass
        return exposures
