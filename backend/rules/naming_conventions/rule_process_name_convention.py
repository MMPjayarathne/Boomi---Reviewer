import re
from backend.rules.base_rule import BaseRule, Finding
from backend.utils.severity import Severity
from backend.parser.models import BoomiProcess

PASCAL_CASE = re.compile(r'^[A-Z][a-zA-Z0-9]*(?:[A-Z][a-zA-Z0-9]*)*$')
BAD_NAME_PATTERNS = [
    re.compile(r'^test\d*$', re.IGNORECASE),
    re.compile(r'^untitled', re.IGNORECASE),
    re.compile(r'^new process', re.IGNORECASE),
    re.compile(r'^copy of', re.IGNORECASE),
    re.compile(r'^\d'),  # starts with number
]


class ProcessNameConventionRule(BaseRule):
    rule_id = "NAME001"
    rule_name = "Process Naming Convention"
    severity = Severity.LOW

    def check(self, process: BoomiProcess) -> list[Finding]:
        name = process.process_name
        findings = []

        for pattern in BAD_NAME_PATTERNS:
            if pattern.search(name):
                findings.append(self._finding(
                    description=(
                        f"Process name '{name}' appears to be a placeholder or "
                        "default name. This makes processes hard to identify in the "
                        "Boomi Platform UI."
                    ),
                    recommendation=(
                        "Use a descriptive, business-meaningful name in PascalCase format. "
                        "Example: 'SalesOrderToSAP', 'CustomerSyncFromSalesforce'."
                    ),
                ))
                return findings

        if " " in name:
            findings.append(self._finding(
                description=f"Process name '{name}' contains spaces.",
                recommendation=(
                    "Use PascalCase without spaces. "
                    f"Suggestion: '{name.title().replace(' ', '')}'"
                ),
            ))

        return findings
