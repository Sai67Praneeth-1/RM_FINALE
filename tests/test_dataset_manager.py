"""
Unit and Integration tests for Dataset Manager and Remote CFPB / Kaggle integration.
"""

import pytest
from pathlib import Path
from backend.config import settings
from backend.tools.file_tools import list_sample_datasets, read_sample_dataset
from backend.orchestration.dynamic_query_engine import analyze_dynamic_query


def test_dataset_settings_configured():
    """Verify that dataset URLs from .env are loaded into system settings."""
    assert settings.CFPB_COMPLAINTS_URL != ""
    assert "consumerfinance.gov" in settings.CFPB_COMPLAINTS_URL
    assert settings.KAGGLE_CFPB_DATASET == "selener/consumer-complaint-database"


def test_sample_datasets_available():
    """Verify that sample datasets include both customer complaints and dedicated CFPB datasets."""
    datasets = list_sample_datasets()
    names = [d["name"] for d in datasets]
    assert "customer_complaints.csv" in names
    assert "cfpb_complaints.csv" in names
    assert "system_access_logs.csv" in names


def test_dataset_contains_rich_cfpb_records():
    """Verify that dataset rows contain both common information model schema and CFPB fields."""
    ds = read_sample_dataset("customer_complaints.csv")
    assert ds["row_count"] >= 1000
    first_row = ds["data"][0]
    # Standard multi-agent fields
    assert "ticket_id" in first_row
    assert "customer_id" in first_row
    assert "category" in first_row
    assert "severity" in first_row
    assert "sentiment_score" in first_row
    assert "description" in first_row
    assert "status" in first_row
    assert "account_tier" in first_row


def test_dynamic_query_against_cfpb_institutions():
    """Verify that dynamic query engine resolves research goals against CFPB entities."""
    res = analyze_dynamic_query("Analyze consumer complaints against Experian regarding credit inquiries")
    assert res["domain"] == "complaints"
    assert res["matched_count"] > 0
    assert "Experian" in res["executive_summary"] or "Experian" in str(res["key_findings"])


def test_dynamic_query_against_financial_products():
    """Verify that dynamic query engine handles financial product categories."""
    res = analyze_dynamic_query("Audit high severity disputes in credit reporting and debt collection")
    assert res["domain"] == "complaints"
    assert res["matched_count"] > 0
    assert len(res["recommendations"]) > 0
