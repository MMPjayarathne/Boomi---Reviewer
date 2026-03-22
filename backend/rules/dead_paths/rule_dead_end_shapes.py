from backend.rules.base_rule import BaseRule, Finding
from backend.utils.severity import Severity
from backend.parser.models import BoomiProcess
from backend.parser.graph_builder import build_graph

TERMINAL_TYPES = {"stop", "end", "endshape", "process_stop", "return"}


class DeadEndShapesRule(BaseRule):
    rule_id = "DEAD002"
    rule_name = "Dead-End Shape"
    severity = Severity.HIGH

    def check(self, process: BoomiProcess) -> list[Finding]:
        if len(process.shapes) < 2:
            return []
        g = build_graph(process)
        findings = []
        for shape in process.shapes:
            if shape.type.lower() in TERMINAL_TYPES:
                continue
            if g.out_degree(shape.id) == 0:
                findings.append(self._finding(
                    description=(
                        f"Shape '{shape.label or shape.id}' (type: {shape.type}) "
                        "has no outgoing connection. The process will stall here."
                    ),
                    recommendation=(
                        "Add an outgoing connection from this shape to continue the flow, "
                        "or replace it with a Stop/End shape if this is intentional."
                    ),
                    shape_id=shape.id,
                    shape_label=shape.label,
                ))
        return findings
