import json
import logging
import httpx
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FunnelAnalyst")

class FunnelAnalyst:
    def __init__(self):
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "llama3.2"  # Default model
        self._cache = {} # Simple in-memory cache: (project_id, prompt_type) -> result

    async def analyze_project(self, project_path: Path, project_id: str, prompt_type: str = "default_audit", text_override: str = None):
        """
        Analyzes the funnel map of a project using local LLM.
        """
        # 0. Check Cache
        cache_key = f"{project_id}_{prompt_type}"
        # Skip cache if overriding text (it's dynamic)
        if not text_override and cache_key in self._cache:
            logging.info(f"Returning cached analysis for {cache_key}")
            return {"analysis": self._cache[cache_key]}

        context_text = ""
        
        if text_override:
            context_text = text_override
        else:
            funnel_path = project_path / "funnel_map.json"
            
            # If we are doing a 5As audit, we might not strictly need the funnel map if we had scrapings,
            # but for now we rely on it. If missing, we warn.
            if not funnel_path.exists():
                return {"error": "Funnel map not found. Please run the funnel mapper first."}

            try:
                with open(funnel_path, "r", encoding="utf-8") as f:
                    funnel_data = json.load(f)
            except Exception as e:
                logger.error(f"Error reading funnel map: {e}")
                return {"error": f"Failed to read funnel data: {e}"}

            # 1. Prepare Context from Funnel Data
            context_text = self._prepare_context(funnel_data, project_id)

        # 2. Construct Prompt Logic
        prompt = self._construct_dynamic_prompt(prompt_type, context_text)

        # 3. Call Ollama
        try:
            response_text = await self._call_ollama(prompt)
            
            # Save to disk for Persistence/Reporting: handle differently based on type
            # If default audit, overwrite analysis.md. If special, maybe append or save separate?
            # For simplicity, we just return it and let frontend handle state, 
            # OR we save specific files like analysis_mkt40.json?
            # User wants "Compass" -> Real-time data.
            # But persistence is good.
            
            filename = "analysis.md"
            if "marketing_40" in prompt_type:
                filename = f"analysis_{prompt_type}.json"
            
            try:
                save_path = project_path / filename
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(response_text)
            except Exception as e:
                logger.error(f"Failed to save {filename}: {e}")

            # Update Cache
            self._cache[cache_key] = response_text
            
            return {"analysis": response_text}
        
        except httpx.ConnectError:
            return {
                "error": "Ollama is not running. Please install and start Ollama (http://localhost:11434) to use AI features."
            }
        except Exception as e:
            logger.error(f"AI Analysis failed: {e}")
            return {"error": f"AI Analysis failed: {str(e)}"}

    def _prepare_context(self, funnel_data, project_id):
        """Aggregates relevant info from the funnel map into a text blob."""
        text = f"Project: {project_id}\n\n"
        text += f"Total Steps: {len(funnel_data)}\n\n"
        
        for step in funnel_data:
            text += f"--- Step {step.get('step')} ---\n"
            text += f"Type: {step.get('title', 'Unknown Page')}\n"
            text += f"URL: {step.get('url')}\n"
            
            # Add detected prices
            prices = step.get('prices_detected', [])
            if prices:
                text += f"Prices Mentioned: {', '.join(prices)}\n"
            
            # Add Tech Stack info
            stack = step.get('tech_stack', {})
            platform = stack.get('platform')
            if platform and platform != 'Custom/Unknown':
                 text += f"Platform: {platform}\n"
            
            text += "\n"
            
        return text

    def _construct_dynamic_prompt(self, prompt_type, context_text):
        
        # 1. Try Marketing 4.0
        try:
            from backend.core.knowledge.marketing_40 import MKT40_SYSTEM_PROMPTS
            if prompt_type in MKT40_SYSTEM_PROMPTS:
                system_instruction = MKT40_SYSTEM_PROMPTS[prompt_type]
                return f"{system_instruction}\n\nCONTEXTO DO PROJETO:\n{context_text}"
        except ImportError:
            pass

        # 2. Proposal Generator
        if prompt_type == "proposal_generator":
             return f"""Você é um Consultor de Crescimento (Growth Consultant) especializado em Funis de Vendas.
Seu objetivo é gerar uma PROPOSTA IRRECUSÁVEL (Pitch Kit) cruzando dois contextos:
1. O CONTEXTO DO LEAD (O alvo - fornecido no texto abaixo em JSON).
2. O CONTEXTO DO CLONE (A Solução - considere que o 'contexto' também inclui a url do projeto clonado se disponível).

DADOS COMBINADOS:
{context_text}

Gere um documento Markdown estruturado assim:
# Proposta de Aceleração Digital

## 1. O Diagnóstico (Dores Detectadas)
Cite 3 pontos fracos da presença atual do Lead baseando-se nos dados fornecidos (Categoria, Rating, Website ausente ou ruim).

## 2. A Solução Sugerida
Explique que instalaremos um Funil de Alta Conversão (baseado no projeto selecionado).

## 3. A Estratégia (O Match)
Sugira:
- Headline Adaptada.
- Isca Digital sugerida.
- Oferta Principal.

## 4. Próximos Passos
CTA para fechar contrato.

Seja direto e persuasivo."""

        # 3. Default Fallback (Old logic)
        return self._construct_prompt(context_text)

    def _construct_prompt(self, context_text):
        return f"""
You are a World-Class Digital Marketing Strategist and Funnel Expert (like Russell Brunson).
Analyze the following Sales Funnel structure and metadata.

DATA:
{context_text}

TASK:
Provide a "Strategic Audit" of this funnel in Markdown format.
Include the following sections:

1. 🎯 **Funnel Architecture Analysis**: What type of funnel is this? (Webinar, VSL, PLF, etc.) based on the pages?
2. 💰 **Offer & Pricing Strategy**: Analyze the pricing points found. Are there tripwires? High-ticket offers?
3. 🛠️ **Tech Stack Insights**: Comment on the platform used (e.g., usually Hotmart funnels convert well in Brazil).
4. 🧠 **Gap Analysis**: What seems to be missing? (e.g., No upsell detected, no order bump).
5. 🚀 **Optimization Plan**: 3 Concrete steps to improve this funnel.

Use Emojis and Bold text for readability.
Write in PORTUGUESE (Brazil).
"""

    async def _call_ollama(self, prompt):
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            logger.info(f"Sending request to Ollama ({self.model})...")
            response = await client.post(self.ollama_url, json=payload)
            
            if response.status_code != 200:
                raise Exception(f"Ollama Error: {response.status_code} - {response.text}")
                
            data = response.json()
            return data.get("response", "No response from AI")
