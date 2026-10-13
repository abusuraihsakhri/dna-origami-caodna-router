"""FastAPI interface for the illustrative rule-based audit service."""
import hmac
import os
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from .base import AuditLogger, SecurityException
from .models import SystemTaskPayload
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="DNA Origami CAODNA Router — Rule-Based Audit",
    description="Illustrative threshold/descriptor evaluations; no DNA strand routing or design validation.",
    version="2.0.0",
)

class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=10000)


@app.get("/")
def index():
    page = Path(__file__).resolve().parent.parent / "web" / "index.html"
    if not page.is_file():
        raise HTTPException(status_code=404, detail="Web UI unavailable in this installation")
    return FileResponse(page)


@app.get("/health")
def health():
    key = os.environ.get("AUDIT_SECRET_KEY", "")
    if len(key) < 32:
        return JSONResponse(
            status_code=503,
            content={"status": "DEGRADED", "reason": "AUDIT_SECRET_KEY must contain at least 32 characters"},
        )
    return {"status": "HEALTHY", "service": "dna-origami-caodna-router", "version": "2.0.0"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()) if len(os.environ.get("AUDIT_SECRET_KEY", "")) >= 32 else 0,
        "format": "json",
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    if len(os.environ.get("AUDIT_SECRET_KEY", "")) < 32:
        raise HTTPException(status_code=503, detail="Audit signing key not configured")
    try:
        return supervisor.process_task(payload).to_dict()
    except SecurityException as exc:
        raise HTTPException(status_code=422, detail="Input contains a blocked identifier pattern") from exc


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        return {"response": supervisor.query_supervisory_chat(req.query)}
    except SecurityException as exc:
        raise HTTPException(status_code=422, detail="Input contains a blocked identifier pattern") from exc


def require_audit_log_token(authorization: Optional[str] = Header(default=None)):
    expected = os.environ.get("AUDIT_LOG_READ_TOKEN", "")
    if len(expected) < 32 or not hmac.compare_digest(
        authorization or "", "Bearer " + expected
    ):
        raise HTTPException(status_code=403, detail="Audit log access denied")


@app.get("/api/audit/logs", dependencies=[Depends(require_audit_log_token)])
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
