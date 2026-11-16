"""
LLM Client Subsystem: Google Gemini API (Primary) with Legacy Fallbacks.
Provides unified LLM inference for:
  1. General chatbot conversation (answers any question like ChatGPT)
  2. Multi-agent pipeline tool enrichment
  3. Multi-agent dialogue simulation

Uses Google Gemini API (free tier) as the primary engine.
Neural chain-of-thought stripping (<think> blocks) is enforced on all outputs.
"""

import os
import re
import logging
from typing import Optional, Dict, Any, List, Tuple

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from backend.config import settings
from backend.gateway.privacy import strip_chain_of_thought

logger = logging.getLogger(__name__)


# ==============================================================================
# 1. Internal Reasoning Stripping
# ==============================================================================

def strip_internal_reasoning(raw_text: str) -> str:
    """
    Strips out internal reasoning chains or <think> blocks
    to ensure only public communication is logged between agents.
    """
    if not raw_text:
        return ""
    cleaned = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL)
    return strip_chain_of_thought(cleaned.strip())


# ==============================================================================
# 2. Google Gemini Client (Primary LLM Engine — Free Tier)
# ==============================================================================

import httpx

_http_client: Optional[httpx.Client] = None

def _get_http_client() -> httpx.Client:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.Client(
            timeout=httpx.Timeout(12.0, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20, keepalive_expiry=60.0)
        )
    return _http_client

def _get_api_key() -> str:
    return (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or settings.GEMINI_API_KEY
        or ""
    )
def is_gemini_available() -> bool:
    """Checks whether the Gemini API key is configured."""
    return bool(_get_api_key())

def is_huggingface_available(api_key: Optional[str] = None, base_url: Optional[str] = None) -> bool:
    """Checks whether either Hugging Face or Gemini API is available."""
    key = api_key or settings.HF_API_KEY
    if key and key.startswith("hf_"):
        return True
    return is_gemini_available()

FALLBACK_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
]

def _normalize_model(model_name: Optional[str]) -> str:
    known_bad = {
        "gemini-3.8-flash", "gemini-2.0-flash", "gemini-1.5-flash",
        "gemini-2.0-flash-lite"
    }
    if not model_name or model_name in known_bad:
        return settings.GEMINI_MODEL or "gemini-3.5-flash-lite"
    return model_name

def query_gemini(
    prompt: str,
    system_prompt: str = "",
    model_name: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048
) -> Optional[str]:
    """
    Direct, ultra-fast REST client for Google Gemini API with HTTP connection pooling.
    Provides resilient response latency with automatic multi-model failover.
    """
    api_key = _get_api_key()
    if not api_key:
        return None

    primary = _normalize_model(model_name)
    models_to_try = [primary] + [m for m in FALLBACK_MODELS if m != primary]

    payload: Dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens
        }
    }
    if system_prompt:
        payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

    client = _get_http_client()

    for m in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
        try:
            resp = client.post(url, json=payload, timeout=12.0)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        raw_text = parts[0].get("text", "")
                        return strip_internal_reasoning(raw_text)
            elif resp.status_code in (429, 503, 404):
                logger.debug(f"[LLM Client] Model {m} returned {resp.status_code}, trying fallback...")
                continue
        except Exception as e:
            logger.debug(f"[LLM Client] Model {m} request note: {e}, trying fallback...")
            continue

    return None


def query_gemini_chat(
    messages: List[Dict[str, str]],
    system_prompt: str = "",
    model_name: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048
) -> Optional[str]:
    """
    Direct, ultra-fast REST multi-turn chat client for Google Gemini API with connection pooling.
    """
    api_key = _get_api_key()
    if not api_key:
        return None

    primary = _normalize_model(model_name)
    models_to_try = [primary] + [m for m in FALLBACK_MODELS if m != primary]

    contents = []
    for msg in messages:
        role = msg.get("role", "user")
        if role in ("assistant", "system"):
            role = "model"
        elif role != "user":
            role = "user"
        contents.append({
            "role": role,
            "parts": [{"text": msg.get("content", "")}]
        })

    payload: Dict[str, Any] = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens
        }
    }
    if system_prompt:
        payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

    client = _get_http_client()

    for m in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
        try:
            resp = client.post(url, json=payload, timeout=12.0)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        raw_text = parts[0].get("text", "")
                        return strip_internal_reasoning(raw_text)
            elif resp.status_code in (429, 503, 404):
                logger.debug(f"[LLM Client] Model {m} returned {resp.status_code}, trying fallback...")
                continue
        except Exception as e:
            logger.debug(f"[LLM Client] Model {m} request note: {e}, trying fallback...")
            continue

    return None


# ==============================================================================
# 3. Unified Query Interface
# ==============================================================================

def query_agent_llm(
    prompt: str,
    system_prompt: str,
    model_name: Optional[str] = None,
    mode: str = "live_api",
    temperature: float = 0.5
) -> Optional[str]:
    """
    Unified agent LLM inference function.
    Tries Gemini first, falls back to None (deterministic mode).
    """
    if mode in ["live_api", "live_gemini", "live_huggingface", "live_ollama", "api"]:
        result = query_gemini(
            prompt=prompt,
            system_prompt=system_prompt,
            model_name=model_name,
            temperature=temperature
        )
        if result:
            return result

    return None


# Backwards-compatible aliases
def is_ollama_available(base_url=None) -> bool:
    return False

def is_huggingface_available(api_key=None, base_url=None) -> bool:
    return is_gemini_available()

def is_api_available(api_key=None) -> bool:
    return is_gemini_available()

def list_installed_ollama_models(base_url=None) -> List[str]:
    return []

def list_huggingface_router_models() -> List[str]:
    return [settings.GEMINI_MODEL or "gemini-3.5-flash-lite"]

def query_local_llm(prompt, system_prompt, model_name=None, temperature=0.2):
    return query_gemini(prompt=prompt, system_prompt=system_prompt, model_name=model_name, temperature=temperature)

def query_huggingface_llm(prompt, system_prompt, model_name=None, shared_history=None, temperature=0.3, max_tokens=250):
    return query_gemini(prompt=prompt, system_prompt=system_prompt, model_name=model_name, temperature=temperature, max_tokens=max_tokens)


# ==============================================================================
# 4. Multi-Agent Simulation Helpers
# ==============================================================================

def extract_goal_from_history(shared_history: list) -> str:
    """Extracts original research directive / goal from shared conversation history."""
    for msg in shared_history:
        content = msg.get("content", "")
        if "Research Goal:" in content:
            return content.split("Research Goal:")[-1].strip()
        if "Goal:" in content:
            return content.split("Goal:")[-1].strip()
    return "Audit customer complaints for critical severity anomalies and verify system SLAs."


def generate_simulated_turn_message(agent_name: str, model_name: str, shared_history: list) -> str:
    """Fallback for multi-agent simulation when LLM is unavailable."""
    from backend.orchestration.dynamic_query_engine import generate_dynamic_agent_dialogue
    goal = extract_goal_from_history(shared_history)
    turn_num = len([m for m in shared_history if "[" in m.get("content", "") and "Principal" not in m.get("content", "")]) + 1
    return generate_dynamic_agent_dialogue(agent_name, model_name, turn_num, goal)


def run_agent_turn(
    model_name: str,
    agent_name: str,
    system_prompt: str,
    shared_history: list,
    client=None,
    temperature: float = 0.3,
    max_tokens: int = 150
) -> str:
    """Executes a single agent turn using Gemini API."""
    # Build the prompt from shared history
    history_text = "\n".join([m.get("content", "") for m in shared_history[-6:]])
    full_prompt = f"{history_text}\n\nNow respond as {agent_name}:"

    try:
        result = query_gemini(
            prompt=full_prompt,
            system_prompt=system_prompt,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens
        )
        if result:
            public_message = result
        else:
            public_message = generate_simulated_turn_message(agent_name, model_name, shared_history)
    except Exception:
        public_message = generate_simulated_turn_message(agent_name, model_name, shared_history)

    print(f"[{agent_name} ({model_name})]: {public_message}\n")

    shared_history.append({
        "role": "user",
        "content": f"[{agent_name}]: {public_message}"
    })

    return public_message


# Keep init_hf_client and init_llm_client as no-ops for backwards compat
def init_hf_client(api_key=None, base_url=None):
    return None

def init_llm_client(api_key=None, base_url=None):
    return None
