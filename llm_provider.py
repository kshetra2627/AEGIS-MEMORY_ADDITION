"""Single-interface LLM provider abstraction with automatic failover: Groq -> Gemini -> OpenRouter.
Switching providers requires only env var changes, never code changes.
"""
import os
from dotenv import load_dotenv

load_dotenv()

_DEFAULT_GROQ_MODELS = ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]


def _call_groq(messages: list[dict], temperature: float) -> str:
    from openai import OpenAI
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not configured")

    configured = os.getenv("GROQ_MODEL", "").strip()
    models = [m for m in [configured, *_DEFAULT_GROQ_MODELS] if m]
    seen = set()
    ordered = []
    for model in models:
        if model not in seen:
            seen.add(model)
            ordered.append(model)

    last_error = None
    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1", timeout=20)
    for model in ordered:
        try:
            resp = client.chat.completions.create(model=model, messages=messages, temperature=temperature)
            return resp.choices[0].message.content
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            msg = str(exc).lower()
            if "model_not_found" not in msg and "404" not in msg:
                raise
    if last_error is not None:
        raise last_error
    raise RuntimeError("No valid Groq model available")


def _call_gemini(messages: list[dict], temperature: float) -> str:
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not configured")
    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    system_parts = [m["content"] for m in messages if m["role"] == "system"]
    user_parts = [m["content"] for m in messages if m["role"] != "system"]
    model = genai.GenerativeModel(model_name, system_instruction="\n".join(system_parts) or None)
    resp = model.generate_content(
        "\n".join(user_parts),
        generation_config={"temperature": temperature},
        request_options={"timeout": 20},
    )
    return resp.text


def _call_openrouter(messages: list[dict], temperature: float) -> str:
    from openai import OpenAI
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    model = os.getenv("OPENROUTER_MODEL", "").strip()
    if not api_key or not model:
        raise RuntimeError("OPENROUTER_API_KEY/OPENROUTER_MODEL not configured")
    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1", timeout=20)
    resp = client.chat.completions.create(model=model, messages=messages, temperature=temperature)
    return resp.choices[0].message.content


PROVIDERS = [
    ("groq", _call_groq),
    ("gemini", _call_gemini),
    ("openrouter", _call_openrouter),
]


def get_llm_response(messages: list[dict], temperature: float = 0.1) -> dict:
    """Tries each configured provider in priority order. Never raises -- on total failure
    returns provider='none' with a safe fallback message so the app keeps operating.
    """
    attempts = []
    for name, fn in PROVIDERS:
        try:
            text = fn(messages, temperature)
            attempts.append({"provider": name, "status": "success", "error": None})
            return {"text": text, "provider": name, "attempts": attempts}
        except Exception as e:
            attempts.append({"provider": name, "status": "failed", "error": str(e)})
            continue

    return {
        "text": "",
        "provider": "none",
        "attempts": attempts,
    }
