"""
Grant writing pipeline orchestrator.

Runs the 8-step grant writing pipeline from RFP ingestion to quality review.

Adapted from Engage Together POC -- same patterns for step registry, cost tracking,
budget enforcement, and intermediate output saving.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml
from rich.console import Console
from rich.panel import Panel

from src.llm_client import CostTracker, LLMClient
from src.steps.rfp_ingestion import RFPIngestionStep
from src.steps.compliance_extraction import ComplianceExtractionStep
from src.steps.org_context_assembly import OrgContextAssemblyStep
from src.steps.vpi_integration import VPIIntegrationStep
from src.steps.needs_statement import NeedsStatementStep
from src.steps.program_design import ProgramDesignStep
from src.steps.narrative_assembly import NarrativeAssemblyStep
from src.steps.quality_review import QualityReviewStep
from src.utils.language_guard import scan_text, auto_fix_prohibited

console = Console()

# Step registry -- order matters
STEP_REGISTRY = [
    ("rfp_ingestion", RFPIngestionStep),
    ("compliance_extraction", ComplianceExtractionStep),
    ("org_context_assembly", OrgContextAssemblyStep),
    ("vpi_integration", VPIIntegrationStep),
    ("needs_statement", NeedsStatementStep),
    ("program_design", ProgramDesignStep),
    ("narrative_assembly", NarrativeAssemblyStep),
    ("quality_review", QualityReviewStep),
]

STEP_NAMES = [name for name, _ in STEP_REGISTRY]


class GrantPipeline:
    """Orchestrates the multi-step grant writing pipeline."""

    def __init__(
        self,
        api_key: str,
        config_dir: Path,
        output_dir: Path,
        settings: Optional[dict] = None,
    ):
        self.config_dir = config_dir
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load settings
        if settings is None:
            settings_path = config_dir / "settings.yaml"
            with open(settings_path) as f:
                settings = yaml.safe_load(f)
        self.settings = settings

        # Initialize cost tracker
        self.cost_tracker = CostTracker()
        if "model_costs" in settings:
            self.cost_tracker.set_rates(settings["model_costs"])

        # Initialize LLM client
        self.llm = LLMClient(
            api_key=api_key,
            cost_tracker=self.cost_tracker,
        )

        # Initialize all steps
        self.steps: dict[str, Any] = {}
        for name, step_class in STEP_REGISTRY:
            self.steps[name] = step_class(
                llm_client=self.llm,
                config_dir=config_dir,
            )

    def run(
        self,
        rfp_text: str,
        org_profile: dict,
        file_name: str = "rfp_document",
        page_count: int = 0,
        word_count: int = 0,
        tables_markdown: str = "",
        vpi_data: Optional[dict] = None,
        target_state: str = "",
        start_from: Optional[str] = None,
        stop_after: Optional[str] = None,
        save_intermediate: bool = True,
        on_step_complete: Optional[Any] = None,
    ) -> dict[str, Any]:
        """
        Run the grant writing pipeline.

        Args:
            rfp_text: Full extracted text of the RFP document.
            org_profile: Organization profile dict (from database).
            file_name: Original filename of the uploaded RFP.
            page_count: Number of pages in the RFP.
            word_count: Word count of the RFP.
            tables_markdown: Extracted tables in markdown format.
            vpi_data: VPI data dict for the target state (optional).
            target_state: Target state name for VPI lookup.
            start_from: Step name to start from (skips prior steps).
            stop_after: Step name to stop after (skips later steps).
            save_intermediate: Save each step's output to disk.
            on_step_complete: Callback(step_name, output) called after each step.

        Returns:
            Dict with final_report, step_outputs, cost_summary, scorecard.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = self.output_dir / f"run_{timestamp}"
        run_dir.mkdir(parents=True, exist_ok=True)

        # Build shared context
        context: dict[str, Any] = {
            # RFP data
            "rfp_text": rfp_text,
            "file_name": file_name,
            "page_count": page_count,
            "word_count": word_count,
            "tables_markdown": tables_markdown,
            # Organization
            "org_profile": org_profile,
            # VPI
            "vpi_data": vpi_data or {},
            "target_state": target_state,
            # Pipeline state
            "step_outputs": {},
            "previous_step_output": "",
        }

        # Determine step range
        start_idx = 0
        stop_idx = len(STEP_NAMES) - 1

        if start_from:
            if start_from not in STEP_NAMES:
                raise ValueError(f"Unknown step: {start_from}. Valid: {STEP_NAMES}")
            start_idx = STEP_NAMES.index(start_from)

        if stop_after:
            if stop_after not in STEP_NAMES:
                raise ValueError(f"Unknown step: {stop_after}. Valid: {STEP_NAMES}")
            stop_idx = STEP_NAMES.index(stop_after)

        # Skip VPI step if no VPI data provided
        skip_vpi = not vpi_data and not target_state

        max_cost = self.settings.get("max_total_cost_usd", 10.00)
        delay = self.settings.get("rate_limit_delay_seconds", 3)

        console.print(Panel(
            f"[bold]Grant Writer Pipeline[/bold]\n"
            f"RFP: {file_name}\n"
            f"Organization: {org_profile.get('name', 'Unknown')}\n"
            f"Target State: {target_state or 'Not specified'}\n"
            f"Steps: {STEP_NAMES[start_idx]} -> {STEP_NAMES[stop_idx]}\n"
            f"Budget: ${max_cost:.2f}",
            title="Pipeline Start",
        ))

        # Run each step in sequence
        for i in range(start_idx, stop_idx + 1):
            step_name = STEP_NAMES[i]

            # Skip VPI integration if no data
            if step_name == "vpi_integration" and skip_vpi:
                console.print(f"\n[dim]Skipping {step_name} (no VPI data provided)[/dim]")
                context["step_outputs"][step_name] = "VPI data not provided for this application."
                continue

            step = self.steps[step_name]

            # Check cost budget
            if self.cost_tracker.total_cost >= max_cost:
                console.print(
                    f"\n[red]Budget exceeded[/red] "
                    f"(${self.cost_tracker.total_cost:.2f} >= ${max_cost:.2f}). "
                    f"Stopping after {STEP_NAMES[i-1]}."
                )
                break

            console.print(f"\n[bold cyan]Step {i+1}/{stop_idx+1}: {step_name}[/bold cyan]")

            # Get per-step overrides from settings
            overrides = self.settings.get("step_overrides", {}).get(step_name, {})

            # Run the step
            start_time = time.time()
            output = step.run(
                context=context,
                model_override=overrides.get("model"),
                temperature_override=overrides.get("temperature"),
                max_tokens_override=overrides.get("max_tokens"),
            )
            elapsed = time.time() - start_time

            # Update context for next step
            context["step_outputs"][step_name] = output
            context["previous_step_output"] = output

            console.print(f"  [dim]{step_name} completed in {elapsed:.1f}s[/dim]")

            # Callback
            if on_step_complete:
                on_step_complete(step_name, output)

            # Save intermediate output
            if save_intermediate:
                out_path = run_dir / f"{i+1:02d}_{step_name}.md"
                with open(out_path, "w") as f:
                    f.write(output)

            # Rate limit delay between steps
            if i < stop_idx and delay > 0:
                time.sleep(delay)

        # --- Post-processing ---

        # Extract scorecard and final report from quality review
        qa_output = context["step_outputs"].get("quality_review", "")
        narrative_output = context["step_outputs"].get(
            "narrative_assembly",
            context.get("previous_step_output", ""),
        )

        scorecard = ""
        final_report = qa_output or narrative_output

        if qa_output and "===REVISED_DRAFT_START===" in qa_output:
            parts = qa_output.split("===REVISED_DRAFT_START===", 1)
            scorecard = parts[0].strip()
            final_report = parts[1].strip()
        elif qa_output:
            # Fallback split
            for marker in ["## Revised Draft", "# Revised Draft", "---\n# "]:
                if marker in qa_output:
                    idx = qa_output.index(marker)
                    scorecard = qa_output[:idx].strip()
                    final_report = qa_output[idx:].strip()
                    break

        # Run language guardrails scan on final report
        language_scan = scan_text(final_report)
        if not language_scan.passed:
            console.print(f"\n[yellow]Language scan: {language_scan.summary()}[/yellow]")
            final_report, fix_count = auto_fix_prohibited(final_report)
            if fix_count > 0:
                console.print(f"  [green]Auto-fixed {fix_count} prohibited term(s)[/green]")

        # Save final report
        report_path = run_dir / f"Grant_Application_{timestamp}.md"
        with open(report_path, "w") as f:
            f.write(final_report)

        # Save scorecard
        if scorecard:
            scorecard_path = run_dir / f"QA_Scorecard_{timestamp}.md"
            with open(scorecard_path, "w") as f:
                f.write(scorecard)

        # Save cost summary
        cost_summary = self.cost_tracker.summary()
        cost_path = run_dir / "cost_summary.json"
        with open(cost_path, "w") as f:
            json.dump(cost_summary, f, indent=2)

        console.print(Panel(
            f"[bold green]Pipeline Complete[/bold green]\n"
            f"Total cost: ${cost_summary['total_cost_usd']:.4f}\n"
            f"Total tokens: {cost_summary['total_input_tokens']:,} in + "
            f"{cost_summary['total_output_tokens']:,} out\n"
            f"Report: {report_path}\n"
            f"Language scan: {language_scan.summary()}",
            title="Results",
        ))

        return {
            "final_report": final_report,
            "report_path": str(report_path),
            "scorecard": scorecard,
            "step_outputs": context["step_outputs"],
            "cost_summary": cost_summary,
            "language_scan": {
                "passed": language_scan.passed,
                "summary": language_scan.summary(),
                "violations": [
                    {"term": v.term, "category": v.category, "line": v.line_number}
                    for v in language_scan.violations
                ],
            },
            "run_dir": str(run_dir),
        }
