"""
Safety layer — runs after every agent output, before the doctor sees it.

This module exists separately from the agents on purpose: any agent's
output passes through these checks, so a bug in one agent can't bypass
red-flag detection.

v0 is intentionally simple: pattern-based red flags + a small drug
interaction table. Real systems will swap in LLM-based detectors and
pharmacopeia lookups behind the same interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


# Minimal, deliberately conservative red-flag patterns.
# Any of these in patient text should prompt a human-priority alert.
RED_FLAG_PATTERNS: list[tuple[str, str]] = [
    ("chest pain", "Possible acute coronary syndrome — escalate to physician immediately."),
    ("crushing chest", "Possible acute coronary syndrome — escalate immediately."),
    ("worst headache", "Possible subarachnoid hemorrhage — escalate immediately."),
    ("sudden severe headache", "Possible subarachnoid hemorrhage — escalate immediately."),
    ("slurred speech", "Possible stroke — activate stroke pathway."),
    ("facial droop", "Possible stroke — activate stroke pathway."),
    ("one-sided weakness", "Possible stroke — activate stroke pathway."),
    ("difficulty breathing", "Respiratory distress — assess airway and oxygenation."),
    ("shortness of breath at rest", "Respiratory distress — assess immediately."),
    ("blood in stool", "GI bleed — assess hemodynamics, escalate if unstable."),
    ("blood in vomit", "Upper GI bleed — escalate immediately."),
    ("hematemesis", "Upper GI bleed — escalate immediately."),
    ("suicidal", "Mental-health emergency — do not leave patient alone, escalate."),
    ("self-harm", "Mental-health emergency — do not leave patient alone, escalate."),
    ("anaphylaxis", "Anaphylaxis — IM epinephrine, escalate."),
    ("loss of consciousness", "Syncope or worse — escalate, full workup."),
]


@dataclass
class SafetyFlag:
    """One safety alert raised against an agent output or patient input."""

    severity: str  # 'urgent' | 'warning' | 'info'
    category: str  # 'red_flag' | 'drug_interaction' | 'allergy' | ...
    message: str
    matched_text: str | None = None


def detect_red_flags(text: str | None) -> list[SafetyFlag]:
    """Pattern-scan free-text for red-flag phrases. Conservative by design."""
    if not text:
        return []
    lowered = text.lower()
    flags: list[SafetyFlag] = []
    seen: set[str] = set()
    for pattern, message in RED_FLAG_PATTERNS:
        if pattern in lowered and pattern not in seen:
            seen.add(pattern)
            flags.append(
                SafetyFlag(
                    severity="urgent",
                    category="red_flag",
                    message=message,
                    matched_text=pattern,
                )
            )
    return flags


# Tiny illustrative interaction table. Replace with a real pharmacopeia.
DRUG_INTERACTIONS: dict[tuple[str, str], str] = {
    ("warfarin", "aspirin"): "Increased bleeding risk — review indication.",
    ("warfarin", "ibuprofen"): "Increased bleeding risk — prefer acetaminophen.",
    ("warfarin", "nsaid"): "Increased bleeding risk — prefer acetaminophen.",
    ("ssri", "tramadol"): "Serotonin syndrome risk — review necessity.",
    ("metformin", "iv contrast"): "Hold metformin around contrast administration.",
    ("clopidogrel", "omeprazole"): "Reduced clopidogrel efficacy — consider pantoprazole.",
}


def _norm(name: str) -> str:
    return name.strip().lower()


def detect_drug_interactions(
    proposed: Iterable[str], existing: Iterable[str]
) -> list[SafetyFlag]:
    """Cross-check proposed prescriptions against current meds. v0 = exact name match."""
    flags: list[SafetyFlag] = []
    proposed_n = [_norm(p) for p in proposed]
    existing_n = [_norm(e) for e in existing]
    for p in proposed_n:
        for e in existing_n:
            key = tuple(sorted([p, e]))
            for (a, b), msg in DRUG_INTERACTIONS.items():
                pair = tuple(sorted([a, b]))
                if pair == key:
                    flags.append(
                        SafetyFlag(
                            severity="warning",
                            category="drug_interaction",
                            message=msg,
                            matched_text=f"{p} + {e}",
                        )
                    )
    return flags


def check(
    patient_text: str | None = None,
    proposed_prescriptions: Iterable[str] | None = None,
    current_medications: Iterable[str] | None = None,
) -> list[SafetyFlag]:
    """One-stop check for the layers above."""
    flags: list[SafetyFlag] = []
    if patient_text:
        flags.extend(detect_red_flags(patient_text))
    if proposed_prescriptions and current_medications:
        flags.extend(
            detect_drug_interactions(proposed_prescriptions, current_medications)
        )
    return flags
