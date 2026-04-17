#!/usr/bin/env python3
"""
Run the grant writer pipeline for the OVC ECM Task Force solicitation.

Context:
- RFP: O-OVC-2025-172524 (ECM Task Force to Combat Human Trafficking)
- Category 3: Statewide, previously OJP-funded
- Victim Service Provider lead: The WellHouse
- Law Enforcement lead: Alabama Attorney General's Office
- Altus Solutions is NOT a named partner -- referenced only as product/data source
- The Alabama Human Trafficking Alliance has operated ~6 years under ECM model
- Previously OJP-funded, did not receive funding in the prior cycle
- Covers all 67 Alabama counties
- Altus completed Engage Together Phase 1 assessment; will be contracted post-award for Phase 2
"""

import json
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from dotenv import load_dotenv

from src.pipeline import GrantPipeline
from src.utils.pdf_parser import extract_document, format_tables_as_markdown

load_dotenv(PROJECT_DIR / ".env", override=True)


def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: Set ANTHROPIC_API_KEY in .env")
        sys.exit(1)

    # --- Org Profile: The WellHouse (Victim Service Provider Lead) ---
    org_profile = {
        "name": "The WellHouse",
        "org_type": "501(c)(3) Nonprofit -- Victim Service Provider",
        "website": "thewellhouse.org",
        "mission_statement": (
            "The WellHouse provides rescue, restoration, and empowerment to survivors "
            "of human trafficking through safe housing, comprehensive services, and "
            "advocacy. As the victim service provider co-lead of the Alabama Human "
            "Trafficking Alliance, The WellHouse coordinates statewide survivor services "
            "across all 67 Alabama counties."
        ),
        "product_catalog_json": json.dumps({
            "NOTE": "The WellHouse is the victim service provider applicant. Technology "
                    "platforms referenced below are third-party tools used by the Alliance, "
                    "NOT products of The WellHouse. Do NOT name Altus Solutions anywhere in "
                    "the application. Reference these tools by product name only.",
            "technology_platforms_used_by_alliance": {
                "Engage Together": {
                    "description": "Community vulnerability assessment platform analyzing "
                                   "37 indicators across 14 validated data sources to produce "
                                   "county-level Vulnerability Profile Index scores",
                    "status": "Phase 1 statewide assessment completed 2026",
                    "reference_as": "Engage Together Alabama Statewide Assessment 2026",
                    "role_in_grant": "Data source for needs statement evidence; will be used "
                                    "for ongoing vulnerability monitoring in Phase 2"
                },
                "Justice U": {
                    "description": "CEU-eligible online training platform for anti-trafficking "
                                   "professional development",
                    "reference_as": "statewide training portal",
                    "role_in_grant": "Will be deployed as the Alliance's statewide training "
                                    "platform for multidisciplinary professional development"
                },
                "Just in Time (JIT)": {
                    "description": "White-labeled mobile application for trafficking screening, "
                                   "identification, and case management",
                    "reference_as": "mobile screening and case management application",
                    "role_in_grant": "Will be customized with Alabama-specific protocols and "
                                    "service directories for frontline professionals"
                }
            },
            "alliance_context": {
                "name": "Alabama Human Trafficking Alliance",
                "years_operating": "Nearly 6 years using the Enhanced Collaborative Model",
                "prior_ovc_funding": "Previously funded by OJP ECM program. Did NOT receive "
                                     "funding in the most recent prior cycle. Alliance executed "
                                     "a sustainability plan to maintain operations during the "
                                     "funding gap.",
                "geographic_scope": "Statewide -- all 67 Alabama counties",
                "category": "Category 3: Enhanced Support for Statewide Task Forces "
                            "(Previously OJP-funded)",
                "co_lead_law_enforcement": "Alabama Attorney General's Office",
                "co_lead_victim_service_provider": "The WellHouse",
                "task_force_structure": (
                    "Co-led by the Alabama Attorney General's Office (law enforcement) and "
                    "The WellHouse (victim services). The Alliance includes state agencies, "
                    "law enforcement at local/state/federal levels, prosecutors, victim "
                    "service providers, survivor leaders, healthcare providers, educators, "
                    "and community organizations across all 67 counties."
                ),
                "sustainability_during_gap": (
                    "When OJP ECM funding lapsed, the Alliance maintained operations through "
                    "state resources, partner contributions, and institutional commitment. "
                    "This demonstrates the Alliance's sustainability and the state's investment "
                    "in anti-trafficking coordination."
                ),
                "legislative_work": (
                    "The Alliance has contributed to Alabama's anti-trafficking legislative "
                    "framework. Reference as 'ETP Legislative Report' where relevant."
                )
            },
            "application_instructions": {
                "CRITICAL_1": "This is the VICTIM SERVICE PROVIDER application. The Alabama "
                              "Attorney General's Office submits a separate but coordinated "
                              "LAW ENFORCEMENT application.",
                "CRITICAL_2": "Do NOT name Altus Solutions as a partner, subrecipient, or "
                              "subcontractor. Reference technology platforms by product name "
                              "only (Engage Together, Justice U, Just in Time).",
                "CRITICAL_3": "Category 3 previously funded statewide task forces should follow "
                              "Category 2 deliverables per the NOFO.",
                "CRITICAL_4": "Award ceiling is $1,000,000 per applicant ($2,000,000 per task "
                              "force). Performance period is 36 months.",
                "CRITICAL_5": "25% match required. Match is based on total project costs.",
                "CRITICAL_6": "Page limit for Proposal Narrative is 25 pages, double-spaced, "
                              "12-point font, 1-inch margins, numbered pages.",
                "CRITICAL_7": "Abstract must be 2,000 characters or fewer, in paragraph form "
                              "without bullets or tables, written in third person.",
                "CRITICAL_8": "The Proposal Narrative must include exactly four sections: "
                              "1) Description of the Need, 2) Project Goals and Objectives, "
                              "3) Project Design and Implementation, 4) Capabilities and "
                              "Competencies."
            }
        })
    }

    # --- Extract RFP ---
    rfp_path = PROJECT_DIR / "data" / "sample_rfps" / "OVC-2025-172524_ECM.pdf"
    if not rfp_path.exists():
        print(f"Error: RFP not found at {rfp_path}")
        sys.exit(1)

    print(f"Extracting: {rfp_path}")
    extracted = extract_document(rfp_path)
    print(f"  {extracted.page_count} pages, {extracted.word_count:,} words, {len(extracted.tables)} tables")

    # --- VPI Data ---
    # Load VPI data from previous run output (Alabama assessment already completed)
    vpi_path = PROJECT_DIR / "output" / "run_20260410_082716" / "04_vpi_integration.md"
    vpi_data = None
    if vpi_path.exists():
        with open(vpi_path) as f:
            vpi_text = f.read()
        # Pass as dict with the pre-processed text
        vpi_data = {
            "state": "Alabama",
            "pre_processed_summary": vpi_text,
            "source": "Engage Together Alabama Statewide Assessment 2026"
        }
        print(f"Loaded VPI data from previous run ({len(vpi_text):,} chars)")

    # --- Run Pipeline ---
    pipeline = GrantPipeline(
        api_key=api_key,
        config_dir=PROJECT_DIR / "config",
        output_dir=PROJECT_DIR / "output",
    )

    print("\n" + "=" * 60)
    print("RUNNING GRANT WRITER PIPELINE")
    print(f"RFP: OVC-2025-172524 (ECM Task Force)")
    print(f"Category: 3 (Statewide, Previously OJP-funded)")
    print(f"Applicant: The WellHouse (Victim Service Provider)")
    print(f"Co-Lead: Alabama Attorney General's Office (Law Enforcement)")
    print("=" * 60 + "\n")

    result = pipeline.run(
        rfp_text=extracted.full_text,
        org_profile=org_profile,
        file_name="OVC-2025-172524_ECM.pdf",
        page_count=extracted.page_count,
        word_count=extracted.word_count,
        tables_markdown=format_tables_as_markdown(extracted.tables),
        vpi_data=vpi_data,
        target_state="Alabama",
    )

    print(f"\nResults in: {result['run_dir']}")
    print(f"Total cost: ${result['cost_summary']['total_cost_usd']:.4f}")


if __name__ == "__main__":
    main()
