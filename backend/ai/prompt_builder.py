"""
Builds structured prompts for the Ollama LLM.
"""

from backend.parser.models import BoomiProcess
from backend.rules.base_rule import Finding

SYSTEM_PROMPT = """You are a senior Boomi integration developer and architect with 10+ years of experience.
You review Boomi integration processes and provide precise, actionable technical feedback.

When analyzing issues:
- Explain the ROOT CAUSE, not just the symptom
- Quantify the RISK (data loss, performance impact, security breach, etc.)
- Give CONCRETE recommendations with Boomi-specific implementation steps
- Use technical Boomi terminology (Atom, Shape, Connector, Process Property, etc.)
- Be direct and professional — you are speaking to a developer, not a manager

Format your responses with clear sections when appropriate.
Do not repeat yourself. Do not add unnecessary caveats."""


def build_analysis_prompt(process: BoomiProcess, findings: list[Finding]) -> str:
    """Build the initial system context message for a new chat session."""
    shape_summary = "\n".join(
        f"  - [{s.type}] {s.label or s.id}" for s in process.shapes[:30]
    )
    if len(process.shapes) > 30:
        shape_summary += f"\n  ... and {len(process.shapes) - 30} more shapes"

    findings_by_severity: dict[str, list[Finding]] = {}
    for f in findings:
        findings_by_severity.setdefault(f.severity.value, []).append(f)

    findings_text = ""
    for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
        flist = findings_by_severity.get(severity, [])
        if flist:
            findings_text += f"\n### {severity} ({len(flist)} issues)\n"
            for f in flist:
                shape_ref = f" (shape: '{f.shape_label or f.shape_id}')" if f.shape_id else ""
                findings_text += f"- [{f.rule_id}]{shape_ref}: {f.description}\n"

    return f"""## Boomi Process Under Review: {process.process_name}

### Process Structure
- Total shapes: {len(process.shapes)}
- Total connections: {len(process.connections)}
- Start shape: {process.start_shape_id or 'not detected'}

### Shapes
{shape_summary}

### Detected Issues
{findings_text if findings_text else "No issues detected by the rule engine."}

The user will now ask questions about this process. Use the context above to give precise answers."""


def build_chat_messages(
    process: BoomiProcess,
    findings: list[Finding],
    chat_history: list[dict],
    user_question: str,
    rag_context: list[dict],
) -> list[dict]:
    """Assemble the full messages list for Ollama."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": build_analysis_prompt(process, findings)},
    ]

    # Inject RAG context if available
    if rag_context:
        rag_text = "### Relevant past discussions:\n"
        for ctx in rag_context:
            role_label = "Developer" if ctx["role"] == "user" else "You (past)"
            rag_text += f"**{role_label}:** {ctx['content'][:300]}\n\n"
        messages.append({
            "role": "system",
            "content": rag_text,
        })

    # Include recent chat history (last 10 messages)
    for msg in chat_history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # The current question
    messages.append({"role": "user", "content": user_question})
    return messages
