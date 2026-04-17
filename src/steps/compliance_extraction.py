"""Step 2: Compliance checklist extraction from parsed RFP."""

from __future__ import annotations
from typing import Any

from src.steps.base_step import BaseStep


class ComplianceExtractionStep(BaseStep):
    step_name = "compliance_extraction"
    prompt_file = "02_compliance_extraction.yaml"

    def build_user_prompt(self, context: dict[str, Any]) -> str:
        template = self.user_prompt_template
        return template.format(
            previous_step_output=context.get("previous_step_output", ""),
        )
