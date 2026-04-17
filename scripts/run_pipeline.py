#!/usr/bin/env python3
"""
CLI runner for the grant writer pipeline.

Usage:
    python scripts/run_pipeline.py --rfp path/to/rfp.pdf --state Alabama
    python scripts/run_pipeline.py --rfp path/to/rfp.pdf --state Tennessee --vpi data/vpi/tennessee_vpi.json
"""

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from dotenv import load_dotenv

from src.database import init_db, seed_altus_org, get_org
from src.pipeline import GrantPipeline
from src.utils.pdf_parser import extract_document, format_tables_as_markdown
from src.utils.docx_export import markdown_to_docx


def main():
    load_dotenv(PROJECT_DIR / ".env", override=True)

    parser = argparse.ArgumentParser(description="Run the grant writer pipeline")
    parser.add_argument("--rfp", required=True, help="Path to the RFP document (PDF or DOCX)")
    parser.add_argument("--state", default="", help="Target state for VPI data")
    parser.add_argument("--vpi", default="", help="Path to VPI JSON data file")
    parser.add_argument("--org-id", type=int, default=1, help="Organization ID (default: 1 = Altus)")
    parser.add_argument("--max-cost", type=float, default=10.0, help="Max cost per run in USD")
    parser.add_argument("--start-from", default=None, help="Step to start from")
    parser.add_argument("--stop-after", default=None, help="Step to stop after")
    parser.add_argument("--no-docx", action="store_true", help="Skip DOCX export")
    args = parser.parse_args()

    # API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: Set ANTHROPIC_API_KEY in .env or environment")
        sys.exit(1)

    # Initialize database
    init_db()
    seed_altus_org()

    # Load org profile
    org = get_org(args.org_id)
    if not org:
        print(f"Error: Organization ID {args.org_id} not found")
        sys.exit(1)

    # Extract RFP document
    rfp_path = Path(args.rfp)
    if not rfp_path.exists():
        print(f"Error: RFP file not found: {rfp_path}")
        sys.exit(1)

    print(f"Extracting: {rfp_path}")
    extracted = extract_document(rfp_path)
    print(f"  {extracted.page_count} pages, {extracted.word_count:,} words, {len(extracted.tables)} tables")

    # Load VPI data
    vpi_data = None
    if args.vpi:
        vpi_path = Path(args.vpi)
        if vpi_path.exists():
            with open(vpi_path) as f:
                vpi_data = json.load(f)
            print(f"Loaded VPI data from {vpi_path}")

    # Run pipeline
    project_dir = Path(__file__).parent.parent
    pipeline = GrantPipeline(
        api_key=api_key,
        config_dir=project_dir / "config",
        output_dir=project_dir / "output",
    )

    result = pipeline.run(
        rfp_text=extracted.full_text,
        org_profile=org,
        file_name=rfp_path.name,
        page_count=extracted.page_count,
        word_count=extracted.word_count,
        tables_markdown=format_tables_as_markdown(extracted.tables),
        vpi_data=vpi_data,
        target_state=args.state,
        start_from=args.start_from,
        stop_after=args.stop_after,
    )

    # DOCX export
    if not args.no_docx:
        docx_path = Path(result["run_dir"]) / "Grant_Application.docx"
        markdown_to_docx(
            markdown_text=result["final_report"],
            output_path=docx_path,
            title="Grant Application",
            applicant=org.get("name", "Altus Solutions"),
        )
        print(f"\nDOCX exported: {docx_path}")

    print(f"\nResults in: {result['run_dir']}")


if __name__ == "__main__":
    main()
