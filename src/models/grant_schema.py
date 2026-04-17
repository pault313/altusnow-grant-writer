"""
Pydantic models for grant application data validation.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class OrgType(str, Enum):
    NONPROFIT = "nonprofit"
    FOR_PROFIT = "for_profit"
    GOVERNMENT = "government"
    ACADEMIC = "academic"


class RFPStatus(str, Enum):
    UPLOADED = "uploaded"
    PARSED = "parsed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ApplicationStatus(str, Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    FINAL = "final"
    SUBMITTED = "submitted"


class RequirementType(str, Enum):
    ELIGIBILITY = "eligibility"
    CONTENT = "content"
    FORMAT = "format"
    BUDGET = "budget"
    ATTACHMENT = "attachment"
    DEADLINE = "deadline"


class Priority(str, Enum):
    CRITICAL = "critical"
    IMPORTANT = "important"
    RECOMMENDED = "recommended"


class FunderAgency(str, Enum):
    """Common federal funder agencies in the anti-trafficking space."""
    OVC = "OVC"      # Office for Victims of Crime
    OTIP = "OTIP"    # Office on Trafficking in Persons
    HRSA = "HRSA"    # Health Resources and Services Administration
    BJA = "BJA"      # Bureau of Justice Assistance
    CDC = "CDC"      # Centers for Disease Control
    SAMHSA = "SAMHSA"  # Substance Abuse and Mental Health Services Administration
    ACF = "ACF"      # Administration for Children and Families
    NIJ = "NIJ"      # National Institute of Justice
    OTHER = "OTHER"


class Organization(BaseModel):
    """Applicant organization profile."""
    id: Optional[int] = None
    name: str
    ein: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    website: Optional[str] = None
    mission_statement: Optional[str] = None
    org_type: OrgType = OrgType.NONPROFIT
    annual_budget: Optional[float] = None
    staff_count: Optional[int] = None
    year_founded: Optional[int] = None
    product_catalog_json: Optional[str] = None


class RFP(BaseModel):
    """Request for Proposals metadata."""
    id: Optional[int] = None
    title: str
    funder_name: Optional[str] = None
    funder_agency: Optional[str] = None
    opportunity_number: Optional[str] = None
    cfda_number: Optional[str] = None
    deadline: Optional[str] = None
    max_award: Optional[float] = None
    min_award: Optional[float] = None
    duration_months: Optional[int] = None
    status: RFPStatus = RFPStatus.UPLOADED


class ComplianceItem(BaseModel):
    """A single compliance requirement extracted from an RFP."""
    id: Optional[int] = None
    requirement_text: str
    requirement_type: RequirementType = RequirementType.CONTENT
    priority: Priority = Priority.IMPORTANT
    source_page: Optional[int] = None
    is_met: bool = False
    section_reference: Optional[str] = None
    notes: Optional[str] = None


class ApplicationSection(BaseModel):
    """A section of a grant application."""
    section_name: str
    section_order: int
    raw_output: Optional[str] = None
    edited_content: Optional[str] = None
    compliance_score: Optional[float] = None
    word_count: Optional[int] = None
    version: int = 1


class PipelineRunConfig(BaseModel):
    """Configuration for a pipeline run."""
    rfp_id: int
    org_id: int
    target_state: str = ""
    vpi_data_path: str = ""
    start_from: Optional[str] = None
    stop_after: Optional[str] = None
    max_cost_usd: float = 10.00


class CostSummary(BaseModel):
    """Summary of API costs for a pipeline run."""
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    total_calls: int
    by_step: dict = Field(default_factory=dict)
