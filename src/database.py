"""
SQLite database layer for the grant writer.

Handles schema creation, seed data, and basic CRUD operations.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


DB_PATH = Path(__file__).parent.parent / "data" / "grant_writer.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS organizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    ein TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    website TEXT,
    mission_statement TEXT,
    org_type TEXT CHECK(org_type IN ('nonprofit', 'for_profit', 'government', 'academic')),
    annual_budget REAL,
    staff_count INTEGER,
    year_founded INTEGER,
    product_catalog_json TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS rfps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    funder_name TEXT,
    funder_agency TEXT,
    opportunity_number TEXT,
    cfda_number TEXT,
    deadline TEXT,
    max_award REAL,
    min_award REAL,
    duration_months INTEGER,
    eligible_applicants TEXT,
    file_path TEXT NOT NULL,
    extracted_text TEXT,
    structured_json TEXT,
    compliance_checklist_json TEXT,
    status TEXT DEFAULT 'uploaded' CHECK(status IN ('uploaded', 'parsed', 'in_progress', 'completed', 'archived')),
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS grant_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rfp_id INTEGER NOT NULL REFERENCES rfps(id),
    org_id INTEGER NOT NULL REFERENCES organizations(id),
    title TEXT NOT NULL,
    target_state TEXT,
    target_counties TEXT,
    vpi_data_path TEXT,
    status TEXT DEFAULT 'draft' CHECK(status IN ('draft', 'in_progress', 'review', 'final', 'submitted')),
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS application_sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL REFERENCES grant_applications(id),
    section_name TEXT NOT NULL,
    section_order INTEGER NOT NULL,
    prompt_used TEXT,
    raw_output TEXT,
    edited_content TEXT,
    compliance_score REAL,
    word_count INTEGER,
    version INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL REFERENCES grant_applications(id),
    status TEXT DEFAULT 'running' CHECK(status IN ('running', 'completed', 'failed', 'cancelled')),
    steps_completed TEXT,
    cost_summary_json TEXT,
    total_cost_usd REAL,
    total_input_tokens INTEGER,
    total_output_tokens INTEGER,
    started_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS compliance_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rfp_id INTEGER NOT NULL REFERENCES rfps(id),
    requirement_text TEXT NOT NULL,
    requirement_type TEXT CHECK(requirement_type IN ('eligibility', 'content', 'format', 'budget', 'attachment', 'deadline')),
    priority TEXT DEFAULT 'important' CHECK(priority IN ('critical', 'important', 'recommended')),
    source_page INTEGER,
    is_met INTEGER DEFAULT 0,
    section_reference TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS language_guardrails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL CHECK(category IN ('prohibited', 'preferred', 'context_dependent')),
    term TEXT NOT NULL,
    replacement TEXT,
    context_note TEXT,
    source TEXT DEFAULT 'OTIP_guidelines'
);
"""

SEED_GUARDRAILS = [
    ("prohibited", "prostitute", "person who has been trafficked", "Never use stigmatizing language", "OTIP_guidelines"),
    ("prohibited", "child prostitute", "child who has been trafficked", "All minors are trafficking victims by definition under TVPA", "TVPA"),
    ("prohibited", "illegal alien", "undocumented individual", "Avoid criminalizing language about immigration status", "OTIP_guidelines"),
    ("prohibited", "rescue", "identify and support", "Avoid paternalistic framing of anti-trafficking work", "OTIP_guidelines"),
    ("prohibited", "rescued", "identified and supported", "Avoid paternalistic framing of anti-trafficking work", "OTIP_guidelines"),
    ("prohibited", "modern-day slavery", None, "Use 'trafficking' or 'forced labor' with specific legal definitions from TVPA", "TVPA"),
    ("prohibited", "modern day slavery", None, "Use 'trafficking' or 'forced labor' with specific legal definitions from TVPA", "TVPA"),
    ("prohibited", "sex slave", "person subjected to sex trafficking", "Use legal terminology, not sensationalized language", "OTIP_guidelines"),
    ("prohibited", "sold into slavery", "trafficked", "Use legal terminology per TVPA definitions", "TVPA"),
    ("prohibited", "hooker", "person who has been trafficked", "Never use stigmatizing language", "OTIP_guidelines"),
    ("context_dependent", "victim", "Use in identification/exit context; use 'survivor' in recovery/restoration", None, "OTIP_guidelines"),
    ("context_dependent", "at-risk", "Specify the risk factor rather than labeling populations", None, "ET_style_guide"),
    ("preferred", "survivor-centered", None, "Preferred framing for all service delivery descriptions", "OTIP_guidelines"),
    ("preferred", "trauma-informed", None, "Required modifier for training and service descriptions", "OTIP_guidelines"),
    ("preferred", "strengths-based", None, "Preferred over deficit-focused language when describing communities", "OTIP_guidelines"),
    ("preferred", "person-first language", None, "Always use person-first language when referencing affected populations", "OTIP_guidelines"),
    ("preferred", "culturally responsive", None, "Preferred descriptor for services adapted to community needs", "OTIP_guidelines"),
    ("preferred", "evidence-based", None, "Required when describing program methodologies", "OTIP_guidelines"),
    ("preferred", "survivor-informed", None, "Indicates survivor input in program design", "OTIP_guidelines"),
]


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Get a database connection with row factory enabled."""
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Create all tables and seed guardrails data."""
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA_SQL)

        # Seed guardrails if empty
        count = conn.execute("SELECT COUNT(*) FROM language_guardrails").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO language_guardrails (category, term, replacement, context_note, source) "
                "VALUES (?, ?, ?, ?, ?)",
                SEED_GUARDRAILS,
            )
            conn.commit()
    finally:
        conn.close()


def seed_altus_org(db_path: Optional[Path] = None) -> int:
    """Insert the Altus Solutions organization profile. Returns the org ID."""
    conn = get_connection(db_path)
    try:
        # Check if already exists
        existing = conn.execute(
            "SELECT id FROM organizations WHERE name = 'Altus Solutions'"
        ).fetchone()
        if existing:
            return existing[0]

        product_catalog = json.dumps({
            "products": [
                {
                    "name": "Justice U",
                    "type": "Training Platform",
                    "description": "CEU-eligible online training platform for anti-trafficking education. "
                                   "Accredited courses covering trafficking identification, trauma-informed care, "
                                   "and survivor-centered approaches.",
                    "key_features": [
                        "CEU/CE credit eligible",
                        "Elevance Health partnership",
                        "HealthStream LMS integration",
                        "Self-paced online format",
                        "Healthcare professional focus",
                    ],
                    "grant_fit": "Training components, capacity building, professional development",
                    "typical_budget_line": "Contractual -- Training Platform License",
                },
                {
                    "name": "Just in Time (JIT)",
                    "type": "Mobile Application",
                    "description": "White-labeled mobile app for healthcare professionals to recognize "
                                   "trafficking indicators and connect survivors to services. Includes "
                                   "case management and service navigation for reentry populations.",
                    "key_features": [
                        "Trafficking indicator recognition tool",
                        "Service navigation and referral",
                        "Case management capabilities",
                        "White-label customization",
                        "TBI partnership",
                    ],
                    "grant_fit": "Case management, service coordination, technology components",
                    "typical_budget_line": "Contractual -- Mobile App License & Customization",
                },
                {
                    "name": "Engage Together",
                    "type": "Community Assessment Platform",
                    "description": "Community vulnerability assessment and mobilization platform. "
                                   "Uses the Vulnerability Profile Index (VPI) to analyze 37 indicators "
                                   "across 14 data sources at the county level.",
                    "key_features": [
                        "37-indicator Vulnerability Profile Index (VPI)",
                        "14 validated data sources",
                        "County-level analysis",
                        "6 vulnerability categories",
                        "Sex and labor trafficking indices",
                        "Interactive data dashboards",
                        "Statewide assessment reports",
                    ],
                    "grant_fit": "Needs assessment, data-driven program design, community engagement",
                    "typical_budget_line": "Contractual -- Community Assessment Platform",
                },
            ],
        })

        cursor = conn.execute(
            """INSERT INTO organizations
            (name, ein, address, city, state, zip, website, mission_statement,
             org_type, annual_budget, staff_count, year_founded, product_catalog_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "Altus Solutions",
                None,  # EIN -- populate when available
                None,  # Address
                None,  # City
                None,  # State
                None,  # Zip
                "https://altusnow.com",
                "Altus Solutions is a B-Corp dedicated to ending human trafficking through "
                "technology, data, and community empowerment. We build tools that equip "
                "coalitions, healthcare professionals, and government agencies to identify "
                "vulnerability, train responders, and coordinate survivor services.",
                "for_profit",  # B-Corp
                None,  # Annual budget
                None,  # Staff count
                None,  # Year founded
                product_catalog,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


# --- CRUD helpers ---

def create_rfp(
    title: str,
    file_path: str,
    funder_name: str = "",
    funder_agency: str = "",
    db_path: Optional[Path] = None,
) -> int:
    """Insert a new RFP record. Returns the RFP ID."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "INSERT INTO rfps (title, file_path, funder_name, funder_agency) VALUES (?, ?, ?, ?)",
            (title, file_path, funder_name, funder_agency),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_rfp(rfp_id: int, updates: dict[str, Any], db_path: Optional[Path] = None) -> None:
    """Update an RFP record with the given fields."""
    conn = get_connection(db_path)
    try:
        updates["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [rfp_id]
        conn.execute(f"UPDATE rfps SET {set_clause} WHERE id = ?", values)
        conn.commit()
    finally:
        conn.close()


def get_rfp(rfp_id: int, db_path: Optional[Path] = None) -> Optional[dict]:
    """Fetch an RFP by ID."""
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM rfps WHERE id = ?", (rfp_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_application(
    rfp_id: int,
    org_id: int,
    title: str,
    target_state: str = "",
    vpi_data_path: str = "",
    db_path: Optional[Path] = None,
) -> int:
    """Insert a new grant application. Returns the application ID."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "INSERT INTO grant_applications (rfp_id, org_id, title, target_state, vpi_data_path) "
            "VALUES (?, ?, ?, ?, ?)",
            (rfp_id, org_id, title, target_state, vpi_data_path),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def save_section(
    application_id: int,
    section_name: str,
    section_order: int,
    raw_output: str,
    db_path: Optional[Path] = None,
) -> int:
    """Save a generated section. Returns the section ID."""
    conn = get_connection(db_path)
    try:
        word_count = len(raw_output.split())
        cursor = conn.execute(
            "INSERT INTO application_sections "
            "(application_id, section_name, section_order, raw_output, word_count) "
            "VALUES (?, ?, ?, ?, ?)",
            (application_id, section_name, section_order, raw_output, word_count),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_guardrails(db_path: Optional[Path] = None) -> list[dict]:
    """Fetch all language guardrails."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT * FROM language_guardrails ORDER BY category, term").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_org(org_id: int, db_path: Optional[Path] = None) -> Optional[dict]:
    """Fetch an organization by ID."""
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM organizations WHERE id = ?", (org_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_orgs(db_path: Optional[Path] = None) -> list[dict]:
    """List all organizations."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT id, name, org_type FROM organizations ORDER BY name").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
