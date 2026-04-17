"""
Grant Writer -- Streamlit UI

AI-powered grant writing tool for Altus Solutions.
Upload an RFP, provide VPI data, and generate a complete grant application draft
with compliance checking and trauma-informed language guardrails.
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
from src.pipeline import GrantPipeline, STEP_NAMES
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

/* Global font */
html, body, [class*="css"] {
    font-family: 'Open Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* Header bar */
header[data-testid="stHeader"] {
    background: #FFFFFF;
    border-bottom: 2px solid var(--teal);
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #FFFFFF;
    border-right: 1px solid var(--light-gray);
}

section[data-testid="stSidebar"] .stMarkdown h1 {
    color: var(--slate);
    font-weight: 700;
    letter-spacing: -0.01em;
}

/* Primary buttons */
.stButton > button[kind="primary"],
button[data-testid="stBaseButton-primary"] {
    background: var(--teal) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    padding: 0.6rem 1.5rem !important;
    transition: background 0.2s ease !important;
}

.stButton > button[kind="primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover {
    background: var(--teal-dark) !important;
}

/* Secondary buttons */
.stButton > button:not([kind="primary"]),
button[data-testid="stBaseButton-secondary"] {
    border: 1px solid var(--light-gray) !important;
    color: var(--slate) !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}

.stButton > button:not([kind="primary"]):hover,
button[data-testid="stBaseButton-secondary"]:hover {
    border-color: var(--teal) !important;
    color: var(--teal) !important;
}

/* Download buttons */
.stDownloadButton > button {
    background: var(--teal) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
}

.stDownloadButton > button:hover {
    background: var(--teal-dark) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 2px solid var(--light-gray);
}

.stTabs [data-baseweb="tab"] {
    font-family: 'Open Sans', sans-serif;
    font-weight: 600;
    color: var(--slate-light);
    padding: 12px 20px;
    border-radius: 8px 8px 0 0;
}

.stTabs [aria-selected="true"] {
    color: var(--teal) !important;
    border-bottom: 3px solid var(--teal) !important;
}

/* Metrics */
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
    letter-spacing: 0.03em !important;
}

[data-testid="stMetricValue"] {
    color: var(--teal) !important;
    font-weight: 700 !important;
}

/* Expanders */
.streamlit-expanderHeader {
    font-weight: 600;
    color: var(--slate);
    border-radius: 8px;
}

/* Progress bar */
.stProgress > div > div {
    background: var(--teal) !important;
}

/* Success/warning/error alerts */
.stAlert [data-testid="stAlertContentSuccess"] {
    border-left-color: var(--success) !important;
}
.stAlert [data-testid="stAlertContentWarning"] {
    border-left-color: var(--warning) !important;
}
.stAlert [data-testid="stAlertContentError"] {
    border-left-color: var(--danger) !important;
}

/* File uploader */
[data-testid="stFileUploader"] {
    border-radius: 8px;
}

/* Slider */
.stSlider [data-testid="stThumbValue"] {
    color: var(--teal) !important;
}

/* Dividers */
hr {
    border-color: var(--light-gray) !important;
}

/* Links */
a {
    color: var(--teal) !important;
}
a:hover {
    color: var(--teal-dark) !important;
}

/* Branded step indicators */
.step-active {
    background: var(--teal-light);
    border-left: 3px solid var(--teal);
    padding: 8px 12px;
    border-radius: 0 6px 6px 0;
    margin-bottom: 4px;
    font-weight: 600;
    color: var(--teal-dark);
}

.step-complete {
    background: #f0fdf4;
    border-left: 3px solid var(--success);
    padding: 8px 12px;
    border-radius: 0 6px 6px 0;
    margin-bottom: 4px;
    color: var(--success);
}

.step-pending {
    background: var(--off-white);
    border-left: 3px solid var(--light-gray);
    padding: 8px 12px;
    border-radius: 0 6px 6px 0;
    margin-bottom: 4px;
    color: var(--slate-light);
}

/* Cost badge */
.cost-badge {
    background: var(--teal-light);
    color: var(--teal-dark);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
    display: inline-block;
}

/* Guardrail badge */
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
    "org_context_assembly": "Org Context",
    "vpi_integration": "VPI Data Integration",
    "needs_statement": "Needs Statement",
    "program_design": "Program Design & Budget",
    "narrative_assembly": "Narrative Assembly",
    "quality_review": "Quality Review",
}

STEP_ICONS = {
    "rfp_ingestion": "1",
    "compliance_extraction": "2",
    "org_context_assembly": "3",
    "vpi_integration": "4",
    "needs_statement": "5",
    "program_design": "6",
    "narrative_assembly": "7",
    "quality_review": "8",
}


def initialize():
    """Initialize database and session state."""
    init_db()
    seed_altus_org()

    defaults = {
        "pipeline_result": None,
        "extracted_doc": None,
        "current_step": None,
        "edited_sections": {},
        "completed_steps": [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def render_sidebar(api_key_from_env: str):
    """Render the branded sidebar."""
    with st.sidebar:
        # Brand header
        st.markdown(
            '<h1 style="margin-bottom: 0; font-size: 1.5rem;">AltusNow</h1>'
            '<p style="color: #19948A; font-weight: 600; font-size: 0.95rem; margin-top: -4px;">'
            'Grant Writer</p>',
            unsafe_allow_html=True,
        )
        st.caption("AI-powered grant applications with trauma-informed language guardrails")

        st.divider()

        # API key
        api_key = api_key_from_env
        if not api_key:
            # Check Streamlit secrets
            api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            api_key = st.text_input(
                "Anthropic API Key",
                type="password",
                help="Required for AI generation. Set in Streamlit secrets or enter here.",
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

        # Pipeline progress (sidebar step tracker)
        if st.session_state.completed_steps:
            st.markdown(
                '<p style="font-weight: 600; font-size: 0.8rem; color: #7A8289; '
                'text-transform: uppercase; letter-spacing: 0.05em;">Pipeline Progress</p>',
                unsafe_allow_html=True,
            )
            for step_name in STEP_NAMES:
                label = STEP_LABELS.get(step_name, step_name)
                num = STEP_ICONS.get(step_name, "")
                if step_name in st.session_state.completed_steps:
                    st.markdown(
                        f'<div class="step-complete">{num}. {label}</div>',
                        unsafe_allow_html=True,
                    )
                elif step_name == st.session_state.current_step:
                    st.markdown(
                        f'<div class="step-active">{num}. {label}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<div class="step-pending">{num}. {label}</div>',
                        unsafe_allow_html=True,
                    )

            st.divider()

        # Cost tracking
        if st.session_state.pipeline_result:
            cost = st.session_state.pipeline_result.get("cost_summary", {})
            total_cost = cost.get("total_cost_usd", 0)
            total_tokens = cost.get("total_input_tokens", 0) + cost.get("total_output_tokens", 0)
            st.markdown(
                f'<div class="cost-badge">${total_cost:.2f} total cost</div>',
                unsafe_allow_html=True,
            )
            st.caption(f"{total_tokens:,} tokens used")

            # Language scan badge
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


def main():
    initialize()

    # Inject brand CSS
    st.markdown(BRAND_CSS, unsafe_allow_html=True)

    # Get API key from env
    api_key_from_env = os.getenv("ANTHROPIC_API_KEY", "")

    # Render sidebar
    api_key, selected_org = render_sidebar(api_key_from_env)

    # --- Main Content ---
    tab_upload, tab_generate, tab_review, tab_export = st.tabs([
        "Upload RFP",
        "Generate Draft",
        "Review & Edit",
        "Export",
    ])

    # === TAB 1: Upload RFP ===
    with tab_upload:
        st.header("Upload RFP Document")
        st.markdown(
            '<p style="color: #7A8289;">Upload a Request for Proposals from grants.gov or SAM.gov. '
            'The system will extract text, tables, and structure for analysis.</p>',
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
                help="State for VPI data integration in the needs statement",
            )

        with col2:
            vpi_file = st.file_uploader(
                "VPI Data (optional)",
                type=["json", "csv"],
                help="Upload Engage Together VPI JSON for county-level vulnerability data",
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

                    # Summary metrics
                    col_a, col_b, col_c = st.columns(3)
                    col_a.metric("Pages", extracted.page_count)
                    col_b.metric("Words", f"{extracted.word_count:,}")
                    col_c.metric("Tables", len(extracted.tables))

                    with st.expander("Document Preview", expanded=False):
                        st.text(extracted.full_text[:3000] + "\n\n[... truncated ...]")

                    if extracted.tables:
                        with st.expander(f"Extracted Tables ({len(extracted.tables)})", expanded=False):
                            st.markdown(format_tables_as_markdown(extracted.tables))

                finally:
                    tmp_path.unlink(missing_ok=True)

    # === TAB 2: Generate Draft ===
    with tab_generate:
        st.header("Generate Grant Application")

        if not st.session_state.extracted_doc:
            st.info("Upload an RFP document in the first tab to get started.")
            return

        if not api_key:
            st.warning("Enter your Anthropic API key in the sidebar to enable generation.")
            return

        extracted = st.session_state.extracted_doc

        # VPI data handling
        vpi_data = None
        if vpi_file:
            try:
                if vpi_file.name.endswith(".json"):
                    vpi_data = json.loads(vpi_file.getvalue())
                else:
                    st.warning("CSV VPI data requires conversion to JSON. Use JSON format.")
            except json.JSONDecodeError:
                st.error("Invalid JSON in VPI file.")

        # Pipeline configuration
        with st.expander("Pipeline Settings", expanded=False):
            max_cost = st.slider("Max Cost per Run ($)", 1.0, 25.0, 10.0, 0.5)
            use_opus = st.checkbox(
                "Use Opus for Narrative Assembly",
                value=False,
                help="Higher quality narrative but approximately 5x more expensive for that step",
            )

        # Generate button
        if st.button("Generate Grant Application", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            status_container = st.container()
            step_statuses = {}
            st.session_state.completed_steps = []

            def on_step_complete(step_name: str, output: str):
                step_idx = STEP_NAMES.index(step_name)
                progress = (step_idx + 1) / len(STEP_NAMES)
                progress_bar.progress(progress)
                step_statuses[step_name] = len(output.split())
                st.session_state.completed_steps.append(step_name)
                st.session_state.current_step = (
                    STEP_NAMES[step_idx + 1] if step_idx + 1 < len(STEP_NAMES) else None
                )
                with status_container:
                    for sn in STEP_NAMES:
                        label = STEP_LABELS.get(sn, sn)
                        num = STEP_ICONS.get(sn, "")
                        if sn in step_statuses:
                            st.markdown(
                                f'<div class="step-complete">'
                                f'{num}. {label} &mdash; {step_statuses[sn]:,} words</div>',
                                unsafe_allow_html=True,
                            )

            # Set first step as active
            st.session_state.current_step = STEP_NAMES[0]

            # Build settings overrides
            settings = None
            if use_opus or max_cost != 10.0:
                import yaml
                with open(CONFIG_DIR / "settings.yaml") as f:
                    settings = yaml.safe_load(f)
                if use_opus:
                    settings["step_overrides"] = settings.get("step_overrides", {})
                    settings["step_overrides"]["narrative_assembly"] = {
                        "model": "claude-opus-4-20250514"
                    }
                settings["max_total_cost_usd"] = max_cost

            try:
                pipeline = GrantPipeline(
                    api_key=api_key,
                    config_dir=CONFIG_DIR,
                    output_dir=OUTPUT_DIR,
                    settings=settings,
                )

                result = pipeline.run(
                    rfp_text=extracted.full_text,
                    org_profile=selected_org or {"name": "Altus Solutions"},
                    file_name=uploaded_file.name if uploaded_file else "rfp_document",
                    page_count=extracted.page_count,
                    word_count=extracted.word_count,
                    tables_markdown=format_tables_as_markdown(extracted.tables),
                    vpi_data=vpi_data,
                    target_state=target_state,
                    on_step_complete=on_step_complete,
                )

                st.session_state.pipeline_result = result
                st.session_state.current_step = None
                progress_bar.progress(1.0)

                total_cost = result["cost_summary"]["total_cost_usd"]
                st.success(f"Grant application generated. Total cost: ${total_cost:.2f}")

                # Language scan results
                lang = result.get("language_scan", {})
                if lang.get("passed"):
                    st.markdown(
                        f'<div class="guardrail-pass">'
                        f'Language Guardrails: PASSED &mdash; {lang.get("summary", "")}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<div class="guardrail-fail">'
                        f'Language Guardrails: REVIEW &mdash; {lang.get("summary", "")}</div>',
                        unsafe_allow_html=True,
                    )

            except Exception as e:
                st.error(f"Pipeline error: {e}")
                raise

    # === TAB 3: Review & Edit ===
    with tab_review:
        st.header("Review & Edit Sections")

        if not st.session_state.pipeline_result:
            st.info("Generate a draft in the previous tab to review it here.")
            return

        result = st.session_state.pipeline_result
        step_outputs = result.get("step_outputs", {})

        # QA Scorecard
        if result.get("scorecard"):
            with st.expander("Quality Scorecard", expanded=True):
                st.markdown(result["scorecard"])

        # Section-by-section review
        review_steps = [
            "needs_statement",
            "program_design",
            "narrative_assembly",
        ]

        for step_name in review_steps:
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

                # Language scan for this section
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

        # Compliance check view
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
                    st.write(
                        f"{icon} {item['requirement_text'][:100]}"
                    )

    # === TAB 4: Export ===
    with tab_export:
        st.header("Export Grant Application")

        if not st.session_state.pipeline_result:
            st.info("Generate a draft first, then export it here.")
            return

        result = st.session_state.pipeline_result

        # Use edited version if available
        final_text = st.session_state.edited_sections.get(
            "narrative_assembly",
            result.get("final_report", ""),
        )

        # Final language check before export
        scan = scan_text(final_text)
        if not scan.passed:
            st.markdown(
                f'<div class="guardrail-fail">'
                f'Export blocked: {scan.prohibited_count} prohibited term(s) found. '
                f'Fix them in the Review tab first.</div>',
                unsafe_allow_html=True,
            )
            st.code(scan.details(), language=None)
            return

        st.markdown(
            '<div class="guardrail-pass">Language guardrails: PASSED &mdash; ready for export</div>',
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
                    rfp_summary = result.get("step_outputs", {}).get("rfp_ingestion", "")
                    title = "Grant Application"
                    funder = ""

                    docx_path = OUTPUT_DIR / f"Grant_Application_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
                    markdown_to_docx(
                        markdown_text=final_text,
                        output_path=docx_path,
                        title=title,
                        funder=funder,
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
                    num = STEP_ICONS.get(step_name, "")
                    st.write(
                        f"**{num}. {label}**: ${step_cost['cost_usd']:.4f} "
                        f"({step_cost['input_tokens']:,} + {step_cost['output_tokens']:,} tokens, "
                        f"{step_cost.get('duration_seconds', 0):.0f}s)"
                    )


if __name__ == "__main__":
    main()
