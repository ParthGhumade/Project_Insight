import os
from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Configuration ---
# Fail closed if credentials are missing
SUPABASE_URL = os.getenv("SUPABASE_URL")
# Prefer SUPABASE_ANON_KEY, fallback to SUPABASE_KEY for backward compatibility
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL:
    raise RuntimeError("Critical: SUPABASE_URL is not set in environment variables.")

if not SUPABASE_ANON_KEY:
    raise RuntimeError("Critical: SUPABASE_ANON_KEY (or SUPABASE_KEY) is not set in environment variables.")

# --- Supabase Client ---
# Initialize with the anon key. This client is safe for client-side operations 
# and respects Row Level Security (RLS).
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# --- Authentication Logic ---
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Validates the Bearer token using Supabase Auth.
    
    Returns:
        A dictionary containing minimal user info (id, email) if valid.
        
    Raises:
        HTTPException(401): If the token is invalid, expired, or missing.
    """
    token = credentials.credentials
    
    try:
        # get_user() validates the JWT signature and expiration against the project's secret
        user_response = supabase.auth.get_user(token)
        
        if not user_response or not user_response.user:
            raise ValueError("No user returned from Supabase")
            
        user = user_response.user
        
        # Return minimal user object as requested
        return {
            "user_id": user.id,
            "email": user.email
        }
        
    except Exception as e:
        # Log the error internally if needed (print for now, replace with logger later)
        print(f"Authentication Failed: {str(e)}")
        
        # Fail closed with generic message
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )