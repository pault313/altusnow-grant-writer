"""Step 6: Program design, goals/objectives, and budget narrative."""

from __future__ import annotations
from typing import Any

from src.steps.base_step import BaseStep


class ProgramDesignStep(BaseStep):
    step_name = "program_design"
    prompt_file = "06_program_design.yaml"

    def build_user_prompt(self, context: dict[str, Any]) -> str:
        template = self.user_prompt_template
        step_outputs = context.get("step_outputs", {})

        return template.format(
            rfp_summary=step_outputs.get("rfp_ingestion", ""),
            needs_statement=step_outputs.get("needs_statement", ""),
            org_context=step_outputs.get("org_context_assembly", ""),
            vpi_evidence=step_outputs.get("vpi_integration", ""),
            section_requirements=_extract_section_reqs(
                step_outputs.get("compliance_extraction", ""),
            ),
            intake_answers=context.get("intake_answers_text", "No intake answers provided."),
        )


def _extract_section_reqs(compliance_text: str) -> str:
    """Extract compliance items relevant to program design and budget."""
    if not compliance_text:
        return "No specific requirements extracted."

    relevant = []
    keywords = ["program", "design", "budget", "goal", "objective", "evaluation",
                "performance", "measure", "activity", "timeline"]
    for line in compliance_text.split("\n"):
        line_lower = line.lower()
        if any(kw in line_lower for kw in keywords):
            relevant.append(line.strip())

    if relevant:
        return "\n".join(relevant)
    return "Refer to full compliance checklist for section-specific requirements."
