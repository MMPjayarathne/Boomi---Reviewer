import networkx as nx
from backend.rules.base_rule import BaseRule, Finding
from backend.utils.severity import Severity
from backend.parser.models import BoomiProcess
from backend.parser.graph_builder import build_graph


class DisconnectedGraphRule(BaseRule):
    rule_id = "DEAD003"
    rule_name = "Disconnected Process Graph"
    severity = Severity.MEDIUM

    def check(self, process: BoomiProcess) -> list[Finding]:
        if len(process.shapes) < 2:
            return []
        g = build_graph(process)
        components = list(nx.weakly_connected_components(g))
        if len(components) <= 1:
            return []
        findings = []
        for i, component in enumerate(components[1:], start=2):
            shape_labels = []
            for sid in component:
                shape = process.shape_by_id(sid)
                shape_labels.append(shape.label or sid if shape else sid)
            findings.append(self._finding(
                description=(
                    f"Disconnected subgraph #{i} detected containing shapes: "
                    f"{', '.join(shape_labels[:5])}{'...' if len(shape_labels) > 5 else ''}. "
                    "These shapes are isolated from the main process flow."
                ),
                recommendation=(
                    "Connect this group of shapes to the main process flow or "
                    "remove them if they are leftover from a previous design."
                ),
            ))
        return findings
