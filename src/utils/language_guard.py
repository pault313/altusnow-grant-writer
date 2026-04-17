"""
Trauma-informed language guardrails scanner.

Scans generated text for prohibited terms and flags violations.
Uses the language_guardrails table from the database.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.database import get_guardrails


@dataclass
class Violation:
    """A single language guardrail violation."""
    term: str
    category: str  # prohibited, context_dependent
    replacement: Optional[str]
    context_note: Optional[str]
    source: str
    line_number: int
    line_text: str
    position: int  # character position in line


@dataclass
class ScanResult:
    """Result of scanning text for language violations."""
    violations: list[Violation]
    prohibited_count: int
    context_dependent_count: int

    @property
    def passed(self) -> bool:
        """Pass if no prohibited terms found. Context-dependent terms are warnings."""
        return self.prohibited_count == 0

    @property
    def total_count(self) -> int:
        return len(self.violations)

    def summary(self) -> str:
        if self.passed and self.context_dependent_count == 0:
            return "PASSED: No language guardrail violations found."
        parts = []
        if self.prohibited_count > 0:
            parts.append(f"FAILED: {self.prohibited_count} prohibited term(s) found")
        if self.context_dependent_count > 0:
            parts.append(f"WARNING: {self.context_dependent_count} context-dependent term(s) to review")
        return ". ".join(parts) + "."

    def details(self) -> str:
        """Format violations for display."""
        if not self.violations:
            return "No violations found."

        lines = []
        for v in self.violations:
            tag = "PROHIBITED" if v.category == "prohibited" else "REVIEW"
            replacement = f' -> "{v.replacement}"' if v.replacement else ""
            lines.append(
                f"  [{tag}] Line {v.line_number}: \"{v.term}\"{replacement}\n"
                f"    Context: ...{v.line_text.strip()[:100]}...\n"
                f"    Note: {v.context_note or 'See ' + v.source}"
            )
        return "\n".join(lines)


def scan_text(
    text: str,
    db_path: Optional[Path] = None,
    guardrails: Optional[list[dict]] = None,
) -> ScanResult:
    """
    Scan text for language guardrail violations.

    Args:
        text: The text to scan.
        db_path: Optional database path (uses default if None).
        guardrails: Pre-loaded guardrails (skips DB query if provided).

    Returns:
        ScanResult with all violations found.
    """
    if guardrails is None:
        guardrails = get_guardrails(db_path)

    violations: list[Violation] = []
    lines = text.split("\n")

    for guardrail in guardrails:
        category = guardrail["category"]
        if category == "preferred":
            continue  # preferred terms are not violations

        term = guardrail["term"]
        # Build case-insensitive word-boundary pattern
        pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)

        for line_num, line in enumerate(lines, 1):
            for match in pattern.finditer(line):
                violations.append(Violation(
                    term=match.group(),
                    category=category,
                    replacement=guardrail.get("replacement"),
                    context_note=guardrail.get("context_note"),
                    source=guardrail.get("source", ""),
                    line_number=line_num,
                    line_text=line,
                    position=match.start(),
                ))

    prohibited_count = sum(1 for v in violations if v.category == "prohibited")
    context_count = sum(1 for v in violations if v.category == "context_dependent")

    return ScanResult(
        violations=violations,
        prohibited_count=prohibited_count,
        context_dependent_count=context_count,
    )


def auto_fix_prohibited(text: str, db_path: Optional[Path] = None) -> tuple[str, int]:
    """
    Auto-replace prohibited terms with their preferred replacements.

    Returns:
        Tuple of (fixed_text, replacement_count).
    """
    guardrails = get_guardrails(db_path)
    fixed = text
    count = 0

    for guardrail in guardrails:
        if guardrail["category"] != "prohibited" or not guardrail.get("replacement"):
            continue
        pattern = re.compile(r"\b" + re.escape(guardrail["term"]) + r"\b", re.IGNORECASE)
        new_text, n = pattern.subn(guardrail["replacement"], fixed)
        if n > 0:
            fixed = new_text
            count += n

    return fixed, count
