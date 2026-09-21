"""
Chat router — conversational intake API.
POST /chat/start    → start a new intake session
POST /chat/message  → send a patient message, get AI reply
POST /chat/submit   → finalize case, run urgency check, add to queue
POST /chat/tts      → synthesise TTS audio for an AI reply text
POST /chat/stt      → transcribe patient voice recording to text
"""

import asyncio
import os 
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import shutil

from backend.database import get_db
from backend.models import Patient, MedicalHistory, Case, Queue
from backend.services import ai_service, urgency_service, tts_service, stt_service
from backend.services.websocket_manager import ws_manager

router = APIRouter(prefix="/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class StartSession(BaseModel):
    patient_id: str
    language: str = "English"
    first_complaint: str


class SendMessage(BaseModel):
    session_id: str
    text: str


class FinishSession(BaseModel):
    session_id: str


class SubmitCase(BaseModel):
    session_id: str
    patient_id: str
    department: Optional[str] = "general"
    attachments: Optional[List[str]] = []


class TTSRequest(BaseModel):
    text: str
    language: str = "English"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/start")
def start_chat(data: StartSession, db: Session = Depends(get_db)):
    """
    Start a new intake session for a patient.
    Loads existing medical history to avoid repeating known information.
    """
    # Load patient history for context injection
    history_record = db.query(MedicalHistory).filter(
        MedicalHistory.patient_id == data.patient_id
    ).first()

    history_dict = None
    if history_record:
        history_dict = {
            "allergies": history_record.allergies or [],
            "chronic_conditions": history_record.chronic_conditions or [],
            "current_medications": history_record.current_medications or [],
        }

    session_id = str(uuid.uuid4())

    reply = ai_service.start_session(
        session_id=session_id,
        language=data.language,
        first_complaint=data.first_complaint,
        history=history_dict,
    )

    session = ai_service._sessions.get(session_id, {})
    done = session.get("done", False)
    summary = session.get("summary")

    return {
        "session_id": session_id,
        "reply": reply,
        "done": done,
        "summary": summary,
    }


@router.post("/message")
def send_message(data: SendMessage):
    """Send a patient message and receive the next AI question or final summary."""
    try:
        result = ai_service.send_message(data.session_id, data.text)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@router.post("/finish")
def finish_chat(data: FinishSession):
    """Manually conclude the intake and generate clinical summary."""
    try:
        summary = ai_service.finalize_summary(data.session_id)
        return {"done": True, "summary": summary}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/submit")
async def submit_case(data: SubmitCase, db: Session = Depends(get_db)):
    """
    Finalize the intake session:
    1. Saves Case + transcript to DB
    2. Runs urgency flagging
    3. Adds to queue
    """
    session = ai_service._sessions.get(data.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or already submitted")

    transcript = session.get("transcript", [])
    first_complaint = session.get("first_complaint", "")

    # Build a plain-text summary from transcript for urgency check
    full_text = " ".join(t["text"] for t in transcript)

    # Run urgency evaluation
    urgency = urgency_service.evaluate_urgency(first_complaint, full_text)

    # Extract structured summary
    summary_dict = session.get("summary") or ai_service.extract_clinical_summary(transcript, first_complaint)

    # Save Case
    case = Case(
        case_id=str(uuid.uuid4()),
        patient_id=data.patient_id,
        chief_complaint=first_complaint,
        symptom_details=summary_dict,
        conversation_transcript=transcript,
        urgency_flag=urgency["urgency_flag"],
        urgency_reason=urgency["urgency_reason"],
        attachments=data.attachments or [],
        status="waiting",
        department=data.department,
    )
    db.add(case)
    db.flush()  # get case_id before queue insert

    # Add to Queue — urgent cases get position 0 (handled manually by staff)
    existing_count = db.query(Queue).count()
    queue_entry = Queue(
        queue_id=str(uuid.uuid4()),
        case_id=case.case_id,
        position=0 if urgency["urgency_flag"] else existing_count + 1,
        priority_flag=urgency["urgency_flag"],
        department=data.department or "general",
    )
    db.add(queue_entry)
    db.commit()

    # Clean up session from memory
    ai_service.close_session(data.session_id)

    # Broadcast real-time queue update via WebSocket
    try:
        await ws_manager.broadcast({
            "event": "queue_updated",
            "case_id": case.case_id,
            "patient_id": data.patient_id,
            "urgency_flag": urgency["urgency_flag"],
            "department": data.department or "general",
        })
    except Exception as e:
        print(f"[chat] WebSocket broadcast notice: {e}")

    return {
        "case_id": case.case_id,
        "urgency_flag": urgency["urgency_flag"],
        "urgency_reason": urgency["urgency_reason"],
        "queue_position": queue_entry.position,
        "status": "submitted",
        "message": "Your case has been recorded. Please wait to be called.",
    }


@router.post("/upload-attachment")
async def upload_attachment(file: UploadFile = File(...)):
    """
    Upload a patient medical attachment (image of wound, rash, skin condition).
    Saves to /uploads directory and returns static URL.
    """
    allowed_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    _, ext = os.path.splitext(file.filename or "")
    if ext.lower() not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(allowed_exts)}",
        )

    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)

    filename = f"{uuid.uuid4()}{ext.lower()}"
    file_path = os.path.join(upload_dir, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "filename": filename,
        "url": f"/uploads/{filename}",
        "content_type": file.content_type,
    }


@router.post("/tts")
async def get_tts(data: TTSRequest, background_tasks: BackgroundTasks):
    """
    Convert AI reply text to speech using edge-tts and return MP3 file.
    The temp file is deleted automatically after the response is sent.
    """
    try:
        # Run blocking TTS synthesis in a thread to avoid blocking the event loop
        mp3_path = await asyncio.to_thread(
            tts_service.text_to_speech, data.text, data.language
        )
        # Schedule temp-file cleanup after response is sent
        background_tasks.add_task(os.unlink, mp3_path)
        return FileResponse(
            mp3_path,
            media_type="audio/mpeg",
            filename="reply.mp3",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")


@router.post("/stt")
async def speech_to_text(
    file: UploadFile = File(...),
    language: str = Form("English"),
):
    """
    Transcribe patient voice recording to text using Whisper.
    Accepts any audio format (webm, wav, mp3, ogg).
    Returns: { "text": "transcribed text" }
    """
    try:
        audio_bytes = await file.read()
        text = stt_service.transcribe(
            audio_bytes=audio_bytes,
            language=language,
            filename=file.filename or "audio.webm",
        )
        if not text:
            raise HTTPException(status_code=422, detail="Could not transcribe audio — please speak clearly or type instead.")
        return {"text": text, "language": language}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT failed: {str(e)}")
