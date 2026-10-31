"""
LLM interaction module.

Builds a detailed prompt, sends it to the configured LLM provider, and parses
the response into a structured dictionary.

Supported providers (set LLM_PROVIDER in backend/.env):
- "gemini"  -> Google Gemini API (default)
- "openai"  -> OpenAI Chat Completions (GPT-3.5 / GPT-4)
- "ollama"  -> local Ollama instance (e.g. llama2)
"""

import json
import re
from typing import Dict, List

from .config import settings

# Non-critical characters we do not want to feed to the model.
MAX_TEXT_LENGTH = 12000


def _explanation_field(language: str) -> str:
    """Return the JSON field name used for the regional explanation."""
    return "simplified_explanation_hi" if language.lower() == "hindi" else (
        f"simplified_explanation_{language.lower()}"
    )


def _truncate(text: str, limit: int = MAX_TEXT_LENGTH) -> str:
    """Truncate oversized documents so we stay within token limits."""
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated for length]"


def _build_prompt(text: str, target_language: str = "hindi") -> str:
    """
    Construct the system + user prompt instructing the model to act as a
    legal document analyst and return strict JSON.
    """
    language_name = {
        "hindi": "Hindi",
        "english": "English",
        "punjabi": "Punjabi",
        "tamil": "Tamil",
        "telugu": "Telugu",
        "bengali": "Bengali",
        "marathi": "Marathi",
        "gujarati": "Gujarati",
        "kannada": "Kannada",
        "malayalam": "Malayalam",
    }.get(target_language.lower(), "Hindi")

    system_prompt = (
        "You are an expert legal assistant who helps everyday people understand "
        "legal documents. You always respond with valid JSON only, never with "
        "markdown or surrounding prose."
    )

    user_prompt = f"""
Act as an expert legal document analyst. Given the following legal notice text,
extract the following fields in JSON format:

- document_type (e.g., summons, notice, court order)
- court_authority (name of court or authority)
- parties (list of parties involved)
- case_number (if any)
- court_date (date of hearing, if present)
- deadlines (list of important dates/deadlines)
- required_actions (bullet points of what the recipient must do)
- simplified_explanation_en (a simple, plain English summary of the notice)
- {_explanation_field(target_language)} (a simple {language_name}
  translation of the above explanation)
- warnings (any critical warnings like "do not ignore", "contempt of court", etc.)
- action_steps (step-by-step recommended actions for the user)

Rules:
- Return ONLY a single valid JSON object with these keys.
- Use empty strings or empty arrays when information is not present.
- Keep explanations simple, clear, and non-technical.
- The {language_name} explanation must be a natural translation written in
  the {language_name} script.

Notice text:
\"\"\"{text}\"\"\"

Output only valid JSON.
"""

    return system_prompt, user_prompt


def _call_gemini(system_prompt: str, user_prompt: str) -> str:
    """Call the Google Gemini API using the google-genai SDK."""
    if not settings.GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to backend/.env (see .env.example)."
            " Get a free key from https://aistudio.google.com/apikey"
        )

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:  # pragma: no cover - defensive
        raise RuntimeError(
            "The 'google-genai' package is not installed. Run: pip install google-genai"
        ) from exc

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )
    return response.text


def _call_openai(system_prompt: str, user_prompt: str) -> str:
    """Call the OpenAI chat completions API."""
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - defensive
        raise RuntimeError(
            "The 'openai' package is not installed. Run: pip install openai"
        ) from exc

    # Support OpenAI-compatible providers (e.g. proxies) via base_url.
    kwargs = {
        "api_key": settings.OPENAI_API_KEY,
        "base_url": settings.OPENAI_BASE_URL,
    } if settings.OPENAI_BASE_URL else {"api_key": settings.OPENAI_API_KEY}

    if not settings.OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to backend/.env (see .env.example)."
        )

    client = OpenAI(**kwargs)
    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content


def _call_ollama(system_prompt: str, user_prompt: str) -> str:
    """Call a local Ollama instance (OpenAI-compatible /api/chat endpoint)."""
    import httpx

    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "format": "json",
    }
    try:
        resp = httpx.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")
    except Exception as exc:  # pragma: no cover - defensive
        raise RuntimeError(
            f"Could not reach local Ollama at {settings.OLLAMA_BASE_URL}. "
            "Is Ollama running? Error: {exc}"
        ) from exc


def _call_llm(system_prompt: str, user_prompt: str) -> str:
    """
    Dispatch to the configured LLM provider.

    Provider priority: LLM_PROVIDER env var, falling back to USE_LOCAL_LLM
    (kept for backward compatibility).
    """
    provider = settings.LLM_PROVIDER
    if provider == "ollama" or (provider == "gemini" and settings.USE_LOCAL_LLM):
        return _call_ollama(system_prompt, user_prompt)
    if provider == "openai":
        return _call_openai(system_prompt, user_prompt)
    return _call_gemini(system_prompt, user_prompt)


def _clean_json_text(raw: str) -> str:
    """Strip code fences and surrounding prose from an LLM response."""
    cleaned = raw.strip()
    # Remove leading/trailing triple-backtick fences.
    cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    return cleaned


def _parse_json_response(raw: str) -> Dict:
    """Parse the LLM output into a dictionary with graceful fallbacks."""
    cleaned = _clean_json_text(raw)

    # Try standard parsing first.
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to locate the first JSON object inside the text.
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError("The model did not return valid JSON.")


def _normalize_result(data: Dict, target_language: str) -> Dict:
    """
    Ensure the returned dict has all expected keys, coercing values to the
    correct types so downstream code never crashes.
    """
    field = _explanation_field(target_language)
    regional = data.get(field)

    def _to_list(value) -> List:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v) for v in value]
        return [str(value)]

    if target_language.lower() == "hindi":
        result_regional = regional or data.get("simplified_explanation_en")
    else:
        result_regional = regional or data.get("simplified_explanation_hi") or (
            data.get("simplified_explanation_en")
        )

    result = {
        "document_type": data.get("document_type"),
        "court_authority": data.get("court_authority"),
        "parties": _to_list(data.get("parties")),
        "case_number": data.get("case_number"),
        "court_date": data.get("court_date"),
        "deadlines": _to_list(data.get("deadlines")),
        "required_actions": _to_list(data.get("required_actions")),
        "simplified_explanation_en": data.get("simplified_explanation_en"),
        "simplified_explanation_hi": data.get("simplified_explanation_hi"),
        "warnings": _to_list(data.get("warnings")),
        "action_steps": _to_list(data.get("action_steps")),
    }

    # Hindi tab always needs the regional translation under its key.
    result["simplified_explanation_hi"] = (
        data.get("simplified_explanation_hi")
        or regional
        or data.get("simplified_explanation_en")
    )

    # Expose the selected-language explanation under its own field too.
    if target_language.lower() != "hindi":
        result[field] = result_regional
        # Always keep a `hi` field for the simplified Hindi tab as well.
        if not result["simplified_explanation_hi"]:
            result["simplified_explanation_hi"] = result_regional

    return result


def analyze_legal_document(
    text: str, target_language: str = "hindi"
) -> Dict:
    """
    Analyze a legal document's text and return a structured summary dict.

    Parameters
    ----------
    text : str
        Plain text extracted from the PDF.
    target_language : str
        Language code for the regional translation (e.g. 'hindi', 'punjabi').

    Returns
    -------
    dict
        A normalized dict matching the frontend's expected shape.
    """
    text = _truncate(text)
    system_prompt, user_prompt = _build_prompt(text, target_language)

    try:
        raw = _call_llm(system_prompt, user_prompt)
    except (RuntimeError, Exception) as exc:
        # Re-raise known runtime errors; wrap unexpected ones.
        if isinstance(exc, RuntimeError):
            raise
        raise RuntimeError(f"LLM request failed: {exc}") from exc

    data = _parse_json_response(raw)
    return _normalize_result(data, target_language)


def _call_llm_text(system_prompt: str, user_prompt: str) -> str:
    """Send a single-turn text request to the configured provider (no JSON)."""
    provider = settings.LLM_PROVIDER
    if provider == "openai":
        return _call_openai(system_prompt, user_prompt)
    if provider == "ollama" or (provider == "gemini" and settings.USE_LOCAL_LLM):
        return _call_ollama(system_prompt, user_prompt)

    # Gemini text generation (no response_mime_type -> free-form text).
    if not settings.GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to backend/.env (see .env.example)."
        )
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:  # pragma: no cover - defensive
        raise RuntimeError(
            "The 'google-genai' package is not installed. Run: pip install google-genai"
        ) from exc

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.4,
        ),
    )
    return response.text


def chat_about_document(
    document_text: str,
    analysis: Dict,
    question: str,
    history: list,
    target_language: str = "hindi",
) -> str:
    """
    Ask the LLM a question about a specific legal document.

    Parameters
    ----------
    document_text : str
        The extracted plain text of the notice.
    analysis : dict
        The structured analysis previously produced for the document.
    question : str
        The user's current question.
    history : list of {role, content}
        Prior turns in the conversation.
    target_language : str
        Preferred language code for helpful responses.
    """
    language_name = {
        "hindi": "Hindi",
        "english": "English",
        "punjabi": "Punjabi",
        "tamil": "Tamil",
        "telugu": "Telugu",
        "bengali": "Bengali",
        "marathi": "Marathi",
        "gujarati": "Gujarati",
        "kannada": "Kannada",
        "malayalam": "Malayalam",
    }.get(target_language.lower(), "Hindi")

    truncated_doc = _truncate(document_text, limit=6000)
    analysis_json = json.dumps(analysis, ensure_ascii=False)[:4000]

    # Build a compact conversation transcript.
    transcript = "\n".join(
        f"{turn.get('role', 'user').upper()}: {turn.get('content', '')}"
        for turn in history[-10:]
    )

    system_prompt = (
        "You are a patient, helpful legal assistant embedded in a court notice "
        "translator app. You help a non-lawyer understand ONE specific legal "
        "document they uploaded. You explain things in simple, clear language "
        "in " + language_name + " when appropriate. You are honest about "
        "uncertainty and always encourage consulting a qualified lawyer for "
        "legal advice. You NEVER invent facts not supported by the document."
    )

    user_prompt = f"""
You are helping the user understand a legal document they uploaded.

DOCUMENT (extracted text):
\"\"\"{truncated_doc}\"\"\"

STRUCTURED ANALYSIS OF THE DOCUMENT:
{analysis_json}

CONVERSATION SO FAR:
{transcript or "(none yet)"}

The user's latest question is:
\"\"\"{question}\"\"\"

Answer helpfully based only on the document and the analysis above. Keep it
concise, friendly, and in simple {language_name}. Use plain text (no markdown
tables); short bullet points are fine. If the answer isn't in the document,
say so and suggest what to do next.
"""

    try:
        return _call_llm_text(system_prompt, user_prompt).strip()
    except (RuntimeError, Exception) as exc:
        if isinstance(exc, RuntimeError):
            raise
        raise RuntimeError(f"LLM chat request failed: {exc}") from exc
