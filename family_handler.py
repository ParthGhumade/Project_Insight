from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Dict, Any, List
import uuid

from authentication import get_current_user, get_user_supabase

router = APIRouter(prefix="/family", tags=["family"])


class AddFamilyMemberRequest(BaseModel):
    member_email: str
    relation: str

class RemoveFamilyMemberRequest(BaseModel):
    member_email: str


@router.post("/add")
def add_family_member(
    payload: AddFamilyMemberRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    supabase = get_user_supabase(user["token"])
    user_id = user["user_id"]

    try:
        # Check if the user trying to be added exists in profiles
        member_profile = (
            supabase.table("profiles")
            .select("id")
            .eq("email", payload.member_email)
            .execute()
        )

        if not member_profile.data:
            raise HTTPException(status_code=404, detail="User with this email not found")

        member_id = member_profile.data[0]["id"]
        
        # Prevent adding oneself
        if user_id == member_id:
            raise HTTPException(status_code=400, detail="Cannot add yourself as a family member")

        # Fetch current user's profile to get existing family_members
        user_profile = (
            supabase.table("profiles")
            .select("family_members")
            .eq("id", user_id)
            .execute()
        )

        if not user_profile.data:
            raise HTTPException(status_code=404, detail="User profile not found")

        current_members = user_profile.data[0].get("family_members")
        if current_members is None:
            current_members = []

        # Check if relationship already exists
        for member in current_members:
            if member.get("userid") == member_id:
                return {"message": "Family member relation already exists", "data": member}

        new_member = {
            "relation": payload.relation,
            "email": payload.member_email,
            "userid": member_id
        }
        current_members.append(new_member)

        response = (
            supabase.table("profiles")
            .update({"family_members": current_members})
            .eq("id", user_id)
            .execute()
        )
        
        return {"message": "Family member added successfully", "data": new_member}
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/remove")
def remove_family_member(
    payload: RemoveFamilyMemberRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    supabase = get_user_supabase(user["token"])
    user_id = user["user_id"]
    
    try:
        user_profile = (
            supabase.table("profiles")
            .select("family_members")
            .eq("id", user_id)
            .execute()
        )

        if not user_profile.data:
            raise HTTPException(status_code=404, detail="User profile not found")

        current_members = user_profile.data[0].get("family_members")
        if current_members is None:
            current_members = []

        new_members = [m for m in current_members if m.get("email") != payload.member_email]
        
        if len(new_members) == len(current_members):
            raise HTTPException(status_code=404, detail="Family member relation not found")

        response = (
            supabase.table("profiles")
            .update({"family_members": new_members})
            .eq("id", user_id)
            .execute()
        )

        return {"message": "Family member removed successfully"}

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
def list_family_members(
    user: Dict[str, Any] = Depends(get_current_user)
):
    supabase = get_user_supabase(user["token"])
    user_id = user["user_id"]

    try:
        user_profile = (
            supabase.table("profiles")
            .select("family_members")
            .eq("id", user_id)
            .execute()
        )
        
        if not user_profile.data:
            raise HTTPException(status_code=404, detail="User profile not found")

        family_members = user_profile.data[0].get("family_members")
        if family_members is None:
            family_members = []
            
        return {"data": family_members}
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
