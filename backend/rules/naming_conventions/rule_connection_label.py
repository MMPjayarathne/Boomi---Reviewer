from backend.rules.base_rule import BaseRule, Finding
from backend.utils.severity import Severity
from backend.parser.models import BoomiProcess
from backend.parser.graph_builder import build_graph

BRANCH_TYPES = {"decision", "route", "branchroute", "flowcontrol", "condition"}


class ConnectionLabelRule(BaseRule):
    rule_id = "NAME003"
    rule_name = "Conditional Connector Missing Label"
    severity = Severity.MEDIUM

    def check(self, process: BoomiProcess) -> list[Finding]:
        # Find decision/branching shapes
        branch_shape_ids = {
            s.id for s in process.shapes
            if s.type.lower() in BRANCH_TYPES
        }
        if not branch_shape_ids:
            return []

        findings = []
        for conn in process.connections:
            if conn.from_shape in branch_shape_ids and not conn.label.strip():
                from_shape = process.shape_by_id(conn.from_shape)
                findings.append(self._finding(
                    description=(
                        f"Connection from branching shape "
                        f"'{from_shape.label or conn.from_shape if from_shape else conn.from_shape}' "
                        f"(ID: {conn.id}) has no label. It is unclear what condition "
                        "triggers this path."
                    ),
                    recommendation=(
                        "Label all outgoing connections from Decision/Route shapes "
                        "with the condition they represent, e.g., 'Success', 'No Match', "
                        "'Amount > 1000'."
                    ),
                ))
        return findings
