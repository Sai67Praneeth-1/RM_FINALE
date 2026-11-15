"""
FastAPI Server Entry Point.
Fully deployable application with integrated SPA frontend serving and API routes.
"""

from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

# Frontend static distribution directory for production deployment
dist_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if (dist_dir / "assets").exists():
    app.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")

@app.get("/")
def root(request: Request):
    index_file = dist_dir / "index.html"
    accept = request.headers.get("accept", "")
    if "application/json" in accept or not index_file.exists():
        return {
            "message": "Multi-Agent Transparency & Observability API is running",
            "docs_url": "/docs",
            "api_status": "/api/status"
        }
    return FileResponse(index_file)

@app.get("/{full_path:path}")
async def serve_spa_route(full_path: str):
    """
    Catch-all SPA fallback ensuring each frontend page URL (e.g. /chat, /events, /benchmarks)
    resolves cleanly to index.html for direct access, deep-linking, and browser refreshes.
    """
    if full_path.startswith("api") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
        raise HTTPException(status_code=404, detail="API route not found")
        
    static_file = dist_dir / full_path
    if static_file.is_file():
        return FileResponse(static_file)
        
    index_file = dist_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    raise HTTPException(
        status_code=404,
        detail="Page not found. Compile frontend using 'npm run build' for standalone deployment."
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)


