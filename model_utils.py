# model_utils.py – resilient model selection (tries GPT-5, falls back cleanly)
import os
from openai import OpenAI
from openai import APIError

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Put your preferred model first; env var can override.
MODEL_CHAIN = [
    os.getenv("OPENAI_MODEL") or "gpt-5-chat",  # will 404 today; that's fine
    "gpt-4o",
    "gpt-4o-mini",
]

def chat_call(messages, temperature=0.2):
    """
    Try models in MODEL_CHAIN until one works.
    Returns (model_used, text).
    """
    last_err = None
    for model_name in MODEL_CHAIN:
        if not model_name:
            continue
        try:
            resp = _client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
            )
            text = (resp.choices[0].message.content or "").strip()
            return model_name, text
        except Exception as e:
            # swallow 404/missing model and try next
            msg = str(e).lower()
            if "model" in msg and ("not found" in msg or "does not exist" in msg):
                last_err = e
                continue
            # other API errors (rate limit, auth) -> bubble up
            if isinstance(e, APIError):
                raise
            last_err = e
            continue
    raise RuntimeError(f"No usable model from chain {MODEL_CHAIN}. Last error: {last_err}")
