"""
IntakeAgent — runs before the patient enters.

Reads the patient's prior chart notes and produces:
  - a one-paragraph brief for the doctor
  - 3–6 high-yield questions to ask first
  - any red flags found in the prior notes

Doctor-in-the-loop: this is decision support. The doctor decides what
to actually ask.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from ..llm import chat
from ..safety import check as safety_check
from ..schema import VisitContext
from .base import Agent, AgentOutput, AuditEntry


PROMPT = """\
You are a medical scribe assistant helping a doctor prepare for an outpatient visit.

You are NOT making a diagnosis. You are summarizing prior notes and suggesting
what the doctor should ask first.

Patient context:
- Age: {age}
- Sex: {sex}
- Known conditions: {conditions}
- Current medications: {meds}
- Allergies: {allergies}

Prior chart notes (most recent first):
\"\"\"
{prior_notes}
\"\"\"

Visit type: {visit_type}

Return ONLY valid JSON with this shape:
{{
  "brief": "one paragraph (<= 80 words) summarizing the patient and the open clinical questions",
  "questions_to_ask": ["question 1", "question 2", "question 3"],
  "things_to_watch": ["red flag 1", "red flag 2"]
}}
"""


@dataclass
class IntakeResult:
    brief: str
    questions_to_ask: list[str] = field(default_factory=list)
    things_to_watch: list[str] = field(default_factory=list)


class IntakeAgent(Agent):
    name = "IntakeAgent"

    def __init__(self, prefer_provider: str | None = None):
        self.prefer_provider = prefer_provider

    def run(self, context: VisitContext) -> AgentOutput:
        p = context.patient
        prompt = PROMPT.format(
            age=p.age if p.age is not None else "unknown",
            sex=p.sex or "unknown",
            conditions=", ".join(p.known_conditions) or "none on record",
            meds=", ".join(p.current_medications) or "none on record",
            allergies=", ".join(p.allergies) or "none on record",
            prior_notes="\n\n".join(context.prior_notes) or "(no prior notes available)",
            visit_type=context.visit_type,
        )

        start = time.time()
        resp = chat(prompt, prefer=self.prefer_provider)
        latency_ms = int((time.time() - start) * 1000)

        result = self._parse(resp.text)

        # Run safety against the prior-notes corpus too — red flags in old
        # notes deserve attention before the patient walks in.
        flags = safety_check(
            patient_text="\n".join(context.prior_notes) if context.prior_notes else None
        )

        # Mock backend gives a fixed skeleton — confidence stays low so the
        # UI doesn't pretend this is real medical reasoning.
        confidence = 0.7 if resp.provider in ("openai", "anthropic") else 0.2

        summary = (
            result.brief[:140] + "…" if len(result.brief) > 140 else result.brief
        )

        return AgentOutput(
            agent=self.name,
            result=result,
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
    def _parse(text: str) -> IntakeResult:
        """Tolerant JSON parsing — LLMs sometimes wrap JSON in code fences."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()
        try:
            data = json.loads(cleaned)
        except Exception:
            return IntakeResult(
                brief=f"(could not parse LLM response) Raw: {text[:200]}",
                questions_to_ask=[],
                things_to_watch=[],
            )

        # Mock returns a 'soap_draft' instead of an intake brief; coerce.
        if "_mock" in data:
            return IntakeResult(
                brief=data.get("summary", "(mock) review prior notes manually."),
                questions_to_ask=data.get("questions_to_ask", []),
                things_to_watch=["(mock) demo only — set an API key for real output"],
            )

        return IntakeResult(
            brief=data.get("brief", ""),
            questions_to_ask=data.get("questions_to_ask", []),
            things_to_watch=data.get("things_to_watch", []),
        )
