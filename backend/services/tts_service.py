"""
TTS Service — uses edge-tts (Microsoft Azure neural voices) for reliable,
high-quality multilingual text-to-speech.

edge-tts is async internally. This module exposes a plain synchronous
text_to_speech() that is safe to call from FastAPI via asyncio.to_thread(),
because each call creates and tears down its own event loop in the worker
thread (avoids "no running event loop" / "cannot run nested" errors).
"""

import asyncio
import os
import tempfile
import time

import edge_tts

# ---------------------------------------------------------------------------
# Language → Microsoft edge-tts voice mappings
# ---------------------------------------------------------------------------
EDGE_VOICES = {
    "English":   "en-IN-NeerjaNeural",
    "Hindi":     "hi-IN-SwaraNeural",
    "Telugu":    "te-IN-ShrutiNeural",
    "Tamil":     "ta-IN-PallaviNeural",
    "Kannada":   "kn-IN-SapnaNeural",
    "Malayalam": "ml-IN-SobhanaNeural",
    "Bengali":   "bn-IN-TanishaaNeural",
    "Marathi":   "mr-IN-AarohiNeural",
    "Gujarati":  "gu-IN-DhwaniNeural",
    "Punjabi":   "pa-IN-OjasNeural",
}

DEFAULT_VOICE = "en-IN-NeerjaNeural"
MAX_ATTEMPTS  = 3
RETRY_DELAY   = 1.5   # seconds between retries (doubles each time)


async def _synthesise(text: str, voice: str, path: str) -> None:
    """Pure async synthesis — called inside a fresh event loop."""
    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(path)


def text_to_speech(text: str, language: str = "English") -> str:
    """
    Convert *text* to an MP3 file using Microsoft edge-tts.

    Safe to call from any thread (including asyncio.to_thread workers)
    because it creates its own event loop instead of using asyncio.run().

    Returns the absolute path to the generated MP3 (caller deletes it).
    Raises RuntimeError after MAX_ATTEMPTS failures.
    """
    voice = EDGE_VOICES.get(language, DEFAULT_VOICE)

    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp_path = tmp.name
    tmp.close()

    last_error: Exception | None = None
    delay = RETRY_DELAY

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            # Create a brand-new event loop for this worker thread.
            # asyncio.run() would fail if a loop already exists; this is safe.
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_synthesise(text, voice, tmp_path))
            finally:
                loop.close()
            return tmp_path                    # success
        except Exception as exc:
            last_error = exc
            print(f"[tts_service] Attempt {attempt}/{MAX_ATTEMPTS} failed: {exc}")
            if attempt < MAX_ATTEMPTS:
                time.sleep(delay)
                delay *= 2                     # exponential back-off

    # Cleanup empty/partial file before raising
    try:
        os.unlink(tmp_path)
    except OSError:
        pass

    raise RuntimeError(
        f"TTS failed after {MAX_ATTEMPTS} attempts for '{language}': {last_error}"
    )
