"""
PERF004 — Unbounded iteration loops.

Boomi "Flow Control" (shapetype flowcontrol) is *not* always a loop: per official docs it
configures parallel processing (threads/processes) and document batching (run each
document individually, batches of N, chunk/thread modes). Those must NOT be flagged here.

Only treat Flow Control as an iteration-risk when configuration indicates a *loop* mode
(e.g. loopType) and no max iteration guard.

References (AtomSphere / Integration):
  https://help.boomi.com/docs/atomsphere/integration/process%20building/r-atm-flow_control_shape_91fdf4a1-c765-4d4b-a0c0-c8159222ee32/
  https://help.boomi.com/docs/atomsphere/integration/process%20building/c-atm-flow_control_shape_and_fiber_executions_b03b9567-f7b2-4f43-9c34-b96904744287/
  https://help.boomi.com/docs/atomsphere/integration/process%20building/c-atm-flow_control_shape_ex_run_each_document_individuall_5a1b8e96-d153-4cb3-b925-67d70eb25390/
"""

from backend.rules.base_rule import BaseRule, Finding
from backend.utils.severity import Severity
from backend.parser.models import BoomiProcess

# Explicit loop / iterator shapes (not Boomi Flow Control document routing)
_LOOP_SHAPE_TYPES = {"forloop", "loop", "foreach", "for_each", "iterator"}


def _flatten_props(props: dict) -> dict:
    flat: dict[str, str] = {}
    for k, v in props.items():
        if isinstance(v, str):
            flat[k.lower()] = v
        elif isinstance(v, dict):
            flat.update(_flatten_props(v))
    return flat


def _max_iteration_value(flat: dict[str, str]) -> str | None:
    return (
        flat.get("maxiterations")
        or flat.get("maxiter")
        or flat.get("max_iterations")
        or flat.get("limit")
    )


def _has_bounded_iterations(flat: dict[str, str]) -> bool:
    max_iter = _max_iteration_value(flat)
    if not max_iter:
        return False
    return max_iter not in ("0", "-1", "unlimited", "")


def _is_flowcontrol_document_or_parallel_mode(flat: dict[str, str]) -> bool:
    """
    Flow Control step: parallel processing, document batching, chunk/thread fiber runs.
    chunkStyle / forEachCount / chunks indicate document routing — not a for-loop.
    """
    if flat.get("chunkstyle") or flat.get("chunk_style"):
        return True
    if flat.get("foreachcount") is not None or flat.get("foreach_count") is not None:
        return True
    # Threads/processes parallel (document fan-out), not iteration count
    if flat.get("threads") or flat.get("processes") or flat.get("parallelprocessing"):
        return True
    return False


def _flowcontrol_is_iteration_loop_mode(flat: dict[str, str]) -> bool:
    """Only flag when configuration suggests loop/retry iteration semantics."""
    lt = (flat.get("looptype") or flat.get("loop_type") or "").strip().lower()
    if not lt:
        return False
    # Known loop-style modes in exports; parallel/batch are not loops
    if lt in ("none", "parallel", "parallelprocessing", "documentbatch", "threadonly"):
        return False
    return True


class UnboundedLoopsRule(BaseRule):
    rule_id = "PERF004"
    rule_name = "Unbounded Loop"
    severity = Severity.HIGH

    def check(self, process: BoomiProcess) -> list[Finding]:
        findings = []
        for shape in process.shapes:
            st = (shape.type or "").lower()
            flat = _flatten_props(shape.properties)

            if _has_bounded_iterations(flat):
                continue

            if st in _LOOP_SHAPE_TYPES:
                findings.append(self._finding(
                    description=(
                        f"Loop shape '{shape.label or shape.id}' has no maximum iteration "
                        "limit configured. An infinite loop will exhaust process resources "
                        "and cause the Atom to become unresponsive."
                    ),
                    recommendation=(
                        "Set a maximum iteration count on the loop shape. "
                        "Add a break condition or timeout guard to prevent runaway loops."
                    ),
                    shape_id=shape.id,
                    shape_label=shape.label,
                ))
                continue

            if st != "flowcontrol":
                continue

            # Boomi Flow Control: default is document batching / parallel fibers — not a loop.
            if _is_flowcontrol_document_or_parallel_mode(flat):
                continue

            if not _flowcontrol_is_iteration_loop_mode(flat):
                continue

            findings.append(self._finding(
                description=(
                    f"Flow Control shape '{shape.label or shape.id}' has loop-style settings "
                    "(loopType) but no maximum iteration limit configured. An unbounded "
                    "retry loop can exhaust process resources and make the Atom unresponsive."
                ),
                recommendation=(
                    "Configure a maximum iteration count or exit condition for this loop. "
                    "If this step is only for parallel processing or document batching, "
                    "use the Flow Control options for threads/batches (see Boomi docs) "
                    "rather than loop iteration."
                ),
                shape_id=shape.id,
                shape_label=shape.label,
            ))
        return findings
