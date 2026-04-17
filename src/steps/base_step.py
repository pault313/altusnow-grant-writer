"""
Abstract base class for grant writing pipeline steps.

Each step:
  1. Loads its prompt template from config/prompts/
  2. Builds a user prompt with context from prior steps
  3. Calls the LLM
  4. Returns structured output for downstream steps

Adapted from Engage Together POC -- same pattern, grant-specific context keys.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

import yaml

from src.llm_client import LLMClient


class BaseStep(ABC):
    """Abstract base class for all pipeline steps."""

    # Subclasses must set these
    step_name: str = ""
    prompt_file: str = ""  # e.g., "01_rfp_ingestion.yaml"

    def __init__(self, llm_client: LLMClient, config_dir: Path):
        self.llm = llm_client
        self.config_dir = config_dir
        self._prompt_config: Optional[dict] = None

    @property
    def prompt_config(self) -> dict:
        """Load and cache the prompt YAML file."""
        if self._prompt_config is None:
            path = self.config_dir / "prompts" / self.prompt_file
            if not path.exists():
                raise FileNotFoundError(f"Prompt template not found: {path}")
            with open(path) as f:
                self._prompt_config = yaml.safe_load(f)
        return self._prompt_config

    @property
    def model(self) -> str:
        return self.prompt_config.get("model", "claude-sonnet-4-5-20250929")

    @property
    def temperature(self) -> float:
        return self.prompt_config.get("temperature", 0.3)

    @property
    def max_tokens(self) -> int:
        return self.prompt_config.get("max_tokens", 4000)

    @property
    def system_prompt(self) -> str:
        return self.prompt_config.get("system_prompt", "")

    @property
    def user_prompt_template(self) -> str:
        return self.prompt_config.get("user_prompt_template", "")

    @abstractmethod
    def build_user_prompt(self, context: dict[str, Any]) -> str:
        """
        Build the user prompt from context.

        Args:
            context: Dict with keys like 'rfp_text', 'compliance_checklist',
                     'org_context', 'vpi_summary', 'previous_step_output', etc.

        Returns:
            Formatted user prompt string.
        """
        ...

    def run(
        self,
        context: dict[str, Any],
        model_override: Optional[str] = None,
        temperature_override: Optional[float] = None,
        max_tokens_override: Optional[int] = None,
    ) -> str:
        """
        Execute this pipeline step.

        Args:
            context: Shared context dict with data and prior step outputs.
            model_override: Override the model from settings.yaml.
            temperature_override: Override temperature.
            max_tokens_override: Override max tokens.

        Returns:
            The LLM response text.
        """
        user_prompt = self.build_user_prompt(context)

        return self.llm.call(
            step_name=self.step_name,
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            model=model_override or self.model,
            temperature=temperature_override if temperature_override is not None else self.temperature,
            max_tokens=max_tokens_override or self.max_tokens,
        )
