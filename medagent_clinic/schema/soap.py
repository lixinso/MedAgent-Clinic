"""
SOAP note schema — Subjective / Objective / Assessment / Plan.

Models every clinical concept the agents read or produce. Designed to be
small enough to fit in your head, strict enough to fail loudly when the
LLM drifts off-format.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------- Patient & visit context ----------


class Patient(BaseModel):
    """Minimal patient context. Anonymized by default."""

    patient_id: str = Field(..., description="Local opaque ID. Never PII.")
    age: Optional[int] = Field(None, ge=0, le=130)
    sex: Optional[str] = Field(None, description="'M' / 'F' / 'other' / 'unknown'")
    known_conditions: list[str] = Field(default_factory=list)
    current_medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)


class VisitContext(BaseModel):
    """Everything an agent needs to know before/during a visit."""

    patient: Patient
    visit_date: date = Field(default_factory=date.today)
    visit_type: str = Field("outpatient", description="outpatient / follow-up / urgent")
    prior_notes: list[str] = Field(
        default_factory=list,
        description="Free-text prior chart notes, most recent first.",
    )
    raw_dialog: Optional[str] = Field(
        None,
        description="Raw doctor-patient dialog (transcribed or typed).",
    )


# ---------- SOAP components ----------


class ChiefComplaint(BaseModel):
    """The patient's main reason for the visit, in their own words when possible."""

    text: str
    duration: Optional[str] = None  # e.g. "3 days"


class HistoryOfPresentIllness(BaseModel):
    """OPQRST-structured HPI."""

    onset: Optional[str] = None
    provokes: Optional[str] = None
    quality: Optional[str] = None
    radiates: Optional[str] = None
    severity: Optional[str] = None  # e.g. "7/10"
    timing: Optional[str] = None
    associated_symptoms: list[str] = Field(default_factory=list)
    narrative: Optional[str] = Field(
        None, description="Free-text narrative if structured fields are insufficient."
    )


class ReviewOfSystems(BaseModel):
    """Brief ROS — only positives and pertinent negatives."""

    positives: list[str] = Field(default_factory=list)
    pertinent_negatives: list[str] = Field(default_factory=list)


class PhysicalExam(BaseModel):
    """Doctor-entered findings. Agent never invents these."""

    vitals: dict[str, str] = Field(
        default_factory=dict,
        description="e.g. {'BP': '128/82', 'HR': '78', 'Temp': '37.0'}",
    )
    findings: list[str] = Field(default_factory=list)


class Assessment(BaseModel):
    """Doctor's diagnostic impression. Agent may suggest, doctor confirms."""

    primary: str = Field(..., description="Primary diagnosis or working impression.")
    differentials: list[str] = Field(default_factory=list)
    icd10_candidates: list[str] = Field(
        default_factory=list,
        description="Suggested ICD-10 codes. Doctor must confirm.",
    )


class Plan(BaseModel):
    """Orders, labs, prescriptions, follow-up."""

    investigations: list[str] = Field(
        default_factory=list, description="Labs, imaging, etc."
    )
    prescriptions: list[str] = Field(default_factory=list)
    patient_education: list[str] = Field(default_factory=list)
    follow_up: Optional[str] = None
    referrals: list[str] = Field(default_factory=list)


# ---------- Composed note ----------


class SOAPNote(BaseModel):
    """Full SOAP note. The doctor signs this; the agent drafts it."""

    patient_id: str
    visit_date: date = Field(default_factory=date.today)

    # Subjective
    chief_complaint: ChiefComplaint
    hpi: HistoryOfPresentIllness
    ros: ReviewOfSystems = Field(default_factory=ReviewOfSystems)

    # Objective
    physical_exam: PhysicalExam = Field(default_factory=PhysicalExam)

    # Assessment
    assessment: Assessment

    # Plan
    plan: Plan

    # Provenance
    drafted_by: str = Field("medagent-clinic", description="Agent or human author.")
    drafted_at: datetime = Field(default_factory=datetime.now)
    requires_review: bool = Field(True, description="Always True until doctor signs.")

    def to_markdown(self) -> str:
        """Render as a doctor-readable Markdown note."""
        lines = [
            f"# SOAP Note — {self.visit_date.isoformat()} (Patient {self.patient_id})",
            "",
            "## S — Subjective",
            f"**Chief complaint:** {self.chief_complaint.text}"
            + (f" ({self.chief_complaint.duration})" if self.chief_complaint.duration else ""),
            "",
            "**HPI:**",
        ]

        hpi = self.hpi
        for label, value in [
            ("Onset", hpi.onset),
            ("Provokes", hpi.provokes),
            ("Quality", hpi.quality),
            ("Radiates", hpi.radiates),
            ("Severity", hpi.severity),
            ("Timing", hpi.timing),
        ]:
            if value:
                lines.append(f"- {label}: {value}")
        if hpi.associated_symptoms:
            lines.append(f"- Associated symptoms: {', '.join(hpi.associated_symptoms)}")
        if hpi.narrative:
            lines.append("")
            lines.append(hpi.narrative)

        if self.ros.positives or self.ros.pertinent_negatives:
            lines.append("")
            lines.append("**ROS:**")
            if self.ros.positives:
                lines.append(f"- Positives: {', '.join(self.ros.positives)}")
            if self.ros.pertinent_negatives:
                lines.append(
                    f"- Pertinent negatives: {', '.join(self.ros.pertinent_negatives)}"
                )

        lines.extend(["", "## O — Objective"])
        if self.physical_exam.vitals:
            lines.append(
                "**Vitals:** "
                + ", ".join(f"{k} {v}" for k, v in self.physical_exam.vitals.items())
            )
        for finding in self.physical_exam.findings:
            lines.append(f"- {finding}")
        if not self.physical_exam.vitals and not self.physical_exam.findings:
            lines.append("_(not yet entered by doctor)_")

        lines.extend(["", "## A — Assessment", f"**Primary:** {self.assessment.primary}"])
        if self.assessment.differentials:
            lines.append(
                "**Differentials:** " + "; ".join(self.assessment.differentials)
            )
        if self.assessment.icd10_candidates:
            lines.append(
                "**ICD-10 (suggested, requires confirmation):** "
                + ", ".join(self.assessment.icd10_candidates)
            )

        lines.extend(["", "## P — Plan"])
        for label, items in [
            ("Investigations", self.plan.investigations),
            ("Prescriptions", self.plan.prescriptions),
            ("Patient education", self.plan.patient_education),
            ("Referrals", self.plan.referrals),
        ]:
            for item in items:
                lines.append(f"- {label}: {item}")
        if self.plan.follow_up:
            lines.append(f"- Follow-up: {self.plan.follow_up}")

        if self.requires_review:
            lines.extend(
                [
                    "",
                    "---",
                    "_⚠️ Draft. Requires physician review and signature._",
                ]
            )

        return "\n".join(lines)
