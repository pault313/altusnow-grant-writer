"""Step 4: VPI data integration for needs statement evidence."""

from __future__ import annotations

import json
from typing import Any

from src.steps.base_step import BaseStep


class VPIIntegrationStep(BaseStep):
    step_name = "vpi_integration"
    prompt_file = "04_vpi_integration.yaml"

    def build_user_prompt(self, context: dict[str, Any]) -> str:
        template = self.user_prompt_template

        state_name = context.get("target_state", "Unknown State")

        # VPI data can be provided as JSON string or dict
        vpi_data = context.get("vpi_data", {})
        if isinstance(vpi_data, dict):
            vpi_text = json.dumps(vpi_data, indent=2)
        else:
            vpi_text = str(vpi_data)

        # Truncate if extremely large (> 100K chars)
        if len(vpi_text) > 100_000:
            vpi_text = vpi_text[:100_000] + "\n\n[... truncated for length ...]"

        return template.format(
            state_name=state_name,
            vpi_data=vpi_text,
        )
