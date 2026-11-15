"""
Configuration settings for the Multi-Agent Transparency & Observability Platform.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

class Settings(BaseModel):
    # Storage settings
    DATABASE_PATH: str = Field(
        default=os.getenv("DATABASE_PATH", str(PROJECT_ROOT / "data" / "generated" / "transparency_events.db"))
    )
    
    # Capture settings: 1 = Metadata Only, 2 = Metadata + Summary (default), 3 = Full Observable Message Content
    DEFAULT_CAPTURE_LEVEL: int = Field(
        default=int(os.getenv("DEFAULT_CAPTURE_LEVEL", "2"))
    )
    
    # Redaction configuration for privacy Level 3
    REDACT_PII: bool = Field(default=True)
    
    # Hugging Face Router settings
    HF_ROUTER_BASE_URL: str = Field(
        default=os.getenv("HF_ROUTER_BASE_URL", "https://router.huggingface.co/v1")
    )
    HF_API_KEY: str = Field(
        default=os.getenv("HF_TOKEN") or os.getenv("HF_API_KEY") or ""
    )
    HF_COORDINATOR_MODEL: str = Field(
        default=os.getenv("HF_COORDINATOR_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
    )
    HF_EXECUTOR_MODEL: str = Field(
        default=os.getenv("HF_EXECUTOR_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    )

    # Ollama settings (fallback / legacy)
    OLLAMA_BASE_URL: str = Field(
        default=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    )
    OLLAMA_MODEL: str = Field(
        default=os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    )
    
    # MongoDB Storage for Chat History & Sessions
    MONGODB_URI: str = Field(
        default=os.getenv("MONGODB_URI", "")
    )
    MONGODB_DB_NAME: str = Field(
        default=os.getenv("MONGODB_DB_NAME", "transparency_platform")
    )

    # Server settings
    API_HOST: str = Field(default=os.getenv("API_HOST", "127.0.0.1"))
    API_PORT: int = Field(default=int(os.getenv("API_PORT", "8000")))
    DASHBOARD_PORT: int = Field(default=int(os.getenv("DASHBOARD_PORT", "8501")))
    
    # Dataset URLs (CFPB & Kaggle from .env)
    CFPB_COMPLAINTS_URL: str = Field(
        default=os.getenv("CFPB_COMPLAINTS_URL", "https://files.consumerfinance.gov/ccdb/complaints.csv.zip")
    )
    KAGGLE_CFPB_DATASET: str = Field(
        default=os.getenv("KAGGLE_CFPB_DATASET", "selener/consumer-complaint-database")
    )
    MAX_DATASET_RECORDS: int = Field(
        default=int(os.getenv("MAX_DATASET_RECORDS", "10000"))
    )
    
    # Paths
    SAMPLES_DIR: str = Field(default=str(PROJECT_ROOT / "data" / "samples"))
    GENERATED_DIR: str = Field(default=str(PROJECT_ROOT / "data" / "generated"))

settings = Settings()

# Ensure generated directory exists
os.makedirs(Path(settings.DATABASE_PATH).parent, exist_ok=True)

