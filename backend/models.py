from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import uuid


def gen_uuid():
    return str(uuid.uuid4())


class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    age = Column(Integer)
    gender = Column(String)
    contact = Column(String)
    preferred_language = Column(String, default="English")
    abha_id = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    cases = relationship("Case", back_populates="patient")
    history = relationship("MedicalHistory", back_populates="patient", uselist=False)


class MedicalHistory(Base):
    __tablename__ = "medical_history"

    history_id = Column(String, primary_key=True, default=gen_uuid)
    patient_id = Column(String, ForeignKey("patients.patient_id"), unique=True)
    allergies = Column(JSON, default=list)           # ["penicillin", "dust"]
    chronic_conditions = Column(JSON, default=list)  # ["diabetes", "hypertension"]
    current_medications = Column(JSON, default=list) # ["metformin 500mg"]
    past_diagnoses = Column(JSON, default=list)

    patient = relationship("Patient", back_populates="history")


class Case(Base):
    __tablename__ = "cases"

    case_id = Column(String, primary_key=True, default=gen_uuid)
    patient_id = Column(String, ForeignKey("patients.patient_id"))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    chief_complaint = Column(String)
    symptom_details = Column(JSON)          # structured summary dict
    conversation_transcript = Column(JSON, default=list)  # list of {role, text}
    urgency_flag = Column(Boolean, default=False)
    urgency_reason = Column(Text, nullable=True)
    doctor_notes = Column(Text, nullable=True)
    attachments = Column(JSON, default=list)  # list of file URLs / relative paths
    status = Column(String, default="waiting")  # waiting | in-review | completed
    department = Column(String, nullable=True)

    patient = relationship("Patient", back_populates="cases")
    queue_entry = relationship("Queue", back_populates="case", uselist=False)


class Queue(Base):
    __tablename__ = "queue"

    queue_id = Column(String, primary_key=True, default=gen_uuid)
    case_id = Column(String, ForeignKey("cases.case_id"), unique=True)
    position = Column(Integer)
    priority_flag = Column(Boolean, default=False)
    department = Column(String, default="general")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    case = relationship("Case", back_populates="queue_entry")


class Staff(Base):
    __tablename__ = "staff"

    staff_id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    role = Column(String)          # doctor | triage | admin
    department = Column(String)
    username = Column(String, unique=True)
    password_hash = Column(String)
