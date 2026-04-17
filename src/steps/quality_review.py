"""Step 8: Quality review, compliance check, and trauma-informed language audit."""

from __future__ import annotations
from typing import Any

from src.steps.base_step import BaseStep


class QualityReviewStep(BaseStep):
    step_name = "quality_review"
    prompt_file = "08_quality_review.yaml"

    def build_user_prompt(self, context: dict[str, Any]) -> str:
        template = self.user_prompt_template
        step_outputs = context.get("step_outputs", {})

        return template.format(
            compliance_checklist=step_outputs.get("compliance_extraction", ""),
            draft=step_outputs.get("narrative_assembly", context.get("previous_step_output", "")),
        )
