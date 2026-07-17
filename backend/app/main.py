import asyncio
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from dotenv import load_dotenv
from fastapi.responses import FileResponse
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.chat import router as chat_router
from app.api.analytics import router as analytics_router
from app.api.admin import router as admin_router
from app.api.conversations import router as conversations_router
from app.api.documents import router as documents_router
from app.api.inventories import router as inventories_router
from app.api.products import router as products_router
from app.api.users import router as users_router
from app.db.session import engine
from app.deps import get_db
from app.reports.links import with_report_urls
from app.reports.storage import load_report, resolve_asset_path
from app.schemas.report import GeneratedReport
from app.tools.db import get_db_info
from app.tools.mcp_tools import close_mcp_server, start_mcp_server
from app.tools.read_write import CHART_OUTPUT_DIR
from app.tools.voice import VoiceTranscriptionUnavailable, transcribe_audio_bytes

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)


app = FastAPI(title="ProductAI Backend")

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products_router)
app.include_router(users_router)
app.include_router(inventories_router)
app.include_router(analytics_router)
app.include_router(conversations_router)
app.include_router(documents_router)
app.include_router(admin_router)
app.include_router(chat_router)

SANDBOX_CHART_OUTPUT_DIR = (Path(__file__).resolve().parents[1] / ".sandbox_runtime" / "charts").resolve()


@app.on_event("startup")
def startup_mcp_server():
    start_mcp_server()


@app.on_event("shutdown")
def shutdown_mcp_server():
    close_mcp_server()


@app.get("/health")
async def read_root():
    return {"message": "Welcome to the ProductAI Backend!"}


class ComputeRequest(BaseModel):
    x: int
    y: int


@app.post("/compute")
def compute(req: ComputeRequest):
    # call the function end-to-end
    return {"result": req.x + req.y}


@app.get("/db-info")
def db_info(
    db: Session = Depends(get_db),
    include_row_counts: bool = Query(default=True),
):
    return get_db_info(db=db, engine=engine, include_row_counts=include_row_counts).model_dump()


@app.post("/voice/transcribe")
async def transcribe_voice(file: UploadFile = File(...)):
    content_type = file.content_type or ""
    if not content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Upload an audio file.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")

    suffix = Path(file.filename or "recording.webm").suffix or ".webm"
    try:
        return transcribe_audio_bytes(content, suffix=suffix).model_dump()
    except VoiceTranscriptionUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc


@app.get("/reports/{report_id}", response_model=GeneratedReport)
def get_report(report_id: str):
    try:
        report = load_report(report_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Report not found.") from exc
    return with_report_urls(report)


@app.get("/reports/{report_id}/assets/{filename}")
def view_report_asset(report_id: str, filename: str):
    try:
        asset_path = resolve_asset_path(report_id, filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Report asset not found.") from exc

    if not asset_path.exists():
        raise HTTPException(status_code=404, detail="Report asset not found.")

    media_type = "text/plain"
    if asset_path.suffix == ".md":
        media_type = "text/markdown; charset=utf-8"
    elif asset_path.suffix == ".html":
        media_type = "text/html; charset=utf-8"
    elif asset_path.suffix == ".json":
        media_type = "application/json"
    elif asset_path.suffix == ".pdf":
        media_type = "application/pdf"
    elif asset_path.suffix == ".png":
        media_type = "image/png"

    return FileResponse(asset_path, media_type=media_type)


@app.get("/reports/{report_id}/download/{filename}")
def download_report_asset(report_id: str, filename: str):
    try:
        asset_path = resolve_asset_path(report_id, filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Report asset not found.") from exc

    if not asset_path.exists():
        raise HTTPException(status_code=404, detail="Report asset not found.")

    return FileResponse(asset_path, filename=asset_path.name)


@app.get("/charts/view/{filename}")
def view_chart(filename: str):
    asset_path = resolve_chart_path(filename)
    if not asset_path.exists():
        raise HTTPException(status_code=404, detail="Chart not found.")

    return FileResponse(asset_path, media_type="image/png")


@app.get("/charts/download/{filename}")
def download_chart(filename: str):
    asset_path = resolve_chart_path(filename)
    if not asset_path.exists():
        raise HTTPException(status_code=404, detail="Chart not found.")

    return FileResponse(asset_path, media_type="image/png", filename=asset_path.name)


def resolve_chart_path(filename: str) -> Path:
    safe_name = Path(filename).name
    for charts_dir in (CHART_OUTPUT_DIR, SANDBOX_CHART_OUTPUT_DIR):
        asset_path = (charts_dir / safe_name).resolve()
        try:
            asset_path.relative_to(charts_dir)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid chart path.") from exc
        if asset_path.exists():
            return asset_path
    return (CHART_OUTPUT_DIR / safe_name).resolve()
