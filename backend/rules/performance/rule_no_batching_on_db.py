from backend.rules.base_rule import BaseRule, Finding
from backend.utils.severity import Severity
from backend.parser.models import BoomiProcess

DB_CONNECTOR_TYPES = {"database", "db", "jdbc", "databaseconnector"}


def _flatten_props(props: dict) -> dict:
    flat = {}
    for k, v in props.items():
        if isinstance(v, str):
            flat[k.lower()] = v
        elif isinstance(v, dict):
            flat.update(_flatten_props(v))
    return flat


class NoBatchingOnDbRule(BaseRule):
    rule_id = "PERF002"
    rule_name = "Database Connector Without Batching"
    severity = Severity.HIGH

    def check(self, process: BoomiProcess) -> list[Finding]:
        findings = []
        for shape in process.shapes:
            if shape.type.lower() not in DB_CONNECTOR_TYPES:
                continue
            flat = _flatten_props(shape.properties)
            batch_enabled = flat.get("batchcount") or flat.get("batch") or flat.get("commitinterval")
            if not batch_enabled:
                findings.append(self._finding(
                    description=(
                        f"Database connector shape '{shape.label or shape.id}' has no "
                        "batch commit configuration. Each record will trigger a separate "
                        "transaction, severely impacting performance at scale."
                    ),
                    recommendation=(
                        "Enable batch commits in the database connector configuration. "
                        "Set an appropriate batch size (e.g., 100–1000 records) based on "
                        "your data volume and database capabilities."
                    ),
                    shape_id=shape.id,
                    shape_label=shape.label,
                ))
        return findings
