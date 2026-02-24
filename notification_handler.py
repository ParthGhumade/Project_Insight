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
    print(f"DEBUG /fcm/register: Received fcm_token={fcm_token}")
    print(f"DEBUG /fcm/register: Authenticated user_id={user.get('user_id')}")
    supabase = get_user_supabase(user["token"])
    print("DEBUG /fcm/register: Supabase client initialized")
    
    try:
        # Check if the token already exists
        print(f"DEBUG /fcm/register: Checking for existing token for user_id={user['user_id']}")
        existing = (
            supabase.table("fcm_tokens")
            .select("*")
            .eq("user_id", user["user_id"])
            .eq("fcm_token", fcm_token)
            .execute()
        )
        print(f"DEBUG /fcm/register: Existing token query result: {existing.data}")
        if existing.data:
            print("DEBUG /fcm/register: FCM token already registered. Returning.")
            return {"message": "FCM token already registered", "data": existing.data[0]}
            
        # Insert the new token
        print("DEBUG /fcm/register: Token not found, inserting new fcm_token...")
        response = (
            supabase.table("fcm_tokens")
            .insert({
                "user_id": user["user_id"],
                "fcm_token": fcm_token
            })
            .execute()
        )
        print(f"DEBUG /fcm/register: Insert successful. DB Response: {response.data}")
        return {"message": "FCM token registered successfully", "data": response.data[0]}
    except Exception as e:
        print(f"DEBUG /fcm/register: Exception occurred: {e}")
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
    print(f"DEBUG send_notification: Sending notification title='{title}', user_ids={user_ids}")
    supabase = get_user_supabase(user["token"])
    print("DEBUG send_notification: Supabase client initialized")
    
    try:
        # Fetch FCM tokens for all provided user_ids
        print(f"DEBUG send_notification: Fetching FCM tokens from DB for users: {user_ids}")
        response = (
            supabase.table("fcm_tokens")
            .select("fcm_token")
            .in_("user_id", user_ids)
            .execute()
        )
        print(f"DEBUG send_notification: Fetched DB response data: {response.data}")
        
        tokens = [row["fcm_token"] for row in response.data]
        print(f"DEBUG send_notification: Extracted tokens from DB: {tokens}")
        
        if not tokens:
            print("DEBUG send_notification: No valid FCM tokens found for the provided users. Returning.")
            return {"message": "No valid FCM tokens found for the provided users", "success_count": 0}

        # Create multicast message
        print("DEBUG send_notification: Creating MulticastMessage object...")
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            tokens=tokens
        )
        
        # Send a message to the devices corresponding to the provided registration tokens.
        print("DEBUG send_notification: Calling Firebase messaging.send_each_for_multicast...")
        batch_response = messaging.send_each_for_multicast(message)
        print(f"DEBUG send_notification: Batch response received. Success={batch_response.success_count}, Failure={batch_response.failure_count}")
        
        return {
            "message": "Notifications sent",
            "success_count": batch_response.success_count,
            "failure_count": batch_response.failure_count
        }

    except Exception as e:
        print(f"DEBUG send_notification: Exception occurred: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notifications: {str(e)}"
        )