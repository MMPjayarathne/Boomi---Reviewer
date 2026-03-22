import uuid
from backend.db.database import get_db
from backend.rules.base_rule import Finding


async def save_findings(session_id: str, findings: list[Finding]) -> None:
    if not findings:
        return
    rows = [
        (
            str(uuid.uuid4()),
            session_id,
            f.rule_id,
            f.rule_name,
            f.severity.value,
            f.shape_id or None,
            f.shape_label or None,
            f.description,
            f.recommendation,
        )
        for f in findings
    ]
    async with get_db() as db:
        await db.executemany(
            """INSERT INTO rule_findings
               (id, session_id, rule_id, rule_name, severity, shape_id, shape_label,
                description, recommendation)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        await db.commit()


async def get_findings(session_id: str) -> list[dict]:
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM rule_findings WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
