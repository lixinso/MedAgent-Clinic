"""
Agent base contract — every MedAgent obeys this protocol.

An agent is a pure function: ClinicalContext in, AgentOutput out.
No side effects on the EHR. The doctor decides what gets saved.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..schema import VisitContext
from ..safety import SafetyFlag


@dataclass
class AuditEntry:
    """One LLM call, captured for review and compliance."""

    agent: str
    model: str
    provider: str
    prompt: str
    response: str
    latency_ms: int
    started_at: float = field(default_factory=time.time)


@dataclass
class AgentOutput:
    agent: str
    result: Any  # Pydantic model or dict, agent-specific
    summary: str  # One-line summary for the doctor's UI
    confidence: float  # 0.0 – 1.0
    requires_review: bool = True
    safety_flags: list[SafetyFlag] = field(default_factory=list)
    audit_trail: list[AuditEntry] = field(default_factory=list)


class Agent(Protocol):
    name: str

    def run(self, context: VisitContext) -> AgentOutput: ...
