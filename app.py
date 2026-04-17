"""
Grant Writer -- Streamlit UI

AI-powered grant writing tool for Altus Solutions.
Upload an RFP, answer intake questions, and generate a complete grant application
draft with compliance checking and trauma-informed language guardrails.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.database import init_db, seed_altus_org, get_org, list_orgs, get_guardrails
from src.pipeline import GrantPipeline, STEP_NAMES, ANALYZE_STEPS, GENERATE_STEPS
from src.utils.pdf_parser import extract_document, format_tables_as_markdown
from src.utils.language_guard import scan_text
from src.utils.compliance_checker import parse_compliance_checklist, check_draft_compliance
from src.utils.docx_export import markdown_to_docx

load_dotenv(Path(__file__).parent / ".env", override=True)

# --- Page Config ---
st.set_page_config(
    page_title="AltusNow Grant Writer",
    page_icon=":page_facing_up:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Altus Brand CSS ---
BRAND_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;500;600;700&display=swap');

:root {
    --teal: #19948A;
    --teal-dark: #147A72;
    --teal-light: #E8F5F3;
    --gold: #E2BC50;
    --deep-gold: #DBA71F;
    --gold-light: #FFF8EC;
    --slate: #575F65;
    --slate-light: #7A8289;
    --off-white: #F7F8F9;
    --light-gray: #E0E1E2;
    --success: #2D9F5C;
    --warning: #E8A317;
    --danger: #D94F4F;
}

html, body, [class*="css"] {
    font-family: 'Open Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

header[data-testid="stHeader"] {
    background: #FFFFFF;
    border-bottom: 2px solid var(--teal);
}

section[data-testid="stSidebar"] {
    background: #FFFFFF;
    border-right: 1px solid var(--light-gray);
}

.stButton > button[kind="primary"],
button[data-testid="stBaseButton-primary"] {
    background: var(--teal) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    padding: 0.6rem 1.5rem !important;
}

.stButton > button[kind="primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover {
    background: var(--teal-dark) !important;
}

.stButton > button:not([kind="primary"]),
button[data-testid="stBaseButton-secondary"] {
    border: 1px solid var(--light-gray) !important;
    color: var(--slate) !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
}

.stDownloadButton > button {
    background: var(--teal) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
}

.stTabs [data-baseweb="tab"] {
    font-family: 'Open Sans', sans-serif;
    font-weight: 600;
    color: var(--slate-light);
}

.stTabs [aria-selected="true"] {
    color: var(--teal) !important;
    border-bottom: 3px solid var(--teal) !important;
}

[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid var(--light-gray);
    border-radius: 8px;
    padding: 16px;
}

[data-testid="stMetricLabel"] {
    color: var(--slate-light) !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    font-size: 0.75rem !important;
}

[data-testid="stMetricValue"] {
    color: var(--teal) !important;
    font-weight: 700 !important;
}

.stProgress > div > div {
    background: var(--teal) !important;
}

hr { border-color: var(--light-gray) !important; }
a { color: var(--teal) !important; }

.step-complete {
    background: #f0fdf4;
    border-left: 3px solid var(--success);
    padding: 8px 12px;
    border-radius: 0 6px 6px 0;
    margin-bottom: 4px;
    color: var(--success);
}

.step-active {
    background: var(--teal-light);
    border-left: 3px solid var(--teal);
    padding: 8px 12px;
    border-radius: 0 6px 6px 0;
    margin-bottom: 4px;
    font-weight: 600;
    color: var(--teal-dark);
}

.step-pending {
    background: var(--off-white);
    border-left: 3px solid var(--light-gray);
    padding: 8px 12px;
    border-radius: 0 6px 6px 0;
    margin-bottom: 4px;
    color: var(--slate-light);
}

.cost-badge {
    background: var(--teal-light);
    color: var(--teal-dark);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
    display: inline-block;
}

.guardrail-pass {
    background: #f0fdf4;
    color: var(--success);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
    display: inline-block;
}

.guardrail-fail {
    background: #fef2f2;
    color: var(--danger);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
    display: inline-block;
}

.question-card {
    background: #FFFFFF;
    border: 1px solid var(--light-gray);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
}

.question-critical {
    border-left: 3px solid var(--danger);
}

.question-recommended {
    border-left: 3px solid var(--gold);
}

.category-header {
    color: var(--teal);
    font-weight: 700;
    font-size: 1.1rem;
    margin-top: 24px;
    margin-bottom: 8px;
    padding-bottom: 4px;
    border-bottom: 2px solid var(--teal-light);
}
</style>
"""

# --- Constants ---
PROJECT_DIR = Path(__file__).parent
CONFIG_DIR = PROJECT_DIR / "config"
OUTPUT_DIR = PROJECT_DIR / "output"
DATA_DIR = PROJECT_DIR / "data"
VPI_DIR = DATA_DIR / "vpi"

STEP_LABELS = {
    "rfp_ingestion": "RFP Analysis",
    "compliance_extraction": "Compliance Checklist",
    "intake_questionnaire": "Intake Questions",
    "org_context_assembly": "Org Context",
    "vpi_integration": "VPI Data Integration",
    "needs_statement": "Needs Statement",
    "program_design": "Program Design & Budget",
    "narrative_assembly": "Narrative Assembly",
    "quality_review": "Quality Review",
}


def initialize():
    """Initialize database and session state."""
    init_db()
    seed_altus_org()

    defaults = {
        "pipeline": None,
        "analysis_result": None,
        "pipeline_result": None,
        "extracted_doc": None,
        "intake_answers": {},
        "edited_sections": {},
        "completed_steps": [],
        "current_step": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def get_api_key() -> str:
    """Get API key from environment, secrets, or user input."""
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        try:
            key = st.secrets.get("ANTHROPIC_API_KEY", "")
        except Exception:
            key = ""
    return key


def render_sidebar():
    """Render the branded sidebar."""
    with st.sidebar:
        st.markdown(
            '<h1 style="margin-bottom: 0; font-size: 1.5rem;">AltusNow</h1>'
            '<p style="color: #19948A; font-weight: 600; font-size: 0.95rem; margin-top: -4px;">'
            'Grant Writer</p>',
            unsafe_allow_html=True,
        )
        st.caption("AI-powered grant applications with trauma-informed language guardrails")

        st.divider()

        # API key
        api_key = get_api_key()
        if not api_key:
            api_key = st.text_input(
                "Anthropic API Key",
                type="password",
                help="Required for AI generation.",
            )

        st.divider()

        # Organization selector
        orgs = list_orgs()
        org_names = [o["name"] for o in orgs]
        selected_org_name = st.selectbox(
            "Applicant Organization",
            org_names,
            index=0 if org_names else None,
        )
        selected_org = None
        if selected_org_name:
            org_match = [o for o in orgs if o["name"] == selected_org_name]
            if org_match:
                selected_org = get_org(org_match[0]["id"])

        st.divider()

        # Cost tracking
        total_cost = 0
        if st.session_state.analysis_result:
            total_cost += st.session_state.analysis_result.get("cost_summary", {}).get("total_cost_usd", 0)
        if st.session_state.pipeline_result:
            total_cost = st.session_state.pipeline_result.get("cost_summary", {}).get("total_cost_usd", 0)

        if total_cost > 0:
            st.markdown(
                f'<div class="cost-badge">${total_cost:.2f} total cost</div>',
                unsafe_allow_html=True,
            )

        # Language scan badge
        if st.session_state.pipeline_result:
            lang = st.session_state.pipeline_result.get("language_scan", {})
            if lang.get("passed"):
                st.markdown(
                    '<div class="guardrail-pass">Language: PASSED</div>',
                    unsafe_allow_html=True,
                )
            elif lang:
                st.markdown(
                    '<div class="guardrail-fail">Language: REVIEW</div>',
                    unsafe_allow_html=True,
                )

    return api_key, selected_org


def render_upload_tab():
    """Tab 1: Upload RFP."""
    st.header("Upload RFP Document")
    st.markdown(
        '<p style="color: #7A8289;">Upload a Request for Proposals. '
        'The system will parse it and generate targeted intake questions.</p>',
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "Upload RFP (PDF or DOCX)",
        type=["pdf", "docx"],
        help="Supports federal NOFOs, solicitations, and RFP documents",
    )

    col1, col2 = st.columns(2)
    with col1:
        target_state = st.text_input(
            "Target State",
            placeholder="e.g., Alabama, Tennessee",
            help="State for VPI data integration",
        )
    with col2:
        vpi_file = st.file_uploader(
            "VPI Data (optional)",
            type=["json", "csv"],
            help="Engage Together VPI JSON for county-level data",
        )

    if uploaded_file:
        with st.spinner("Extracting document..."):
            suffix = Path(uploaded_file.name).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = Path(tmp.name)

            try:
                extracted = extract_document(tmp_path)
                st.session_state.extracted_doc = extracted

                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Pages", extracted.page_count)
                col_b.metric("Words", f"{extracted.word_count:,}")
                col_c.metric("Tables", len(extracted.tables))

                with st.expander("Document Preview", expanded=False):
                    st.text(extracted.full_text[:3000] + "\n\n[... truncated ...]")
            finally:
                tmp_path.unlink(missing_ok=True)

    return uploaded_file, target_state, vpi_file


def render_intake_tab(api_key: str, selected_org: dict, uploaded_file, target_state: str, vpi_file):
    """Tab 2: Analyze RFP and present intake questions."""
    st.header("Intake Questions")

    if not st.session_state.extracted_doc:
        st.info("Upload an RFP document in the first tab.")
        return

    if not api_key:
        st.warning("Enter your Anthropic API key in the sidebar.")
        return

    extracted = st.session_state.extracted_doc

    # VPI data
    vpi_data = None
    if vpi_file:
        try:
            if vpi_file.name.endswith(".json"):
                vpi_data = json.loads(vpi_file.getvalue())
        except (json.JSONDecodeError, AttributeError):
            pass

    # Step 1: Analyze RFP (runs steps 1-2 + question generation)
    if not st.session_state.analysis_result:
        st.markdown(
            '<p style="color: #7A8289;">Click below to analyze the RFP. '
            'This runs AI parsing and compliance extraction (~$0.35, ~5 min), '
            'then generates targeted questions for your team.</p>',
            unsafe_allow_html=True,
        )

        if st.button("Analyze RFP & Generate Questions", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            status = st.empty()

            def on_step(step_name: str, output: str):
                label = STEP_LABELS.get(step_name, step_name)
                if step_name == "rfp_ingestion":
                    progress_bar.progress(0.33)
                    status.write(f"Completed: {label}")
                elif step_name == "compliance_extraction":
                    progress_bar.progress(0.66)
                    status.write(f"Completed: {label}")
                elif step_name == "intake_questionnaire":
                    progress_bar.progress(1.0)
                    status.write(f"Completed: {label}")

            pipeline = GrantPipeline(
                api_key=api_key,
                config_dir=CONFIG_DIR,
                output_dir=OUTPUT_DIR,
            )
            st.session_state.pipeline = pipeline

            result = pipeline.analyze(
                rfp_text=extracted.full_text,
                org_profile=selected_org or {"name": "Altus Solutions"},
                file_name=uploaded_file.name if uploaded_file else "rfp_document",
                page_count=extracted.page_count,
                word_count=extracted.word_count,
                tables_markdown=format_tables_as_markdown(extracted.tables),
                vpi_data=vpi_data,
                target_state=target_state,
                on_step_complete=on_step,
            )

            st.session_state.analysis_result = result
            cost = result["cost_summary"]["total_cost_usd"]
            st.success(f"Analysis complete. {len(result['questions'])} questions generated. Cost: ${cost:.2f}")
            st.rerun()

    # Step 2: Display questions for user to answer
    if st.session_state.analysis_result:
        result = st.session_state.analysis_result
        questions = result.get("questions", [])

        if not questions:
            st.warning("No questions were generated. You can proceed directly to generation.")
            return

        # Show RFP summary
        with st.expander("RFP Summary (from analysis)", expanded=False):
            st.markdown(result["step_outputs"].get("rfp_ingestion", "")[:3000])

        with st.expander("Compliance Checklist (from analysis)", expanded=False):
            st.markdown(result["step_outputs"].get("compliance_extraction", "")[:3000])

        st.divider()

        # Group questions by category
        categories = {}
        for q in questions:
            cat = q["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(q)

        critical_count = sum(1 for q in questions if q["priority"] == "critical")
        rec_count = len(questions) - critical_count
        st.markdown(
            f"**{len(questions)} questions** generated from your RFP: "
            f"**{critical_count} critical**, {rec_count} recommended. "
            f"Answer what you can -- the more you provide, the better the draft.",
        )

        st.write("")

        # Render questions by category
        for category, cat_questions in categories.items():
            st.markdown(
                f'<div class="category-header">{category}</div>',
                unsafe_allow_html=True,
            )

            for q in cat_questions:
                qid = q["id"]
                priority_tag = "CRITICAL" if q["priority"] == "critical" else "Recommended"
                priority_color = "#D94F4F" if q["priority"] == "critical" else "#E8A317"

                st.markdown(
                    f'<span style="color: {priority_color}; font-weight: 600; font-size: 0.75rem;">'
                    f'{priority_tag}</span>',
                    unsafe_allow_html=True,
                )

                # Get existing answer or default
                existing = st.session_state.intake_answers.get(qid, q.get("default", ""))

                if q["input_type"] == "textarea":
                    answer = st.text_area(
                        q["question"],
                        value=existing,
                        key=f"intake_{qid}",
                        help=q.get("why", ""),
                        height=120,
                    )
                elif q["input_type"] == "number":
                    answer = st.text_input(
                        q["question"],
                        value=str(existing) if existing else "",
                        key=f"intake_{qid}",
                        help=q.get("why", ""),
                    )
                elif q["input_type"] == "select" and q.get("options"):
                    options = [""] + q["options"]
                    idx = options.index(existing) if existing in options else 0
                    answer = st.selectbox(
                        q["question"],
                        options=options,
                        index=idx,
                        key=f"intake_{qid}",
                        help=q.get("why", ""),
                    )
                else:
                    answer = st.text_input(
                        q["question"],
                        value=existing,
                        key=f"intake_{qid}",
                        help=q.get("why", ""),
                    )

                st.session_state.intake_answers[qid] = answer

        # Summary of answered questions
        st.divider()
        answered = sum(1 for v in st.session_state.intake_answers.values() if v and str(v).strip())
        st.markdown(
            f"**{answered} of {len(questions)} questions answered.** "
            f"Proceed to Generate Draft when ready."
        )


def render_generate_tab(api_key: str, selected_org: dict, target_state: str, vpi_file):
    """Tab 3: Generate the draft using intake answers."""
    st.header("Generate Grant Application")

    if not st.session_state.analysis_result:
        st.info("Analyze the RFP and answer intake questions first.")
        return

    if not api_key:
        st.warning("Enter your Anthropic API key in the sidebar.")
        return

    # Show intake answer summary
    answers = st.session_state.intake_answers
    answered = sum(1 for v in answers.values() if v and str(v).strip())
    total_q = len(st.session_state.analysis_result.get("questions", []))

    if answered == 0:
        st.warning(
            "You haven't answered any intake questions. The draft will use assumptions "
            "and may contain placeholders. Go back to the Intake tab to improve results."
        )
    else:
        st.success(f"{answered} of {total_q} intake questions answered.")

    with st.expander(f"Your Answers ({answered} provided)", expanded=False):
        for qid, answer in answers.items():
            if answer and str(answer).strip():
                label = qid.replace("_", " ").title()
                st.write(f"**{label}:** {answer}")

    # Pipeline settings
    with st.expander("Pipeline Settings", expanded=False):
        max_cost = st.slider("Max Cost per Run ($)", 1.0, 25.0, 10.0, 0.5)
        use_opus = st.checkbox(
            "Use Opus for Narrative Assembly",
            value=False,
            help="Higher quality but ~5x more expensive for that step",
        )

    # Generate button
    if st.button("Generate Grant Application", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_container = st.container()
        step_statuses = {}

        def on_step(step_name: str, output: str):
            gen_steps = GENERATE_STEPS
            if step_name in gen_steps:
                idx = gen_steps.index(step_name)
                progress = (idx + 1) / len(gen_steps)
                progress_bar.progress(progress)
                step_statuses[step_name] = len(output.split())
                with status_container:
                    for sn in gen_steps:
                        label = STEP_LABELS.get(sn, sn)
                        if sn in step_statuses:
                            st.markdown(
                                f'<div class="step-complete">{label} -- {step_statuses[sn]:,} words</div>',
                                unsafe_allow_html=True,
                            )

        pipeline = st.session_state.pipeline
        if pipeline is None:
            st.error("Pipeline not initialized. Re-analyze the RFP.")
            return

        # Apply settings overrides
        if use_opus:
            import yaml
            pipeline.settings["step_overrides"] = pipeline.settings.get("step_overrides", {})
            pipeline.settings["step_overrides"]["narrative_assembly"] = {
                "model": "claude-opus-4-20250514"
            }
        pipeline.settings["max_total_cost_usd"] = max_cost

        try:
            context = st.session_state.analysis_result["context"]

            result = pipeline.generate(
                context=context,
                intake_answers=answers,
                on_step_complete=on_step,
            )

            st.session_state.pipeline_result = result
            progress_bar.progress(1.0)

            total_cost = result["cost_summary"]["total_cost_usd"]
            st.success(f"Grant application generated. Total cost: ${total_cost:.2f}")

            lang = result.get("language_scan", {})
            if lang.get("passed"):
                st.markdown(
                    '<div class="guardrail-pass">Language Guardrails: PASSED</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="guardrail-fail">Language Guardrails: REVIEW -- {lang.get("summary", "")}</div>',
                    unsafe_allow_html=True,
                )

        except Exception as e:
            st.error(f"Pipeline error: {e}")
            raise


def render_review_tab():
    """Tab 4: Review and edit sections."""
    st.header("Review & Edit Sections")

    if not st.session_state.pipeline_result:
        st.info("Generate a draft first.")
        return

    result = st.session_state.pipeline_result
    step_outputs = result.get("step_outputs", {})

    if result.get("scorecard"):
        with st.expander("Quality Scorecard", expanded=True):
            st.markdown(result["scorecard"])

    for step_name in ["needs_statement", "program_design", "narrative_assembly"]:
        if step_name not in step_outputs:
            continue

        label = STEP_LABELS.get(step_name, step_name)
        content = step_outputs[step_name]
        word_count = len(content.split())

        with st.expander(f"{label} ({word_count:,} words)", expanded=False):
            edited = st.text_area(
                f"Edit {label}",
                value=st.session_state.edited_sections.get(step_name, content),
                height=400,
                key=f"edit_{step_name}",
                label_visibility="collapsed",
            )
            st.session_state.edited_sections[step_name] = edited

            scan = scan_text(edited)
            if scan.passed and scan.context_dependent_count == 0:
                st.markdown(
                    '<div class="guardrail-pass">Language check: PASSED</div>',
                    unsafe_allow_html=True,
                )
            elif not scan.passed:
                st.markdown(
                    '<div class="guardrail-fail">Language check: FAILED</div>',
                    unsafe_allow_html=True,
                )
                st.code(scan.details(), language=None)
            else:
                st.warning(scan.summary())

    compliance_text = step_outputs.get("compliance_extraction", "")
    if compliance_text:
        with st.expander("Compliance Checklist", expanded=False):
            items = parse_compliance_checklist(compliance_text)
            final_text = st.session_state.edited_sections.get(
                "narrative_assembly",
                step_outputs.get("narrative_assembly", ""),
            )
            compliance_result = check_draft_compliance(final_text, items)
            st.metric("Compliance Score", compliance_result.score_pct)

            for item in compliance_result.items:
                icon = "+" if item["is_met"] else "-"
                st.write(f"{icon} {item['requirement_text'][:100]}")


def render_export_tab(selected_org: dict):
    """Tab 5: Export the grant application."""
    st.header("Export Grant Application")

    if not st.session_state.pipeline_result:
        st.info("Generate a draft first.")
        return

    result = st.session_state.pipeline_result

    final_text = st.session_state.edited_sections.get(
        "narrative_assembly",
        result.get("final_report", ""),
    )

    scan = scan_text(final_text)
    if not scan.passed:
        st.markdown(
            f'<div class="guardrail-fail">'
            f'Export blocked: {scan.prohibited_count} prohibited term(s). '
            f'Fix in Review tab.</div>',
            unsafe_allow_html=True,
        )
        st.code(scan.details(), language=None)
        return

    st.markdown(
        '<div class="guardrail-pass">Language guardrails: PASSED -- ready for export</div>',
        unsafe_allow_html=True,
    )
    st.write("")

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            "Download Markdown",
            data=final_text,
            file_name=f"grant_application_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with col2:
        if st.button("Generate DOCX", use_container_width=True):
            with st.spinner("Creating Word document..."):
                docx_path = OUTPUT_DIR / f"Grant_Application_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
                markdown_to_docx(
                    markdown_text=final_text,
                    output_path=docx_path,
                    title="Grant Application",
                    funder="",
                    applicant=selected_org.get("name", "Altus Solutions") if selected_org else "Altus Solutions",
                )

                with open(docx_path, "rb") as f:
                    st.download_button(
                        "Download DOCX",
                        data=f.read(),
                        file_name=docx_path.name,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                    )
                st.success(f"DOCX created: {docx_path.name}")

    # Cost summary
    st.divider()
    st.subheader("Run Summary")
    cost = result.get("cost_summary", {})
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Cost", f"${cost.get('total_cost_usd', 0):.2f}")
    col2.metric("Input Tokens", f"{cost.get('total_input_tokens', 0):,}")
    col3.metric("Output Tokens", f"{cost.get('total_output_tokens', 0):,}")

    if cost.get("by_step"):
        with st.expander("Cost by Step"):
            for step_name, step_cost in cost["by_step"].items():
                label = STEP_LABELS.get(step_name, step_name)
                st.write(
                    f"**{label}**: ${step_cost['cost_usd']:.4f} "
                    f"({step_cost['input_tokens']:,} + {step_cost['output_tokens']:,} tokens)"
                )


def main():
    initialize()
    st.markdown(BRAND_CSS, unsafe_allow_html=True)

    api_key, selected_org = render_sidebar()

    tab_upload, tab_intake, tab_generate, tab_review, tab_export = st.tabs([
        "1. Upload RFP",
        "2. Intake Questions",
        "3. Generate Draft",
        "4. Review & Edit",
        "5. Export",
    ])

    with tab_upload:
        uploaded_file, target_state, vpi_file = render_upload_tab()

    with tab_intake:
        render_intake_tab(api_key, selected_org, uploaded_file, target_state, vpi_file)

    with tab_generate:
        render_generate_tab(api_key, selected_org, target_state, vpi_file)

    with tab_review:
        render_review_tab()

    with tab_export:
        render_export_tab(selected_org)


if __name__ == "__main__":
    main()
