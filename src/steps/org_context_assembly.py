"""Step 3: Organizational context assembly for grant positioning."""

from __future__ import annotations

import json
from typing import Any

from src.steps.base_step import BaseStep


class OrgContextAssemblyStep(BaseStep):
    step_name = "org_context_assembly"
    prompt_file = "03_org_context_assembly.yaml"

    def build_user_prompt(self, context: dict[str, Any]) -> str:
        template = self.user_prompt_template

        # Build org profile string
        org = context.get("org_profile", {})
        org_profile = (
            f"Organization: {org.get('name', 'Unknown')}\n"
            f"Type: {org.get('org_type', 'nonprofit')}\n"
            f"Website: {org.get('website', '')}\n"
            f"Mission: {org.get('mission_statement', '')}\n"
        )

        # Product catalog
        catalog = org.get("product_catalog_json", "{}")
        if isinstance(catalog, str):
            try:
                catalog = json.loads(catalog)
            except json.JSONDecodeError:
                catalog = {}
        product_text = json.dumps(catalog, indent=2) if catalog else "No products listed."

        return template.format(
            org_profile=org_profile,
            product_catalog=product_text,
            rfp_summary=context.get("step_outputs", {}).get("rfp_ingestion", ""),
            compliance_checklist=context.get("step_outputs", {}).get("compliance_extraction", ""),
        )
