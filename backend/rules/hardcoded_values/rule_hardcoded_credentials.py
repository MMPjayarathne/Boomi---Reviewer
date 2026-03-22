import re
from backend.rules.base_rule import BaseRule, Finding
from backend.utils.severity import Severity
from backend.parser.models import BoomiProcess

CREDENTIAL_PATTERNS = [
    re.compile(r'password', re.IGNORECASE),
    re.compile(r'passwd', re.IGNORECASE),
    re.compile(r'secret', re.IGNORECASE),
    re.compile(r'api[_\-]?key', re.IGNORECASE),
    re.compile(r'access[_\-]?token', re.IGNORECASE),
    re.compile(r'auth[_\-]?token', re.IGNORECASE),
    re.compile(r'private[_\-]?key', re.IGNORECASE),
    re.compile(r'client[_\-]?secret', re.IGNORECASE),
]

# If the value looks like a real secret (not a placeholder or variable)
PLACEHOLDER_PATTERNS = [
    re.compile(r'^\{.*\}$'),       # {variable}
    re.compile(r'^\$\{.*\}$'),     # ${variable}
    re.compile(r'^<.*>$'),         # <placeholder>
    re.compile(r'^%.*%$'),         # %variable%
    re.compile(r'^$'),             # empty
]


def _looks_like_hardcoded(value: str) -> bool:
    if not value or len(value) < 2:
        return False
    for pattern in PLACEHOLDER_PATTERNS:
        if pattern.match(value.strip()):
            return False
    return True


def _flatten_props(props: dict, prefix="") -> list[tuple[str, str]]:
    """Yield (key_path, value) for all string leaf values."""
    results = []
    for k, v in props.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, str):
            results.append((full_key, v))
        elif isinstance(v, dict):
            results.extend(_flatten_props(v, full_key))
    return results


class HardcodedCredentialsRule(BaseRule):
    rule_id = "HC001"
    rule_name = "Hardcoded Credentials"
    severity = Severity.CRITICAL

    def check(self, process: BoomiProcess) -> list[Finding]:
        findings = []
        for shape in process.shapes:
            for key, value in _flatten_props(shape.properties):
                for pattern in CREDENTIAL_PATTERNS:
                    if pattern.search(key) and _looks_like_hardcoded(value):
                        findings.append(self._finding(
                            description=(
                                f"Shape '{shape.label or shape.id}' contains a potential "
                                f"hardcoded credential in property '{key}'. "
                                f"Value starts with: '{value[:4]}...'"
                            ),
                            recommendation=(
                                "Never hardcode credentials in process configurations. "
                                "Use Boomi Connection components with environment-specific "
                                "connection settings, or Boomi's built-in credential store."
                            ),
                            shape_id=shape.id,
                            shape_label=shape.label,
                        ))
                        break
        return findings
