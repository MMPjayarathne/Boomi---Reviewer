from backend.rules.base_rule import BaseRule, Finding
from backend.utils.severity import Severity
from backend.parser.models import BoomiProcess


class DuplicateConnectorsRule(BaseRule):
    rule_id = "DUP001"
    rule_name = "Duplicate Connector"
    severity = Severity.MEDIUM

    def check(self, process: BoomiProcess) -> list[Finding]:
        seen: dict[tuple, list[str]] = {}
        for conn in process.connections:
            key = (conn.from_shape, conn.to_shape)
            seen.setdefault(key, []).append(conn.id)

        findings = []
        for (from_s, to_s), ids in seen.items():
            if len(ids) > 1:
                from_shape = process.shape_by_id(from_s)
                to_shape = process.shape_by_id(to_s)
                findings.append(self._finding(
                    description=(
                        f"Duplicate connection found between "
                        f"'{from_shape.label or from_s if from_shape else from_s}' → "
                        f"'{to_shape.label or to_s if to_shape else to_s}' "
                        f"({len(ids)} times, IDs: {', '.join(ids)})."
                    ),
                    recommendation=(
                        "Remove the duplicate connections. Multiple connections between the "
                        "same two shapes cause unexpected behavior and branching logic errors."
                    ),
                ))
        return findings
