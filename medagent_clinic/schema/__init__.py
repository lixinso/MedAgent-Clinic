"""
Clinical schema — typed Pydantic models for SOAP notes and related concepts.

Why schema-first?
- Outputs are machine-readable (FHIR / EHR export ready).
- Prompts become render(schema) + parse(response), not free-form text.
- Bugs are caught at parse time, not at chart-review time.
"""

from .soap import (
    ChiefComplaint,
    HistoryOfPresentIllness,
    ReviewOfSystems,
    PhysicalExam,
    Assessment,
    Plan,
    SOAPNote,
    Patient,
    VisitContext,
)

__all__ = [
    "ChiefComplaint",
    "HistoryOfPresentIllness",
    "ReviewOfSystems",
    "PhysicalExam",
    "Assessment",
    "Plan",
    "SOAPNote",
    "Patient",
    "VisitContext",
]
