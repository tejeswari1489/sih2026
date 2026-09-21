# Product Requirements Document (PRD) — Implemented System
**Project Title:** AI-Assisted Patient Intake, Triage & Prioritization System (SIH Hackathon)  
**Status:** As-Built / Implemented  
**Date:** September 2026  
**Stack:** FastAPI, Google Gemini (`gemini-3.6-flash`), ChromaDB, Whisper STT, Edge-TTS, SQLite / SQLAlchemy, WebSockets, HTML5/CSS3/Vanilla JS  

---

## 1. Executive Summary & Problem Statement

### 1.1 Problem Statement
Hospital emergency departments and Outpatient Departments (OPD) face severe congestion, long wait times, and manual, error-prone triage. Patients often cannot accurately express symptoms due to language barriers or literacy constraints, while medical staff lack instant, structured clinical summaries and real-time urgency-based queue ordering.

### 1.2 Solution Overview
An end-to-end intelligent triage platform featuring:
- Multilingual voice- and text-driven AI conversational intake for patients.
- Clinical symptom RAG (Retrieval-Augmented Generation) with medical literature guidelines.
- Dual-tier urgency classification (deterministic clinical red-flags + AI LLM scoring).
- Real-time WebSocket-synchronized doctor triage dashboard with live reordering.
- Department-level operational analytics and role-based staff management for hospital administrators.

---

## 2. System Architecture

```
                                  +-----------------------------+
                                  |      Client Interfaces      |
                                  |  (Patient, Doctor, Admin)   |
                                  +--------------+--------------+
                                                 |
                                     HTTP REST / WebSocket
                                                 |
                                  +--------------v--------------+
                                  |       FastAPI Backend       |
                                  |    (Uvicorn ASGI Server)    |
                                  +--------------+--------------+
                                                 |
                 +-------------------------------+-------------------------------+
                 |                               |                               |
  +--------------v--------------+ +--------------v--------------+ +--------------v--------------+
  |       Database & Storage    | |     AI & Medical NLP        | |     Voice & Multilingual    |
  | - SQLite + SQLAlchemy ORM   | | - Google Gemini (3.6 Flash) | | - OpenAI Whisper (Local STT)|
  | - ChromaDB Vector Store     | | - Regex Red-Flag Engine     | | - Edge-TTS (Neural Speech)  |
  | - Local File Uploads        | | - Tenacity Resilience Retry | | - 10 Indian Languages       |
  +-----------------------------+ +-----------------------------+ +-----------------------------+
```

---

## 3. Database Schema & Data Models

### 3.1 `Patient`
- `id` (Integer, Primary Key)
- `name` (String, Indexed)
- `age` (Integer)
- `gender` (String)
- `phone` (String, Unique, Indexed)
- `created_at` (DateTime, Default: UTC Now)
- *Relationships:* `cases`, `medical_history`

### 3.2 `MedicalHistory`
- `id` (Integer, Primary Key)
- `patient_id` (Integer, Foreign Key -> `patients.id`)
- `chronic_conditions` (JSON / Text, e.g., Diabetes, Hypertension)
- `allergies` (JSON / Text)
- `current_medications` (JSON / Text)
- `past_surgeries` (JSON / Text)
- `family_history` (JSON / Text)
- `updated_at` (DateTime)

### 3.3 `Case`
- `id` (Integer, Primary Key)
- `patient_id` (Integer, Foreign Key -> `patients.id`)
- `chief_complaint` (Text)
- `symptoms` (JSON / List of structured symptoms)
- `urgency_level` (Enum / String: `EMERGENT`, `URGENT`, `SEMI-URGENT`, `NON-URGENT`)
- `assigned_department` (String: General Medicine, Cardiology, Pulmonology, Orthopedics, Neurology, Pediatrics, etc.)
- `ai_summary` (Text, Structured SBAR-style clinical intake report)
- `chat_transcript` (JSON, Complete patient-AI dialogue)
- `attachments` (JSON, URLs/paths to uploaded medical images or lab reports)
- `status` (String: `QUEUED`, `IN_CONSULTATION`, `REVIEWED`, `DISCHARGED`)
- `doctor_notes` (Text, Optional clinician input)
- `created_at` (DateTime)

### 3.4 `Queue`
- `id` (Integer, Primary Key)
- `case_id` (Integer, Foreign Key -> `cases.id`, Unique)
- `urgency_score` (Integer / Float: 1-100 prioritization weight)
- `position` (Integer, Current sequence rank)
- `status` (String: `WAITING`, `CALLED`, `COMPLETED`)
- `entered_at` (DateTime)

### 3.5 `Staff`
- `id` (Integer, Primary Key)
- `username` (String, Unique)
- `hashed_password` (String, Bcrypt hashed)
- `role` (String: `DOCTOR`, `TRIAGE_NURSE`, `ADMIN`)
- `full_name` (String)
- `department` (String)
- `is_active` (Boolean)

---

## 4. Implemented Features & Core Capabilities

### 4.1 Patient Conversational Intake (`routers/chat.py`, `services/ai_service.py`)
- **Interactive Adaptive Q&A:** Dynamic conversational clinical question tree powered by Google Gemini (`gemini-3.6-flash`).
- **Context-Aware Medical RAG:** Vector search across ChromaDB medical guidelines to guide diagnostic question generation.
- **Structured Clinical Intake Generation:** Automatically generates chief complaint, symptom list, onset, severity, and SBAR clinical summary upon completion.
- **Attachment Ingestion:** Supports upload of photos and records (`/chat/upload-attachment`) linked directly to the intake case.
- **Draft Session Caching:** Frontend caches dialogue in `localStorage` to safeguard against browser refreshes or network hiccups.

### 4.2 Multilingual Voice Processing (`services/stt_service.py`, `services/tts_service.py`)
- **Speech-to-Text (STT):** Local inference via OpenAI Whisper (`small` model) supporting audio in WAV/WebM/MP3 formats.
- **Text-to-Speech (TTS):** Natural, high-definition neural voice synthesis via Microsoft `edge-tts` with per-thread event loop execution.
- **Supported Indian Languages:** 
  1. English (`en`)
  2. Hindi (`hi`)
  3. Telugu (`te`)
  4. Tamil (`ta`)
  5. Kannada (`kn`)
  6. Bengali (`bn`)
  7. Malayalam (`ml`)
  8. Marathi (`mr`)
  9. Gujarati (`gu`)
  10. Punjabi (`pa`)

### 4.3 Intelligent Urgency & Triage Engine (`services/urgency_service.py`)
- **Dual-Layer Validation:**
  1. *Deterministic Rule Engine:* Regex pattern matching for life-threatening red flags (chest pain, stroke symptoms, acute respiratory distress, cyanosis, severe hemorrhage).
  2. *AI Urgency Classifier:* LLM-evaluated severity assessment for ambiguous cases with score assignment (1–100) and category output (`EMERGENT`, `URGENT`, `SEMI-URGENT`, `NON-URGENT`).
- **Department Routing:** Automated triage recommendation mapping cases to respective medical specialties.

### 4.4 Real-Time Doctor Triage Dashboard (`routers/doctor.py`, `frontend/doctor.html`)
- **Live Synchronized Queue:** Dynamic priority queue powered by WebSockets (`/ws/queue`), rendering instant updates without page refreshes.
- **Visual Urgency Badging:** Color-coded urgency alerts (`EMERGENT` in pulsing red, `URGENT` in orange, `SEMI-URGENT` in yellow, `NON-URGENT` in green).
- **Case Deep-Dive View:** Full clinical dossier display with SBAR intake summary, full chat transcripts, image attachment viewer, and medical history.
- **Doctor Actions:**
  - Complete case review & append clinician notes (`POST /doctor/case/{id}/review`).
  - Manual queue priority overrides (`POST /doctor/queue/reorder`).

### 4.5 Administrative & Hospital Analytics (`routers/admin.py`, `frontend/admin.html`)
- **Executive Metrics & KPI Cards:** Live statistics on total intake volume, urgency breakdown, average triage-to-consultation latency, and active queue counts.
- **Staff Management:** Full CRUD management of hospital personnel (Doctors, Triage Nurses, Admins) with role-based access.
- **Departmental Load Monitoring:** Distribution charts depicting intake loads across clinical specialties.
- **Case Audit Trail:** Complete searchable audit table of all historical and active hospital encounters.

### 4.6 Security & Authentication (`routers/auth.py`, `services/auth_service.py`)
- **Staff Access:** Stateless JWT token authentication with Bcrypt password hashing and role validation (`DOCTOR`, `TRIAGE_NURSE`, `ADMIN`).
- **Patient Access:** Phone-number based OTP verification & auto-registration.
- **Database Auto-Migration:** Automated schema migrations on backend startup ensuring table integrity across versions.

---

## 5. API Endpoint Specifications

| Module | Method | Endpoint | Description |
|---|---|---|---|
| **Auth** | `POST` | `/auth/token` | Staff login, returns JWT bearer token |
| | `POST` | `/auth/patient-otp` | Generate/verify patient intake OTP |
| **Patient** | `POST` | `/patient/register` | Register new patient profile |
| | `POST` | `/patient/login` | Patient phone login |
| | `GET` | `/patient/{id}` | Fetch patient details |
| | `PUT` | `/patient/{id}` | Update patient profile |
| **Chat & AI** | `POST` | `/chat/start` | Initialize AI clinical interview session |
| | `POST` | `/chat/message` | Send message, receive next diagnostic question |
| | `POST` | `/chat/submit` | Finalize interview, run triage & submit to queue |
| | `POST` | `/chat/stt` | Transcribe voice audio to text (Whisper) |
| | `POST` | `/chat/tts` | Synthesize text to spoken audio (Edge-TTS) |
| | `POST` | `/chat/upload-attachment` | Upload photo/record for clinical intake |
| **Doctor** | `GET` | `/doctor/queue` | Retrieve active prioritized triage queue |
| | `GET` | `/doctor/case/{id}` | Retrieve comprehensive case file & transcript |
| | `POST` | `/doctor/case/{id}/review` | Submit clinical consultation notes & discharge |
| | `POST` | `/doctor/queue/reorder` | Override patient queue sequence rank |
| **Admin** | `GET` | `/admin/analytics` | Fetch hospital-wide triage and operational KPIs |
| | `GET` | `/admin/staff` | List all registered hospital staff |
| | `POST` | `/admin/staff` | Create new staff account |
| | `DELETE` | `/admin/staff/{id}` | Deactivate/remove staff account |
| | `GET` | `/admin/cases` | Search and export all historical cases |
| | `GET` | `/admin/departments` | View department-level case loads |
| **History** | `GET` | `/history/{patient_id}`| Retrieve patient past medical history |
| | `PUT` | `/history/{patient_id}`| Update past medical history |
| **Realtime** | `WS` | `/ws/queue` | WebSocket connection for instant queue sync |

---

## 6. Resilience & Reliability Features

- **Google Gemini Fault-Tolerance:** Integrated `tenacity` exponential backoff retry mechanism (4 attempts) handling transient rate limits or upstream network anomalies.
- **Model Standard:** Standardized on `gemini-3.6-flash` across all AI intake and urgency evaluation workflows.
- **Graceful Async Execution:** Localized thread-safe asyncio loops for Edge-TTS to eliminate event loop conflicts under ASGI concurrency.
- **Path Portability:** Dynamic `PROJECT_ROOT` resolution in `main.py` enabling seamless execution whether invoked from the repository root or the `/backend` directory.

---

## 7. Verification & Testing

- **Automated Test Suite:** Comprehensive test suite in `tests/` covering:
  - Auth workflows (JWT generation, verification, password hashing)
  - Urgency categorization (red flag triggers and fallback scoring)
  - Patient intake lifecycle
  - Doctor review and queue updates
- **Status:** 15/15 unit and integration tests passing (`pytest`).
