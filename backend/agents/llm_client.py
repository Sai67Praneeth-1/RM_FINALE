"""
Local LLM client and availability checker.
Supports Ollama local inference with dynamic model discovery,
automatic model fallback, and neural chain-of-thought stripping.
"""

import httpx
from typing import Optional, Dict, Any, List
from backend.config import settings
from backend.gateway.privacy import strip_chain_of_thought

def is_ollama_available(base_url: Optional[str] = None) -> bool:
    """Checks whether the local Ollama service is reachable."""
    url = base_url or settings.OLLAMA_BASE_URL
    try:
        resp = httpx.get(f"{url}/api/tags", timeout=1.5)
        return resp.status_code == 200
    except Exception:
        return False

def list_installed_ollama_models(base_url: Optional[str] = None) -> List[str]:
    """Lists locally installed Ollama models."""
    url = base_url or settings.OLLAMA_BASE_URL
    try:
        resp = httpx.get(f"{url}/api/tags", timeout=2.0)
        if resp.status_code == 200:
            models_info = resp.json().get("models", [])
            return [m.get("name") for m in models_info if m.get("name")]
    except Exception:
        pass
    return []

def get_active_model(model_name: Optional[str] = None, base_url: Optional[str] = None) -> str:
    """
    Selects the best available model:
    1. Explicit model_name or settings.OLLAMA_MODEL if installed
    2. First installed model if configured model not pulled yet
    3. Fallback to settings.OLLAMA_MODEL
    """
    configured = model_name or settings.OLLAMA_MODEL
    installed = list_installed_ollama_models(base_url)
    if not installed:
        return configured
    
    # Check exact match or prefix match
    for m in installed:
        if configured in m or m in configured:
            return m
    return installed[0]

def query_local_llm(
    prompt: str,
    system_prompt: str,
    model_name: Optional[str] = None,
    temperature: float = 0.2
) -> Optional[str]:
    """
    Queries the local Ollama instance using /api/chat (or /api/generate fallback).
    Automatically strips neural chain-of-thought (<think>...</think>) before returning.
    """
    if not is_ollama_available():
        return None
        
    model = get_active_model(model_name)
    base_url = settings.OLLAMA_BASE_URL

    # Try modern /api/chat first
    try:
        chat_url = f"{base_url}/api/chat"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {"temperature": temperature}
        }
        resp = httpx.post(chat_url, json=payload, timeout=60.0)
        if resp.status_code == 200:
            raw_text = resp.json().get("message", {}).get("content", "").strip()
            return strip_chain_of_thought(raw_text)
    except Exception:
        pass

    # Fallback to legacy /api/generate
    try:
        gen_url = f"{base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {"temperature": temperature}
        }
        resp = httpx.post(gen_url, json=payload, timeout=60.0)
        if resp.status_code == 200:
            raw_text = resp.json().get("response", "").strip()
            return strip_chain_of_thought(raw_text)
    except Exception:
        pass

    return None
