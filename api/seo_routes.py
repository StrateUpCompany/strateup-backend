
from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from backend.core.database import db
import os

router = APIRouter(tags=["SEO"])

# Setup Templates
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates_dir = os.path.join(base_dir, "templates")
templates = Jinja2Templates(directory=templates_dir)

@router.get("/ping")
async def ping():
    return {"status": "seo_routes_active"}

@router.get("/s/{slug}", response_class=HTMLResponse)
async def get_seo_page(request: Request, slug: str):
    try:
        # Fetch from Supabase
        response = db.table("seo_pages").select("*").eq("slug", slug).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Page not found")
            
        page = response.data[0]
        content = page.get("content", {})
        
        # Render Template
        return templates.TemplateResponse(
            "seo_landing.html", 
            {"request": request, "page": page, "content": content}
        )
        
    except Exception as e:
        print(f"Error serving SEO page: {e}")
        # In dev, show error. In prod, maybe 404.
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sitemap.xml")
async def sitemap(request: Request):
    """Generates dynamic sitemap for pSEO pages."""
    try:
        # Fetch only published pages
        response = db.table("seo_pages").select("slug, updated_at").eq("status", "published").execute()
        pages = response.data
        
        # Base URL
        base_url = "https://strateup.com.br/s" # Or api.strateup... depending on final proxy
        
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        
        for page in pages:
            url = f"{base_url}/{page['slug']}"
            lastmod = page.get('updated_at', '').split('T')[0]
            xml_content += f"  <url>\n    <loc>{url}</loc>\n    <lastmod>{lastmod}</lastmod>\n  </url>\n"
            
        xml_content += '</urlset>'
        
        return Response(content=xml_content, media_type="application/xml")
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))
