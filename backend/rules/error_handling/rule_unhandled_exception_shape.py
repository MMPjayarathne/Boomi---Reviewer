from backend.rules.base_rule import BaseRule, Finding
from backend.utils.severity import Severity
from backend.parser.models import BoomiProcess
from backend.parser.graph_builder import build_graph

EXCEPTION_TYPES = {"exception", "exceptionshape", "trycatch", "try_catch"}


class UnhandledExceptionShapeRule(BaseRule):
    rule_id = "EH002"
    rule_name = "Unhandled Exception Shape"
    severity = Severity.HIGH

    def check(self, process: BoomiProcess) -> list[Finding]:
        g = build_graph(process)
        findings = []
        for shape in process.shapes:
            if shape.type.lower() in EXCEPTION_TYPES:
                if g.out_degree(shape.id) == 0:
                    findings.append(self._finding(
                        description=(
                            f"Exception shape '{shape.label or shape.id}' has no outgoing "
                            "connection. Caught exceptions are silently discarded."
                        ),
                        recommendation=(
                            "Add a downstream shape to handle the exception: "
                            "log the error details, send a notification, "
                            "and use a Stop shape to end the process gracefully."
                        ),
                        shape_id=shape.id,
                        shape_label=shape.label,
                    ))
        return findings
