import os
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("SupabaseManager")

class SupabaseManager:
    def __init__(self):
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("Supabase credentials missing")
        self.supabase: Client = create_client(url, key)
        self.local_projects = {} # Fallback storage

    def create_project(self, url: str, mode: str, local_path: str = ""):
        """Creates a new project record."""
        data = {
            "url": url,
            "mode": mode,
            "status": "pending",
            "local_path": local_path
        }
        try:
            res = self.supabase.table("projects").insert(data).execute()
            if res.data:
                return res.data[0]['id']
            return None
        except Exception as e:
            logger.error(f"Supabase Create Error: {e}. Using Local Fallback.")
            import uuid
            from datetime import datetime
            
            pid = str(uuid.uuid4())
            data['id'] = pid
            data['created_at'] = datetime.utcnow().isoformat()
            self.local_projects[pid] = data
            return pid

    def update_project(self, project_id, status=None, local_path=None, error=None, funnel_data=None):
        """Updates project status and data."""
        data = {}
        if status: data['status'] = status
        if local_path: data['local_path'] = local_path
        if error: data['error_msg'] = error
        if funnel_data: data['funnel_data'] = funnel_data # JSONB supported

        # Try Local Update first if exists
        if project_id in self.local_projects:
            self.local_projects[project_id].update(data)
            return

        try:
             self.supabase.table("projects").update(data).eq("id", project_id).execute()
        except Exception as e:
            logger.error(f"Supabase Update Error: {e}")
            # If DB failed but we need to track this, maybe add to local? 
            # But we don't have the original record. 
            # For now, just log.

    def get_history(self, limit=50, offset=0):
        """Fetches recent projects with pagination."""
        db_projects = []
        try:
            res = self.supabase.table("projects")\
                .select("*", count="exact")\
                .order("created_at", desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            db_projects = res.data
        except Exception as e:
            logger.error(f"Supabase List Error: {e}")
            
        # Merge with local
        local_list = list(self.local_projects.values())
        # Sort local by created_at desc? 
        # Simple concat for now.
        return local_list + db_projects

    def get_by_id(self, project_id):
        """Get single project."""
        if project_id in self.local_projects:
            return self.local_projects[project_id]
            
        try:
            res = self.supabase.table("projects").select("*").eq("id", project_id).execute()
            if res.data:
                return res.data[0]
            return None
        except Exception as e:
            logger.error(f"Supabase Get Error: {e}")
            return None

    def delete_project(self, project_id):
        """Deletes a project."""
        if project_id in self.local_projects:
            del self.local_projects[project_id]
            return

        try:
            self.supabase.table("projects").delete().eq("id", project_id).execute()
        except Exception as e:
            logger.error(f"Supabase Delete Error: {e}")
    
    def save_lead(self, lead_data: dict, project_id: int = None):
        """
        Saves a lead from scraping (Instagram, Google Maps, etc).
        
        Args:
            lead_data: Dict with source, name, email, phone, etc.
            project_id: Optional project association
        """
        try:
            data = {
                "data": lead_data,  # JSONB
                "project_id": project_id
            }
            res = self.supabase.table("leads").insert(data).execute()
            if res.data:
                return res.data[0].get('id')
            return None
        except Exception as e:
            logger.error(f"Supabase Save Lead Error: {e}")
            return None
    
    def get_leads(self, limit: int = 100, offset: int = 0, source: str = None):
        """
        Fetches leads from database.
        
        Args:
            limit: Max number of leads to return
            offset: Number of items to skip
            source: Filter by source (instagram, google_maps, etc)
        """
        try:
            query = self.supabase.table("leads").select("*", count="exact")
            
            if source:
                # Filter by JSONB field: data->source
                query = query.eq("data->>source", source)
            
            res = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            return res.data
        except Exception as e:
            logger.error(f"Supabase Get Leads Error: {e}")
            return []

    def get_lead_by_id(self, lead_id):
        """Get single lead."""
        try:
            res = self.supabase.table("leads").select("*").eq("id", lead_id).execute()
            if res.data:
                return res.data[0]
            return None
        except Exception as e:
            logger.error(f"Supabase Get Lead Error: {e}")
            return None

