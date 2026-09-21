"""
STT Service — Speech-to-Text powered by Gemini Multimodal Audio (gemini-3.6-flash).
Supports all Indian languages (Hindi, Telugu, Tamil, Kannada, Bengali, etc.) and English.
"""

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
# Retry predicate for Gemini API calls
# ---------------------------------------------------------------------------
_gemini_retry = retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=1, min=1, max=6),
    stop=stop_after_attempt(3),
    reraise=True,
)

# Singleton Gemini client
_gemini_client = None

def get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment.")
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


MIME_MAP = {
    ".webm": "audio/webm",
    ".wav": "audio/wav",
    ".mp3": "audio/mp3",
    ".ogg": "audio/ogg",
    ".m4a": "audio/m4a",
    ".aac": "audio/aac",
    ".flac": "audio/flac",
}


@_gemini_retry
def transcribe(audio_bytes: bytes, language: str = "English", filename: str = "audio.webm") -> str:
    """
    Transcribe audio bytes to text using Gemini Multimodal Audio.
    Transcribes verbatim in the patient's spoken language.
    
    Args:
        audio_bytes: Raw audio bytes (webm, wav, mp3, ogg, etc.)
        language: Expected language hint (e.g. "Hindi", "Telugu", "English")
        filename: Original filename to extract MIME extension
    
    Returns:
        Transcribed string.
    """
    client = get_gemini_client()
    ext = os.path.splitext(filename)[-1].lower() or ".webm"
    mime_type = MIME_MAP.get(ext, "audio/webm")
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

    prompt = (
        f"You are an accurate clinical speech-to-text transcriber. "
        f"Transcribe the attached audio verbatim in its original spoken language (expected language: {language}). "
        f"Output ONLY the exact words spoken by the patient. "
        f"Do NOT include translations, commentary, timestamps, markdown, or quotation marks."
    )

    audio_part = types.Part.from_bytes(
        data=audio_bytes,
        mime_type=mime_type,
    )

    response = client.models.generate_content(
        model=model_name,
        contents=[audio_part, prompt],
        config=types.GenerateContentConfig(
            temperature=0.0,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
    )

    text = response.text.strip() if response and response.text else ""
    return text


@_gemini_retry
def translate_to_english(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """
    Transcribe AND translate audio to English using Gemini Multimodal Audio.
    """
    client = get_gemini_client()
    ext = os.path.splitext(filename)[-1].lower() or ".webm"
    mime_type = MIME_MAP.get(ext, "audio/webm")
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

    prompt = (
        "Transcribe this spoken audio and translate it into clear, natural English. "
        "Output ONLY the English translation without any extra comments, quotes, or markdown."
    )

    audio_part = types.Part.from_bytes(
        data=audio_bytes,
        mime_type=mime_type,
    )

    response = client.models.generate_content(
        model=model_name,
        contents=[audio_part, prompt],
        config=types.GenerateContentConfig(
            temperature=0.0,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
    )

    text = response.text.strip() if response and response.text else ""
    return text
