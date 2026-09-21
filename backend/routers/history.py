"""
History router — read and update a patient's medical history.
GET  /history/{patient_id}  → fetch full history
PUT  /history/{patient_id}  → patient/doctor updates history fields
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from backend.database import get_db
from backend.models import Patient, MedicalHistory, Case
from sqlalchemy import desc
import uuid

router = APIRouter(prefix="/history", tags=["history"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class HistoryUpdate(BaseModel):
    allergies: Optional[list[str]] = None
    chronic_conditions: Optional[list[str]] = None
    current_medications: Optional[list[str]] = None
    past_diagnoses: Optional[list[str]] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/{patient_id}")
def get_history(patient_id: str, db: Session = Depends(get_db)):
    """Fetch full medical history for a patient, plus their last 10 case summaries."""
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    history = db.query(MedicalHistory).filter(
        MedicalHistory.patient_id == patient_id
    ).first()

    # Last 10 completed cases (for longitudinal history)
    past_cases = (
        db.query(Case)
        .filter(Case.patient_id == patient_id)
        .order_by(desc(Case.timestamp))
        .limit(10)
        .all()
    )

    return {
        "patient_id": patient_id,
        "name": patient.name,
        "medical_history": {
            "allergies": history.allergies if history else [],
            "chronic_conditions": history.chronic_conditions if history else [],
            "current_medications": history.current_medications if history else [],
            "past_diagnoses": history.past_diagnoses if history else [],
        },
        "past_visits": [
            {
                "case_id": c.case_id,
                "date": c.timestamp.isoformat() if c.timestamp else None,
                "chief_complaint": c.chief_complaint,
                "urgency_flag": c.urgency_flag,
                "status": c.status,
                "symptom_details": c.symptom_details,
            }
            for c in past_cases
        ],
    }


@router.put("/{patient_id}")
def update_history(patient_id: str, data: HistoryUpdate, db: Session = Depends(get_db)):
    """
    Update a patient's medical history (partial update — only send fields to change).
    Creates a history record if one doesn't exist yet.
    """
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    history = db.query(MedicalHistory).filter(
        MedicalHistory.patient_id == patient_id
    ).first()

    # Auto-create if missing
    if not history:
        history = MedicalHistory(
            history_id=str(uuid.uuid4()),
            patient_id=patient_id,
            allergies=[],
            chronic_conditions=[],
            current_medications=[],
            past_diagnoses=[],
        )
        db.add(history)

    if data.allergies is not None:
        history.allergies = data.allergies
    if data.chronic_conditions is not None:
        history.chronic_conditions = data.chronic_conditions
    if data.current_medications is not None:
        history.current_medications = data.current_medications
    if data.past_diagnoses is not None:
        history.past_diagnoses = data.past_diagnoses

    db.commit()
    db.refresh(history)

    return {
        "message": "Medical history updated successfully",
        "patient_id": patient_id,
        "medical_history": {
            "allergies": history.allergies,
            "chronic_conditions": history.chronic_conditions,
            "current_medications": history.current_medications,
            "past_diagnoses": history.past_diagnoses,
        },
    }
