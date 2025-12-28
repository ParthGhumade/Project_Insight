# authentication.py

import os
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException, status
from typing import Dict, Any

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError("SUPABASE_URL or SUPABASE_ANON_KEY is missing")
    
# ---------------------------
# Supabase helpers (FIRST)
# ---------------------------

def get_user_supabase(token: str) -> Client:
    return create_client(
        SUPABASE_URL,
        SUPABASE_ANON_KEY,
        options=ClientOptions(
            headers={
                "Authorization": f"Bearer {token}"
            }
        )
    )

# ---------------------------
# Base client (optional)
# ---------------------------


security = HTTPBearer(auto_error=False)

# ---------------------------
# Authentication dependency
# ---------------------------

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:

    token = credentials.credentials

    # FIX: Call the function to get the client
    supabase_client = get_user_supabase(token)
    user_response = supabase_client.auth.get_user(token)

    if not user_response or not user_response.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    user = user_response.user

    return {
        "user_id": user.id,
        "email": user.email,
        "token": token
    }

    
#---------------------------
#     Authorisation Logic    
#---------------------------

def get_role(credentials: HTTPAuthorizationCredentials=Depends(security)):

    token=credentials.credentials
    # FIX: Call the function to get the client
    supabase_client = get_user_supabase(token)
    auth_user=supabase_client.auth.get_user(token)
    
    if not auth_user:
        raise HTTPException(status_code=401,detail="Invalid Token")
    
    user_id=auth_user.user.id

    # FIX: Use the client instance
    profile=(supabase_client.table("profiles").select("role").eq("id",user_id).single().execute())

    if not profile.data:
        raise HTTPException( status_code=403,detail="Profile Not Found")
    


    return{
            "id": user_id,
            "role":profile.data["role"]
    }


def require_doctor(user=Depends(get_role)):
    
    if user["role"]!="doctor":
        raise HTTPException(status_code=403,detail="Doctor Access Required")
    

    return user

def require_patient(user=Depends(get_role)):
    
    if user["role"]!="patient":
        raise HTTPException(status_code=403,detail="Patient Access Required")
    

    return user

