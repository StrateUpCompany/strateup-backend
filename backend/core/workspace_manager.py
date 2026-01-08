
import os
import logging
from typing import List, Optional, Dict
from backend.core.supabase_manager import SupabaseManager

logger = logging.getLogger("WorkspaceManager")

class WorkspaceManager:
    def __init__(self):
        self.db = SupabaseManager()

    async def create_workspace(self, user_id: str, name: str) -> Dict:
        """
        Creates a new workspace and assigns the creator as Admin.
        Protocol: "The Office Creation"
        """
        try:
            # 1. Create Workspace
            ws_data = {
                "name": name,
                "owner_id": user_id
            }
            res = self.db.supabase.table("workspaces").insert(ws_data).execute()
            if not res.data:
                raise Exception("Failed to create workspace record")
            
            workspace = res.data[0]
            
            # 2. Add User as Admin Member
            member_data = {
                "workspace_id": workspace["id"],
                "user_id": user_id,
                "role": "admin"
            }
            self.db.supabase.table("workspace_members").insert(member_data).execute()
            
            logger.info(f"Workspace '{name}' created by {user_id}")
            return workspace
            
        except Exception as e:
            logger.error(f"Error creating workspace: {str(e)}")
            raise e

    async def get_user_workspaces(self, user_id: str) -> List[Dict]:
        """
        Get all workspaces a user belongs to.
        """
        try:
            # Join workspaces via workspace_members
            # Supabase-py join syntax can be tricky, doing 2 steps is safer for MVP
            
            # 1. Get IDs from members
            res_members = self.db.supabase.table("workspace_members")\
                .select("workspace_id, role")\
                .eq("user_id", user_id)\
                .execute()
                
            if not res_members.data:
                # Fallback: Check if user has NO workspaces (Legacy User).
                # If so, auto-create "My Workspace"
                logger.info(f"User {user_id} has no workspaces. Auto-creating default.")
                return [await self.create_workspace(user_id, "My Workspace")]
                
            memberships = res_members.data
            ws_ids = [m["workspace_id"] for m in memberships]
            
            # 2. Get Workspaces
            res_ws = self.db.supabase.table("workspaces")\
                .select("*")\
                .in_("id", ws_ids)\
                .execute()
                
            # Merge Role info
            workspaces = []
            for ws in res_ws.data:
                role = next((m["role"] for m in memberships if m["workspace_id"] == ws["id"]), "viewer")
                ws["my_role"] = role
                workspaces.append(ws)
                
            return workspaces
            
        except Exception as e:
            logger.error(f"Error fetching workspaces: {str(e)}")
            return []

    async def invite_member(self, requester_id: str, workspace_id: str, email: str, role: str = "viewer") -> bool:
        """
        Invite a member by email. 
        Note: Simple MVP implementation requires User ID. 
        Real impl would invite by email -> send email -> user accepts -> links generated ID.
        For Internal/MVP: We assume we can lookup user_id by email if they exist, or fail.
        """
        # 1. Verify requester is Admin
        if not await self._is_admin(requester_id, workspace_id):
            raise Exception("Only admins can invite members")
            
        # 2. Lookup User by Email (Mocking this lookup as Supabase Admin API is needed for auth.users)
        # For MVP, we might just fail if we can't fully integrate Auth Admin here.
        # Alternative: Just insert into members if we know the ID.
        # Let's assume for this milestone we pass email, but implementation expects user to exist.
        
        # TODO: Implement proper invite flow (Email Table -> Accept Link).
        # Temporary: Just fail gracefully saying "Invite flow requires Auth Admin" or mock for now.
        return False
        
    async def _is_admin(self, user_id: str, workspace_id: str) -> bool:
        res = self.db.supabase.table("workspace_members")\
            .select("role")\
            .eq("workspace_id", workspace_id)\
            .eq("user_id", user_id)\
            .execute()
        return res.data and res.data[0]["role"] == "admin"

workspace_manager = WorkspaceManager()
