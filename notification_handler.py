"""Database helper for fetching FCM tokens and usernames by user UUIDs.""" 

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Dict, Any
from firebase_admin import messaging
from authentication import get_current_user, get_user_supabase

router = APIRouter(prefix="/fcm", tags=["fcm"])


class FcmTokenCreate(BaseModel):
    user_id: str
    fcm_token: str


@router.post("/register")
async def register_fcm_token(
    fcm_token: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    supabase = get_user_supabase(user["token"])
    
    try:
        # Check if the token already exists
        existing = (
            supabase.table("fcm_tokens")
            .select("*")
            .eq("user_id", user["user_id"])
            .eq("fcm_token", fcm_token)
            .execute()
        )
        if existing.data:
            return {"message": "FCM token already registered", "data": existing.data[0]}
            
        # Insert the new token
        response = (
            supabase.table("fcm_tokens")
            .insert({
                "user_id": user["user_id"],
                "fcm_token": fcm_token
            })
            .execute()
        )
        print(response.data)
        return {"message": "FCM token registered successfully", "data": response.data[0]}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register token: {str(e)}"
        )

class NotificationPayload(BaseModel):
    user_ids: list[str]
    title: str
    body: str

async def send_notification(
    title: str,
    body: str,
    user_ids: list[str],
    user: Dict[str, Any]
):
    supabase = get_user_supabase(user["token"])
    
    try:
        # Fetch FCM tokens for all provided user_ids
        response = (
            supabase.table("fcm_tokens")
            .select("fcm_token")
            .in_("user_id", user_ids)
            .execute()
        )
        
        tokens = [row["fcm_token"] for row in response.data]
        
        if not tokens:
            return {"message": "No valid FCM tokens found for the provided users", "success_count": 0}

        # Create multicast message
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            tokens=tokens
        )
        
        # Send a message to the devices corresponding to the provided registration tokens.
        batch_response = messaging.send_each_for_multicast(message)
        
        return {
            "message": "Notifications sent",
            "success_count": batch_response.success_count,
            "failure_count": batch_response.failure_count
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notifications: {str(e)}"
        )