import pytest
from backend.core.supabase_manager import SupabaseManager
from backend.main import app
from fastapi.testclient import TestClient
import uuid
from unittest.mock import MagicMock, patch

client = TestClient(app)
session_manager = SupabaseManager()

def test_full_business_flow():
    """
    Testa o fluxo completo de negócio:
    1. Criar Projeto
    2. Simular Clone (Update DB)
    3. Simular Captura de Lead (Hijack)
    4. Verificar se Lead está no Banco
    """
    print("\n--- INICIANDO TESTE DE FLUXO DE NEGÓCIO ---")
    
    # 1. Create Project
    user_id = str(uuid.uuid4()) # Mock user
    project_data = {
        "url": "https://example.com",
        "name": f"Test Flow {uuid.uuid4()}",
        "status": "pending",
        "user_id": user_id
    }
    
    # Insert directly via session manager
    # Signature: create_project(self, url: str, mode: str, local_path: str = "")
    # Returns: int (project_id)
    project_id = session_manager.create_project(url=project_data["url"], mode="funnel_map")
    
    if not project_id:
        print("❌ Falha ao criar projeto")
        return
        
    print(f"✅ Passo 1: Projeto Criado (ID: {project_id})")
    
    # 2. Simulate Clone Completion (Engine usually does this)
    update_data = {
        "status": "completed",
        "local_path": "/tmp/test"
    }
    session_manager.update_project(project_id, update_data)
    print(f"✅ Passo 2: Clone Simulado como 'completed'")
    
    # 3. Simulate Lead Capture (The Hijack Feature)
    lead_data = {
        "email": "teste@business.com",
        "name": "Dr. Business",
        "interest": "High Ticket"
    }
    
    # Call the API endpoint
    # Send as form data to match HTML forms default behavior
    # NOTE: API routes have /api prefix in main.py
    response = client.post(
        f"/api/projects/{project_id}/capture",
        data=lead_data, # passing dict to data= sends as form-encoded
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    assert response.status_code == 200
    assert response.json()['status'] == "success"
    print(f"✅ Passo 3: API de Captura respondeu 200 OK")
    
    # 4. Verify Database
    leads = session_manager.supabase.table("leads").select("*").eq("project_id", project_id).execute()
    assert len(leads.data) > 0
    captured_lead = leads.data[0]
    
    # Check if data matches
    # Note: data is stored in 'data' column as jsonb
    assert captured_lead['data']['email'] == "teste@business.com"
    print(f"✅ Passo 4: Lead verificado no Banco de Dados Supabase")
    print("      Dados:", captured_lead['data'])
    
    # Cleanup
    session_manager.delete_project(project_id)
    print("🧹 Projeto de teste limpo.")
    
if __name__ == "__main__":
    test_full_business_flow()
