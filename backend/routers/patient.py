"""
Patient router — register, login, fetch patient + history.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import uuid

from backend.database import get_db
from backend.models import Patient, MedicalHistory

router = APIRouter(prefix="/patient", tags=["patient"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class PatientRegister(BaseModel):
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    contact: Optional[str] = None
    preferred_language: str = "English"
    abha_id: Optional[str] = None


class PatientLogin(BaseModel):
    identifier: str  # name OR abha_id


class HistoryUpdate(BaseModel):
    allergies: Optional[list[str]] = None
    chronic_conditions: Optional[list[str]] = None
    current_medications: Optional[list[str]] = None
    past_diagnoses: Optional[list[str]] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/register")
def register_patient(data: PatientRegister, db: Session = Depends(get_db)):
    """Create a new patient profile."""
    # Check for duplicate ABHA ID
    if data.abha_id:
        existing = db.query(Patient).filter(Patient.abha_id == data.abha_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="ABHA ID already registered")

    patient = Patient(
        patient_id=str(uuid.uuid4()),
        name=data.name,
        age=data.age,
        gender=data.gender,
        contact=data.contact,
        preferred_language=data.preferred_language,
        abha_id=data.abha_id,
    )
    db.add(patient)

    # Create empty medical history record
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

    return {"patient_id": patient.patient_id, "name": patient.name, "message": "Registered successfully"}


@router.post("/login")
def login_patient(data: PatientLogin, db: Session = Depends(get_db)):
    """Find patient by name or ABHA ID."""
    patient = (
        db.query(Patient)
        .filter(
            (Patient.name == data.identifier) |
            (Patient.abha_id == data.identifier)
        )
        .first()
    )
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found. Please register first.")

    history = db.query(MedicalHistory).filter(
        MedicalHistory.patient_id == patient.patient_id
    ).first()

    return {
        "patient_id": patient.patient_id,
        "name": patient.name,
        "preferred_language": patient.preferred_language,
        "history": {
            "allergies": history.allergies if history else [],
            "chronic_conditions": history.chronic_conditions if history else [],
            "current_medications": history.current_medications if history else [],
            "past_diagnoses": history.past_diagnoses if history else [],
        },
    }


@router.get("/{patient_id}")
def get_patient(patient_id: str, db: Session = Depends(get_db)):
    """Fetch full patient profile with medical history."""
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    history = db.query(MedicalHistory).filter(
        MedicalHistory.patient_id == patient_id
    ).first()

    return {
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
    }


@router.put("/{patient_id}/history")
def update_history(patient_id: str, data: HistoryUpdate, db: Session = Depends(get_db)):
    """Patient manually updates their medical history."""
    history = db.query(MedicalHistory).filter(
        MedicalHistory.patient_id == patient_id
    ).first()
    if not history:
        raise HTTPException(status_code=404, detail="Patient history not found")

    if data.allergies is not None:
        history.allergies = data.allergies
    if data.chronic_conditions is not None:
        history.chronic_conditions = data.chronic_conditions
    if data.current_medications is not None:
        history.current_medications = data.current_medications
    if data.past_diagnoses is not None:
        history.past_diagnoses = data.past_diagnoses

    db.commit()
    return {"message": "History updated successfully"}
