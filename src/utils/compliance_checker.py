"""
Compliance checklist scoring and tracking.

Checks a generated grant draft against the compliance items extracted from the RFP.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from src.database import get_connection


@dataclass
class ComplianceResult:
    """Result of checking a draft against compliance requirements."""
    total_items: int
    met_items: int
    unmet_items: int
    items: list[dict]

    @property
    def score(self) -> float:
        if self.total_items == 0:
            return 1.0
        return self.met_items / self.total_items

    @property
    def score_pct(self) -> str:
        return f"{self.score * 100:.0f}%"

    def summary(self) -> str:
        return (
            f"Compliance: {self.score_pct} ({self.met_items}/{self.total_items} requirements met). "
            f"{self.unmet_items} items need attention."
        )


def parse_compliance_checklist(checklist_text: str) -> list[dict]:
    """
    Parse the LLM-generated compliance checklist into structured items.

    Expected format from Step 2 output:
    1. [CRITICAL] Requirement text here (Page X) -- Type: content
    """
    items = []
    # Match numbered items with optional priority tag
    pattern = re.compile(
        r"(\d+)\.\s*"
        r"(?:\[(\w+)\]\s*)?"  # optional [CRITICAL] tag
        r"(.+?)(?:\s*\(Page\s*(\d+)\))?"  # requirement text + optional page
        r"(?:\s*--\s*Type:\s*(\w+))?"  # optional type
        r"$",
        re.MULTILINE,
    )

    for match in pattern.finditer(checklist_text):
        item_id = int(match.group(1))
        priority = (match.group(2) or "important").lower()
        text = match.group(3).strip()
        page = int(match.group(4)) if match.group(4) else None
        req_type = (match.group(5) or "content").lower()

        items.append({
            "id": item_id,
            "requirement_text": text,
            "priority": priority,
            "source_page": page,
            "requirement_type": req_type,
            "is_met": False,
            "notes": "",
        })

    # Fallback: if regex didn't match, try simpler line-by-line parsing
    if not items:
        for line in checklist_text.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Strip leading numbers/bullets
            text = re.sub(r"^[\d\.\-\*\s]+", "", line).strip()
            if text:
                items.append({
                    "id": len(items) + 1,
                    "requirement_text": text,
                    "priority": "important",
                    "source_page": None,
                    "requirement_type": "content",
                    "is_met": False,
                    "notes": "",
                })

    return items


def save_compliance_items(
    rfp_id: int,
    items: list[dict],
    db_path: Optional[Path] = None,
) -> None:
    """Save parsed compliance items to the database."""
    conn = get_connection(db_path)
    try:
        # Clear existing items for this RFP
        conn.execute("DELETE FROM compliance_items WHERE rfp_id = ?", (rfp_id,))

        for item in items:
            conn.execute(
                "INSERT INTO compliance_items "
                "(rfp_id, requirement_text, requirement_type, priority, source_page, is_met, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    rfp_id,
                    item["requirement_text"],
                    item.get("requirement_type", "content"),
                    item.get("priority", "important"),
                    item.get("source_page"),
                    int(item.get("is_met", False)),
                    item.get("notes", ""),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def get_compliance_items(rfp_id: int, db_path: Optional[Path] = None) -> list[dict]:
    """Fetch compliance items for an RFP."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM compliance_items WHERE rfp_id = ? ORDER BY id",
            (rfp_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def check_draft_compliance(
    draft_text: str,
    compliance_items: list[dict],
) -> ComplianceResult:
    """
    Basic keyword-based compliance check.

    For each requirement, checks if key terms appear in the draft.
    This is a heuristic -- the LLM-based quality review step does the real check.
    """
    results = []
    draft_lower = draft_text.lower()

    for item in compliance_items:
        req_text = item["requirement_text"].lower()
        # Extract key phrases (3+ word sequences)
        key_words = [w for w in req_text.split() if len(w) > 3]
        if not key_words:
            key_words = req_text.split()

        # Check if enough key terms appear in the draft
        matched = sum(1 for w in key_words if w in draft_lower)
        coverage = matched / len(key_words) if key_words else 0

        is_met = coverage >= 0.4  # 40% keyword overlap threshold

        results.append({
            **item,
            "is_met": is_met,
            "coverage": round(coverage, 2),
        })

    met = sum(1 for r in results if r["is_met"])
    unmet = len(results) - met

    return ComplianceResult(
        total_items=len(results),
        met_items=met,
        unmet_items=unmet,
        items=results,
    )
