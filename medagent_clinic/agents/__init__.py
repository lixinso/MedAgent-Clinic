"""
Agent implementations — each one is a small, single-purpose unit.
"""

from .base import Agent, AgentOutput, AuditEntry
from .intake import IntakeAgent
from .consult import ConsultAgent

__all__ = ["Agent", "AgentOutput", "AuditEntry", "IntakeAgent", "ConsultAgent"]
