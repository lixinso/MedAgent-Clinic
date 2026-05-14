"""
LLM router — single chat() entry point, multiple backends.

Today: OpenAI, Anthropic, and a deterministic mock for offline demos / tests.
Tomorrow: local models (HuatuoGPT / Qwen-Med / MedLM) added behind the same
interface so callers don't change.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str
    raw: Optional[dict] = None


def _try_openai(prompt: str, model: str = "gpt-4o-mini") -> Optional[LLMResponse]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return LLMResponse(
            text=resp.choices[0].message.content or "",
            model=model,
            provider="openai",
        )
    except Exception as exc:  # pragma: no cover - network path
        return LLMResponse(
            text=f"[openai-error] {exc}",
            model=model,
            provider="openai-error",
        )


def _try_anthropic(prompt: str, model: str = "claude-3-5-sonnet-latest") -> Optional[LLMResponse]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        return LLMResponse(
            text=resp.content[0].text if resp.content else "",
            model=model,
            provider="anthropic",
        )
    except Exception as exc:  # pragma: no cover
        return LLMResponse(
            text=f"[anthropic-error] {exc}",
            model=model,
            provider="anthropic-error",
        )


def _mock(prompt: str) -> LLMResponse:
    """
    Deterministic mock so the demo always runs, even without API keys.

    Returns a JSON skeleton that downstream agents can parse. Good enough to
    show shape; doctors should never trust this output — it is a placeholder.
    """
    skeleton = {
        "_mock": True,
        "_note": "MOCK LLM — set OPENAI_API_KEY or ANTHROPIC_API_KEY for real output.",
        "summary": (
            "Patient presents with a chief complaint requiring further history. "
            "Key items to clarify (mock output)."
        ),
        "questions_to_ask": [
            "When did the symptoms start?",
            "Any associated fever, weight loss, or night sweats?",
            "Any change to existing medications?",
            "Any prior similar episodes?",
        ],
        "soap_draft": {
            "chief_complaint": {"text": "(see dialog)", "duration": None},
            "hpi": {"narrative": "Mock HPI — replace with real LLM output."},
            "assessment": {
                "primary": "Working impression pending physician review",
                "differentials": ["Differential A", "Differential B"],
            },
            "plan": {
                "investigations": ["Basic labs as indicated"],
                "patient_education": ["Return precautions reviewed"],
                "follow_up": "1 week",
            },
        },
    }
    return LLMResponse(
        text=json.dumps(skeleton, ensure_ascii=False, indent=2),
        model="mock-1",
        provider="mock",
    )


def chat(prompt: str, prefer: Optional[str] = None) -> LLMResponse:
    """
    Route a prompt to the first available backend.

    prefer: 'openai' | 'anthropic' | 'mock' | None
    """
    if prefer == "mock":
        return _mock(prompt)

    if prefer == "openai":
        r = _try_openai(prompt)
        return r or _mock(prompt)

    if prefer == "anthropic":
        r = _try_anthropic(prompt)
        return r or _mock(prompt)

    # Auto: openai → anthropic → mock
    r = _try_openai(prompt)
    if r and r.provider == "openai":
        return r
    r = _try_anthropic(prompt)
    if r and r.provider == "anthropic":
        return r
    return _mock(prompt)
