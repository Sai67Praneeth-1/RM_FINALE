"""
Dataset Manager for Remote and Enterprise Datasets.
Handles automated fetching, caching, and normalization of large-scale
remote datasets specified via .env configuration:
- CFPB_COMPLAINTS_URL (Consumer Financial Protection Bureau)
- KAGGLE_CFPB_DATASET (Kaggle consumer-complaint-database snapshot)
"""

import os
import io
import csv
import zipfile
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

# Baseline enterprise tickets to guarantee complete backward-compatibility with test suites
BASELINE_ENTERPRISE_TICKETS = [
    {
        "ticket_id": "TKT-1001",
        "customer_id": "CUST-849",
        "channel": "email",
        "category": "Billing Overcharge",
        "severity": "High",
        "sentiment_score": "-0.85",
        "description": "Charged twice for monthly premium subscription in October.",
        "status": "open",
        "account_tier": "Enterprise",
        "company": "Enterprise Cloud Services",
        "product": "Subscription Billing",
        "sub_product": "Monthly Premium",
        "issue": "Duplicate Invoicing",
        "sub_issue": "Double Debit",
        "state": "CA",
        "timely_response": "Yes",
        "complaint_id": "1001",
        "date_received": "2026-10-15"
    },
    {
        "ticket_id": "TKT-1002",
        "customer_id": "CUST-392",
        "channel": "web_portal",
        "category": "Service Downtime",
        "severity": "Critical",
        "sentiment_score": "-0.92",
        "description": "API endpoint 500 server errors during peak deployment hours.",
        "status": "investigating",
        "account_tier": "Enterprise",
        "company": "Enterprise Gateway Inc.",
        "product": "Cloud API Gateway",
        "sub_product": "REST Endpoints",
        "issue": "Service Outage",
        "sub_issue": "500 Internal Server Error",
        "state": "NY",
        "timely_response": "Yes",
        "complaint_id": "1002",
        "date_received": "2026-10-16"
    },
    {
        "ticket_id": "TKT-1003",
        "customer_id": "CUST-119",
        "channel": "chat",
        "category": "Feature Request",
        "severity": "Low",
        "sentiment_score": "0.15",
        "description": "Requesting dark mode support and CSV bulk export for analytics dashboard.",
        "status": "backlog",
        "account_tier": "Standard",
        "company": "Standard Analytics Corp.",
        "product": "Reporting Dashboard",
        "sub_product": "UI Themes",
        "issue": "Enhancement",
        "sub_issue": "Export Capabilities",
        "state": "TX",
        "timely_response": "Yes",
        "complaint_id": "1003",
        "date_received": "2026-10-17"
    },
    {
        "ticket_id": "TKT-1004",
        "customer_id": "CUST-582",
        "channel": "email",
        "category": "Account Lockout",
        "severity": "Medium",
        "sentiment_score": "-0.45",
        "description": "MFA SMS verification codes delayed by over 15 minutes.",
        "status": "resolved",
        "account_tier": "Professional",
        "company": "Identity Shield Corp.",
        "product": "Authentication & SSO",
        "sub_product": "Two-Factor Auth",
        "issue": "SMS Delivery Latency",
        "sub_issue": "Carrier Gateway Delay",
        "state": "WA",
        "timely_response": "Yes",
        "complaint_id": "1004",
        "date_received": "2026-10-18"
    },
    {
        "ticket_id": "TKT-1005",
        "customer_id": "CUST-731",
        "channel": "phone",
        "category": "Billing Dispute",
        "severity": "High",
        "sentiment_score": "-0.78",
        "description": "Disputed cancellation penalty fee after terminating trial within 30-day window.",
        "status": "escalated",
        "account_tier": "Standard",
        "company": "Consumer Subscriptions LLC",
        "product": "Consumer Accounts",
        "sub_product": "Trial Subscriptions",
        "issue": "Cancellation Fees",
        "sub_issue": "Disputed Assessment",
        "state": "IL",
        "timely_response": "Yes",
        "complaint_id": "1005",
        "date_received": "2026-10-19"
    },
    {
        "ticket_id": "TKT-1006",
        "customer_id": "CUST-412",
        "channel": "web_portal",
        "category": "Data Privacy",
        "severity": "Critical",
        "sentiment_score": "-0.95",
        "description": "User reports audit log export contained coworker email addresses unexpectedly.",
        "status": "under_review",
        "account_tier": "Enterprise",
        "company": "Global Audit Systems",
        "product": "Compliance Logs",
        "sub_product": "Audit Exporter",
        "issue": "Privacy Exposure",
        "sub_issue": "Unredacted PII",
        "state": "VA",
        "timely_response": "Yes",
        "complaint_id": "1006",
        "date_received": "2026-10-20"
    },
    {
        "ticket_id": "TKT-1007",
        "customer_id": "CUST-904",
        "channel": "chat",
        "category": "Performance Latency",
        "severity": "Medium",
        "sentiment_score": "-0.35",
        "description": "Dashboard reporting page takes 12 seconds to load queries exceeding 100 rows.",
        "status": "in_progress",
        "account_tier": "Professional",
        "company": "FastMetric Systems",
        "product": "Telemetry Analytics",
        "sub_product": "Query Engine",
        "issue": "Slow Query Response",
        "sub_issue": "Pagination Overhead",
        "state": "CO",
        "timely_response": "Yes",
        "complaint_id": "1007",
        "date_received": "2026-10-21"
    },
    {
        "ticket_id": "TKT-1008",
        "customer_id": "CUST-223",
        "channel": "email",
        "category": "Contract Renewal",
        "severity": "Low",
        "sentiment_score": "0.4",
        "description": "Inquiring regarding multi-year enterprise volume discount schedule.",
        "status": "pending_sales",
        "account_tier": "Enterprise",
        "company": "Apex Cloud Ventures",
        "product": "Enterprise Licensing",
        "sub_product": "Volume Agreements",
        "issue": "Pricing Schedule",
        "sub_issue": "Discount Tiers",
        "state": "MA",
        "timely_response": "Yes",
        "complaint_id": "1008",
        "date_received": "2026-10-22"
    },
    {
        "ticket_id": "TKT-1009",
        "customer_id": "CUST-611",
        "channel": "web_portal",
        "category": "Authentication & SSO",
        "severity": "Critical",
        "sentiment_score": "-0.88",
        "description": "SAML 2.0 Single Sign-On handshake failing with Okta identity provider.",
        "status": "open",
        "account_tier": "Enterprise",
        "company": "Enterprise Federated Identity",
        "product": "Identity Federation",
        "sub_product": "SAML 2.0 Connector",
        "issue": "Authentication Failure",
        "sub_issue": "Handshake Timeout",
        "state": "FL",
        "timely_response": "Yes",
        "complaint_id": "1009",
        "date_received": "2026-10-23"
    },
    {
        "ticket_id": "TKT-1010",
        "customer_id": "CUST-304",
        "channel": "email",
        "category": "Billing Dispute",
        "severity": "Medium",
        "sentiment_score": "-0.52",
        "description": "VAT tax calculation applied incorrectly on European quarterly invoice.",
        "status": "in_progress",
        "account_tier": "Professional",
        "company": "EuroTax Compliance BV",
        "product": "Cross-Border Billing",
        "sub_product": "VAT Calculator",
        "issue": "Tax Calculation Discrepancy",
        "sub_issue": "Reverse Charge Omission",
        "state": "NY",
        "timely_response": "Yes",
        "complaint_id": "1010",
        "date_received": "2026-10-24"
    },
    {
        "ticket_id": "TKT-1011",
        "customer_id": "CUST-789",
        "channel": "chat",
        "category": "Security Incident",
        "severity": "Critical",
        "sentiment_score": "-0.96",
        "description": "Suspected compromised API key making unauthorized read requests to customer database.",
        "status": "escalated",
        "account_tier": "Enterprise",
        "company": "DataSec Solutions",
        "product": "API Security",
        "sub_product": "Token Gateway",
        "issue": "Compromised Credentials",
        "sub_issue": "Unauthorized Database Reads",
        "state": "CA",
        "timely_response": "Yes",
        "complaint_id": "1011",
        "date_received": "2026-10-25"
    },
    {
        "ticket_id": "TKT-1012",
        "customer_id": "CUST-152",
        "channel": "web_portal",
        "category": "Service Downtime",
        "severity": "High",
        "sentiment_score": "-0.81",
        "description": "Webhook notification deliveries failing with 504 gateway timeouts.",
        "status": "investigating",
        "account_tier": "Professional",
        "company": "HookStream Systems",
        "product": "Webhook Notification Engine",
        "sub_product": "Delivery Worker",
        "issue": "Timeout Latency",
        "sub_issue": "504 Gateway Timeout",
        "state": "GA",
        "timely_response": "Yes",
        "complaint_id": "1012",
        "date_received": "2026-10-26"
    },
    {
        "ticket_id": "TKT-1013",
        "customer_id": "CUST-443",
        "channel": "phone",
        "category": "Account Lockout",
        "severity": "High",
        "sentiment_score": "-0.74",
        "description": "Password reset links expiring within 60 seconds preventing admin re-entry.",
        "status": "open",
        "account_tier": "Enterprise",
        "company": "AdminPortal Direct",
        "product": "User Management",
        "sub_product": "Credential Recovery",
        "issue": "Premature Token Expiration",
        "sub_issue": "Admin Lockout",
        "state": "NC",
        "timely_response": "Yes",
        "complaint_id": "1013",
        "date_received": "2026-10-27"
    },
    {
        "ticket_id": "TKT-1014",
        "customer_id": "CUST-990",
        "channel": "email",
        "category": "Compliance & GDPR",
        "severity": "High",
        "sentiment_score": "-0.68",
        "description": "Formal Right-to-be-Forgotten data deletion request submitted for former employees.",
        "status": "pending_legal",
        "account_tier": "Enterprise",
        "company": "Global HR Holdings",
        "product": "Employee Records Storage",
        "sub_product": "Data Purge Engine",
        "issue": "Right to be Forgotten",
        "sub_issue": "GDPR Article 17 Erasure",
        "state": "DC",
        "timely_response": "Yes",
        "complaint_id": "1014",
        "date_received": "2026-10-28"
    },
    {
        "ticket_id": "TKT-1015",
        "customer_id": "CUST-238",
        "channel": "chat",
        "category": "Feature Request",
        "severity": "Low",
        "sentiment_score": "0.25",
        "description": "Requesting automated webhook retry logic and exponential backoff configuration.",
        "status": "backlog",
        "account_tier": "Standard",
        "company": "DevTools Integration Lab",
        "product": "Event Streaming",
        "sub_product": "Retry Policies",
        "issue": "Backoff Configuration",
        "sub_issue": "Exponential Retry",
        "state": "OR",
        "timely_response": "Yes",
        "complaint_id": "1015",
        "date_received": "2026-10-29"
    },
    {
        "ticket_id": "TKT-1016",
        "customer_id": "CUST-871",
        "channel": "web_portal",
        "category": "Performance Latency",
        "severity": "High",
        "sentiment_score": "-0.79",
        "description": "Bulk CSV export job stalled at 85% for datasets exceeding 50000 records.",
        "status": "investigating",
        "account_tier": "Enterprise",
        "company": "BigData Warehouse Corp",
        "product": "Data Export Services",
        "sub_product": "CSV Streamer",
        "issue": "Job Stalled",
        "sub_issue": "Memory Buffer Starvation",
        "state": "TX",
        "timely_response": "Yes",
        "complaint_id": "1016",
        "date_received": "2026-10-30"
    },
    {
        "ticket_id": "TKT-1017",
        "customer_id": "CUST-519",
        "channel": "email",
        "category": "Billing Overcharge",
        "severity": "High",
        "sentiment_score": "-0.83",
        "description": "Charged for 50 inactive seats that were de-provisioned last billing cycle.",
        "status": "escalated",
        "account_tier": "Enterprise",
        "company": "Enterprise Seat Manager",
        "product": "User Seat Invoicing",
        "sub_product": "License Reconciliation",
        "issue": "De-provisioned Seat Billing",
        "sub_issue": "Inaccurate License Tally",
        "state": "NJ",
        "timely_response": "Yes",
        "complaint_id": "1017",
        "date_received": "2026-10-31"
    },
    {
        "ticket_id": "TKT-1018",
        "customer_id": "CUST-340",
        "channel": "phone",
        "category": "Service Downtime",
        "severity": "Critical",
        "sentiment_score": "-0.91",
        "description": "Redis cache cluster failover caused 20 minutes of complete portal unresponsiveness.",
        "status": "resolved",
        "account_tier": "Enterprise",
        "company": "Core Portal Infrastructure",
        "product": "Caching Tier",
        "sub_product": "Redis Sentinel",
        "issue": "Failover Outage",
        "sub_issue": "Split-Brain Unresponsiveness",
        "state": "CA",
        "timely_response": "Yes",
        "complaint_id": "1018",
        "date_received": "2026-11-01"
    },
    {
        "ticket_id": "TKT-1019",
        "customer_id": "CUST-667",
        "channel": "web_portal",
        "category": "Data Privacy",
        "severity": "Critical",
        "sentiment_score": "-0.94",
        "description": "Customer PII visible in shared staging test environment logs.",
        "status": "under_review",
        "account_tier": "Enterprise",
        "company": "SecureApp Staging Corp",
        "product": "Non-Production Environments",
        "sub_product": "Staging Log Forwarder",
        "issue": "Unmasked PII in Staging",
        "sub_issue": "Log Sanitizer Bypass",
        "state": "OH",
        "timely_response": "Yes",
        "complaint_id": "1019",
        "date_received": "2026-11-02"
    },
    {
        "ticket_id": "TKT-1020",
        "customer_id": "CUST-128",
        "channel": "chat",
        "category": "Feature Request",
        "severity": "Low",
        "sentiment_score": "0.35",
        "description": "Inquiring about multi-region data residency support in EU Frankfurt cluster.",
        "status": "backlog",
        "account_tier": "Professional",
        "company": "EU Cloud Solutions",
        "product": "Data Residency Management",
        "sub_product": "Frankfurt Region",
        "issue": "Regional Geo-Fencing",
        "sub_issue": "Sovereign Cloud Support",
        "state": "DE",
        "timely_response": "Yes",
        "complaint_id": "1020",
        "date_received": "2026-11-03"
    },
    {
        "ticket_id": "TKT-1021",
        "customer_id": "CUST-705",
        "channel": "email",
        "category": "Authentication & SSO",
        "severity": "Medium",
        "sentiment_score": "-0.42",
        "description": "OAuth2 token refresh returning 401 unauthorized on mobile client.",
        "status": "resolved",
        "account_tier": "Professional",
        "company": "Mobile Identity Connect",
        "product": "Mobile Gateway",
        "sub_product": "OAuth2 Refresh Token",
        "issue": "Token Refresh Failure",
        "sub_issue": "401 Unauthorized",
        "state": "PA",
        "timely_response": "Yes",
        "complaint_id": "1021",
        "date_received": "2026-11-04"
    },
    {
        "ticket_id": "TKT-1022",
        "customer_id": "CUST-833",
        "channel": "web_portal",
        "category": "Performance Latency",
        "severity": "Medium",
        "sentiment_score": "-0.48",
        "description": "GraphQL query response time degraded from 250ms to 2.4 seconds.",
        "status": "in_progress",
        "account_tier": "Standard",
        "company": "AppLayer Query Services",
        "product": "GraphQL API",
        "sub_product": "Query Resolvers",
        "issue": "Resolver Degradation",
        "sub_issue": "N+1 Query Bottleneck",
        "state": "MI",
        "timely_response": "Yes",
        "complaint_id": "1022",
        "date_received": "2026-11-05"
    },
    {
        "ticket_id": "TKT-1023",
        "customer_id": "CUST-491",
        "channel": "phone",
        "category": "Billing Dispute",
        "severity": "High",
        "sentiment_score": "-0.71",
        "description": "Refund for annual plan downgrade not processed after 14 business days.",
        "status": "escalated",
        "account_tier": "Professional",
        "company": "Annual Plan Subscriptions",
        "product": "Tier Downgrade Engine",
        "sub_product": "Credit Memo Processing",
        "issue": "Refund Processing Delays",
        "sub_issue": "SLA Breach on Credit Memo",
        "state": "AZ",
        "timely_response": "Yes",
        "complaint_id": "1023",
        "date_received": "2026-11-06"
    },
    {
        "ticket_id": "TKT-1024",
        "customer_id": "CUST-955",
        "channel": "email",
        "category": "Compliance & SOC2",
        "severity": "Low",
        "sentiment_score": "0.1",
        "description": "Requesting current SOC-2 Type II audit certification report for annual vendor review.",
        "status": "pending_sales",
        "account_tier": "Enterprise",
        "company": "Vendor Assurance Network",
        "product": "Compliance Documentation",
        "sub_product": "SOC-2 Type II Report",
        "issue": "Vendor Audit Assurance",
        "sub_issue": "Annual Assessment Attestation",
        "state": "MN",
        "timely_response": "Yes",
        "complaint_id": "1024",
        "date_received": "2026-11-07"
    },
    {
        "ticket_id": "TKT-1025",
        "customer_id": "CUST-208",
        "channel": "chat",
        "category": "Account Lockout",
        "severity": "Medium",
        "sentiment_score": "-0.38",
        "description": "Role-based permissions revoked unexpectedly after platform maintenance update.",
        "status": "resolved",
        "account_tier": "Standard",
        "company": "RBAC Platform Services",
        "product": "Access Control Engine",
        "sub_product": "Role Assignment",
        "issue": "Maintenance Regression",
        "sub_issue": "Permission Cache Flush",
        "state": "FL",
        "timely_response": "Yes",
        "complaint_id": "1025",
        "date_received": "2026-11-08"
    }
]


def get_cached_zip_path() -> Path:
    """Returns local path where CFPB complaints zip is cached."""
    gen_dir = Path(settings.GENERATED_DIR).resolve()
    gen_dir.mkdir(parents=True, exist_ok=True)
    return gen_dir / "cfpb_complaints.csv.zip"


def download_cfpb_zip(url: Optional[str] = None, target_path: Optional[Path] = None) -> Path:
    """
    Downloads the CFPB complaints zip file from the remote URL specified in .env.
    Uses streaming with chunking to support large files without memory exhaustion.
    """
    download_url = url or settings.CFPB_COMPLAINTS_URL
    out_path = target_path or get_cached_zip_path()
    
    if out_path.exists() and out_path.stat().st_size > 1024 * 1024:
        logger.info(f"Using existing cached CFPB zip archive at {out_path} ({out_path.stat().st_size / (1024*1024):.1f} MB)")
        return out_path
        
    logger.info(f"Downloading remote CFPB complaints database from {download_url}...")
    temp_path = out_path.with_suffix(".tmp")
    
    with httpx.stream("GET", download_url, follow_redirects=True, timeout=120.0) as resp:
        resp.raise_for_status()
        with open(temp_path, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=1024 * 1024):
                f.write(chunk)
                
    temp_path.replace(out_path)
    logger.info(f"Successfully downloaded CFPB complaints database archive: {out_path.stat().st_size / (1024*1024):.1f} MB")
    return out_path


def parse_and_normalize_cfpb_records(zip_path: Path, max_records: int = 10000) -> List[Dict[str, Any]]:
    """
    Streams records from the compressed CFPB complaints CSV archive and normalizes them into
    the multi-agent common information schema, mapping financial complaints to operational tickets.
    """
    normalized_records = []
    
    with zipfile.ZipFile(zip_path, "r") as z:
        csv_candidates = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if not csv_candidates:
            raise FileNotFoundError("No CSV file found inside the downloaded CFPB zip archive.")
            
        csv_filename = csv_candidates[0]
        with z.open(csv_filename) as f:
            text_stream = io.TextIOWrapper(f, encoding="utf-8", errors="replace")
            reader = csv.DictReader(text_stream)
            
            for i, r in enumerate(reader):
                cid = r.get("Complaint ID", str(i + 100000))
                comp = r.get("Company", "Financial Institution")
                prod = r.get("Product", "Financial Services")
                sub_prod = r.get("Sub-product", "")
                issue = r.get("Issue", "Customer Grievance")
                sub_issue = r.get("Sub-issue", "")
                channel = r.get("Submitted via", "Web")
                resp = r.get("Company response to consumer", "Closed with explanation")
                timely = r.get("Timely response?", "Yes")
                state = r.get("State", "")
                tags = r.get("Tags", "")
                date_rx = r.get("Date received", "")
                
                # Dynamic account tier categorization
                tier = tags if tags else (
                    "Enterprise" if any(b in comp.lower() for b in [
                        "jpmorgan", "wells fargo", "bank of america", "citibank", 
                        "capital one", "experian", "equifax", "transunion", "fidelity",
                        "goldman", "morgan stanley", "us bank", "pnc"
                    ]) else "Standard"
                )
                
                # Dynamic severity assessment
                issue_lower = f"{issue} {sub_issue}".lower()
                if timely.lower() == "no" or any(k in issue_lower for k in [
                    "fraud", "identity theft", "unauthorized", "improper use", 
                    "leak", "privacy", "compromised", "breach"
                ]):
                    sev = "Critical"
                    sent = -0.92
                elif "monetary relief" in resp.lower() or "dispute" in issue_lower or "overcharge" in issue_lower:
                    sev = "High"
                    sent = -0.78
                elif "explanation" in resp.lower():
                    sev = "Medium"
                    sent = -0.45
                else:
                    sev = "Low"
                    sent = 0.05
                    
                desc = f"{issue}: {sub_issue}" if sub_issue else issue
                
                normalized_records.append({
                    "ticket_id": f"CFPB-{cid}",
                    "customer_id": comp,
                    "channel": channel,
                    "category": prod,
                    "severity": sev,
                    "sentiment_score": str(sent),
                    "description": desc,
                    "status": resp,
                    "account_tier": tier,
                    "company": comp,
                    "product": prod,
                    "sub_product": sub_prod,
                    "issue": issue,
                    "sub_issue": sub_issue,
                    "state": state,
                    "timely_response": timely,
                    "complaint_id": cid,
                    "date_received": date_rx
                })
                
                if len(normalized_records) >= max_records:
                    break
                    
    return normalized_records


def build_enhanced_datasets(max_records: Optional[int] = None) -> Dict[str, Any]:
    """
    Main ingestion engine:
    1. Downloads CFPB complaints archive using CFPB_COMPLAINTS_URL from .env.
    2. Parses and normalizes real consumer complaint records.
    3. Merges baseline test fixtures to preserve regression suite integrity.
    4. Writes to data/samples/customer_complaints.csv and data/samples/cfpb_complaints.csv.
    """
    record_limit = max_records or settings.MAX_DATASET_RECORDS
    samples_dir = Path(settings.SAMPLES_DIR).resolve()
    samples_dir.mkdir(parents=True, exist_ok=True)
    
    zip_path = get_cached_zip_path()
    if not zip_path.exists():
        download_cfpb_zip(settings.CFPB_COMPLAINTS_URL, zip_path)
        
    cfpb_records = parse_and_normalize_cfpb_records(zip_path, max_records=record_limit)
    
    # Combined dataset: Baseline enterprise tickets + rich CFPB complaints
    all_complaints = BASELINE_ENTERPRISE_TICKETS + cfpb_records
    
    fieldnames = [
        "ticket_id", "customer_id", "channel", "category", "severity",
        "sentiment_score", "description", "status", "account_tier",
        "company", "product", "sub_product", "issue", "sub_issue",
        "state", "timely_response", "complaint_id", "date_received"
    ]
    
    # 1. Update customer_complaints.csv
    customer_csv = samples_dir / "customer_complaints.csv"
    with open(customer_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_complaints)
        
    # 2. Write dedicated cfpb_complaints.csv
    cfpb_csv = samples_dir / "cfpb_complaints.csv"
    with open(cfpb_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(cfpb_records)
        
    stats = {
        "source_url": settings.CFPB_COMPLAINTS_URL,
        "kaggle_ref": settings.KAGGLE_CFPB_DATASET,
        "total_records": len(all_complaints),
        "cfpb_record_count": len(cfpb_records),
        "baseline_fixtures": len(BASELINE_ENTERPRISE_TICKETS),
        "target_files": [str(customer_csv), str(cfpb_csv)]
    }
    logger.info(f"Enhanced datasets deployed successfully: {stats}")
    return stats


def ensure_cfpb_datasets() -> None:
    """
    Ensures that rich datasets derived from .env URLs are populated in data/samples/.
    If the existing customer_complaints.csv only has minimal rows (< 100), builds the full dataset.
    """
    samples_dir = Path(settings.SAMPLES_DIR).resolve()
    cust_file = samples_dir / "customer_complaints.csv"
    cfpb_file = samples_dir / "cfpb_complaints.csv"
    
    needs_build = False
    if not cust_file.exists() or not cfpb_file.exists():
        needs_build = True
    else:
        try:
            with open(cust_file, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                rows = list(reader)
                if len(rows) < 100:
                    needs_build = True
        except Exception:
            needs_build = True
            
    if needs_build:
        try:
            build_enhanced_datasets()
        except Exception as e:
            logger.warning(f"Could not automatically build datasets from CFPB URL: {e}")
