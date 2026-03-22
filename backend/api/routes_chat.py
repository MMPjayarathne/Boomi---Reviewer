import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.db.repo_sessions import get_session
from backend.db.repo_findings import get_findings
from backend.db.repo_chat import save_message, get_history
from backend.db.repo_embeddings import save_embedding
from backend.parser.boomi_parser import parse_xml
from backend.parser.models import BoomiProcess, Shape, Connection
from backend.ai.ollama_client import chat_stream
from backend.ai.prompt_builder import build_chat_messages
from backend.ai.rag_retriever import retrieve_similar_context
from backend.ai.embeddings import embed
from backend.rules.base_rule import Finding
from backend.utils.severity import Severity
from backend.utils.logger import get_logger

router = APIRouter(prefix="/api", tags=["chat"])
logger = get_logger(__name__)


class ChatRequest(BaseModel):
    session_id: str
    message: str


def _findings_from_rows(rows: list[dict]) -> list[Finding]:
    findings = []
    for r in rows:
        try:
            findings.append(Finding(
                rule_id=r["rule_id"],
                rule_name=r["rule_name"],
                severity=Severity(r["severity"]),
                description=r["description"],
                recommendation=r["recommendation"],
                shape_id=r.get("shape_id") or "",
                shape_label=r.get("shape_label") or "",
            ))
        except Exception:
            pass
    return findings


def _make_dummy_process(session: dict) -> BoomiProcess:
    """Reconstruct a minimal process model from session metadata for the AI prompt."""
    return BoomiProcess(
        process_name=session["name"],
        process_id=session["id"],
    )


@router.post("/chat")
async def chat(req: ChatRequest):
    session = await get_session(req.session_id)
    if not session:
        raise HTTPException(404, "Session not found.")

    finding_rows = await get_findings(req.session_id)
    findings = _findings_from_rows(finding_rows)
    process = _make_dummy_process(session)
    history = await get_history(req.session_id)
    rag_context = await retrieve_similar_context(req.message)

    messages = build_chat_messages(
        process=process,
        findings=findings,
        chat_history=history,
        user_question=req.message,
        rag_context=rag_context,
    )

    # Save user message
    user_msg_id = await save_message(req.session_id, "user", req.message)
    user_emb = embed(req.message)
    if user_emb is not None:
        await save_embedding(user_msg_id, user_emb)

    async def generate():
        full_response = []
        async for chunk in chat_stream(messages):
            full_response.append(chunk)
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"

        # Save assistant response
        assistant_text = "".join(full_response)
        asst_msg_id = await save_message(req.session_id, "assistant", assistant_text)
        asst_emb = embed(assistant_text)
        if asst_emb is not None:
            await save_embedding(asst_msg_id, asst_emb)

        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/chat/history/{session_id}")
async def chat_history(session_id: str):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found.")
    return await get_history(session_id)
