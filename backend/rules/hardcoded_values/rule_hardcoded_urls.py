import re
from backend.rules.base_rule import BaseRule, Finding
from backend.utils.severity import Severity
from backend.parser.models import BoomiProcess

URL_PATTERN = re.compile(r'https?://[^\s\'"<>{}|\\^`\[\]]{5,}', re.IGNORECASE)
IP_PATTERN = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\b')


def _flatten_props(props: dict, prefix="") -> list[tuple[str, str]]:
    results = []
    for k, v in props.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, str):
            results.append((full_key, v))
        elif isinstance(v, dict):
            results.extend(_flatten_props(v, full_key))
    return results


class HardcodedUrlsRule(BaseRule):
    rule_id = "HC003"
    rule_name = "Hardcoded URL"
    severity = Severity.HIGH

    def check(self, process: BoomiProcess) -> list[Finding]:
        findings = []
        for shape in process.shapes:
            for key, value in _flatten_props(shape.properties):
                if URL_PATTERN.search(value):
                    findings.append(self._finding(
                        description=(
                            f"Shape '{shape.label or shape.id}' has a hardcoded URL in "
                            f"property '{key}': '{value[:60]}{'...' if len(value) > 60 else ''}'"
                        ),
                        recommendation=(
                            "Replace hardcoded URLs with Boomi dynamic process properties "
                            "or environment-specific connection settings. This prevents "
                            "accidental use of dev/test URLs in production."
                        ),
                        shape_id=shape.id,
                        shape_label=shape.label,
                    ))
                elif IP_PATTERN.search(value):
                    findings.append(self._finding(
                        description=(
                            f"Shape '{shape.label or shape.id}' contains a hardcoded IP "
                            f"address in property '{key}': '{value[:40]}'"
                        ),
                        recommendation=(
                            "Replace hardcoded IP addresses with hostnames or "
                            "dynamic process properties to support environment portability."
                        ),
                        shape_id=shape.id,
                        shape_label=shape.label,
                    ))
        return findings
