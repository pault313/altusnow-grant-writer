"""Step 2b: Generate intake questions from parsed RFP and compliance checklist."""

from __future__ import annotations

import json
import re
from typing import Any

from src.steps.base_step import BaseStep


class IntakeQuestionnaireStep(BaseStep):
    step_name = "intake_questionnaire"
    prompt_file = "02b_intake_questionnaire.yaml"

    def build_user_prompt(self, context: dict[str, Any]) -> str:
        template = self.user_prompt_template
        step_outputs = context.get("step_outputs", {})
        return template.format(
            rfp_summary=step_outputs.get("rfp_ingestion", ""),
            compliance_checklist=step_outputs.get("compliance_extraction", ""),
        )

    def parse_questions(self, raw_output: str) -> list[dict]:
        """Parse the LLM output into a structured list of questions."""
        # Try to extract JSON from the response
        text = raw_output.strip()

        # Remove markdown code fences if present
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        try:
            data = json.loads(text)
            questions = data.get("questions", [])
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                try:
                    data = json.loads(match.group())
                    questions = data.get("questions", [])
                except json.JSONDecodeError:
                    questions = []

        # Validate and clean each question
        cleaned = []
        for q in questions:
            if not isinstance(q, dict):
                continue
            if not q.get("question"):
                continue

            cleaned.append({
                "id": q.get("id", f"q_{len(cleaned)}"),
                "category": q.get("category", "General"),
                "question": q["question"],
                "why": q.get("why", ""),
                "priority": q.get("priority", "recommended"),
                "input_type": q.get("input_type", "text"),
                "options": q.get("options", []),
                "default": q.get("default", ""),
            })

        return cleaned
