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

last_error = None


def available():
    return bool(config.GROQ_API_KEY)


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
    """Ask the model for a JSON object. Returns a dict, or None if anything goes wrong."""
    global last_error
    if not available():
        return None
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
    """Voice -> text with Groq Whisper. Works for Hindi, Kannada, English and mixed speech."""
    global last_error
    if not available():
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


def read_photo(image_b64, mime="image/jpeg", hint=""):
    """Photo -> what the model sees (alarm screen text, codes, visible damage). Returns dict or None."""
    global last_error
    if not available():
        return None
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}", "Content-Type": "application/json"}
    prompt = ("You help a worker describe a problem from a photo (machine alarm screen, nameplate, dish, device display, "
              "error screen, car part). Read any visible text and codes exactly. Return ONLY JSON: "
              '{"what_i_see": "1-2 sentences", "codes": ["exact codes or alarm numbers"], "readings": ["numbers with units"], '
              '"suggested_question": "the question the worker should ask Ustaad, one sentence"}. ' + (f"Context: {hint}" if hint else ""))
    payload = {"model": config.GROQ_VISION_MODEL, "temperature": 0.1, "max_tokens": 700,
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
