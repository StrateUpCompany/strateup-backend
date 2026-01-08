
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from backend.core.workspace_manager import workspace_manager

router = APIRouter()

class WorkspaceCreate(BaseModel):
    name: str
    user_id: str # Ideally from Auth Token, but strictly required for MVP

class InviteMember(BaseModel):
    email: str
    role: str = "viewer"
    workspace_id: str
    requester_id: str

@router.post("/", status_code=201)
async def create_workspace(ws: WorkspaceCreate):
    """
    Creates a new digital office (Workspace).
    """
    try:
        return await workspace_manager.create_workspace(ws.user_id, ws.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def list_workspaces(user_id: str):
    """
    List all workspaces a user belongs to.
    """
    return await workspace_manager.get_user_workspaces(user_id)

@router.post("/invite")
async def invite_member(invite: InviteMember):
    """
    Invite a team member to the workspace.
    """
    try:
        success = await workspace_manager.invite_member(
            invite.requester_id, 
            invite.workspace_id, 
            invite.email, 
            invite.role
        )
        if success:
            return {"success": True, "message": "Invitation sent"}
        else:
            return {"success": False, "message": "Invitation failed (User not found or Auth check failed)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
