from backend.rules.base_rule import BaseRule, Finding
from backend.utils.severity import Severity
from backend.parser.models import BoomiProcess

SKIP_TYPES = {"start", "stop", "end", "startshape", "endshape"}


class ShapeLabelMissingRule(BaseRule):
    rule_id = "NAME002"
    rule_name = "Shape Missing Label"
    severity = Severity.INFO

    def check(self, process: BoomiProcess) -> list[Finding]:
        findings = []
        for shape in process.shapes:
            if shape.type.lower() in SKIP_TYPES:
                continue
            if not shape.label or shape.label.strip() == "":
                findings.append(self._finding(
                    description=(
                        f"Shape '{shape.id}' (type: {shape.type}) has no label. "
                        "Unlabeled shapes make the process diagram hard to understand."
                    ),
                    recommendation=(
                        "Add a descriptive label to every shape that explains its "
                        "business purpose, not just its technical type."
                    ),
                    shape_id=shape.id,
                    shape_label="",
                ))
        return findings
