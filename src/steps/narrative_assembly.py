"""Step 7: Full narrative assembly from individual section drafts."""

from __future__ import annotations
from typing import Any

from src.steps.base_step import BaseStep


class NarrativeAssemblyStep(BaseStep):
    step_name = "narrative_assembly"
    prompt_file = "07_narrative_assembly.yaml"

    def build_user_prompt(self, context: dict[str, Any]) -> str:
        template = self.user_prompt_template
        step_outputs = context.get("step_outputs", {})

        return template.format(
            rfp_summary=step_outputs.get("rfp_ingestion", ""),
            compliance_checklist=step_outputs.get("compliance_extraction", ""),
            needs_statement=step_outputs.get("needs_statement", ""),
            program_design=step_outputs.get("program_design", ""),
            org_context=step_outputs.get("org_context_assembly", ""),
            intake_answers=context.get("intake_answers_text", "No intake answers provided."),
        )
