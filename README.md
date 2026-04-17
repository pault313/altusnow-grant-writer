# AltusNow Grant Writer

AI-powered grant writing tool for anti-trafficking and social determinants of health (SDOH) organizations. Built on Claude API with trauma-informed language guardrails.

## Features

- **8-step AI pipeline**: RFP parsing, compliance extraction, VPI data integration, needs statement, program design, narrative assembly, quality review
- **Trauma-informed language guardrails**: Prohibited term scanner with auto-fix (OTIP/TVPA compliant)
- **Compliance checker**: Scores draft against RFP requirements
- **VPI data integration**: Engage Together Vulnerability Profile Index for evidence-based needs statements
- **Cost tracking**: Per-step and per-run API cost monitoring with configurable budget caps
- **DOCX export**: OVC-compliant document formatting

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Configuration

Set your Anthropic API key via Streamlit secrets (recommended for deployment) or `.env` file (local development):

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

## Architecture

```
app.py                    Streamlit UI
config/
  settings.yaml           Pipeline configuration
  prompts/*.yaml           Step-specific system prompts (8 steps)
src/
  llm_client.py           Claude API client with retry + cost tracking
  pipeline.py             8-step grant writing pipeline
  database.py             SQLite schema + seed data
  steps/                  Pipeline step implementations
  utils/
    pdf_parser.py         PyMuPDF + pdfplumber extraction
    language_guard.py     Trauma-informed term scanner
    compliance_checker.py RFP compliance scoring
    docx_export.py        Word document generation
```

## Cost

~$2-5 per complete grant application (Claude Sonnet). Opus for narrative assembly adds ~$1.50.

---

Built by [Altus Solutions](https://altusnow.com) -- a B-Corp dedicated to ending human trafficking through technology, data, and community empowerment.
