from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from authentication import get_current_user, supabase

app = FastAPI()

# --- Schemas ---
class UserProfile(BaseModel):
    id: str
    name: str # From profiles table
    role: str # From profiles table
    email: str # From auth

# --- Endpoints ---

@app.get("/me", response_model=UserProfile)
def get_current_user_profile(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Fetches the current authenticated user's profile.
    Combines auth info (email) with profile info (name, role).
    """

    # Extract auth info
    user_id = user.get("user_id")
    email = user.get("email")

    print("=== /me endpoint called ===")
    print("Auth user_id:", user_id)
    print("Auth email:", email)

    if not user_id:
        print("ERROR: user_id missing from auth payload")
        raise HTTPException(status_code=401, detail="Invalid auth payload")

    try:
        # IMPORTANT: .single() MUST be inside try
        response = (
            supabase
            .table("profiles")
            .select("id, name, role")
            .eq("id", user_id)
            .single()
            .execute()
        )

        print("Supabase raw response:", response)

        data = response.data
        print("Profile data fetched:", data)

        return UserProfile(
            id=data["id"],
            name=data["name"],
            role=data["role"],
            email=email
        )

    except Exception as e:
        print("Profile Fetch Error:", e)
        print("Failed user_id:", user_id)

        raise HTTPException(
            status_code=404,
            detail="User profile not found"
        )

#-----------------------------
# Server health
#-----------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

#-----------------------------
# Search doctors
#-----------------------------
@app.get("/doctors/search")
def search_doctors(query: str):
   
   response=(supabase.table("profiles").select("id","name","role").eq("role","doctor").execute())

   return response.data





