from backend.rules.base_rule import BaseRule, Finding
from backend.utils.severity import Severity
from backend.parser.models import BoomiProcess

LOG_SHAPE_TYPES = {"log", "logging", "message", "notify"}
DEBUG_KEYWORDS = {"debug", "trace", "verbose", "all"}


def _flatten_props(props: dict) -> dict:
    flat = {}
    for k, v in props.items():
        if isinstance(v, str):
            flat[k.lower()] = v.lower()
        elif isinstance(v, dict):
            flat.update(_flatten_props(v))
    return flat


class ExcessiveLoggingRule(BaseRule):
    rule_id = "PERF003"
    rule_name = "Debug Logging Enabled"
    severity = Severity.MEDIUM

    def check(self, process: BoomiProcess) -> list[Finding]:
        findings = []
        for shape in process.shapes:
            if shape.type.lower() not in LOG_SHAPE_TYPES:
                continue
            flat = _flatten_props(shape.properties)
            level = flat.get("loglevel") or flat.get("level") or flat.get("messagelevel", "")
            if any(kw in level for kw in DEBUG_KEYWORDS):
                findings.append(self._finding(
                    description=(
                        f"Shape '{shape.label or shape.id}' has logging level set to "
                        f"'{level}'. Debug/trace logging in production causes significant "
                        "performance overhead and may expose sensitive data."
                    ),
                    recommendation=(
                        "Set the logging level to 'INFO' or 'WARNING' for production. "
                        "Use debug logging only during development and testing phases."
                    ),
                    shape_id=shape.id,
                    shape_label=shape.label,
                ))
        return findings
