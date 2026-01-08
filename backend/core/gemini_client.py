
import os
import google.generativeai as genai
from typing import Optional, List, Dict
from dotenv import load_dotenv

load_dotenv()

class GeminiClient:
    """
    The 'Mind' of the System. 
    Uses Google Gemini 1.5 Flash for high-speed, high-context processing.
    """
    
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("WARNING: GOOGLE_API_KEY not found. AI features will be disabled.")
            self.model = None
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self.vision_model = genai.GenerativeModel('gemini-1.5-flash') # Flash supports vision natively

    async def generate_thought(self, prompt: str, context: str = "") -> str:
        """
        Basic reasoning task. Replaces Ollama.
        """
        if not self.model:
            return "AI Brain Offline (Check API Key)"
            
        try:
            full_prompt = f"Context: {context}\n\nTask: {prompt}" if context else prompt
            response = self.model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            return f"Thinking Error: {str(e)}"

    async def analyze_dom(self, html_content: str, query: str) -> Dict:
        """
        The 'Million Token' Power.
        Feeds the ENTIRE HTML to Gemini to find patterns.
        """
        if not self.model:
            return {"error": "AI Offline"}
            
        try:
            # Gemini 1.5 Flash handles huge text blocks easily.
            # We don't need to chunk it like with GPT-4.
            
            prompt = f"""
            You are a Technical Funnel Auditor.
            Analyze this raw HTML code and answer the query in JSON format.
            
            QUERY: {query}
            
            HTML CODE:
            {html_content[:500000]} # Limit to 500k chars just to be safe, but it handles more
            """
            
            response = self.model.generate_content(prompt)
            # Todo: Parse JSON safely
            return {"analysis": response.text}
            
        except Exception as e:
            return {"error": str(e)}

    async def analyze_vision(self, image_bytes: bytes, prompt: str) -> str:
        """
        The 'Eye'. Analyzes screenshots.
        """
        if not self.vision_model:
            return "Vision Offline"
            
        try:
            from PIL import Image
            import io
            
            img = Image.open(io.BytesIO(image_bytes))
            response = self.vision_model.generate_content([prompt, img])
            return response.text
        except Exception as e:
            return f"Vision Error: {str(e)}"
