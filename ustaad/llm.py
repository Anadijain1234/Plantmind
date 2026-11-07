"""
Groq — the language model that writes Ustaad's answers, Whisper for voice, and a vision model for photos.

If GROQ_API_KEY is missing or Groq fails, every caller has a rule-based fallback,
so the app never shows an empty screen.
"""
import json
import re

import requests

from . import config

CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

SARVAM = "https://api.sarvam.ai"
LANG_CODES = {"en": "en-IN", "hi": "hi-IN", "kn": "kn-IN", "hinglish": "hi-IN"}

last_error = None
last_provider = None


def groq_available():
    return bool(config.GROQ_API_KEY)


def sarvam_available():
    return bool(config.SARVAM_API_KEY)


def available():
    """Is any language model available (Groq first, Sarvam as backup)?"""
    return groq_available() or sarvam_available()


def _extract_json(text):
    if not text:
        return None
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


def chat_json(system, user, max_tokens=1800):
    """Ask for a JSON object: Groq first, then Sarvam-105B as backup. Returns a dict, or None."""
    global last_provider
    data = _groq_json(system, user, max_tokens) if groq_available() else None
    if data is not None:
        last_provider = "Groq"
        return data
    data = _sarvam_json(system, user, max_tokens) if sarvam_available() else None
    if data is not None:
        last_provider = "Sarvam (backup)"
    return data


def _sarvam_json(system, user, max_tokens):
    global last_error
    headers = {"api-subscription-key": config.SARVAM_API_KEY, "Content-Type": "application/json"}
    base = {"model": config.SARVAM_CHAT_MODEL, "temperature": 0.2, "max_tokens": max(max_tokens, 2500),
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    for payload in ({**base, "response_format": {"type": "json_object"}, "reasoning_effort": "low"}, base):
        try:
            r = requests.post(f"{SARVAM}/v1/chat/completions", headers=headers, json=payload, timeout=90)
            if r.status_code in (400, 422):
                last_error = f"Sarvam {r.status_code}: {r.text[:200]}"
                continue
            r.raise_for_status()
            data = _extract_json(r.json()["choices"][0]["message"].get("content") or "")
            if data is not None:
                return data
            last_error = "Sarvam returned text that was not JSON"
        except Exception as e:
            last_error = f"Sarvam error: {e}"
            break
    return None


def _groq_json(system, user, max_tokens=1800):
    global last_error
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}", "Content-Type": "application/json"}
    base = {"model": config.GROQ_MODEL, "temperature": 0.2, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    attempts = [
        {**base, "response_format": {"type": "json_object"}, "reasoning_effort": "low"},
        {**base, "response_format": {"type": "json_object"}},
        base,  # plainest request, for models that reject the extra options
    ]
    for payload in attempts:
        try:
            r = requests.post(CHAT_URL, headers=headers, json=payload, timeout=60)
            if r.status_code == 400:
                last_error = f"Groq 400: {r.text[:200]}"
                continue
            r.raise_for_status()
            content = r.json()["choices"][0]["message"].get("content") or ""
            data = _extract_json(content)
            if data is not None:
                last_error = None
                return data
            last_error = "Groq returned text that was not JSON"
        except Exception as e:
            last_error = f"Groq error: {e}"
            break
    return None


def transcribe(audio_bytes, filename="voice.webm", language=None):
    """Voice -> text. Sarvam Saaras first (built for Indian languages and mixed speech), Groq Whisper as backup.
    Returns (text, engine) or (None, None)."""
    global last_error
    if sarvam_available():
        try:
            r = requests.post(f"{SARVAM}/speech-to-text", headers={"api-subscription-key": config.SARVAM_API_KEY},
                              files={"file": (filename, audio_bytes)},
                              data={"model": config.SARVAM_STT_MODEL, "language_code": LANG_CODES.get(language, "unknown")},
                              timeout=60)
            r.raise_for_status()
            text = (r.json().get("transcript") or "").strip()
            if text:
                return text, "Sarvam Saaras"
        except Exception as e:
            last_error = f"Sarvam speech-to-text error: {e}"
    text = _whisper(audio_bytes, filename, {"hi": "hi", "kn": "kn", "en": "en", "hinglish": "hi"}.get(language))
    return (text, "Groq Whisper") if text else (None, None)


def _whisper(audio_bytes, filename="voice.webm", language=None):
    global last_error
    if not groq_available():
        return None
    data = {"model": config.GROQ_WHISPER_MODEL, "response_format": "json", "temperature": "0"}
    if language:
        data["language"] = language
    try:
        r = requests.post(STT_URL, headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
                          files={"file": (filename, audio_bytes)}, data=data, timeout=60)
        r.raise_for_status()
        return r.json().get("text", "").strip()
    except Exception as e:
        last_error = f"Groq speech-to-text error: {e}"
        return None


def vision_json(prompt, image_b64, mime="image/jpeg", max_tokens=900):
    """Photo + instruction -> JSON dict (Groq vision model), or None."""
    global last_error
    if not groq_available():
        return None
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": config.GROQ_VISION_MODEL, "temperature": 0.1, "max_tokens": max_tokens,
               "messages": [{"role": "user", "content": [
                   {"type": "text", "text": prompt},
                   {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}}]}]}
    for extra in ({"response_format": {"type": "json_object"}}, {}):
        try:
            r = requests.post(CHAT_URL, headers=headers, json={**payload, **extra}, timeout=60)
            if r.status_code == 400 and extra:
                continue
            r.raise_for_status()
            data = _extract_json(r.json()["choices"][0]["message"].get("content") or "")
            if isinstance(data, dict):
                last_error = None
                return data
        except Exception as e:
            last_error = f"Groq vision error: {e}"
            break
    return None


def read_photo(image_b64, mime="image/jpeg", hint=""):
    """Photo -> what the model sees (alarm screen text, codes, visible damage). Returns dict or None."""
    prompt = ("You help a worker describe a problem from a photo (machine alarm screen, nameplate, dish, device display, "
              "error screen, car part). Read any visible text and codes exactly. Return ONLY JSON: "
              '{"what_i_see": "1-2 sentences", "codes": ["exact codes or alarm numbers"], "readings": ["numbers with units"], '
              '"suggested_question": "the question the worker should ask Ustaad, one sentence"}. ' + (f"Context: {hint}" if hint else ""))
    return vision_json(prompt, image_b64, mime, 700)


def speak(text, language="en"):
    """Text -> speech with Sarvam Bulbul. Returns base64 WAV, or None."""
    global last_error
    if not sarvam_available() or not (text or "").strip():
        return None
    try:
        r = requests.post(f"{SARVAM}/text-to-speech",
                          headers={"api-subscription-key": config.SARVAM_API_KEY, "Content-Type": "application/json"},
                          json={"text": text[:2400], "language_code": LANG_CODES.get(language, "en-IN"),
                                "model": config.SARVAM_TTS_MODEL, "pace": 1.0},
                          timeout=60)
        r.raise_for_status()
        audios = r.json().get("audios") or []
        return audios[0] if audios else None
    except Exception as e:
        last_error = f"Sarvam text-to-speech error: {e}"
        return None


def sarvam_translate(texts, language):
    """Translate a list of short strings with Sarvam (simple, spoken-style words). Returns list or None."""
    global last_error
    if not sarvam_available():
        return None
    from concurrent.futures import ThreadPoolExecutor
    target = LANG_CODES.get(language, "hi-IN")
    extra = {"output_script": "roman"} if language == "hinglish" else {}

    def one(t):
        if not (t or "").strip():
            return t
        r = requests.post(f"{SARVAM}/translate",
                          headers={"api-subscription-key": config.SARVAM_API_KEY, "Content-Type": "application/json"},
                          json={"input": t[:990], "source_language_code": "auto", "target_language_code": target,
                                "model": config.SARVAM_TRANSLATE_MODEL, "mode": "modern-colloquial", **extra},
                          timeout=45)
        r.raise_for_status()
        return r.json().get("translated_text") or t
    try:
        with ThreadPoolExecutor(max_workers=6) as ex:
            return list(ex.map(one, texts))
    except Exception as e:
        last_error = f"Sarvam translate error: {e}"
        return None
