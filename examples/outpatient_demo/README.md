# Outpatient demo

A minimal Streamlit UI showing two agents in action:

1. **IntakeAgent** — reads prior chart notes, produces a one-paragraph brief
   and 3–6 high-yield questions to ask first.
2. **ConsultAgent** — reads a doctor-patient dialog and drafts a structured
   SOAP note for the physician to edit and sign.

The safety layer runs automatically and surfaces red flags above the output.

## Run

```bash
pip install -e .
streamlit run examples/outpatient_demo/app.py
```

Optional: set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` for real LLM output.
Without a key, the demo falls back to a deterministic mock so the UI still works.
