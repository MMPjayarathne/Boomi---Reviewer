from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.parser.models import BoomiProcess

from backend.utils.severity import Severity


@dataclass
class Finding:
    rule_id: str
    rule_name: str
    severity: Severity
    description: str
    recommendation: str
    shape_id: str = ""
    shape_label: str = ""
    extra: dict = field(default_factory=dict)


class BaseRule(ABC):
    rule_id: str = ""
    rule_name: str = ""
    severity: Severity = Severity.INFO

    @abstractmethod
    def check(self, process: "BoomiProcess") -> list[Finding]:
        ...

    def _finding(self, description: str, recommendation: str,
                 shape_id: str = "", shape_label: str = "", **extra) -> Finding:
        return Finding(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            severity=self.severity,
            description=description,
            recommendation=recommendation,
            shape_id=shape_id,
            shape_label=shape_label,
            extra=extra,
        )
