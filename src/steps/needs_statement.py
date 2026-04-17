"""Step 5: Needs statement drafting using VPI evidence."""

from __future__ import annotations
from typing import Any

from src.steps.base_step import BaseStep


class NeedsStatementStep(BaseStep):
    step_name = "needs_statement"
    prompt_file = "05_needs_statement.yaml"

    def build_user_prompt(self, context: dict[str, Any]) -> str:
        template = self.user_prompt_template
        step_outputs = context.get("step_outputs", {})

        return template.format(
            rfp_summary=step_outputs.get("rfp_ingestion", ""),
            vpi_evidence=step_outputs.get("vpi_integration", ""),
            org_context=step_outputs.get("org_context_assembly", ""),
            section_requirements=_extract_section_reqs(
                step_outputs.get("compliance_extraction", ""),
                "needs",
            ),
        )


def _extract_section_reqs(compliance_text: str, section_keyword: str) -> str:
    """Extract compliance items relevant to a specific section."""
    if not compliance_text:
        return "No specific requirements extracted."

    relevant = []
    for line in compliance_text.split("\n"):
        line_lower = line.lower()
        if section_keyword in line_lower or "problem" in line_lower or "statement" in line_lower:
            relevant.append(line.strip())

    if relevant:
        return "\n".join(relevant)
    return "Refer to full compliance checklist for section-specific requirements."
