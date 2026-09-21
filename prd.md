# Product Requirements Document (PRD)
## AI-Assisted Patient Case-Taking & Prioritization Mobile App

**Version:** 1.0
**Status:** Draft
**Owner:** [Product Owner Name]
**Last Updated:** September 6, 2026

---

## 1. Purpose & Background

Hospitals today rely on manual, repetitive, and fragmented patient case-taking — fixed questionnaires, paper records, and a common queue where doctors cannot easily distinguish urgent cases from routine ones. This leads to:

- Delayed identification of potentially serious cases.
- Loss of or inaccessible patient medical history.
- Rigid, one-size-fits-all intake forms that don't adapt to the patient's actual complaint.
- Poor accessibility for patients uncomfortable with typing, digital tools, or non-native languages.

This PRD defines a **mobile application** that lets patients describe their health concerns naturally (via text or voice, in their preferred language), dynamically gathers relevant clinical information through an adaptive AI conversation, consolidates it with prior medical history, and flags potentially urgent cases for healthcare staff — **without providing a diagnosis**.

---

## 2. Goals & Objectives

| Goal | Description |
|---|---|
| Reduce manual workload | Replace repetitive fixed forms with adaptive, conversational intake |
| Improve information availability | Centralize current complaint + historical records into one structured view |
| Improve accessibility | Support voice input/output and multiple languages |
| Improve patient safety | Early flagging of potentially urgent symptoms for human review |
| Support, not replace, doctors | System only assists case-taking and prioritization; final clinical judgment stays with doctors |

### Non-Goals (Out of Scope)
- The app will **not** provide a diagnosis or treatment recommendation.
- The app will **not** auto-prioritize patients without human review — it only flags/suggests.
- The app will **not** replace electronic health record (EHR) systems; it feeds into/complements them.
- No prescription, billing, or appointment-payment functionality in v1.

---

## 3. Target Users & Personas

### 3.1 Patient (Primary User)
- Visiting a hospital/clinic, possibly for the first time or as a returning patient.
- May have low digital literacy, prefer voice, or speak a regional/native language.
- May be experiencing mild-to-severe symptoms and may not recognize urgency themselves.

### 3.2 Doctor / Clinician (Primary User)
- Sees many patients daily; needs a fast, structured summary rather than raw transcripts.
- Needs to quickly identify which waiting patients may need earlier attention.

### 3.3 Front-Desk / Triage Staff (Secondary User)
- Manages the physical/virtual queue.
- Needs visibility into flagged cases to re-prioritize the queue if needed.

### 3.4 Hospital Admin (Secondary User)
- Manages user accounts, department routing, and system configuration.

---

## 4. User Stories

**Patient**
1. As a patient, I want to describe my problem in my own words (text or voice) so I don't have to fill lengthy forms.
2. As a patient, I want to speak/read in my native language so I can communicate comfortably.
3. As a patient, I want the app to ask only relevant follow-up questions based on my complaint.
4. As a patient, I want my past visits, prescriptions, and allergies to be remembered so I don't repeat myself.
5. As a patient, I want to know my case has been recorded and submitted to the queue.

**Doctor**
6. As a doctor, I want a structured summary (chief complaint, history, medications, allergies, flags) before the patient enters, so I can prepare faster.
7. As a doctor, I want to see which waiting patients are flagged as potentially urgent, with the reasoning, so I can decide on prioritization.
8. As a doctor, I want access to a patient's full case history across visits in one place.

**Front-Desk/Triage Staff**
9. As triage staff, I want a live queue view sorted by arrival and urgency flags so I can manage patient flow.

**Admin**
10. As an admin, I want to manage doctor/department mapping and view system usage.

---

## 5. Functional Requirements

### 5.1 Patient-Facing Mobile App

**F1. Onboarding & Profile**
- Sign-up/login (phone number/OTP, or hospital ID).
- Basic demographic profile: name, age, gender, contact, preferred language.
- Consent capture for data storage/usage (health data privacy).

**F2. Conversational Case-Taking**
- Free-text or voice input for describing symptoms/concerns.
- AI-driven adaptive questioning:
  - Dynamically generates relevant follow-up questions based on the specific complaint (e.g., duration, severity, associated symptoms, aggravating/relieving factors).
  - Does **not** follow a fixed universal questionnaire.
  - Supports skipping/"I don't know" responses gracefully.
- Multilingual support: input and output in patient's selected language (speech-to-text, translation, text-to-speech).
- Ability to attach photos (e.g., visible injury, rash) — optional.

**F3. Medical History Capture & Reuse**
- On repeat visits, automatically retrieve prior recorded history (past complaints, prescriptions, allergies, chronic conditions).
- AI reconciles "what's new" vs. previously known information, avoiding redundant questioning.
- Patient can manually add/edit known allergies, ongoing medications, chronic conditions.

**F4. Case Summary & Submission**
- After the conversation, generate a structured summary for patient review/confirmation before submission.
- Patient submits the case; receives confirmation and (if applicable) an estimated queue position/status.

**F5. Voice & Accessibility**
- Full voice-mode operation (speak input, hear questions/prompts read aloud).
- Large-text / simplified UI mode for low digital literacy or elderly users.
- Support for at least [N] regional languages (configurable list).

**F6. Notifications**
- Status updates (case received, queue position changes, called in).

### 5.2 Doctor-Facing Interface (Mobile + Web Dashboard)

**F7. Patient Queue Dashboard**
- List of waiting patients sorted by arrival time and urgency flag.
- Visual indicator (e.g., color-coded tag) for flagged/potentially urgent cases.

**F8. Structured Case View**
- Chief complaint, symptom timeline, relevant history, medications, allergies.
- Urgency flag with AI-generated rationale (transparent, not a black-box score).
- Access to past visit summaries for the same patient.

**F9. Doctor Actions**
- Mark case as reviewed.
- Reorder/re-prioritize queue manually (final human decision).
- Add consultation notes/prescription (optional integration point with existing EHR).

### 5.3 Urgency Flagging Engine

**F10. Rule-based + AI Hybrid Triage Support**
- Predefined red-flag symptom patterns (e.g., chest pain + breathlessness, sudden weakness/numbness, high fever with confusion, severe bleeding, difficulty breathing).
- AI classifier layer to catch complaints that match flag patterns in natural language, tuned for **high recall** (prefer over-flagging over missing a serious case).
- All flags are advisory; system explicitly never tells the patient "this is/isn't an emergency."
- Flag + reasoning is only shown to clinical staff, not exposed as a diagnosis to the patient.

### 5.4 Admin Panel

**F11. User & Access Management**
- Manage doctor, staff, and department accounts.
- Configure department routing (e.g., orthopedics vs. general medicine based on complaint type).

**F12. Analytics Dashboard**
- Patient volume, average wait time, flagged-case volume, language usage stats.

---

## 6. Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Privacy & Security** | End-to-end encryption of health data in transit and at rest; compliance with applicable health data regulations (e.g., HIPAA/local equivalent such as India's DPDP Act); role-based access control |
| **Availability** | 99.5%+ uptime for production use in hospital settings |
| **Performance** | Conversational response latency under ~2–3 seconds per turn; voice transcription near real-time |
| **Scalability** | Support concurrent use across multiple hospital departments/queues |
| **Accessibility** | WCAG-aligned UI; voice-first mode; large-text mode |
| **Multilingual Support** | Minimum viable set of languages defined at launch, expandable |
| **Auditability** | Full audit trail of case data access (who viewed what, when) |
| **Offline Resilience** | Graceful degradation if connectivity drops mid-conversation (auto-save partial responses) |

---

## 7. System Architecture (High-Level)

```
[Patient Mobile App] 
      │  (text / voice)
      ▼
[API Gateway]
      │
      ├── [Speech-to-Text Service] ──► [Translation Layer] ──► [Conversational AI Engine]
      │                                                              │
      │                                                     [Urgency Flagging Engine]
      │                                                              │
      ├── [Patient History Service] ◄──── [Patient Records DB] ◄────┘
      │
      ├── [Text-to-Speech Service] (for voice output back to patient)
      │
      ▼
[Case Summary Generator] ──► [Doctor/Triage Dashboard] ──► [EHR Integration (optional)]
      │
      ▼
[Admin Panel] / [Analytics Service]
```

### Suggested Tech Stack

| Layer | Technology Options |
|---|---|
| Mobile app (patient) | Flutter or React Native (cross-platform) |
| Doctor dashboard | React/Next.js (web), optionally mobile-responsive |
| Conversational AI | LLM API (e.g., Claude) with structured-output prompting |
| Speech-to-Text | Whisper or cloud STT (Google/Azure) |
| Text-to-Speech | Cloud TTS service |
| Translation | LLM-based or dedicated MT API |
| Backend | Node.js (NestJS) or Python (FastAPI) |
| Database | PostgreSQL (structured records), object storage for attachments |
| Auth | OTP-based phone auth / hospital SSO for staff |
| Hosting | Cloud (AWS/GCP/Azure) with HIPAA/DPDP-compliant configuration |
| Notifications | Firebase Cloud Messaging / SMS gateway |

---

## 8. Data Model (Simplified)

**Patient**
- patient_id, name, age, gender, contact, preferred_language, consent_flag

**Visit/Case**
- case_id, patient_id, timestamp, chief_complaint, symptom_details (structured JSON), conversation_transcript, attachments, urgency_flag (bool), urgency_reason, status (waiting/in-review/completed)

**Medical History**
- history_id, patient_id, allergies[], chronic_conditions[], current_medications[], past_diagnoses[] (if available), past_prescriptions[]

**Doctor/Staff**
- staff_id, name, role, department

**Queue**
- queue_id, case_id, position, priority_flag, department

---

## 9. Key User Flows

### 9.1 New Patient Flow
1. Download app → Sign up → Select preferred language.
2. Start new case → Describe complaint (text/voice).
3. AI asks adaptive follow-up questions.
4. Patient reviews auto-generated summary → Confirms → Submits.
5. Case enters queue; patient sees status/queue position.
6. Doctor reviews structured case (with flag if applicable) → Calls patient in.

### 9.2 Returning Patient Flow
1. Login → App recognizes returning patient.
2. Prior history auto-loaded and shown for confirmation/update.
3. New complaint captured; AI reconciles with history ("Are these related to your prior visit for X?").
4. Summary generated → Submitted → Queued.

### 9.3 Urgent Case Flow
1. During conversation, red-flag pattern detected.
2. Case auto-tagged as "Priority Review" in doctor/triage dashboard (patient is not alarmed or told this directly).
3. Triage staff/doctor notified; can re-sequence queue manually.

---

## 10. Success Metrics (KPIs)

| Metric | Target (illustrative) |
|---|---|
| Reduction in average intake time per patient | ≥40% vs. manual process |
| % of cases requiring no re-asking of history on repeat visits | ≥80% |
| Urgent-case flag recall (sensitivity) | ≥95% on validated red-flag scenarios |
| Doctor-reported usefulness of case summaries | ≥4/5 average rating |
| Patient satisfaction with conversational intake | ≥4/5 average rating |
| Multilingual usage adoption | Tracked per language |

---

## 11. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| AI misses a genuinely urgent case (false negative) | Bias flagging engine toward high recall; combine rule-based red flags with AI; human review always in the loop |
| Patient over-trusts app as diagnostic | Explicit disclaimers throughout; app never states a diagnosis or urgency verdict to the patient |
| Health data privacy/compliance violation | Encryption, RBAC, compliance review (HIPAA/DPDP or local equivalent), regular audits |
| Low adoption due to distrust of AI in healthcare | Doctor-in-the-loop framing, transparent reasoning shown to clinicians, pilot rollout with feedback loops |
| Voice/translation inaccuracies causing miscommunication | Allow patient to review/edit transcribed text before submission |
| Connectivity issues in hospital settings | Offline draft-save and auto-resume |

---

## 12. Milestones / Rollout Plan (Illustrative)

| Phase | Scope | Duration |
|---|---|---|
| Phase 1 – MVP | Text-based conversational intake, basic history storage, doctor dashboard, rule-based urgency flags | 6–8 weeks |
| Phase 2 – Voice & Multilingual | Voice input/output, multilingual support | 4–6 weeks |
| Phase 3 – AI Flagging Enhancement | Hybrid AI+rule urgency engine, analytics dashboard | 4 weeks |
| Phase 4 – Pilot Deployment | Deploy in 1–2 hospital departments, gather feedback | 4–6 weeks |
| Phase 5 – Scale & EHR Integration | Multi-department rollout, optional EHR integration | Ongoing |

---

## 13. Open Questions

- Which EHR systems (if any) need integration in v1?
- What is the exact list of supported languages at launch?
- Should patients be allowed to see their own urgency flag status, or is it strictly clinician-facing?
- Data retention policy for conversation transcripts?
- Will the app be used only within hospital Wi-Fi/premises, or also for pre-visit remote intake?

---

## 14. Appendix

**Disclaimer statement (to be shown in-app):**
> "This app helps collect your health information to assist doctors. It does not diagnose conditions or provide medical advice. If you are experiencing a medical emergency, please seek immediate help or contact emergency services."
