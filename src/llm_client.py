"""
Anthropic API wrapper with retry logic, cost tracking, and structured logging.

Every API call is logged with step name, model, token counts, cost, and duration.

Copied from Engage Together POC -- shared infrastructure.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

import anthropic
from rich.console import Console

console = Console()


@dataclass
class APICallRecord:
    """Record of a single API call."""
    step_name: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    duration_seconds: float
    success: bool
    error: Optional[str] = None


@dataclass
class CostTracker:
    """Aggregates cost across all API calls in a pipeline run."""
    calls: list[APICallRecord] = field(default_factory=list)

    # Default cost rates (USD per million tokens)
    _rates: dict[str, dict[str, float]] = field(default_factory=lambda: {
        "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
        "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
    })

    def set_rates(self, rates: dict[str, dict[str, float]]) -> None:
        """Update cost rates from settings.yaml."""
        for model, model_rates in rates.items():
            self._rates[model] = {
                "input": model_rates.get("input_per_million", 3.00),
                "output": model_rates.get("output_per_million", 15.00),
            }

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD for a single API call."""
        rates = self._rates.get(model, {"input": 3.00, "output": 15.00})
        return (
            (input_tokens / 1_000_000) * rates["input"]
            + (output_tokens / 1_000_000) * rates["output"]
        )

    def record(self, call: APICallRecord) -> None:
        self.calls.append(call)

    @property
    def total_cost(self) -> float:
        return sum(c.cost_usd for c in self.calls)

    @property
    def total_input_tokens(self) -> int:
        return sum(c.input_tokens for c in self.calls)

    @property
    def total_output_tokens(self) -> int:
        return sum(c.output_tokens for c in self.calls)

    def summary(self) -> dict:
        """Return a summary dict suitable for logging/output."""
        by_step: dict[str, dict] = {}
        for c in self.calls:
            if c.step_name not in by_step:
                by_step[c.step_name] = {
                    "calls": 0, "input_tokens": 0, "output_tokens": 0,
                    "cost_usd": 0.0, "duration_seconds": 0.0,
                }
            s = by_step[c.step_name]
            s["calls"] += 1
            s["input_tokens"] += c.input_tokens
            s["output_tokens"] += c.output_tokens
            s["cost_usd"] += c.cost_usd
            s["duration_seconds"] += c.duration_seconds

        return {
            "total_cost_usd": round(self.total_cost, 4),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_calls": len(self.calls),
            "by_step": {k: {kk: round(vv, 4) if isinstance(vv, float) else vv
                            for kk, vv in v.items()}
                        for k, v in by_step.items()},
        }


class LLMClient:
    """Wrapper around the Anthropic API with retry and cost tracking."""

    def __init__(
        self,
        api_key: str,
        cost_tracker: Optional[CostTracker] = None,
        max_retries: int = 3,
        retry_delay: float = 5.0,
    ):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.cost_tracker = cost_tracker or CostTracker()
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def call(
        self,
        step_name: str,
        system_prompt: str,
        user_prompt: str,
        model: str = "claude-sonnet-4-5-20250929",
        temperature: float = 0.3,
        max_tokens: int = 4000,
    ) -> str:
        """
        Make an API call with retry logic and cost tracking.

        Returns the text content of the response.
        Raises on unrecoverable errors after retries.
        """
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            start = time.time()
            try:
                response = self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                duration = time.time() - start
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                cost = self.cost_tracker.calculate_cost(model, input_tokens, output_tokens)

                record = APICallRecord(
                    step_name=step_name,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost,
                    duration_seconds=duration,
                    success=True,
                )
                self.cost_tracker.record(record)

                console.print(
                    f"  [green]API call[/green] {step_name} | "
                    f"{model} | {input_tokens:,}+{output_tokens:,} tokens | "
                    f"${cost:.4f} | {duration:.1f}s"
                )

                # Extract text from response
                text_parts = [
                    block.text for block in response.content
                    if hasattr(block, "text")
                ]
                return "\n".join(text_parts)

            except anthropic.RateLimitError as e:
                duration = time.time() - start
                last_error = e
                self.cost_tracker.record(APICallRecord(
                    step_name=step_name, model=model,
                    input_tokens=0, output_tokens=0, cost_usd=0.0,
                    duration_seconds=duration, success=False,
                    error=f"Rate limited (attempt {attempt})",
                ))
                wait = self.retry_delay * attempt
                console.print(
                    f"  [yellow]Rate limited[/yellow] {step_name} | "
                    f"attempt {attempt}/{self.max_retries} | waiting {wait:.0f}s"
                )
                time.sleep(wait)

            except anthropic.APIStatusError as e:
                duration = time.time() - start
                last_error = e
                self.cost_tracker.record(APICallRecord(
                    step_name=step_name, model=model,
                    input_tokens=0, output_tokens=0, cost_usd=0.0,
                    duration_seconds=duration, success=False,
                    error=f"API error {e.status_code}: {e.message}",
                ))
                if e.status_code >= 500:
                    wait = self.retry_delay * attempt
                    console.print(
                        f"  [yellow]Server error[/yellow] {step_name} | "
                        f"{e.status_code} | attempt {attempt}/{self.max_retries}"
                    )
                    time.sleep(wait)
                else:
                    raise

        raise RuntimeError(
            f"API call failed after {self.max_retries} attempts for {step_name}: {last_error}"
        )
