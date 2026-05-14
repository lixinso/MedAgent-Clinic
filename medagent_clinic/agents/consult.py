"""
ConsultAgent — runs during / right after the visit.

Reads the doctor-patient dialog and drafts a structured SOAP note.
The doctor edits and signs.
"""

from __future__ import annotations

import json
import time

from ..llm import chat
from ..safety import check as safety_check
from ..schema import (
    Assessment,
    ChiefComplaint,
    HistoryOfPresentIllness,
    Plan,
    ReviewOfSystems,
    SOAPNote,
    VisitContext,
)
from .base import Agent, AgentOutput, AuditEntry


PROMPT = """\
You are a medical scribe drafting a SOAP note from a doctor-patient dialog.

You are NOT making a diagnosis. You are STRUCTURING what was said.
The doctor will review, edit, and sign.

Patient context:
- Age: {age}
- Sex: {sex}
- Known conditions: {conditions}
- Current medications: {meds}
- Allergies: {allergies}

Dialog:
\"\"\"
{dialog}
\"\"\"

Return ONLY valid JSON with this exact shape:
{{
  "chief_complaint": {{"text": "...", "duration": "..."}},
  "hpi": {{
    "onset": "...", "quality": "...", "severity": "...",
    "timing": "...", "associated_symptoms": ["..."],
    "narrative": "..."
  }},
  "ros": {{"positives": ["..."], "pertinent_negatives": ["..."]}},
  "assessment": {{
    "primary": "...",
    "differentials": ["..."],
    "icd10_candidates": ["..."]
  }},
  "plan": {{
    "investigations": ["..."],
    "prescriptions": ["..."],
    "patient_education": ["..."],
    "follow_up": "...",
    "referrals": ["..."]
  }}
}}

If a field is genuinely unknown from the dialog, use an empty string or empty array.
Do NOT invent vitals or physical exam findings — the doctor enters those.
"""


class ConsultAgent(Agent):
    name = "ConsultAgent"

    def __init__(self, prefer_provider: str | None = None):
        self.prefer_provider = prefer_provider

    def run(self, context: VisitContext) -> AgentOutput:
        if not context.raw_dialog:
            return AgentOutput(
                agent=self.name,
                result=None,
                summary="No dialog supplied — nothing to draft.",
                confidence=0.0,
                requires_review=True,
            )

        p = context.patient
        prompt = PROMPT.format(
            age=p.age if p.age is not None else "unknown",
            sex=p.sex or "unknown",
            conditions=", ".join(p.known_conditions) or "none on record",
            meds=", ".join(p.current_medications) or "none on record",
            allergies=", ".join(p.allergies) or "none on record",
            dialog=context.raw_dialog,
        )

        start = time.time()
        resp = chat(prompt, prefer=self.prefer_provider)
        latency_ms = int((time.time() - start) * 1000)

        soap = self._parse(resp.text, context)

        flags = safety_check(
            patient_text=context.raw_dialog,
            proposed_prescriptions=soap.plan.prescriptions if soap else [],
            current_medications=context.patient.current_medications,
        )

        confidence = 0.65 if resp.provider in ("openai", "anthropic") else 0.2
        summary = (
            f"Drafted SOAP for: {soap.assessment.primary}"
            if soap and soap.assessment.primary
            else "Drafted SOAP — review required."
        )

        return AgentOutput(
            agent=self.name,
            result=soap,
            summary=summary,
            confidence=confidence,
            requires_review=True,
            safety_flags=flags,
            audit_trail=[
                AuditEntry(
                    agent=self.name,
                    model=resp.model,
                    provider=resp.provider,
                    prompt=prompt,
                    response=resp.text,
                    latency_ms=latency_ms,
                )
            ],
        )

    @staticmethod
    def _parse(text: str, context: VisitContext) -> SOAPNote | None:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()
        try:
            data = json.loads(cleaned)
        except Exception:
            return _placeholder_soap(context, note=f"Could not parse: {text[:120]}")

        if "_mock" in data:
            d = data.get("soap_draft", {})
            return SOAPNote(
                patient_id=context.patient.patient_id,
                visit_date=context.visit_date,
                chief_complaint=ChiefComplaint(
                    text=d.get("chief_complaint", {}).get("text", "(mock)"),
                    duration=d.get("chief_complaint", {}).get("duration"),
                ),
                hpi=HistoryOfPresentIllness(
                    narrative=d.get("hpi", {}).get(
                        "narrative", "Mock HPI — set an API key for real output."
                    )
                ),
                assessment=Assessment(
                    primary=d.get("assessment", {}).get(
                        "primary", "Working impression pending physician review"
                    ),
                    differentials=d.get("assessment", {}).get("differentials", []),
                ),
                plan=Plan(
                    investigations=d.get("plan", {}).get("investigations", []),
                    patient_education=d.get("plan", {}).get("patient_education", []),
                    follow_up=d.get("plan", {}).get("follow_up"),
                ),
            )

        try:
            cc = data.get("chief_complaint", {}) or {}
            hpi = data.get("hpi", {}) or {}
            ros = data.get("ros", {}) or {}
            asm = data.get("assessment", {}) or {}
            plan = data.get("plan", {}) or {}

            return SOAPNote(
                patient_id=context.patient.patient_id,
                visit_date=context.visit_date,
                chief_complaint=ChiefComplaint(
                    text=cc.get("text", "") or "(see dialog)",
                    duration=cc.get("duration") or None,
                ),
                hpi=HistoryOfPresentIllness(
                    onset=hpi.get("onset") or None,
                    quality=hpi.get("quality") or None,
                    severity=hpi.get("severity") or None,
                    timing=hpi.get("timing") or None,
                    associated_symptoms=hpi.get("associated_symptoms") or [],
                    narrative=hpi.get("narrative") or None,
                ),
                ros=ReviewOfSystems(
                    positives=ros.get("positives") or [],
                    pertinent_negatives=ros.get("pertinent_negatives") or [],
                ),
                assessment=Assessment(
                    primary=asm.get("primary") or "Working impression pending review",
                    differentials=asm.get("differentials") or [],
                    icd10_candidates=asm.get("icd10_candidates") or [],
                ),
                plan=Plan(
                    investigations=plan.get("investigations") or [],
                    prescriptions=plan.get("prescriptions") or [],
                    patient_education=plan.get("patient_education") or [],
                    follow_up=plan.get("follow_up") or None,
                    referrals=plan.get("referrals") or [],
                ),
            )
        except Exception as exc:  # pragma: no cover
            return _placeholder_soap(context, note=f"Schema error: {exc}")


def _placeholder_soap(context: VisitContext, note: str) -> SOAPNote:
    return SOAPNote(
        patient_id=context.patient.patient_id,
        visit_date=context.visit_date,
        chief_complaint=ChiefComplaint(text="(see dialog)"),
        hpi=HistoryOfPresentIllness(narrative=note),
        assessment=Assessment(
            primary="Pending review", differentials=[], icd10_candidates=[]
        ),
        plan=Plan(),
    )
