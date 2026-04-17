"""Step 1: RFP document ingestion and structured extraction."""

from __future__ import annotations
from typing import Any

from src.steps.base_step import BaseStep


class RFPIngestionStep(BaseStep):
    step_name = "rfp_ingestion"
    prompt_file = "01_rfp_ingestion.yaml"

    def build_user_prompt(self, context: dict[str, Any]) -> str:
        template = self.user_prompt_template
        return template.format(
            file_name=context.get("file_name", "uploaded_rfp"),
            page_count=context.get("page_count", "unknown"),
            word_count=context.get("word_count", "unknown"),
            rfp_text=context.get("rfp_text", ""),
            tables_markdown=context.get("tables_markdown", "No tables extracted."),
        )
