# Architecture

> **TL;DR** — MedAgent-Clinic is a thin layer of typed, auditable agents
> that sit between a clinician and an LLM. The clinician is always
> the decision-maker; the agents handle the writing.

---

## 1. Why "agents" and not "one big prompt"?

A single prompt that does "intake + consult + prescription + handoff"
fails for three reasons:

1. **Hard to audit** — when something goes wrong, you can't tell which step.
2. **Hard to test** — every change risks regressing every use case.
3. **Hard to swap models** — different agents have different latency / cost / safety needs.

Each MedAgent is a small, single-purpose unit:

```
┌──────────────────────────────────────────────────────────────┐
│  Doctor (always in loop)                                     │
└──┬────────────┬──────────────┬─────────────────┬─────────────┘
   ▼            ▼              ▼                 ▼
IntakeAgent  ConsultAgent   PrescriptionAgent  HandoffAgent
   │            │              │                 │
   └────────────┴──────┬───────┴─────────────────┘
                       ▼
                  Safety layer (red flags, drug interactions, audit)
                       ▼
                  LLM router (OpenAI / Claude / local)
```

---

## 2. Agent contract

Every agent implements the same interface:

```python
class Agent(Protocol):
    def run(self, context: ClinicalContext) -> AgentOutput:
        """Pure function. No side effects. Returns structured output."""
```

- `ClinicalContext` is a typed Pydantic model (patient info, prior notes, current visit).
- `AgentOutput` always includes:
  - `result`: the actual content (SOAP draft, prescription, etc.)
  - `confidence`: 0.0 – 1.0
  - `requires_review`: bool — if true, agent is flagging this for the doctor
  - `audit_trail`: list of LLM calls + prompts + responses
  - `safety_flags`: list of triggered red flags (empty if clean)

The doctor's UI shows `result`, but `safety_flags` and `requires_review`
gate whether anything is auto-saved.

---

## 3. Schema-first design

We use Pydantic models for every clinical concept:

- `ChiefComplaint`
- `HistoryOfPresentIllness` (HPI — OPQRST structured)
- `ReviewOfSystems`
- `PhysicalExam`
- `Assessment` (with ICD-10 codes)
- `Plan` (orders, labs, prescriptions, follow-up)
- `SOAPNote` (composition of all above)

Why schema-first?
- Output is **machine-readable** → can be exported to FHIR, MES, HIS.
- Bugs are caught at parse time, not at chart-review time.
- Prompts become **render(schema) + parse(response)**, not free-form text.

---

## 4. Safety layer

Three independent guardrails run **after** every agent output, **before** the doctor sees it:

1. **Red-flag detector** — pattern match + LLM check for life-threatening symptoms
   (chest pain + radiation, sudden severe headache, suspected stroke, etc.).
   If triggered → output is annotated `URGENT`, doctor is notified prominently.
2. **Drug interaction checker** — every prescription is cross-checked against the
   patient's current medication list (initially via rule table, later via LLM + pharmacopoeia).
3. **Audit logger** — every LLM call (model, prompt, response, latency) is
   persisted to a tamper-evident log. Required for clinical / regulatory review.

---

## 5. LLM router

The `llm/` module exposes a single `chat()` function that takes a
provider hint (or none). Routing logic:

- Default: OpenAI GPT-4-class model
- Latency-sensitive (intake summary): smaller / cheaper model
- Privacy-sensitive (full visit transcript): local model preferred (HuatuoGPT, MedLM, Qwen-Med)
- Fallback: explicit `requires_review=True` if no model is available

---

## 6. Integration adapters

Real clinics live in HIS / EHR systems. The `integration/` module provides:

- `his_adapter` — pull patient context, push completed SOAP back
- `voice` — Whisper / iFlytek for visit audio → text
- `fhir` — export structured outputs as FHIR resources

We start with **mock adapters** so the demo runs standalone. Real adapters
are added per partner deployment.

---

## 7. Why open source?

Three reasons:

1. **Trust** — clinicians and IT teams need to audit what the AI is doing.
   Closed-source EHR-AI vendors lose this fight.
2. **Distribution** — small clinics can't afford $3k/doctor/month for proprietary scribes.
3. **Velocity** — the medical AI space moves fast; a public codebase moves faster than any one vendor.

The business model (later) is around enterprise deployment, support, and
hospital-grade integrations — not around hiding the core.

---

## 8. What this project is **not**

- ❌ Not a diagnostic AI. It does not tell doctors what diagnosis to make.
- ❌ Not a patient-facing chatbot. The patient never talks to the agent directly.
- ❌ Not a replacement for an EHR. It writes *into* an EHR.
- ❌ Not a medical device under FDA / NMPA classification (today). It's
  decision-support software with a doctor in the loop on every action.

---

## 9. Current status

This document describes the **target architecture**, not the current state.
See [README.md](../README.md) for the 8-week roadmap and what's actually built today.
