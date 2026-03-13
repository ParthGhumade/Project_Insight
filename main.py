from fastapi import FastAPI, Depends, HTTPException,Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List
from authentication import get_current_user, get_user_supabase
from datetime import datetime, timezone
import notification_handler
import family_handler


app = FastAPI(title="Project Insight")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(notification_handler.router)
app.include_router(family_handler.router)

# -----------------------------
# Schemas
# -----------------------------

class UserProfile(BaseModel):
    id: str
    name: str
    role: str
    email: str


class Medicine(BaseModel):
    name: str
    brand: str
    frequency: str
    duration: str


class PrescriptionContent(BaseModel):
    medicines: List[Medicine]
    follow_up_date: str
    notes: str


class PrescriptionCreate(BaseModel):
    patient_id: str
    content: PrescriptionContent

class GrantHistoryAccess(BaseModel):
    doctor_id: str
    expires_at: str

# -----------------------------
# Health
# -----------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


# -----------------------------
# Current user profile
# -----------------------------

@app.get("/me", response_model=UserProfile)
def get_current_user_profile(
    user: Dict[str, Any] = Depends(get_current_user)
):
    print("AUTH USER PAYLOAD:", user)

    user_supabase = get_user_supabase(user["token"])

    response = (
    user_supabase
    .table("profiles")
    .select("id, name, role")
    .eq("id", user["user_id"])
    .execute()
    )

    print("DATA:", response.data)
    # Changed to print full response for debugging as .error attribute does not exist
    print("FULL RESPONSE:", response)




    if not response.data:
        raise HTTPException(status_code=404, detail="Profile not found")

    data = response.data[0]

    return UserProfile(
        id=data["id"],
        name=data["name"],
        role=data["role"],
        email=user["email"]
    )


# -----------------------------
# Search patients
# -----------------------------

@app.get("/patients/search")
def search_patients(
    q: str = Query(None),
    user: Dict[str, Any] = Depends(get_current_user)
):
    user_supabase = get_user_supabase(user["token"])

    query = (
        user_supabase
        .table("profiles")
        .select("id, name")
        .eq("role", "patient")
    )

    if q:
        query = query.ilike("name", f"%{q}%")

    resp = query.execute()
    return resp.data


# -----------------------------
# Fetch prescription
# -----------------------------


@app.get("/history/{patient_id}")
def get_patient_history(
    patient_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    supabase = get_user_supabase(user["token"])

    resp = (
        supabase
        .table("prescriptions")
        .select("*")
        .eq("patient_id", patient_id)
        .order("created_at", desc=True)
        .execute()
    )

    print(resp.data)
    return resp.data

@app.get("/history/doctor/{doctor_id}")
def get_doctor_prescription_history(
    doctor_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    supabase = get_user_supabase(user["token"])

    # 🔒 Optional safety check (can remove if you want it fully open for now)
    # Ensures a doctor can only view their own prescriptions
    if user["user_id"] != doctor_id:
        raise HTTPException(
            status_code=403,
            detail="You can only view your own prescription history"
        )

    resp = (
        supabase
        .table("prescriptions")
        .select("*")
        .eq("doctor_id", doctor_id)
        .order("created_at", desc=True)
        .execute()
    )

    return resp.data


# -----------------------------
# Doctor's own prescriptions
# -----------------------------

@app.get("/prescriptions/mine")
def get_my_prescriptions(
    user: Dict[str, Any] = Depends(get_current_user)
):
    supabase = get_user_supabase(user["token"])
    doctor_id = user["user_id"]

    # Ensure caller is a doctor
    profile = (
        supabase
        .table("profiles")
        .select("role")
        .eq("id", doctor_id)
        .execute()
    )

    if not profile.data or profile.data[0]["role"] != "doctor":
        raise HTTPException(status_code=403, detail="Doctors only")

    resp = (
        supabase
        .table("prescriptions")
        .select("*")
        .eq("doctor_id", doctor_id)
        .order("created_at", desc=True)
        .execute()
    )

    return {"data": resp.data}


# -----------------------------
# Create prescriptions
# -----------------------------

from notification_handler import send_notification

@app.post("/prescriptions")
async def create_prescription(
    data: PrescriptionCreate,
    user: Dict[str, Any] = Depends(get_current_user)
):
    user_supabase = get_user_supabase(user["token"])
    doctor_id = user["user_id"]

    doctor_profile = (
        user_supabase
        .table("profiles")
        .select("name")
        .eq("id", doctor_id)
        .execute()
    )

    if not doctor_profile.data:
        raise HTTPException(status_code=403, detail="Doctor profile not found")
        
    doctor_name = doctor_profile.data[0]["name"]

    user_supabase.table("prescriptions").insert({
        "doctor_id": doctor_id,
        "doctor_name": doctor_name,
        "patient_id": data.patient_id,
        "content": data.model_dump()
    }).execute()
    
    # Send push notification to the patient
    try:
        await send_notification(
            title="New Prescription Received",
            body=f"Dr. {doctor_name} has just uploaded a new prescription for you. Please check the history tab.",
            user_ids=[data.patient_id],
            user=user
        )
    except Exception as e:
        print(f"Non-fatal error: Failed to send notification to patient: {e}")

    return {
        "status": "success",
        "message": "Prescription created successfully"
    }

# -----------------------------
# prescription access
# -----------------------------

@app.post("/prescriptions/grant-access")
def grant_history_access(
    payload: GrantHistoryAccess,
    user: Dict[str, Any] = Depends(get_current_user)
):
    user_supabase = get_user_supabase(user["token"])
    patient_id = user["user_id"]

    print("AUTH USER:", user["user_id"])
    print("INSERT patient_id:", user["user_id"])


    user_supabase.table("prescription_access").insert({
        "patient_id": patient_id,
        "doctor_id": payload.doctor_id,
        "expires_at": payload.expires_at
    }).execute()

    return {"status": "history access granted"}






