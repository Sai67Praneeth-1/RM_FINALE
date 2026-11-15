"""
Configuration settings for the Multi-Agent Transparency & Observability Platform.
"""

import os
from pathlib import Path
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent

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
    
    # Ollama settings
    OLLAMA_BASE_URL: str = Field(
        default=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    )
    OLLAMA_MODEL: str = Field(
        default=os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    )
    
    # Server settings
    API_HOST: str = Field(default=os.getenv("API_HOST", "127.0.0.1"))
    API_PORT: int = Field(default=int(os.getenv("API_PORT", "8000")))
    DASHBOARD_PORT: int = Field(default=int(os.getenv("DASHBOARD_PORT", "8501")))
    
    # Paths
    SAMPLES_DIR: str = Field(default=str(PROJECT_ROOT / "data" / "samples"))
    GENERATED_DIR: str = Field(default=str(PROJECT_ROOT / "data" / "generated"))

settings = Settings()

# Ensure generated directory exists
os.makedirs(Path(settings.DATABASE_PATH).parent, exist_ok=True)

