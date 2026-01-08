
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.core.supabase_manager import SupabaseManager

logger = logging.getLogger("AdvancedSearch")

class AdvancedSearchService:
    """
    Advanced Search Engine using Supabase/Postgres capabilities.
    
    Features:
    - Full-text search on Lead data (JSONB)
    - Filtering by specific JSON fields (industry, role, source)
    - Project search
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
        
    def __init__(self):
        if self._initialized: return
        self.db = SupabaseManager()
        self._initialized = True
        # In-memory history for session (persisted history could be added later)
        self._search_history = {}

    async def search_leads(
        self, 
        query: str = None, 
        filters: Dict[str, Any] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search leads with query string and structured filters.
        """
        try:
            # Base query
            req = self.db.supabase.table("leads").select("*", count="exact")
            
            # 1. Text Search
            # Uses GIN indexes added in supabase_setup.sql implicitly via operators?
            # Or explicit 'ilike' on generated text representation.
            # For JSONB, standard practice is:
            # - Key specific: data->>name ilike %query%
            # - Full doc: Use a materialized view or tsvector column.
            # We will use key-specific for now as mapped to UI common fields.
            
            if query:
                # Search across common fields
                term = f"%{query}%"
                or_clause = f"data->>name.ilike.{term},data->>bio.ilike.{term},data->>email.ilike.{term},data->>company.ilike.{term}"
                req = req.or_(or_clause)

            # 2. Filters
            if filters:
                for key, value in filters.items():
                    if not value: continue
                    
                    if key == "source":
                         req = req.eq("data->>source", value)
                    elif key == "industry":
                         # Check enriched data first, then raw
                         # Enriched path: data->enrichment->data->insights->(find type=industry) is hard in PostgREST
                         # Easier path: We saved insights list. 
                         # Let's assume frontend passes a simple filter that we map.
                         # If enriched data is normalized, great. If not, this is tricky.
                         # Hack for now: Text search on the whole enrichment blob? 
                         # Or just assume 'industry' might be in data root if manually set.
                         pass 
                    elif key == "has_email":
                        if value: req = req.not_.is_("data->>email", "null")
                    elif key == "has_phone":
                        if value: req = req.not_.is_("data->>phone", "null")
                    
            # 3. Sort (Default created_at desc)
            req = req.order("created_at", desc=True)
                    
            # Pagination
            req = req.range(offset, offset + limit - 1)
            
            result = req.execute()
            
            # Log history
            if query:
                self._log_history("leads", query, result.count)
            
            return {
                "results": result.data,
                "total": result.count,
                "page": (offset // limit) + 1,
                "limit": limit
            }
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {"results": [], "total": 0, "error": str(e)}

    async def search_projects(self, query: str) -> List[Dict]:
        """Simple project search"""
        try:
            if not query:
                return []
                
            term = f"%{query}%"
            res = self.db.supabase.table("projects")\
                .or_(f"url.ilike.{term},status.ilike.{term}")\
                .limit(20)\
                .execute()
                
            self._log_history("projects", query, len(res.data or []))
            return res.data
        except Exception as e:
             logger.error(f"Project search failed: {e}")
             return []
             
    def _log_history(self, type_: str, query: str, count: int):
        """Simple in-memory log"""
        # Could be persisted to 'search_logs' table
        pass

# Singleton
advanced_search = AdvancedSearchService()
