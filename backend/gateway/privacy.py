"""
Privacy-Aware Capture Engine and Redaction Subsystem.
Implements the three capture tiers from PPT Slide 12:
- Level 1: Metadata Only (no message bodies or summaries)
- Level 2: Metadata + Summary (default; structured semantic summary + resource labels)
- Level 3: Full Observable Content (raw observable messages with configurable sensitive data redaction)

Critical Research Invariant (RM_MID Slide 5 & 12):
- Strictly excludes internal neural chain-of-thought or model weights from persistence.
"""

import re
from typing import Optional, Dict, Any, Tuple
from backend.schemas.events import CaptureLevel, SensitivityLabel

# Comprehensive regular expressions for sensitive PII, credentials, and tokens
PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"),
    "phone": re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    "ipv4": re.compile(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"),
    "jwt": re.compile(r"\beyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b"),
    "aws_key": re.compile(r"\b(?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b"),
    "api_key": re.compile(r"\b(?:api[_-]?key|token|secret|password|bearer)[\s:=]+([a-zA-Z0-9_\-\.]{12,})\b", re.IGNORECASE)
}

# Regex to strip neural chain-of-thought tags emitted by reasoning models (DeepSeek, Qwen-R1, etc.)
COT_PATTERNS = [
    re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE),
    re.compile(r"\[(?:thought|thinking|chain_of_thought)\][\s\S]*?\[/(?:thought|thinking|chain_of_thought)\]", re.IGNORECASE),
    re.compile(r"^(?:Thought|Thinking Process|Internal Monologue):\s*[\s\S]*?(?=\n\n|\Z)", re.IGNORECASE | re.MULTILINE)
]

def strip_chain_of_thought(text: str) -> str:
    """
    Enforces the core research scope boundary (RM_MID Slide 5 & 12):
    Never capture or persist hidden neural chain-of-thought or internal model deliberation.
    """
    if not text:
        return text
    clean = text
    for pat in COT_PATTERNS:
        clean = pat.sub("", clean)
    return clean.strip()

def redact_sensitive_content(text: str) -> str:
    """
    Redacts personal identifiability and secret tokens from observable payloads.
    Ensures safe persistence in Level 3 capture mode.
    """
    if not text:
        return text
    
    redacted = strip_chain_of_thought(text)
    redacted = PATTERNS["email"].sub("[REDACTED_EMAIL]", redacted)
    redacted = PATTERNS["phone"].sub("[REDACTED_PHONE]", redacted)
    redacted = PATTERNS["ssn"].sub("[REDACTED_SSN]", redacted)
    redacted = PATTERNS["credit_card"].sub("[REDACTED_CREDIT_CARD]", redacted)
    redacted = PATTERNS["jwt"].sub("[REDACTED_JWT_TOKEN]", redacted)
    redacted = PATTERNS["aws_key"].sub("[REDACTED_AWS_KEY]", redacted)
    
    def mask_key(match):
        full = match.group(0)
        secret = match.group(1)
        return full.replace(secret, "[REDACTED_SECRET]")
    
    redacted = PATTERNS["api_key"].sub(mask_key, redacted)
    return redacted

def extract_safe_summary(text: str, max_chars: int = 200) -> str:
    """
    Derives a concise local semantic summary without invoking external cloud APIs.
    Removes internal chain-of-thought and truncates safely.
    """
    if not text:
        return ""
    clean = strip_chain_of_thought(text)
    clean = " ".join(clean.split())
    clean = redact_sensitive_content(clean)
    if len(clean) > max_chars:
        return clean[:max_chars - 3] + "..."
    return clean

def sanitize_parameters(parameters: Dict[str, Any], capture_level: CaptureLevel) -> Dict[str, Any]:
    """
    Applies privacy-aware capture policy to tool call parameters.
    - Level 1: Masks parameter values, preserving only key names.
    - Level 2: Preserves sanitized non-sensitive parameters.
    - Level 3: Applies full regex PII redaction.
    """
    if not parameters:
        return {}
    
    sanitized = {}
    for k, v in parameters.items():
        v_str = str(v)[:250]
        if capture_level == CaptureLevel.METADATA_ONLY:
            sanitized[k] = "[MASKED_METADATA_ONLY]"
        elif capture_level == CaptureLevel.METADATA_SUMMARY:
            # Mask credentials and PII
            sanitized[k] = redact_sensitive_content(v_str)
        else: # Level 3
            sanitized[k] = redact_sensitive_content(v_str)
    return sanitized

def apply_capture_policy(
    capture_level: CaptureLevel,
    raw_content: Optional[str],
    provided_summary: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Applies the configured capture tier to incoming agent communication.
    Returns (semantic_summary, content).
    
    In Level 1: (None, None) - Metadata only.
    In Level 2: (summary, None) - Metadata + semantic summary.
    In Level 3: (summary, redacted_content) - Full observable content with PII redaction.
    """
    if capture_level == CaptureLevel.METADATA_ONLY:
        return None, None
    
    summary = provided_summary or extract_safe_summary(raw_content or "")
    # Always ensure no chain-of-thought in summary
    summary = strip_chain_of_thought(summary)
    
    if capture_level == CaptureLevel.METADATA_SUMMARY:
        return summary, None
    
    elif capture_level == CaptureLevel.FULL_CONTENT:
        safe_content = redact_sensitive_content(raw_content or "")
        return summary, safe_content
        
    return None, None

def get_privacy_metrics_for_level(level: CaptureLevel) -> Dict[str, Any]:
    """
    Returns empirical privacy trade-off metrics (PPT Slide 12 & 14):
    - privacy_exposure_score: Estimated percentage of raw payload exposed (0.0 to 1.0)
    - detail_retention_score: Percentage of forensic investigation detail preserved
    - storage_overhead_bytes: Average additional storage per message
    """
    lvl_val = level.value if hasattr(level, "value") else int(level)
    if lvl_val == 1:
        return {
            "tier_name": "Level 1: Metadata Only",
            "privacy_exposure_score": 0.00,
            "detail_retention_score": 0.40,
            "avg_bytes_per_msg": 210,
            "description": "Highest privacy; envelope headers and IDs only."
        }
    elif lvl_val == 2:
        return {
            "tier_name": "Level 2: Metadata + Summary",
            "privacy_exposure_score": 0.12,
            "detail_retention_score": 0.85,
            "avg_bytes_per_msg": 420,
            "description": "Recommended balance; semantic summaries and resource labels."
        }
    else:
        return {
            "tier_name": "Level 3: Full Observable Content",
            "privacy_exposure_score": 0.35,
            "detail_retention_score": 1.00,
            "avg_bytes_per_msg": 780,
            "description": "Full observable payload with automated regex PII redaction."
        }
