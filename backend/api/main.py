"""
FastAPI Server Entry Point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import router
from backend.storage.database import init_db
from backend.tools.dataset_manager import ensure_cfpb_datasets
from backend.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(settings.DATABASE_PATH)
    ensure_cfpb_datasets()
    yield

app = FastAPI(
    title="Multi-Agent Transparency & Observability Gateway API",
    description="Capturing Inter-Agent Communication, Execution Context, and Authority Delegation",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/")
def root():
    return {
        "message": "Multi-Agent Transparency & Observability API is running",
        "docs_url": "/docs",
        "api_status": "/api/status"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)

