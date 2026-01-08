from fastapi import APIRouter, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
import threading
import os
import json
from backend.core.crawler import ClonagemThread
from backend.core.supabase_manager import SupabaseManager
from backend.core.ai_manager import AIManager
from backend.core.analyst import FunnelAnalyst
from backend.core.reporter import PDFReporter
from backend.core.security_scanner import SecurityScanner
from backend.core.storage import StorageManager
from backend.core.apify_client import get_apify_client
from backend.core.gamification import GamificationEngine
from backend.api.websocket_manager import manager as ws_manager
from backend.utils.limiter import limiter
from backend.core.scraper_manager import scraper_manager
from backend.core.apify_client import get_apify_client # Still used for direct status/posts
from . import (
    lead_routes as leads_routes,
    # project_routes, # Missing
    # websocket_routes, # Missing
    enrichment_routes,
    search_routes,
    export_routes,
    workspace_routes,
    subscription_routes,
    seo_routes,
    compliance_routes
)

api_router = APIRouter()
router = api_router # Alias for main.py compatibility

api_router.include_router(leads_routes.router)
# api_router.include_router(project_routes.router) # Missing
# api_router.include_router(websocket_routes.router) # Missing
api_router.include_router(enrichment_routes.router)
api_router.include_router(search_routes.router)
api_router.include_router(export_routes.router)
api_router.include_router(workspace_routes.router)
api_router.include_router(subscription_routes.router)
api_router.include_router(seo_routes.router)
api_router.include_router(compliance_routes.router)
session_manager = SupabaseManager()
ai_manager = AIManager()
funnel_analyst = FunnelAnalyst()
security_scanner = SecurityScanner()
storage_manager = StorageManager()
gamification_engine = GamificationEngine()
# PDFReporter is instantiated per request as it holds state


# --- Models ---
class CloneRequest(BaseModel):
    """
    Request model for starting a cloning process.
    """
    url: str
    mode: str = "static" # static, funnel, recursive
    options: Optional[dict] = {}

# AnalysisRequest model is defined below near /analyze endpoint

class ProjectUpdate(BaseModel):
    funnel_data: Optional[dict] = None

@router.patch("/projects/{project_id}")
async def update_project(project_id: int, update: ProjectUpdate):
    """Atualiza dados do projeto (ex: salvar funil)"""
    try:
        # Convert dict to json string if necessary, or pass as is if manager handles it
        # SupabaseManager.update_project expects kwargs matching table columns
        # funnel_data is jsonb, so passing dict is correct for direct update if using supabase-py
        # But let's check session_manager.update_project signature.
        # Assuming it takes **kwargs and passes them to update().
        
        # Filter only provided fields
        data = {k: v for k, v in update.model_dump().items() if v is not None}
        
        if not data:
            raise HTTPException(status_code=400, detail="No data provided for update")
            
        session_manager.update_project(project_id, **data)
        return {"status": "success", "message": "Projet updated"}
    except Exception as e:
        logger.error(f"Error updating project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Routes ---

@router.get("/projects")
def get_projects(page: int = 1, limit: int = 50):
    """
    Retorna histórico de projetos (paginado).
    - page: Page number (1-based)
    - limit: Items per page (default 50)
    """
    offset = (page - 1) * limit
    return session_manager.get_history(limit=limit, offset=offset)

@router.get("/projects/{project_id}")
def get_project(project_id: int):
    """Retorna um projeto específico"""
    try:
        project = session_manager.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Projeto não encontrado")
        return project
    except Exception as e:
        logger.error(f"Error fetching project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clone")
async def start_clone(req: CloneRequest):
    """Inicia processo de clonagem em Background Thread"""
    logger.info(f"Recebido pedido de clone: {req.url} [{req.mode}]")
    
    # Configura opções baseado no modo
    opcoes = req.options or {}
    if req.mode == "funnel":
        opcoes['modo_funnel'] = True
    elif req.mode == "recursive":
        opcoes['modo_recursivo'] = True
    elif req.mode == "smart":
        opcoes['use_headless'] = True
    
    # 1. Create Project immediately for persistence/UI feedback
    project_id = session_manager.create_project(req.url, req.mode)
    if not project_id:
        raise HTTPException(status_code=500, detail="Failed to create project record")

    # Inicia Thread
    try:
        logger.debug(f"Iniciando thread de clonagem para {req.url} (ID: {project_id})")
        # Pass project_id to thread so it updates this record instead of creating new
        thread = ClonagemThread(req.url, opcoes, project_id=project_id)
        thread.start()
        logger.info(f"Thread iniciada com sucesso. Thread ID: {thread.ident}")
        return {
            "status": "started", 
            "message": "Clonagem iniciada com sucesso",
            "project_id": project_id
        }
    except Exception as e:
        logger.error(f"Erro ao iniciar thread: {e}")
        # Update status to error if thread fails to start
        session_manager.update_project(project_id, "ERROR", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/projects/{project_id}/reclone")
async def reclone_project(project_id: int):
    """
    Reinicia o processo de clonagem para um projeto existente.
    Útil para projetos 'órfãos' sem arquivos locais.
    """
    project = session_manager.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    url = project.get("url")
    mode = project.get("mode", "static")
    
    # Configura opções
    opcoes = {}
    if mode == "funnel":
        opcoes['modo_funnel'] = True
    elif mode == "recursive":
        opcoes['modo_recursivo'] = True
    
    # Inicia Thread reutilizando lógica
    try:
        logger.info(f"Iniciando Re-clone para Projeto {project_id}: {url}")
        
        # Sobrescreve engine para forçar update no mesmo ID em vez de criar novo?
        # A Engine atual cria um NOVO projeto no init se não passar ID.
        # Precisamos passar o project_id para a Engine ou Thread.
        # Engine não aceita project_id no construtor hoje.
        # Workaround: Atualizar status e rodar como se fosse novo, 
        # mas Engine vai criar duplicata no DB se não mudarmos ela.
        # SOLUÇÃO RAPIDA MVP: ClonagemThread cria novo registro? 
        # Vamos verificar engine.py. Engine chama session_manager.create_project.
        # Se quisermos 'repair', precisamos que a Engine aceite um ID existente.
        
        # Como a Engine é bloqueante e cria registro, vamos fazer um Patch na thread:
        thread = ClonagemThread(url, opcoes, project_id=project_id)
        thread.start()
        
        session_manager.update_project(project_id, status="processing", error=None)
        
        return {"status": "started", "message": "Re-clonagem iniciada"}
    except Exception as e:
        logger.error(f"Erro ao iniciar re-clone: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class AnalysisRequest(BaseModel):
    """
    Request model for AI analysis.
    """
    prompt_type: str = "default_audit"
    text_override: Optional[str] = None

@router.post("/projects/{project_id}/analyze")
async def analyze_project(project_id: int, request: AnalysisRequest = AnalysisRequest()):
    """
    Analisa um projeto já clonado usando AI.
    Suporta prompt_type: 'default_audit' ou 'marketing_40_5as' (via body).
    """
    project = session_manager.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    local_path = project.get("local_path")
    if not local_path or not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail="Arquivos do projeto não encontrados")
        
    # Chama o analista
    result = await funnel_analyst.analyze_project(
        Path(local_path), 
        str(project_id), 
        request.prompt_type,
        text_override=request.text_override
    )
    
    if "error" in result:
        # Se for erro de conexão com Ollama, retorna 503 (Service Unavailable) ou 400
        if "Ollama is not running" in result["error"]:
             raise HTTPException(status_code=503, detail=result["error"])
        raise HTTPException(status_code=500, detail=result["error"])
        
    return result

@router.get("/projects/{project_id}/files")
async def list_project_files(project_id: int):
    """Lista arquivos na pasta clonada do projeto."""
    project = session_manager.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    local_path = project.get("local_path")
    if not local_path or not os.path.exists(local_path):
        return {"files": [], "error": "Pasta local não encontrada. Execute um clone primeiro."}
    
    files = []
    for root, dirs, filenames in os.walk(local_path):
        for f in filenames:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, local_path)
            files.append({
                "name": f,
                "path": rel_path,
                "size": os.path.getsize(full_path),
                "type": "html" if f.endswith(".html") else "asset"
            })
    
    return {"local_path": local_path, "files": files[:100]} # Limit for safety

@router.get("/projects/{project_id}/html")
async def get_project_html(project_id: int, file: str = "index.html"):
    """
    Retorna o HTML clonado para visualização no app.
    Query param: ?file=step_1/index.html
    """
    project = session_manager.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    local_path = project.get("local_path")
    if not local_path:
        raise HTTPException(status_code=404, detail="local_path não definido para este projeto")
    
    # Sanitize to prevent path traversal
    safe_file = os.path.normpath(file).lstrip("/").lstrip("\\")
    if ".." in safe_file:
        raise HTTPException(status_code=400, detail="Invalid file path")
        
    target_path = Path(local_path) / safe_file
    
    if not target_path.exists():
        raise HTTPException(status_code=404, detail=f"Arquivo não encontrado: {safe_file}")
    
    return FileResponse(target_path, media_type="text/html")

@router.post("/projects/{project_id}/security")
async def scan_security(project_id: int):
    """Realiza auditoria de segurança"""
    project = session_manager.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
        
    url = project.get("url")
    return security_scanner.scan(url)

@router.post("/projects/{project_id}/deploy")
async def deploy_project(project_id: int):
    """Deploy project files to Supabase Storage"""
    project = session_manager.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
        
    local_path = project.get("local_path")
    if not local_path or not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail="Arquivos locais não encontrados")
        
    # Upload
    try:
        result = storage_manager.upload_project_files(str(project_id), Path(local_path))
        
        if result.get("errors"):
            logger.warning(f"Deploy errors: {result['errors']}")
            
        public_url = result.get("public_url")
        
        # Save Deploy URL in funnel_data (JSONB)
        funnel_data = project.get("funnel_data") or {}
        funnel_data['deploy_url'] = public_url
        session_manager.update_project(project_id, funnel_data=funnel_data)
        
        return result
    except Exception as e:
        logger.error(f"Deploy failed: {e}")
        raise HTTPException(status_code=500, detail=f"Deploy failed: {str(e)}")

@router.get("/projects/{project_id}/report/pdf")
async def get_pdf_report(project_id: int):
    """Gera e retorna o relatório PDF"""
    project = session_manager.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    local_path = Path(project.get("local_path"))
    if not local_path.exists():
        raise HTTPException(status_code=404, detail="Arquivos não encontrados")
        
    pdf_path = local_path / "audit_report.pdf"
    
    # Se já existe, retorna (cache simples)
    # Em produção, poderíamos checar timestamp ou permitir ?force=true
    if pdf_path.exists():
         return FileResponse(pdf_path, media_type='application/pdf', filename=f"audit_{project_id}.pdf")
         
    # Gera novo PDF
    # 1. Carrega dados do funil
    try:
        with open(local_path / "funnel_map.json", "r") as f:
            funnel_data = json.load(f)
    except:
        funnel_data = []
        
    # 2. Carrega análise AI (se houver)
    ai_text = "AI Analysis not run yet. Please run 'Strategic Consultant' first."
    if (local_path / "analysis.md").exists():
        ai_text = (local_path / "analysis.md").read_text(encoding="utf-8")
        
    # 3. Gera
    reporter = PDFReporter(project, funnel_data, ai_text)
    try:
        reporter.generate(pdf_path)
    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)}")
        
    return FileResponse(pdf_path, media_type='application/pdf', filename=f"audit_{project_id}.pdf")

@router.post("/projects/{project_id}/capture")
async def capture_lead(project_id: int, request: Request):
    """
    Receives form submissions from cloned sites.
    Saves to 'leads' table in Supabase.
    """
    try:
        # Handle various content types
        content_type = request.headers.get('content-type', '')
        if 'application/json' in content_type:
            data = await request.json()
        else:
            # Form data
            form_data = await request.form()
            data = dict(form_data)
            
        logger.info(f"Lead captured for project {project_id}: {data.keys()}")
        
        # Save to DB
        res = session_manager.supabase.table("leads").insert({
            "project_id": project_id,
            "data": data
        }).execute()
        
        return {"status": "success", "message": "Dados recebidos com sucesso!"}
        
    except Exception as e:
        logger.error(f"Capture error: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar dados")

@router.get("/projects/{project_id}/leads")
async def get_project_leads(project_id: int):
    """Fetches captured leads for a project"""
    try:
        res = session_manager.supabase.table("leads").select("*").eq("project_id", project_id).order("created_at", desc=True).execute()
        return res.data
    except Exception as e:
        logger.error(f"Fetch leads error: {e}")
        return []

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Mantém conexão viva e ouve comandos do frontend (opcional)
            data = await websocket.receive_text()
            # Pode processar comandos via WS também se quiser
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

@router.get("/projects/{project_id}/funnel")
def get_project_funnel(project_id: int):
    """Lê o arquivo funnel_map.json do projeto"""
    project = session_manager.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    local_path = project.get("local_path")
    if not local_path or not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail="Arquivos do projeto não encontrados no servidor")
        
    funnel_map_path = os.path.join(local_path, "funnel_map.json")
    if not os.path.exists(funnel_map_path):
        # Tenta fallback para verificar se é um clone estático que pode ter sido mapeado?
        # Por enquanto, apenas erro.
        raise HTTPException(status_code=404, detail="Funnel Map não encontrado para este projeto")
        
    try:
        with open(funnel_map_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Erro ao ler funnel_map.json: {e}")
        raise HTTPException(status_code=500, detail="Erro ao ler arquivo de mapa")


# ============================================================
# APIFY SCRAPING ENDPOINTS
# ============================================================

class InstagramProfileRequest(BaseModel):
    username: str

class InstagramPostsRequest(BaseModel):
    username: str
    limit: int = 12

class BusinessSearchRequest(BaseModel):
    """
    Request model for searching businesses on Google Maps.
    """
    query: str
    location: str = "Brazil"
    limit: int = 20
    min_rating: float = 0.0
    min_reviews: int = 0


@router.get("/scrape/status")
@limiter.limit("20/minute")
async def get_apify_status(request: Request):
    """
    Verifica status da conta Apify e créditos disponíveis.
    Requer APIFY_TOKEN em .env
    """
    client = get_apify_client()
    return await client.get_account_info()


@router.post("/scrape/instagram/profile")
@limiter.limit("5/minute")
async def scrape_instagram_profile(request: Request, req: InstagramProfileRequest):
    """
    Scrape dados públicos de um perfil do Instagram.
    
    Retorna:
    - username, fullName, biography
    - followersCount, followsCount, postsCount
    - profilePicUrl, isVerified
    - externalUrl, email (se na bio), phone (se na bio)
    """
    if not req.username:
        raise HTTPException(status_code=400, detail="Username é obrigatório")
    
    # Remove @ se usuário incluiu
    username = req.username.lstrip("@").lower()
    
    username = req.username.lstrip("@").lower()
    
    # improved: use unified manager
    result = await scraper_manager.scrape_instagram_profile(username)
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Perfil não encontrado (Local & Apify falharam)"
        )
        
    # Compatibilidade com formato anterior se result vier flat
    if "profile" not in result:
        result = {"success": True, "profile": result}
    
    # Salvar lead no banco (opcional)
    try:
        profile = result["profile"]
        lead_data = {
            "source": "instagram",
            "username": profile.get("username"),
            "name": profile.get("fullName"),
            "email": profile.get("email"),
            "phone": profile.get("phone"),
            "bio": profile.get("biography"),
            "followers": profile.get("followersCount"),
            "website": profile.get("externalUrl"),
            "raw_data": profile
        }
        session_manager.save_lead(lead_data)
    except Exception as e:
        logger.warning(f"Failed to save lead: {e}")
    
    return result


@router.post("/scrape/instagram/posts")
@limiter.limit("5/minute")
async def scrape_instagram_posts(request: Request, req: InstagramPostsRequest):
    """
    Scrape últimos posts de um perfil do Instagram.
    
    Retorna lista de posts com:
    - imageUrl, caption, likesCount, commentsCount, timestamp
    """
    if not req.username:
        raise HTTPException(status_code=400, detail="Username é obrigatório")
    
    username = req.username.lstrip("@").lower()
    
    client = get_apify_client()
    result = await client.scrape_instagram_posts(username, limit=req.limit)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Erro ao buscar posts"))
    
    return result


@router.post("/scrape/businesses")
async def search_businesses(req: BusinessSearchRequest):
    """
    Busca empresas no Google Maps.
    
    Exemplo: query="agência de marketing", location="São Paulo"
    
    Retorna lista de negócios com:
    - name, address, phone, website
    - rating, reviewsCount, category
    """
    if not req.query:
        raise HTTPException(status_code=400, detail="Query é obrigatória")
    
    if not req.query:
        raise HTTPException(status_code=400, detail="Query é obrigatória")
    
    # improved: use unified manager with fallback
    items = await scraper_manager.search_google_maps(
        query=req.query,
        location=req.location,
        limit=req.limit
    )
    
    if not items:
        # Se retornou vazio, pode ser erro ou zero resultados.
        # ScraperManager (Local) retorna lista vazia em erro?
        # Sim, retorna [] se falhar todas tentativas.
        raise HTTPException(status_code=404, detail="Nenhum resultado encontrado ou falha nos provedores")
    
    result = {"success": True, "businesses": items}
    
    # Salvar leads no banco
    try:
        for biz in result.get("businesses", []):
            lead_data = {
                "source": "google_maps",
                "name": biz.get("name"),
                "phone": biz.get("phone"),
                "website": biz.get("website"),
                "address": biz.get("address"),
                "category": biz.get("category"),
                "rating": biz.get("rating"),
                "raw_data": biz
            }
            session_manager.save_lead(lead_data)
    except Exception as e:
        logger.warning(f"Failed to save leads: {e}")
    
    return result


@router.post("/leads")
async def save_lead_endpoint(request: Request):
    """
    Manually save a lead.
    """
    try:
        data = await request.json()
        lead_id = session_manager.save_lead(data)
        if not lead_id:
             raise HTTPException(status_code=500, detail="Failed to save lead")
        return {"status": "success", "id": lead_id}
    except Exception as e:
        logger.error(f"Save lead error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/leads")
async def get_all_leads(page: int = 1, limit: int = 100):
    """
    Fetches all leads (paginated).
    - page: Page number (1-based)
    - limit: Items per page (default 100)
    """
    offset = (page - 1) * limit
    return session_manager.get_leads(limit=limit, offset=offset)



# ============================================================
# PROPOSAL GENERATION
# ============================================================
from backend.core.proposal_service import ProposalService
proposal_service = ProposalService()

class ProposalRequest(BaseModel):
    lead_id: str

@router.post("/projects/{project_id}/proposal")
async def generate_proposal_endpoint(project_id: int, req: ProposalRequest):
    """Generates a sales proposal for a specific lead using project data."""
    result = await proposal_service.generate_proposal(str(project_id), req.lead_id)
    if "error" in result:
         raise HTTPException(status_code=404, detail=result["error"])
    return result



router = api_router
