import hashlib
from backend.rules.base_rule import BaseRule, Finding
from backend.utils.severity import Severity
from backend.parser.models import BoomiProcess


class DuplicateShapesRule(BaseRule):
    rule_id = "DUP002"
    rule_name = "Duplicate Shape Configuration"
    severity = Severity.LOW

    def check(self, process: BoomiProcess) -> list[Finding]:
        # Group shapes by type first, then compare properties
        by_type: dict[str, list] = {}
        for shape in process.shapes:
            by_type.setdefault(shape.type, []).append(shape)

        findings = []
        for stype, shapes in by_type.items():
            if len(shapes) < 2:
                continue
            hashes: dict[str, list] = {}
            for shape in shapes:
                # Hash properties dict (excluding id/label)
                props_copy = {k: v for k, v in shape.properties.items()
                              if k.lower() not in ("id", "label", "name", "shapeid")}
                h = hashlib.md5(str(sorted(props_copy.items())).encode()).hexdigest()
                hashes.setdefault(h, []).append(shape)

            for h, dup_shapes in hashes.items():
                if len(dup_shapes) > 1:
                    labels = [s.label or s.id for s in dup_shapes]
                    findings.append(self._finding(
                        description=(
                            f"{len(dup_shapes)} shapes of type '{stype}' have identical "
                            f"configurations: {', '.join(labels)}."
                        ),
                        recommendation=(
                            "Consider consolidating these shapes into a single reusable "
                            "component, or verify they are intentionally duplicated."
                        ),
                    ))
        return findings
