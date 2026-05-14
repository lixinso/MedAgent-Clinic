# MedAgent-Clinic

> Open-source AI agent toolkit for outpatient clinics.
> Built so doctors can spend less time on charts and more time on patients.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)]()

---

## 🩺 The problem

Outpatient doctors today spend roughly **two hours a day** writing chart notes after seeing patients. EHR systems haven't meaningfully changed since 1990. Voice scribe products lock data into proprietary clouds at $1,500–3,000 per doctor per month.

There should be an open-source alternative — small, auditable, self-hostable, and built for the way an outpatient visit actually flows.

---

## 🤖 What MedAgent-Clinic does

A small, composable Python framework that runs alongside an outpatient doctor and helps with the parts of the visit that aren't human-to-human:

| Agent | What it does | Who's in the loop |
|---|---|---|
| **IntakeAgent** | Summarize prior chart notes & flag what to ask first | Doctor reviews before patient enters |
| **ConsultAgent** | Listen to the visit, draft structured SOAP in real time | Doctor confirms / edits before save |
| **PrescriptionAgent** | Suggest orders, labs, drug dose & flag interactions | Doctor signs every order |
| **HandoffAgent** | Generate referral letters, follow-up notes, patient summary | Doctor reviews & sends |

The doctor stays in the loop on every clinical decision. The agents handle writing.

---

## 🧭 Design principles

1. **Doctor-in-the-loop, always.** No agent ships an order without a human signature.
2. **Schema first, prompts second.** Every output is structured (SOAP / FHIR / ICD-10 ready).
3. **Safety as a first-class module.** Red-flag detection, drug interactions, audit log on every LLM call.
4. **Self-hostable from day 1.** Runs on a laptop or behind a hospital firewall. No data has to leave.
5. **Small enough to read.** Each agent module aims to stay under 300 lines. The whole core should be auditable in an afternoon.
6. **Clarity over cleverness.** No hidden magic.

---

## 🚀 Quick start (5 minutes)

```bash
git clone https://github.com/lixinso/MedAgent-Clinic.git
cd MedAgent-Clinic
pip install -e .

# Set your LLM key (OpenAI / Claude / local model)
export OPENAI_API_KEY=sk-...

# Run the outpatient demo
streamlit run examples/outpatient_demo/app.py
```

Opens a browser at `http://localhost:8501` with a simulated outpatient visit.

---

## 📦 Project structure

```
MedAgent-Clinic/
├── medagent_clinic/          # Core framework (target: < 1500 LoC total)
│   ├── agents/               # IntakeAgent, ConsultAgent, ...
│   ├── schema/               # SOAP, HPI, FHIR types
│   ├── safety/               # Red flags, drug interactions, audit
│   ├── llm/                  # LLM router (OpenAI / Anthropic / local)
│   └── integration/          # HIS / EHR / voice adapters
├── examples/
│   └── outpatient_demo/      # Streamlit demo — start here
├── tests/
└── docs/
```

---

## 🏥 Who this is for

- **Doctors** who want their evenings back.
- **Clinic IT teams** who need an EHR-adjacent AI tool that doesn't ship patient data offshore.
- **Engineers** building medical AI products — use this as a foundation, not as competition.
- **Researchers** studying clinical LLM safety, schema design, and human-AI collaboration in medicine.

---

## 🛣️ Status

This project is in early alpha. The architecture is documented in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). The first runnable example is in `examples/outpatient_demo/`.

If you're a clinician, an AI engineer, or both — please open an issue. This works best as a community project.

---

## ⚠️ Disclaimer

MedAgent-Clinic is **decision-support software**, not a medical device. It does not provide diagnoses or treatments. Every clinical action requires a licensed physician's confirmation. Use at your own risk and in compliance with local regulations.

---

## 📜 License

[MIT](LICENSE) — free for personal, academic, and commercial use.
