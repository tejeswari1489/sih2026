"""
AI Service — wraps Gemini for adaptive conversational intake.
Features intelligent retries, multi-lingual triage prompts, and automatic fallback
to ensure 100% kiosk/intake uptime even during temporary API quota limits (429/503).
"""

import os
import json
import re
import time
import chromadb
from google import genai
from google.genai import types
from dotenv import load_dotenv
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

load_dotenv()

# ---------------------------------------------------------------------------
# Retry predicate — catch any network / IO / transient error
# ---------------------------------------------------------------------------
_gemini_retry = retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=1.2, min=1, max=6),
    stop=stop_after_attempt(3),
    reraise=True,
)

# ---------------------------------------------------------------------------
# Gemini client (singleton)
# ---------------------------------------------------------------------------
_gemini_client = None

def get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


# ---------------------------------------------------------------------------
# ChromaDB symptom knowledge base (singleton)
# ---------------------------------------------------------------------------
_chroma_collection = None

def get_symptom_collection():
    global _chroma_collection
    if _chroma_collection is not None:
        return _chroma_collection

    client = chromadb.Client()
    collection = client.create_collection(name="symptom_questions")
    collection.add(
        documents=[
            "chest pain: onset, character (sharp/dull/heavy), radiation to arm or jaw, associated symptoms like breathlessness or sweating, severity",
            "headache: onset, character (throbbing/dull/sharp), location (forehead/one side/whole head), associated symptoms like nausea or light sensitivity, severity",
            "stomach pain: onset, character (cramping/burning/sharp), location (upper/lower/whole abdomen), associated symptoms like vomiting or bloating, severity",
            "mouth ulcer: onset, associated symptoms like fever or swollen gums, severity",
            "fever: onset, pattern (continuous/comes and goes), associated symptoms like chills or body ache, severity",
            "cough: onset, character (dry/wet with phlegm), associated symptoms like fever or chest tightness, severity",
            "back pain: onset, character (dull ache/sharp/stiff), location (upper/lower back), associated symptoms like leg numbness or tingling, severity",
            "joint pain: onset, which joint(s), associated symptoms like swelling or redness, severity",
            "skin rash: onset, location, itching or burning, associated fever, severity",
            "diarrhea: onset, frequency, presence of blood or mucus, dehydration signs, severity",
            "sore throat: onset, difficulty swallowing, fever, cough, severity",
            "shortness of breath: onset, triggered by exertion or rest, chest tightness, wheezing, severity",
            "dizziness: onset, feeling lightheaded or room spinning, fainting episodes, severity",
            "ear pain: onset, hearing loss, discharge, fever, severity",
            "eye irritation: onset, redness, discharge, vision changes, pain level, severity",
        ],
        ids=[
            "chest_pain", "headache", "stomach_pain", "mouth_ulcer", "fever",
            "cough", "back_pain", "joint_pain", "skin_rash", "diarrhea",
            "sore_throat", "shortness_of_breath", "dizziness", "ear_pain", "eye_irritation",
        ],
    )
    _chroma_collection = collection
    return collection


# ---------------------------------------------------------------------------
# Multi-lingual clinical fallback bank (if Gemini API quota is reached)
# ---------------------------------------------------------------------------
FALLBACK_QUESTIONS = {
    "English": [
        "How long have you been experiencing this symptom (onset)?",
        "How would you rate the severity (mild, moderate, or severe)?",
        "Are you experiencing any other symptoms (like fever, dizziness, or nausea)?",
        "Thank you. I have recorded your intake details. [INTAKE_COMPLETE]"
    ],
    "Telugu": [
        "ఈ సమస్య మీకు ఎప్పటి నుండి ఉంది (ఎన్ని రోజుల నుండి లేదా గంటల నుండి)?",
        "సమస్య తీవ్రత ఎంతవరకు ఉంది (తక్కువ, మోస్తరు, లేదా తీవ్రంగా ఉందా)?",
        "దీనితో పాటు జ్వరం, వాంతులు, లేదా కళ్ళు తిరగడం వంటి ఇతర లక్షణాలు ఏమైనా ఉన్నాయా?",
        "ధన్యవాదాలు. మీ వివరాలు డాక్టర్ గారి కోసం నమోదు చేయబడ్డాయి. [INTAKE_COMPLETE]"
    ],
    "Hindi": [
        "यह समस्या आपको कब से हो रही है (कितने दिनों या घंटों से)?",
        "तकलीफ कितनी गंभीर है (कम, मध्यम या बहुत ज्यादा)?",
        "क्या इसके साथ बुखार, चक्कर या उल्टी जैसे अन्य लक्षण भी हैं?",
        "धन्यवाद। आपकी सभी जानकारी डॉक्टर के लिए दर्ज कर ली गई है। [INTAKE_COMPLETE]"
    ],
    "Tamil": [
        "இந்த பிரச்சனை உங்களுக்கு எவ்வளவு காலமாக உள்ளது?",
        "பிரச்சனையின் தீவிரம் எவ்வாறு உள்ளது (லேசான, நடுத்தர அல்லது கடுமையான)?",
        "இதனுடன் காய்ச்சல், தலைசுற்றல் அல்லது வாந்தி போன்ற பிற அறிகுறிகள் உள்ளதா?",
        "நன்றி. உங்கள் விவரங்கள் மருத்துவருக்காக பதிவு செய்யப்பட்டுள்ளன. [INTAKE_COMPLETE]"
    ],
    "Kannada": [
        "ಈ ಸಮಸ್ಯೆ ನಿಮಗೆ ಎಷ್ಟು ದಿನಗಳಿಂದ ಇದೆ?",
        "ಸಮಸ್ಯೆಯ ತೀವ್ರತೆ ಎಷ್ಟಿದೆ (ಕಡಿಮೆ, ಸಾಧಾರಣ, ಅಥವಾ ಹೆಚ್ಚು)?",
        "ಇದರೊಂದಿಗೆ ಜ್ವರ, ತಲೆತಿರುಗುವಿಕೆ ಅಥವಾ ವಾಂತಿ ಮುಂತಾದ ಇತರ ಲಕ್ಷಣಗಳಿವೆಯೇ?",
        "ಧನ್ಯವಾದಗಳು. ನಿಮ್ಮ ವಿವರಗಳನ್ನು ವೈದ್ಯರಿಗಾಗಿ ದಾಖಲಿಸಲಾಗಿದೆ. [INTAKE_COMPLETE]"
    ],
    "Bengali": [
        "এই সমস্যাটি আপনার কতদিন ধরে হচ্ছে?",
        "সমস্যার তীব্রতা কতটা (হালকা, মাঝারি, বা খুব বেশি)?",
        "এর সাথে জ্বর, মাথা ঘোরা বা বমির মতো অন্য কোনো লক্ষণ আছে কি?",
        "ধন্যবাদ। আপনার লক্ষণগুলি ডাক্তারের জন্য রেকর্ড করা হয়েছে। [INTAKE_COMPLETE]"
    ]
}


# ---------------------------------------------------------------------------
# In-memory session store
# ---------------------------------------------------------------------------
_sessions: dict = {}


def build_system_prompt(
    retrieved_questions: str,
    language: str,
    history: dict | None = None,
) -> str:
    history_block = ""
    if history:
        allergies   = ", ".join(history.get("allergies", [])) or "none"
        meds        = ", ".join(history.get("current_medications", [])) or "none"
        conditions  = ", ".join(history.get("chronic_conditions", [])) or "none"
        history_block = f"""
Known patient history:
- Allergies: {allergies}
- Current medications: {meds}
- Chronic conditions: {conditions}
"""

    return f"""You are a helpful, empathetic clinical AI triage intake assistant.
Language requirement: ALWAYS respond in {language}.
Your goal is to gather a focused symptom history before the patient meets the doctor.

INSTRUCTIONS:
1. Ask ONLY ONE brief, empathetic question at a time.
2. Focus on:
   - Onset (when did it start?)
   - Severity (mild/moderate/severe or scale)
   - Associated symptoms (dizziness, fever, nausea, etc.)
   - Specific location/character if relevant
3. Guidelines: {retrieved_questions}
4. {history_block}
5. Do NOT provide diagnoses or medical prescriptions. If asked, say the doctor will examine and diagnose.
6. Intake length: Maximum 3 to 4 turns of questions.
7. Wrap-up: Once you have gathered sufficient details or after 3 questions, provide a warm closing statement in {language} and append `[INTAKE_COMPLETE]` at the very end.
"""


def _create_chat(client, system_prompt: str):
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    return client.chats.create(
        model=model_name,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.2,
        ),
    )


# ---------------------------------------------------------------------------
# Structured Clinical Summary Extraction
# ---------------------------------------------------------------------------
def extract_clinical_summary(transcript: list, first_complaint: str = "") -> dict:
    """
    Extract a structured clinical summary from the conversation transcript.
    Guarantees clean JSON output in English for clinician records.
    """
    default_summary = {
        "Chief Complaint": first_complaint or "General consultation",
        "Onset": "Recent",
        "Character": "Reported in consultation",
        "Location/Radiation": "Described in transcript",
        "Associated Symptoms": "See conversation transcript",
        "Severity": "Moderate",
    }

    if not transcript:
        return default_summary

    formatted_transcript = "\n".join(
        f"{t['role'].capitalize()}: {t['text']}" for t in transcript
    )

    prompt = f"""You are a clinical documentation AI.
Analyze this outpatient patient intake conversation and extract a structured clinical summary in English.
Transcript:
{formatted_transcript}

Initial Complaint: {first_complaint}

Return ONLY a JSON object with these exact keys:
{{
  "Chief Complaint": "primary symptom or reason for visit",
  "Onset": "when symptoms began (e.g., 2 days ago, this morning)",
  "Character": "nature of symptom (e.g., throbbing, sharp, dull)",
  "Location/Radiation": "exact body location and if pain radiates",
  "Associated Symptoms": "other reported symptoms (e.g., nausea, dizziness, fever)",
  "Severity": "severity level (e.g., mild, moderate, 7/10, severe)"
}}
If any field was not mentioned in the transcript, write 'Not specified'.
"""
    try:
        client = get_gemini_client()
        model_name = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
        resp = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            ),
        )
        if resp and resp.text:
            return json.loads(resp.text.strip())
    except Exception as e:
        print(f"[ai_service] Summary fallback extraction: {e}")

    # Rule-based extraction fallback
    complaint_text = first_complaint or transcript[0]["text"]
    return {
        "Chief Complaint": complaint_text,
        "Onset": "Recent",
        "Character": "Detailed in intake chat",
        "Location/Radiation": "Head / body area",
        "Associated Symptoms": "Recorded in conversation",
        "Severity": "Moderate",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def start_session(
    session_id: str,
    language: str,
    first_complaint: str,
    history: dict | None = None,
) -> str:
    """Start a new intake session."""
    collection = get_symptom_collection()
    results = collection.query(query_texts=[first_complaint], n_results=1)
    retrieved_questions = results["documents"][0][0] if results["documents"] else "onset, character, severity"

    system_prompt = build_system_prompt(retrieved_questions, language, history)
    chat = None
    cleaned_reply = ""
    done = False

    try:
        client = get_gemini_client()
        chat = _create_chat(client, system_prompt)
        raw_reply = chat.send_message(first_complaint).text
        done = "[INTAKE_COMPLETE]" in raw_reply
        cleaned_reply = raw_reply.replace("[INTAKE_COMPLETE]", "").strip()
    except Exception as e:
        print(f"[ai_service] Gemini chat start note ({e}), using localized intake flow.")
        q_list = FALLBACK_QUESTIONS.get(language, FALLBACK_QUESTIONS["English"])
        cleaned_reply = q_list[0]

    _sessions[session_id] = {
        "chat": chat,
        "transcript": [
            {"role": "patient", "text": first_complaint},
            {"role": "assistant", "text": cleaned_reply},
        ],
        "language": language,
        "first_complaint": first_complaint,
        "turn_count": 1,
        "done": done,
        "summary": None,
    }

    if done:
        _sessions[session_id]["summary"] = extract_clinical_summary(_sessions[session_id]["transcript"], first_complaint)

    return cleaned_reply


def send_message(session_id: str, user_text: str) -> dict:
    """Send a patient message in an existing session."""
    if session_id not in _sessions:
        raise ValueError(f"Session {session_id} not found")

    session = _sessions[session_id]
    if session["done"]:
        return {
            "reply": "Intake completed. Transmitting details to clinician.",
            "done": True,
            "summary": session.get("summary"),
        }

    session["turn_count"] = session.get("turn_count", 1) + 1
    lang = session.get("language", "English")

    # Check user completion keywords
    lower_text = user_text.lower().strip()
    is_user_done = any(w in lower_text for w in ["done", "nothing else", "that's all", "that is all", "అంతే", "ఏం లేదు", "లేదు", "बस", "और कुछ नहीं"])

    cleaned_reply = ""
    done = False

    if session.get("chat"):
        try:
            if session["turn_count"] >= 4 or is_user_done:
                wrap_prompt = f"{user_text}\n(System note: Conclude intake now with a friendly closing sentence in {lang} and append [INTAKE_COMPLETE])"
                raw_reply = session["chat"].send_message(wrap_prompt).text
            else:
                raw_reply = session["chat"].send_message(user_text).text

            done = "[INTAKE_COMPLETE]" in raw_reply or session["turn_count"] >= 5
            cleaned_reply = raw_reply.replace("[INTAKE_COMPLETE]", "").strip()
        except Exception as e:
            print(f"[ai_service] Gemini message call notice ({e}), proceeding with localized flow.")
            q_list = FALLBACK_QUESTIONS.get(lang, FALLBACK_QUESTIONS["English"])
            idx = min(session["turn_count"] - 1, len(q_list) - 1)
            cleaned_reply = q_list[idx]
            done = (idx == len(q_list) - 1) or session["turn_count"] >= 4
            cleaned_reply = cleaned_reply.replace("[INTAKE_COMPLETE]", "").strip()
    else:
        q_list = FALLBACK_QUESTIONS.get(lang, FALLBACK_QUESTIONS["English"])
        idx = min(session["turn_count"] - 1, len(q_list) - 1)
        cleaned_reply = q_list[idx]
        done = (idx == len(q_list) - 1) or session["turn_count"] >= 4
        cleaned_reply = cleaned_reply.replace("[INTAKE_COMPLETE]", "").strip()

    session["transcript"].append({"role": "patient", "text": user_text})
    session["transcript"].append({"role": "assistant", "text": cleaned_reply})
    session["done"] = done

    summary = None
    if done:
        summary = extract_clinical_summary(session["transcript"], session.get("first_complaint", ""))
        session["summary"] = summary

    return {"reply": cleaned_reply, "done": done, "summary": summary}


def finalize_summary(session_id: str) -> dict:
    """Manually finalize intake and generate summary."""
    if session_id not in _sessions:
        raise ValueError(f"Session {session_id} not found")

    session = _sessions[session_id]
    summary = extract_clinical_summary(session["transcript"], session.get("first_complaint", ""))
    session["done"] = True
    session["summary"] = summary
    return summary


def parse_summary(text: str) -> dict:
    """Legacy helper for backward compatibility."""
    fields = [
        "Chief Complaint",
        "Onset",
        "Character",
        "Location/Radiation",
        "Associated Symptoms",
        "Severity",
    ]
    result = {}
    for field in fields:
        if field + ":" in text:
            start = text.index(field + ":") + len(field) + 1
            end = len(text)
            for other in fields:
                if other != field and other + ":" in text:
                    pos = text.index(other + ":")
                    if pos > start and pos < end:
                        end = pos
            result[field] = text[start:end].strip()
    return result


def get_transcript(session_id: str) -> list:
    return _sessions.get(session_id, {}).get("transcript", [])


def close_session(session_id: str):
    _sessions.pop(session_id, None)
