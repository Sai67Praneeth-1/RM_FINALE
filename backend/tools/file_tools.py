"""
Allowlisted File and Data Ingestion Tools.
Restricted strictly to the sample and data directory to prevent arbitrary file access.
"""

import os
import csv
from pathlib import Path
from typing import Dict, Any, List
from backend.config import settings

def get_allowed_samples_dir() -> Path:
    return Path(settings.SAMPLES_DIR).resolve()

def list_sample_datasets() -> List[Dict[str, Any]]:
    """Lists allowlisted dataset files available in data/samples/."""
    samples_dir = get_allowed_samples_dir()
    if not samples_dir.exists():
        return []
    
    files = []
    for f in samples_dir.glob("*.*"):
        files.append({
            "name": f.name,
            "size_bytes": f.stat().st_size,
            "path": str(f)
        })
    return files

def read_sample_dataset(file_name: str) -> Dict[str, Any]:
    """
    Safely reads an allowlisted dataset file from data/samples/.
    Rejects path traversal attempts.
    """
    samples_dir = get_allowed_samples_dir()
    clean_name = os.path.basename(file_name)
    target_path = (samples_dir / clean_name).resolve()
    
    # Path traversal check
    if not str(target_path).startswith(str(samples_dir)):
        raise PermissionError(f"Access denied: path traversal attempt for {file_name}")
    if not target_path.exists():
        raise FileNotFoundError(f"File not found in samples: {clean_name}")
        
    ext = target_path.suffix.lower()
    if ext == ".csv":
        with open(target_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        return {
            "file_name": clean_name,
            "format": "csv",
            "row_count": len(rows),
            "data": rows
        }
    else:
        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {
            "file_name": clean_name,
            "format": "text",
            "character_count": len(content),
            "data": content
        }

