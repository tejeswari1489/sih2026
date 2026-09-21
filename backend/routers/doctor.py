import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import Optional

from backend.database import get_db
from backend.models import Case, Queue, Patient, MedicalHistory
from backend.services.websocket_manager import ws_manager

router = APIRouter(prefix="/doctor", tags=["doctor"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ReviewCase(BaseModel):
    notes: Optional[str] = None


class ReorderQueue(BaseModel):
    case_id: str
    new_position: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/queue")
def get_queue(department: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Get all waiting patients in the queue.
    Urgent/flagged cases appear first, then by arrival order.
    """
    query = db.query(Queue).filter(
        Queue.case_id.in_(
            db.query(Case.case_id).filter(Case.status == "waiting")
        )
    )
    if department:
        query = query.filter(Queue.department == department)

    queue_entries = query.order_by(
        desc(Queue.priority_flag),   # urgent first
        Queue.position,              # then by position
        Queue.created_at,            # then by arrival time
    ).all()

    result = []
    for entry in queue_entries:
        case = db.query(Case).filter(Case.case_id == entry.case_id).first()
        patient = db.query(Patient).filter(Patient.patient_id == case.patient_id).first()
        result.append({
            "queue_id": entry.queue_id,
            "position": entry.position,
            "priority_flag": entry.priority_flag,
            "department": entry.department,
            "arrived_at": entry.created_at.isoformat() if entry.created_at else None,
            "case": {
                "case_id": case.case_id,
                "chief_complaint": case.chief_complaint,
                "urgency_flag": case.urgency_flag,
                "urgency_reason": case.urgency_reason,
                "status": case.status,
                "attachments_count": len(case.attachments) if getattr(case, "attachments", None) else 0,
            },
            "patient": {
                "patient_id": patient.patient_id,
                "name": patient.name,
                "age": patient.age,
                "gender": patient.gender,
            } if patient else {},
        })

    return {"queue": result, "total": len(result)}


@router.get("/case/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db)):
    """Full structured case view for the doctor."""
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    patient = db.query(Patient).filter(Patient.patient_id == case.patient_id).first()
    history = db.query(MedicalHistory).filter(
        MedicalHistory.patient_id == case.patient_id
    ).first()

    # Past visits for this patient (excluding current)
    past_cases = db.query(Case).filter(
        Case.patient_id == case.patient_id,
        Case.case_id != case_id,
        Case.status == "completed",
    ).order_by(desc(Case.timestamp)).limit(5).all()

    return {
        "case_id": case.case_id,
        "timestamp": case.timestamp.isoformat() if case.timestamp else None,
        "status": case.status,
        "chief_complaint": case.chief_complaint,
        "symptom_details": case.symptom_details,
        "urgency_flag": case.urgency_flag,
        "urgency_reason": case.urgency_reason,
        "doctor_notes": getattr(case, "doctor_notes", None),
        "attachments": getattr(case, "attachments", []) or [],
        "department": case.department,
        "patient": {
            "patient_id": patient.patient_id,
            "name": patient.name,
            "age": patient.age,
            "gender": patient.gender,
            "preferred_language": patient.preferred_language,
            "contact": patient.contact,
        } if patient else {},
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
                "symptom_details": c.symptom_details,
                "doctor_notes": getattr(c, "doctor_notes", None),
                "attachments": getattr(c, "attachments", []) or [],
            }
            for c in past_cases
        ],
    }


@router.post("/case/{case_id}/review")
async def mark_reviewed(case_id: str, data: ReviewCase, db: Session = Depends(get_db)):
    """Mark a case as reviewed (waiting/in-review -> completed) and save doctor consultation notes."""
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case.status = "completed"
    if data.notes:
        case.doctor_notes = data.notes
    db.commit()

    # Broadcast queue update to connected clients
    try:
        await ws_manager.broadcast({
            "event": "case_completed",
            "case_id": case_id,
            "patient_id": case.patient_id,
        })
    except Exception as e:
        print(f"[doctor] WebSocket broadcast notice: {e}")

    return {"message": "Case marked as reviewed", "case_id": case_id, "notes_saved": bool(data.notes)}


@router.post("/queue/reorder")
async def reorder_queue(data: ReorderQueue, db: Session = Depends(get_db)):
    """Manually reorder a patient's queue position (doctor/triage decision)."""
    entry = db.query(Queue).filter(Queue.case_id == data.case_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")

    entry.position = data.new_position
    db.commit()

    # Broadcast reorder event to connected clients
    try:
        await ws_manager.broadcast({
            "event": "queue_reordered",
            "case_id": data.case_id,
            "new_position": data.new_position,
        })
    except Exception as e:
        print(f"[doctor] WebSocket broadcast notice: {e}")

    return {"message": "Queue updated", "case_id": data.case_id, "new_position": data.new_position}
