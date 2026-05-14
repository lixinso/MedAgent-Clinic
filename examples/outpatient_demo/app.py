"""
Outpatient demo — minimal Streamlit UI showing IntakeAgent + ConsultAgent + safety.

Run:
    streamlit run examples/outpatient_demo/app.py

Without an API key, the demo runs against a deterministic mock backend
so the UI still works for screenshots / testing.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow running without `pip install -e .`
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from medagent_clinic.agents import ConsultAgent, IntakeAgent  # noqa: E402
from medagent_clinic.schema import Patient, VisitContext  # noqa: E402


SAMPLE_PRIOR_NOTE = """\
2026-04-12 follow-up: 58 y/o male, hypertension and type 2 diabetes. BP 138/86 today.
HbA1c trending down (7.2 → 6.9). Continue metformin 1000 mg BID, lisinopril 20 mg daily.
Reports occasional left-knee discomfort with stairs. Advised PT and weight management.
Return in 3 months for diabetes follow-up.
"""

SAMPLE_DIALOG = """\
Doctor: Good morning. What brings you in today?
Patient: Doc, I've been getting this dull ache in my left knee for about 2 weeks.
        It's worse going up stairs.
Doctor: Any swelling or redness?
Patient: A little swelling at the end of the day. No redness.
Doctor: Any fever, or did you injure it?
Patient: No fever. I don't remember any specific injury.
Doctor: How is your blood sugar?
Patient: I've been better. I missed my metformin a few times last week.
Doctor: Okay. How's your blood pressure at home?
Patient: Around 130 over 80, mostly.
Doctor: Any chest pain, shortness of breath, or new symptoms?
Patient: No, none of that.
Doctor: Got it. Let me examine your knee.
"""


def _provider_status() -> str:
    if os.getenv("OPENAI_API_KEY"):
        return "🟢 OpenAI key detected"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "🟢 Anthropic key detected"
    return "🟡 No API key — running mock backend (set OPENAI_API_KEY or ANTHROPIC_API_KEY for real output)"


def main() -> None:
    st.set_page_config(page_title="MedAgent-Clinic — Outpatient demo", layout="wide")
    st.title("🩺 MedAgent-Clinic — Outpatient demo")
    st.caption(
        "Open-source AI agent toolkit for outpatient clinics. "
        "Doctor-in-the-loop on every decision."
    )
    st.info(_provider_status())

    with st.sidebar:
        st.header("Patient")
        patient_id = st.text_input("Patient ID (anonymized)", "P-001")
        age = st.number_input("Age", min_value=0, max_value=130, value=58)
        sex = st.selectbox("Sex", ["M", "F", "other", "unknown"], index=0)
        conditions = st.text_input(
            "Known conditions (comma-separated)", "hypertension, type 2 diabetes"
        )
        meds = st.text_input(
            "Current medications (comma-separated)",
            "metformin 1000mg BID, lisinopril 20mg daily",
        )
        allergies = st.text_input("Allergies", "NKDA")
        st.divider()
        st.caption("Switch backend (auto = best available)")
        prefer = st.selectbox("Backend", ["auto", "openai", "anthropic", "mock"], index=0)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Prior chart notes")
        prior_notes = st.text_area(
            "One note per blank line (most recent first)",
            value=SAMPLE_PRIOR_NOTE,
            height=200,
        )
    with col2:
        st.subheader("Today's dialog")
        dialog = st.text_area(
            "Doctor-patient dialog (typed or transcribed)",
            value=SAMPLE_DIALOG,
            height=200,
        )

    patient = Patient(
        patient_id=patient_id,
        age=age,
        sex=sex,
        known_conditions=[c.strip() for c in conditions.split(",") if c.strip()],
        current_medications=[m.strip() for m in meds.split(",") if m.strip()],
        allergies=[a.strip() for a in allergies.split(",") if a.strip()],
    )
    context = VisitContext(
        patient=patient,
        prior_notes=[n.strip() for n in prior_notes.split("\n\n") if n.strip()],
        raw_dialog=dialog,
    )
    prefer_provider = None if prefer == "auto" else prefer

    run_intake = st.button("1️⃣ Run IntakeAgent (pre-visit brief)")
    run_consult = st.button("2️⃣ Run ConsultAgent (draft SOAP)")
    run_both = st.button("⚡ Run both")

    if run_intake or run_both:
        st.divider()
        st.subheader("IntakeAgent output")
        with st.spinner("Reading prior notes…"):
            out = IntakeAgent(prefer_provider=prefer_provider).run(context)
        _render_output(out, kind="intake")

    if run_consult or run_both:
        st.divider()
        st.subheader("ConsultAgent output")
        with st.spinner("Drafting SOAP…"):
            out = ConsultAgent(prefer_provider=prefer_provider).run(context)
        _render_output(out, kind="consult")

    st.divider()
    st.caption(
        "⚠️ Decision-support only. Not a medical device. Every clinical action "
        "requires a licensed physician's confirmation."
    )


def _render_output(out, kind: str) -> None:
    cols = st.columns([3, 1])
    with cols[0]:
        if kind == "intake" and out.result is not None:
            st.markdown(f"**Brief:** {out.result.brief}")
            if out.result.questions_to_ask:
                st.markdown("**Suggested questions:**")
                for q in out.result.questions_to_ask:
                    st.markdown(f"- {q}")
            if out.result.things_to_watch:
                st.markdown("**Things to watch:**")
                for t in out.result.things_to_watch:
                    st.markdown(f"- {t}")
        elif kind == "consult" and out.result is not None:
            st.markdown(out.result.to_markdown())
        else:
            st.warning(out.summary or "No result.")
    with cols[1]:
        st.metric("Confidence", f"{out.confidence:.0%}")
        st.markdown("**Requires review**")
        st.markdown("✅ Yes" if out.requires_review else "❌ No")

    if out.safety_flags:
        st.error(
            "🚨 Safety flags:\n"
            + "\n".join(
                f"- **[{f.severity.upper()}] {f.category}** — {f.message}"
                + (f" _(matched: {f.matched_text})_" if f.matched_text else "")
                for f in out.safety_flags
            )
        )

    with st.expander("Audit trail (LLM calls)"):
        for entry in out.audit_trail:
            st.markdown(
                f"- **{entry.agent}** via `{entry.provider}/{entry.model}` "
                f"({entry.latency_ms} ms)"
            )


if __name__ == "__main__":
    main()
