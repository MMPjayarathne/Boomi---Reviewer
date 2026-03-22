from backend.rules.base_rule import BaseRule, Finding
from backend.utils.severity import Severity
from backend.parser.models import BoomiProcess
from backend.parser.graph_builder import build_graph

TRY_CATCH_TYPES = {"trycatch", "try_catch", "exceptionhandler", "exception_handler"}
EXCEPTION_PATH_LABELS = {"error", "exception", "failure", "failed", "catch"}


class MissingTryCatchRule(BaseRule):
    rule_id = "EH001"
    rule_name = "Missing Error Handling"
    severity = Severity.CRITICAL

    def check(self, process: BoomiProcess) -> list[Finding]:
        # Check if any try/catch or exception shape exists
        has_error_handling = any(
            s.type.lower() in TRY_CATCH_TYPES for s in process.shapes
        )
        if has_error_handling:
            return []

        # Check if any connector is labeled as an error path
        has_error_path = any(
            any(lbl in conn.label.lower() for lbl in EXCEPTION_PATH_LABELS)
            for conn in process.connections
        )
        if has_error_path:
            return []

        # No error handling found at all
        if not process.shapes:
            return []

        return [self._finding(
            description=(
                f"Process '{process.process_name}' has no error handling. "
                "There are no Try/Catch shapes and no exception paths defined."
            ),
            recommendation=(
                "Add a Try/Catch shape around connector calls and data operations. "
                "Add an exception branch to handle failures gracefully — log the error, "
                "send notifications, and stop the process cleanly instead of leaving "
                "documents in an unknown state."
            ),
        )]
