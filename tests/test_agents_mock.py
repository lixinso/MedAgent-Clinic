from medagent_clinic.agents import IntakeAgent, ConsultAgent
from medagent_clinic.schema import Patient, VisitContext


def _ctx() -> VisitContext:
    return VisitContext(
        patient=Patient(
            patient_id="P-001",
            age=58,
            sex="M",
            known_conditions=["hypertension"],
            current_medications=["lisinopril 20mg daily"],
        ),
        prior_notes=["Last visit: BP controlled. Continue current regimen."],
        raw_dialog=(
            "Doctor: How are you?\nPatient: My knee aches when I climb stairs."
        ),
    )


def test_intake_runs_with_mock():
    out = IntakeAgent(prefer_provider="mock").run(_ctx())
    assert out.agent == "IntakeAgent"
    assert out.requires_review is True
    assert out.result is not None
    assert out.audit_trail and out.audit_trail[0].provider == "mock"


def test_consult_runs_with_mock():
    out = ConsultAgent(prefer_provider="mock").run(_ctx())
    assert out.agent == "ConsultAgent"
    assert out.result is not None
    assert out.result.patient_id == "P-001"
    md = out.result.to_markdown()
    assert "SOAP Note" in md
