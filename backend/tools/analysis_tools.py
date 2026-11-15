"""
Analytical calculation and statistical aggregation tools.
Permitted quantitative operations for Agent C (Analysis Agent).
"""

from typing import Dict, Any, List

def analyze_sentiment_and_severity(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes statistical sentiment metrics and severity distributions
    over customer complaint records.
    """
    if not records:
        return {"error": "Empty dataset"}
    
    total = len(records)
    sentiment_scores = []
    severities = {}
    categories = {}
    critical_tickets = []
    
    for r in records:
        try:
            score = float(r.get("sentiment_score", 0.0))
            sentiment_scores.append(score)
        except (ValueError, TypeError):
            pass
            
        sev = r.get("severity", "Unknown")
        severities[sev] = severities.get(sev, 0) + 1
        
        cat = r.get("category", "General")
        categories[cat] = categories.get(cat, 0) + 1
        
        if sev in ("High", "Critical"):
            critical_tickets.append({
                "ticket_id": r.get("ticket_id"),
                "customer_id": r.get("customer_id"),
                "category": cat,
                "severity": sev,
                "sentiment_score": r.get("sentiment_score")
            })
            
    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
    
    return {
        "total_tickets": total,
        "average_sentiment": round(avg_sentiment, 3),
        "sentiment_polarity": "strongly_negative" if avg_sentiment < -0.4 else "neutral_or_positive",
        "severity_distribution": severities,
        "category_distribution": categories,
        "high_priority_count": len(critical_tickets),
        "critical_incidents": critical_tickets
    }

def audit_security_access(access_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Audits access logs for unauthorized accesses, sensitive resource touches,
    and externalization drift patterns.
    """
    if not access_logs:
        return {"error": "Empty log dataset"}
        
    violations = []
    sensitive_touches = []
    
    for log in access_logs:
        is_auth = str(log.get("authorized", "true")).lower() == "true"
        sens = log.get("sensitivity", "internal")
        
        if not is_auth or "flagged" in str(log.get("authorized", "")).lower():
            violations.append(log)
            
        if sens in ("confidential", "restricted"):
            sensitive_touches.append(log)
            
    return {
        "total_access_events": len(access_logs),
        "violations_detected": len(violations),
        "flagged_events": violations,
        "sensitive_access_count": len(sensitive_touches),
        "sensitive_details": sensitive_touches
    }

def analyze_text_content(content: Any) -> Dict[str, Any]:
    """
    Analyzes unstructured or semi-structured text notes, extracting metrics,
    identified topics, and action items.
    """
    text = str(content or "")
    words = text.split()
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    
    # Identify mentions of key research dimensions
    topics = []
    if any(k in text.lower() for k in ["delegation", "authority", "token"]):
        topics.append("Delegation Authority & Non-Identifiability")
    if any(k in text.lower() for k in ["privacy", "redact", "capture"]):
        topics.append("Privacy-Aware Telemetry")
    if any(k in text.lower() for k in ["graph", "interaction", "provenance"]):
        topics.append("Multi-Graph Provenance & Lineage")
    if not topics:
        topics.append("General Research Findings")

    action_items = [ln for ln in lines if any(k in ln.lower() for k in ["must", "action", "recommend", "todo", "note"])]

    return {
        "total_characters": len(text),
        "total_words": len(words),
        "total_paragraphs": len(lines),
        "topics_identified": topics,
        "key_action_items": action_items[:5] if action_items else ["Implement multi-agent transparency gateway"]
    }

