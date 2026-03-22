from backend.rules.base_rule import BaseRule, Finding
from backend.utils.severity import Severity
from backend.parser.models import BoomiProcess

NOTIFY_TYPES = {"notify", "notification", "sendemail", "email", "alert", "message"}
ERROR_TYPES = {"exception", "trycatch", "try_catch", "exceptionhandler"}


class MissingNotifyOnErrorRule(BaseRule):
    rule_id = "EH003"
    rule_name = "No Notification on Error"
    severity = Severity.HIGH

    def check(self, process: BoomiProcess) -> list[Finding]:
        has_error_shape = any(s.type.lower() in ERROR_TYPES for s in process.shapes)
        if not has_error_shape:
            return []  # EH001 will catch this case

        has_notify = any(s.type.lower() in NOTIFY_TYPES for s in process.shapes)
        if has_notify:
            return []

        return [self._finding(
            description=(
                f"Process '{process.process_name}' has error handling shapes but "
                "no notification mechanism. Failures will be caught but not reported."
            ),
            recommendation=(
                "Add a Notify shape (or Send Mail shape) on the error path to alert "
                "operations teams when the process fails. Silent failures are hard to "
                "detect in production environments."
            ),
        )]
