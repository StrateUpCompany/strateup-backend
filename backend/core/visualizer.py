import os
import json
from urllib.parse import urlparse

class FunnelVisualizer:
    """
    Gera um diagrama visual (Mermaid.js) a partir do mapeamento do funil.
    """
    def __init__(self, funnel_data):
        self.funnel_data = funnel_data

    def generate_html(self, output_path):
        mermaid_code = self._generate_mermaid_code()
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Funnel Map Visualization</title>
            <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
            <script>mermaid.initialize({{startOnLoad:true}});</script>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f4f4f4; padding: 20px; }}
                .container {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); max-width: 1200px; margin: 0 auto; }}
                h1 {{ color: #333; text-align: center; }}
                .meta-info {{ margin-bottom: 20px; padding: 15px; background: #e9ecef; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Funnel Map Visualization</h1>
                <div class="meta-info">
                    <strong>Total Steps:</strong> {len(self.funnel_data)}<br>
                    <strong>Start URL:</strong> {self.funnel_data[0]['url'] if self.funnel_data else 'N/A'}
                </div>
                <div class="mermaid">
                    {mermaid_code}
                </div>
            </div>
        </body>
        </html>
        """
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        return output_path

    def _generate_mermaid_code(self):
        graph = ["graph TD"]
        
        for i, step in enumerate(self.funnel_data):
            step_id = f"step{step['step']}"
            url_short = urlparse(step['url']).path
            if not url_short or url_short == '/': url_short = "Home"
            if len(url_short) > 20: url_short = url_short[:17] + "..."
            
            # Node Definition
            label = f"Step {step['step']}<br>{step.get('title', 'No Title')}<br><small>{url_short}</small>"
            graph.append(f'{step_id}["{label}"]')
            
            # Edges (Connections)
            # Conecta sequencialmente se não houver lógica explicita, ou usa next_step_url
            if i < len(self.funnel_data) - 1:
                next_step = self.funnel_data[i+1]
                next_id = f"step{next_step['step']}"
                
                # Verifica se houve um CTA detectado que levou para lá
                ctas = step.get('ctas_found', [])
                connector_text = "Next Step"
                
                # Tenta achar qual CTA match com a URL do next step
                for cta in ctas:
                    if cta['url'] == next_step['url']:
                        connector_text = cta['text'][:15]
                        break
                        
                graph.append(f"{step_id} -->|{connector_text}| {next_id}")

        # Style
        graph.append("classDef default fill:#f9f9f9,stroke:#333,stroke-width:2px;")
        graph.append("classDef start fill:#d4edda,stroke:#28a745,stroke-width:2px;")
        graph.append("class step1 start;")
        
        return "\n".join(graph)
