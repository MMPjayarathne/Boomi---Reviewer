"""
Auto-discovers and runs all rules.
Drop any new BaseRule subclass into a rules/ subpackage and it is picked up automatically.
"""

import importlib
import pkgutil
import inspect
import asyncio
from pathlib import Path

from backend.rules.base_rule import BaseRule, Finding
from backend.parser.models import BoomiProcess
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_RULES_DIR = Path(__file__).parent
_RULES_PACKAGE = "backend.rules"

# Subpackages that contain rule modules (not the registry itself)
_RULE_SUBPKGS = [
    "dead_paths",
    "duplicates",
    "hardcoded_values",
    "error_handling",
    "performance",
    "naming_conventions",
]


def _discover_rules() -> list[BaseRule]:
    rules: list[BaseRule] = []
    for subpkg in _RULE_SUBPKGS:
        pkg_path = _RULES_DIR / subpkg
        pkg_name = f"{_RULES_PACKAGE}.{subpkg}"
        for finder, module_name, _ in pkgutil.iter_modules([str(pkg_path)]):
            full_name = f"{pkg_name}.{module_name}"
            try:
                module = importlib.import_module(full_name)
            except Exception as exc:
                logger.warning(f"Could not import rule module {full_name}: {exc}")
                continue
            for _, cls in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(cls, BaseRule)
                    and cls is not BaseRule
                    and cls.__module__ == full_name
                ):
                    rules.append(cls())
    # Sort by severity weight descending (run CRITICAL first)
    rules.sort(key=lambda r: r.severity.weight, reverse=True)
    logger.info(f"Loaded {len(rules)} rules: {[r.rule_id for r in rules]}")
    return rules


# Cache discovered rules for the lifetime of the process
_CACHED_RULES: list[BaseRule] | None = None


def get_rules() -> list[BaseRule]:
    global _CACHED_RULES
    if _CACHED_RULES is None:
        _CACHED_RULES = _discover_rules()
    return _CACHED_RULES


async def run_all_rules(process: BoomiProcess) -> list[Finding]:
    """Run all rules concurrently and return aggregated findings."""
    rules = get_rules()

    async def _run_one(rule: BaseRule) -> list[Finding]:
        try:
            # Rules are synchronous; run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, rule.check, process)
        except Exception as exc:
            logger.error(f"Rule {rule.rule_id} raised an exception: {exc}", exc_info=True)
            return []

    results = await asyncio.gather(*[_run_one(r) for r in rules])
    all_findings: list[Finding] = []
    for findings in results:
        all_findings.extend(findings)

    logger.info(
        f"Analysis complete: {len(all_findings)} findings "
        f"across {len(rules)} rules for process '{process.process_name}'"
    )
    return all_findings
