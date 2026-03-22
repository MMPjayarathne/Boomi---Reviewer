from backend.rules.base_rule import BaseRule, Finding
from backend.utils.severity import Severity
from backend.parser.models import BoomiProcess
from backend.parser.graph_builder import build_graph

START_TYPES = {"start", "startshape", "process_start"}


class UnreachableShapesRule(BaseRule):
    rule_id = "DEAD001"
    rule_name = "Unreachable Shape"
    severity = Severity.HIGH

    def check(self, process: BoomiProcess) -> list[Finding]:
        if len(process.shapes) < 2:
            return []
        g = build_graph(process)
        findings = []
        for shape in process.shapes:
            if shape.type.lower() in START_TYPES:
                continue
            if g.in_degree(shape.id) == 0:
                findings.append(self._finding(
                    description=(
                        f"Shape '{shape.label or shape.id}' (type: {shape.type}) "
                        "has no incoming connection and is never executed."
                    ),
                    recommendation=(
                        "Connect this shape to the process flow or remove it. "
                        "Unreachable shapes indicate dead code or a broken process design."
                    ),
                    shape_id=shape.id,
                    shape_label=shape.label,
                ))
        return findings
