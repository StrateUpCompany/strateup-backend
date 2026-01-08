
import asyncio
from backend.core.database import db
from backend.core.ai_manager import AIManager

ai_manager = AIManager()

async def generate_content_for_page(page: dict):
    slug = page['slug']
    keyword = page['keyword']
    niche = page['category']
    
    print(f"🧠 Generating content for: {slug}...")
    
    prompt = f"""
    You are a world-class Copywriter and SEO Expert.
    Write the content for a Landing Page targeting the keyword: "{keyword}".
    The goal is to sell a "High Conversion Sales Funnel Template" to {niche}.
    
    Structure the response as a JSON object with these keys:
    - h1: The main headline (H1)
    - intro: A compelling introduction paragraph (2-3 sentences)
    - pain_points: A bulleted list of 3-5 pain points this niche faces with marketing.
    - solution_benefits: A bulleted list of benefits of using our funnel.
    - cta_text: The text for the main Call to Action button.
    
    Content should be in Portuguese (Brazil).
    Make it persuasive, professional, and optimized for conversions.
    """
    
    try:
        # Call AI (using generate_text for simplicity, assuming it returns text. 
        # For this MVP, we'll ask for JSON strictly.
        
        response_text = ai_manager.generate_text(prompt)
        
        # Simple/Naive JSON parsing if response is markdown fenced
        import json
        import re
        
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            content_json = json.loads(json_match.group(0))
        else:
            # Fallback if AI fails to give JSON
            content_json = {
                "h1": f"Domine o Mercado de {niche}",
                "intro": response_text[:200],
                "pain_points": ["Baixa conversão", "Leads desqualificados", "Custo alto de anúncios"],
                "solution_benefits": ["Automação completa", "Maior ROI", "Setup Rápido"],
                "cta_text": "Quero meu Funil Grátis"
            }
            
        # Update DB
        db.table("seo_pages").update({
            "content": content_json,
            "status": "published",
            "updated_at": "now()"
        }).eq("id", page['id']).execute()
        
        print(f"✅ Published: {slug}")
        
    except Exception as e:
        print(f"❌ Error generating {slug}: {e}")

async def run_batch():
    # Fetch drafts
    response = db.table("seo_pages").select("*").eq("status", "draft").limit(50).execute()
    pages = response.data
    
    if not pages:
        print("No draft pages found.")
        return

    print(f"Found {len(pages)} drafts. Starting generation...")
    
    for page in pages:
        await generate_content_for_page(page)

def run():
    asyncio.run(run_batch())

if __name__ == "__main__":
    run()
