from backend.core.ai_manager import AIManager
from backend.core.supabase_manager import SupabaseManager
from backend.utils.logger import logger
import json
import os

class ProposalService:
    def __init__(self):
        self.ai_manager = AIManager()
        self.db = SupabaseManager()

    async def generate_proposal(self, project_id: str, lead_id: str):
        """
        Orchestrates the proposal generation.
        1. Fetch Project (Clone) Data
        2. Fetch Lead Data
        3. Validates and merges context
        4. Calls LLM
        """
        # 1. Fetch Project
        project = self.db.get_by_id(project_id)
        if not project:
            return {"error": "Project not found"}
        
        # 2. Fetch Lead
        lead = self.db.get_lead_by_id(lead_id)
        if not lead:
             # Fallbck: If lead_id is "generic", maybe generate a template?
             # For now, require lead.
             return {"error": "Lead not found"}

        # 3. Construct Context
        # Extract Funnel Structure
        funnel_map = project.get("funnel_data", {})
        tech_stack = "Unknown" # Need to extract if stored, or parse from analysis
        
        # Extract Lead Info
        lead_data = lead.get("data", {})
        lead_name = lead_data.get("name", "Potential Client")
        lead_niche = lead_data.get("category", "General Business")
        lead_pain = "Low online visibility" # Default if not enriched
        
        context = f"""
        TARGET LEAD:
        Name: {lead_name}
        Niche: {lead_niche}
        Known Pain Points: {lead_pain}
        Source: {lead_data.get("source", "Manual Input")}
        
        CLONED SOLUTION (The Funnel):
        Origin URL: {project.get("url")}
        Mode: {project.get("mode")}
        """
        
        # 4. Generate
        logger.info(f"Generating proposal for {lead_name} based on project {project_id}")
        proposal_md = self.ai_manager.generate_content(context, prompt_type="proposal_generator")
        
        return {
            "status": "success",
            "lead_name": lead_name,
            "proposal_markdown": proposal_md
        }
