"""
FastAPI main application entry point.
Run with: uvicorn backend.main:app --reload
"""

import sys
import os
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database import engine, Base, SessionLocal, migrate_db_schema
from backend.routers import patient, chat, doctor, history, auth, admin
from backend.services.websocket_manager import ws_manager

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# Ensure uploads directory exists
uploads_dir = os.path.join(PROJECT_ROOT, "uploads")
os.makedirs(uploads_dir, exist_ok=True)

# Create all DB tables on startup & migrate any missing columns
Base.metadata.create_all(bind=engine)
migrate_db_schema()

# Seed default demo staff accounts
try:
    with SessionLocal() as db_session:
        auth.seed_default_staff(db_session)
except Exception as e:
    print(f"Startup staff seed notice: {e}")

app = FastAPI(
    title="SIH — AI Patient Intake API",
    description="AI-assisted patient case-taking and prioritization backend",
    version="1.0.0",
)

from fastapi import Request

@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Allow frontend (React dev server / static hosts) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8080", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register routers
app.include_router(auth.router)
app.include_router(patient.router)
app.include_router(chat.router)
app.include_router(doctor.router)
app.include_router(history.router)
app.include_router(admin.router)

# Mount static directories
if os.path.isdir(uploads_dir):
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

frontend_dir = os.path.join(PROJECT_ROOT, "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/frontend", StaticFiles(directory=frontend_dir, html=True), name="frontend")


# ---------------------------------------------------------------------------
# WebSocket Endpoint: Live Queue & Event Streaming
# ---------------------------------------------------------------------------
@app.websocket("/ws/queue")
async def websocket_queue_endpoint(websocket: WebSocket):
    """
    WebSocket connection for real-time live queue and case status synchronization.
    Used by Doctor Dashboards, Triage Stations, and Patient Waiting Screens.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep-alive receive loop
            data = await websocket.receive_text()
            # Echo or handle ping
            if data == "ping":
                await websocket.send_text('{"event":"pong"}')
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


from fastapi.responses import RedirectResponse

@app.get("/")
def root():
    return RedirectResponse(url="/frontend/index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


