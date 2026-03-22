import hashlib
import json
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from backend.parser.boomi_parser import parse_xml
from backend.rules.registry import run_all_rules
from backend.db.repo_sessions import create_session, get_session_by_hash, get_session
from backend.db.repo_findings import save_findings, get_findings
from backend.config import settings
from backend.utils.logger import get_logger

router = APIRouter(prefix="/api", tags=["analysis"])
logger = get_logger(__name__)


def _xml_cache_hash(xml_bytes: bytes) -> str:
    """Hash XML + analysis version so rule/parser updates invalidate cached analyses."""
    h = hashlib.sha256()
    h.update(xml_bytes)
    h.update(b"\0")
    h.update(str(settings.analysis_cache_version).encode())
    return h.hexdigest()


def _summarize(findings) -> dict:
    summary: dict[str, int] = {}
    for f in findings:
        summary[f.severity.value] = summary.get(f.severity.value, 0) + 1
    return summary


@router.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    xml_bytes = await file.read()
    if not xml_bytes:
        raise HTTPException(400, "Empty file uploaded.")

    xml_hash = _xml_cache_hash(xml_bytes)

    # Cache: if same XML + analysis version was seen before, return cached result
    cached = await get_session_by_hash(xml_hash)
    if cached:
        findings = await get_findings(cached["id"])
        logger.info(
            "Analyze cache hit session=%s findings=%s",
            cached["id"],
            len(findings),
        )
        return {
            "session_id": cached["id"],
            "process_name": cached["name"],
            "cached": True,
            "summary": json.loads(cached["summary"] or "{}"),
            "findings": findings,
        }

    # Parse
    try:
        process = parse_xml(xml_bytes)
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    # Run rules
    findings = await run_all_rules(process)
    summary = _summarize(findings)
    logger.info(
        "Analyze fresh: process=%r shapes=%s connections=%s findings=%s",
        process.process_name,
        len(process.shapes),
        len(process.connections),
        len(findings),
    )

    # Persist
    session_id = await create_session(
        name=process.process_name,
        filename=file.filename or "process.xml",
        xml_hash=xml_hash,
        summary=summary,
    )
    await save_findings(session_id, findings)

    return {
        "session_id": session_id,
        "process_name": process.process_name,
        "cached": False,
        "summary": summary,
        "findings": [
            {
                "rule_id": f.rule_id,
                "rule_name": f.rule_name,
                "severity": f.severity.value,
                "shape_id": f.shape_id,
                "shape_label": f.shape_label,
                "description": f.description,
                "recommendation": f.recommendation,
            }
            for f in findings
        ],
    }


@router.get("/sessions/{session_id}")
async def get_session_detail(session_id: str):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found.")
    findings = await get_findings(session_id)
    return {**session, "findings": findings}
