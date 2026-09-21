"""
Authentication & Authorization Router
Provides staff JWT login/registration, RBAC dependencies, and Patient OTP verification.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import uuid
import random

from backend.database import get_db
from backend.models import Staff, Patient, MedicalHistory
from backend.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/staff/login", auto_error=False)

# In-memory store for OTP simulation: {contact_or_abha: {"otp": "123456", "expires_at": timestamp}}
_otp_store = {}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class StaffRegisterRequest(BaseModel):
    name: str
    username: str
    password: str
    role: str = "doctor"  # doctor | triage | admin
    department: str = "General Medicine"


class StaffLoginRequest(BaseModel):
    username: str
    password: str


class StaffResponse(BaseModel):
    staff_id: str
    name: str
    username: str
    role: str
    department: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    staff: StaffResponse


class SendOTPRequest(BaseModel):
    identifier: str  # Mobile number or ABHA ID


class VerifyOTPRequest(BaseModel):
    identifier: str
    otp: str


# ---------------------------------------------------------------------------
# Auth Dependencies
# ---------------------------------------------------------------------------
def get_current_staff(
    token: Optional[str] = Depends(oauth2_scheme),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Staff:
    """Validate JWT token and return authenticated Staff member."""
    raw_token = token
    if not raw_token and authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split(" ")[1]

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required (Bearer token missing)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(raw_token)
        staff_id = payload.get("sub")
        if not staff_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    staff = db.query(Staff).filter(Staff.staff_id == staff_id).first()
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff user no longer exists",
        )
    return staff


def require_role(allowed_roles: List[str]):
    """Decorator / dependency factory for Role-Based Access Control (RBAC)."""
    def role_checker(current_staff: Staff = Depends(get_current_staff)):
        if current_staff.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of roles: {', '.join(allowed_roles)}",
            )
        return current_staff
    return role_checker


# ---------------------------------------------------------------------------
# Endpoints: Staff Auth
# ---------------------------------------------------------------------------
@router.post("/staff/register", response_model=TokenResponse)
def register_staff(data: StaffRegisterRequest, db: Session = Depends(get_db)):
    """Register a new staff account (doctor, nurse/triage, or admin)."""
    existing = db.query(Staff).filter(Staff.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")

    staff = Staff(
        staff_id=str(uuid.uuid4()),
        name=data.name,
        username=data.username,
        role=data.role.lower(),
        department=data.department,
        password_hash=hash_password(data.password),
    )
    db.add(staff)
    db.commit()
    db.refresh(staff)

    token = create_access_token({
        "sub": staff.staff_id,
        "username": staff.username,
        "role": staff.role,
        "name": staff.name,
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "staff": {
            "staff_id": staff.staff_id,
            "name": staff.name,
            "username": staff.username,
            "role": staff.role,
            "department": staff.department,
        },
    }


@router.post("/staff/login", response_model=TokenResponse)
def login_staff(data: StaffLoginRequest, db: Session = Depends(get_db)):
    """Authenticate staff with username/password and return signed JWT."""
    staff = db.query(Staff).filter(Staff.username == data.username).first()
    if not staff or not verify_password(data.password, staff.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_access_token({
        "sub": staff.staff_id,
        "username": staff.username,
        "role": staff.role,
        "name": staff.name,
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "staff": {
            "staff_id": staff.staff_id,
            "name": staff.name,
            "username": staff.username,
            "role": staff.role,
            "department": staff.department,
        },
    }


@router.get("/staff/me", response_model=StaffResponse)
def get_me(current_staff: Staff = Depends(get_current_staff)):
    """Get the currently logged-in staff member profile."""
    return {
        "staff_id": current_staff.staff_id,
        "name": current_staff.name,
        "username": current_staff.username,
        "role": current_staff.role,
        "department": current_staff.department,
    }


# ---------------------------------------------------------------------------
# Endpoints: Patient OTP Login (ABHA / Mobile Simulation)
# ---------------------------------------------------------------------------
@router.post("/patient/send-otp")
def send_patient_otp(data: SendOTPRequest):
    """
    Generate and dispatch a 6-digit OTP for patient authentication (ABHA / Mobile).
    In development/demo mode, the OTP is returned directly for seamless testing.
    """
    if not data.identifier or len(data.identifier.strip()) < 3:
        raise HTTPException(status_code=400, detail="Invalid mobile number or ABHA ID")

    # Generate 6-digit OTP
    otp = f"{random.randint(100000, 999999)}"
    _otp_store[data.identifier.strip()] = otp

    return {
        "message": f"OTP successfully sent to {data.identifier}",
        "identifier": data.identifier,
        "demo_otp": otp,  # Included for demo/hackathon ease of testing
    }


@router.post("/patient/verify-otp")
def verify_patient_otp(data: VerifyOTPRequest, db: Session = Depends(get_db)):
    """Verify submitted OTP and return or auto-create patient profile."""
    identifier = data.identifier.strip()
    expected_otp = _otp_store.get(identifier)

    # Allow universal fallback demo OTP '123456' or exact match
    if data.otp != "123456" and (not expected_otp or expected_otp != data.otp.strip()):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    # Clean OTP store
    _otp_store.pop(identifier, None)

    # Check if patient exists by contact or ABHA
    patient = (
        db.query(Patient)
        .filter((Patient.contact == identifier) | (Patient.abha_id == identifier) | (Patient.name == identifier))
        .first()
    )

    is_new = False
    if not patient:
        is_new = True
        patient = Patient(
            patient_id=str(uuid.uuid4()),
            name=f"Patient-{identifier[-4:] if len(identifier)>=4 else 'User'}",
            contact=identifier if identifier.isdigit() else None,
            abha_id=identifier if not identifier.isdigit() else None,
            preferred_language="English",
        )
        db.add(patient)
        history = MedicalHistory(
            history_id=str(uuid.uuid4()),
            patient_id=patient.patient_id,
            allergies=[],
            chronic_conditions=[],
            current_medications=[],
            past_diagnoses=[],
        )
        db.add(history)
        db.commit()
        db.refresh(patient)

    history = db.query(MedicalHistory).filter(MedicalHistory.patient_id == patient.patient_id).first()

    # Generate patient session token
    patient_token = create_access_token({
        "sub": patient.patient_id,
        "role": "patient",
        "name": patient.name,
    })

    return {
        "message": "OTP verified successfully",
        "is_new_user": is_new,
        "access_token": patient_token,
        "token_type": "bearer",
        "patient": {
            "patient_id": patient.patient_id,
            "name": patient.name,
            "age": patient.age,
            "gender": patient.gender,
            "contact": patient.contact,
            "preferred_language": patient.preferred_language,
            "abha_id": patient.abha_id,
            "history": {
                "allergies": history.allergies if history else [],
                "chronic_conditions": history.chronic_conditions if history else [],
                "current_medications": history.current_medications if history else [],
                "past_diagnoses": history.past_diagnoses if history else [],
            },
        },
    }


# ---------------------------------------------------------------------------
# Database Seed Helper for Demo Staff
# ---------------------------------------------------------------------------
def seed_default_staff(db: Session):
    """Seed demo doctor, triage nurse, and admin accounts if they do not exist."""
    demo_accounts = [
        {
            "name": "Dr. Ananya Sharma",
            "username": "dr.sharma",
            "password": "doctor123",
            "role": "doctor",
            "department": "Emergency Medicine",
        },
        {
            "name": "Nurse Rajesh Kumar",
            "username": "triage.nurse",
            "password": "triage123",
            "role": "triage",
            "department": "Triage / Intake",
        },
        {
            "name": "Hospital Admin",
            "username": "admin",
            "password": "admin123",
            "role": "admin",
            "department": "Hospital Administration",
        },
    ]

    for acc in demo_accounts:
        existing = db.query(Staff).filter(Staff.username == acc["username"]).first()
        if not existing:
            staff = Staff(
                staff_id=str(uuid.uuid4()),
                name=acc["name"],
                username=acc["username"],
                role=acc["role"],
                department=acc["department"],
                password_hash=hash_password(acc["password"]),
            )
            db.add(staff)
    try:
        db.commit()
    except Exception:
        db.rollback()
