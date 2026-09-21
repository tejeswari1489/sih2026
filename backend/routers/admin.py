"""
Admin Router — Hospital operations, staff management, department routing, and analytics.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid

from backend.database import get_db
from backend.models import Staff, Patient, Case, Queue, MedicalHistory
from backend.services.auth_service import hash_password
from backend.routers.auth import require_role, get_current_staff

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class StaffCreateRequest(BaseModel):
    name: str
    username: str
    password: str
    role: str = "doctor"  # doctor | triage | admin
    department: str = "General Medicine"


class StaffItem(BaseModel):
    staff_id: str
    name: str
    username: str
    role: str
    department: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints: Analytics & KPIs
# ---------------------------------------------------------------------------
@router.get("/analytics")
def get_hospital_analytics(db: Session = Depends(get_db)):
    """
    Returns high-level hospital KPI metrics:
    - Total patient volume
    - Active waiting queue count
    - Urgent cases flagged and % rate
    - Language distribution
    - Department case volume breakdown
    - Estimated average wait time (minutes)
    """
    total_patients = db.query(Patient).count()
    total_cases = db.query(Case).count()
    active_queue = db.query(Queue).count()

    waiting_cases = db.query(Case).filter(Case.status == "waiting").count()
    in_review_cases = db.query(Case).filter(Case.status == "in-review").count()
    completed_cases = db.query(Case).filter(Case.status == "completed").count()

    urgent_cases_count = db.query(Case).filter(Case.urgency_flag == True).count()
    urgent_rate = round((urgent_cases_count / total_cases * 100), 1) if total_cases > 0 else 0.0

    # Language breakdown across patients
    lang_counts = (
        db.query(Patient.preferred_language, func.count(Patient.patient_id))
        .group_by(Patient.preferred_language)
        .all()
    )
    languages = {lang or "Unknown": count for lang, count in lang_counts}

    # Department breakdown across cases
    dept_counts = (
        db.query(Case.department, func.count(Case.case_id))
        .group_by(Case.department)
        .all()
    )
    departments = {dept or "General Medicine": count for dept, count in dept_counts}

    # Estimated average wait time: 10 mins per waiting patient in queue
    avg_wait_minutes = active_queue * 10

    return {
        "total_patients": total_patients,
        "total_cases": total_cases,
        "active_queue": active_queue,
        "waiting_cases": waiting_cases,
        "in_review_cases": in_review_cases,
        "completed_cases": completed_cases,
        "urgent_cases": urgent_cases_count,
        "urgent_percentage": urgent_rate,
        "avg_wait_minutes": avg_wait_minutes,
        "languages": languages,
        "departments": departments,
    }


# ---------------------------------------------------------------------------
# Endpoints: Staff Management
# ---------------------------------------------------------------------------
@router.get("/staff", response_model=List[StaffItem])
def list_staff(db: Session = Depends(get_db)):
    """List all registered medical and administrative staff."""
    staff_list = db.query(Staff).all()
    return [
        {
            "staff_id": s.staff_id,
            "name": s.name,
            "username": s.username,
            "role": s.role,
            "department": s.department,
        }
        for s in staff_list
    ]


@router.post("/staff", response_model=StaffItem)
def create_staff(
    data: StaffCreateRequest,
    db: Session = Depends(get_db),
    admin_user: Staff = Depends(require_role("admin")),
):
    """Create a new staff member (Doctor, Nurse/Triage, Admin). Restricted to Admins."""
    existing = db.query(Staff).filter(Staff.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    new_staff = Staff(
        staff_id=str(uuid.uuid4()),
        name=data.name,
        username=data.username,
        password_hash=hash_password(data.password),
        role=data.role.lower(),
        department=data.department,
    )
    db.add(new_staff)
    db.commit()
    db.refresh(new_staff)

    return {
        "staff_id": new_staff.staff_id,
        "name": new_staff.name,
        "username": new_staff.username,
        "role": new_staff.role,
        "department": new_staff.department,
    }


@router.delete("/staff/{staff_id}")
def delete_staff(
    staff_id: str,
    db: Session = Depends(get_db),
    admin_user: Staff = Depends(require_role("admin")),
):
    """Delete a staff member account. Restricted to Admins."""
    target = db.query(Staff).filter(Staff.staff_id == staff_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Staff member not found")

    if target.username == admin_user.username:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account")

    db.delete(target)
    db.commit()
    return {"message": f"Staff member '{target.name}' ({target.username}) deleted successfully"}


# ---------------------------------------------------------------------------
# Endpoints: Hospital Cases Audit Log
# ---------------------------------------------------------------------------
@router.get("/cases")
def audit_cases(
    urgency_only: bool = False,
    department: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Hospital-wide case audit trail with filtering.
    """
    query = db.query(Case).join(Patient)

    if urgency_only:
        query = query.filter(Case.urgency_flag == True)
    if department:
        query = query.filter(Case.department == department)

    cases = query.order_by(Case.timestamp.desc()).limit(limit).all()

    results = []
    for c in cases:
        p = c.patient
        results.append({
            "case_id": c.case_id,
            "patient_name": p.name if p else "Unknown",
            "patient_age": p.age if p else None,
            "patient_gender": p.gender if p else None,
            "preferred_language": p.preferred_language if p else "English",
            "chief_complaint": c.chief_complaint,
            "urgency_flag": c.urgency_flag,
            "urgency_reason": c.urgency_reason,
            "status": c.status,
            "department": c.department or "General Medicine",
            "timestamp": c.timestamp.isoformat() if c.timestamp else None,
            "attachments_count": len(c.attachments) if c.attachments else 0,
        })

    return {"total": len(results), "cases": results}


# ---------------------------------------------------------------------------
# Endpoints: Department Overview
# ---------------------------------------------------------------------------
@router.get("/departments")
def get_departments_summary(db: Session = Depends(get_db)):
    """List hospital departments with active queue load and assigned doctor counts."""
    known_depts = [
        "General Medicine",
        "Cardiology",
        "Orthopedics",
        "Dermatology",
        "Pediatrics",
        "Neurology",
        "ENT",
        "Emergency",
    ]

    summary = []
    for dept in known_depts:
        doctor_count = db.query(Staff).filter(Staff.department == dept, Staff.role == "doctor").count()
        active_waiting = (
            db.query(Queue)
            .filter(Queue.department == dept)
            .count()
        )
        total_cases = db.query(Case).filter(Case.department == dept).count()
        summary.append({
            "department": dept,
            "doctors_count": doctor_count,
            "active_waiting_queue": active_waiting,
            "total_lifetime_cases": total_cases,
        })

    return {"departments": summary}
