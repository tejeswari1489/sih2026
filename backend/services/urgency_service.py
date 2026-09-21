"""
Urgency Flagging Service
Phase 1: Rule-based red flag detection (regex, instant, no network)
Phase 2: Gemini AI classifier on full case summary, with retry back-off
"""

import re
import os
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
# Retry decorator for Gemini calls
# ---------------------------------------------------------------------------
_gemini_retry = retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(4),
    reraise=True,
)

# ---------------------------------------------------------------------------
# Red flag symptom rules — high recall (prefer over-flagging)
# ---------------------------------------------------------------------------
RED_FLAG_PATTERNS = [
    # Cardiac
    (r"chest pain.{0,80}(breathless|short.{0,20}breath|sweat|arm|jaw)", "Chest pain with associated cardiac symptoms"),
    (r"(breathless|short.{0,20}breath).{0,80}chest pain",               "Breathing difficulty with chest pain"),
    # Neurological
    (r"sudden.{0,40}(weakness|numbness|paralysis)",                     "Sudden neurological deficit"),
    (r"(slurred.{0,15}speech|facial.{0,15}droop|vision.{0,15}loss)",   "Possible stroke symptoms"),
    (r"(unconscious|unresponsive|seizure|fit|convuls)",                  "Loss of consciousness or seizure"),
    # Respiratory
    (r"(difficulty.{0,20}breath|cannot.{0,15}breath|choking|short.{0,20}breath)", "Severe breathing difficulty"),
    # Infection / sepsis
    (r"high fever.{0,80}(confus|disoriented|deliri)",                   "High fever with altered consciousness"),
    (r"(confus|disoriented).{0,80}fever",                               "Altered consciousness with fever"),
    # Bleeding
    (r"(severe|heavy|uncontrolled).{0,30}bleed",                        "Severe bleeding"),
    (r"(blood.{0,15}vomit|vomit.{0,15}blood|haemoptysis|hemoptysis)",  "Vomiting blood or coughing blood"),
    # Allergic / anaphylaxis
    (r"(anaphyla|throat.{0,20}swell|tongue.{0,20}swell)",              "Anaphylaxis signs"),
    # Paediatric / obstetric (basic)
    (r"(newborn|infant).{0,50}(fever|breath|seizure)",                  "Critical paediatric symptom"),
]


def check_rule_based_flags(text: str) -> tuple[bool, str]:
    """
    Run regex red-flag rules against the symptom text.
    Returns (flagged: bool, reason: str).
    """
    text_lower = text.lower()
    for pattern, reason in RED_FLAG_PATTERNS:
        if re.search(pattern, text_lower):
            return True, reason
    return False, ""


@_gemini_retry
def _call_gemini_urgency(summary_text: str) -> tuple[bool, str]:
    """Single Gemini call — tenacity retries this on network errors."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return False, ""
    client = genai.Client(api_key=api_key)
    prompt = f"""You are a triage support AI. Evaluate the following patient case summary for any red-flag symptoms that might indicate a potentially serious or time-sensitive medical condition.

Case Summary:
{summary_text}

Reply in this exact format (no extra text):
FLAG: true or false
REASON: one concise sentence explaining why or why not
"""
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.1,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
    )
    lines   = response.text.strip().splitlines()
    flagged = False
    reason  = ""
    for line in lines:
        if line.upper().startswith("FLAG:"):
            flagged = "true" in line.lower()
        elif line.upper().startswith("REASON:"):
            reason = line.split(":", 1)[1].strip()
    return flagged, reason


def check_ai_flags(summary_text: str) -> tuple[bool, str]:
    """
    Ask Gemini to evaluate the case summary for red flags.
    Returns (flagged: bool, reason: str). Falls back gracefully on failure.
    """
    try:
        return _call_gemini_urgency(summary_text)
    except Exception as e:
        print(f"[urgency_service] AI check failed after retries: {e}")
        return False, ""


def evaluate_urgency(complaint: str, summary_text: str) -> dict:
    """
    Main entry point — rule-based check first, then AI classifier.
    Returns {"urgency_flag": bool, "urgency_reason": str}
    """
    # Step 1: Rule-based (instant, no network)
    rule_flag, rule_reason = check_rule_based_flags(complaint + " " + summary_text)
    if rule_flag:
        return {"urgency_flag": True, "urgency_reason": f"[Rule] {rule_reason}"}

    # Step 2: AI classifier (with retry)
    ai_flag, ai_reason = check_ai_flags(summary_text)
    if ai_flag:
        return {"urgency_flag": True, "urgency_reason": f"[AI] {ai_reason}"}

    return {"urgency_flag": False, "urgency_reason": ""}
