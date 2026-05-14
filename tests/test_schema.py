from medagent_clinic.schema import (
    Assessment,
    ChiefComplaint,
    HistoryOfPresentIllness,
    Patient,
    Plan,
    SOAPNote,
)


def test_soap_to_markdown_minimal():
    note = SOAPNote(
        patient_id="P-001",
        chief_complaint=ChiefComplaint(text="Cough", duration="3 days"),
        hpi=HistoryOfPresentIllness(narrative="Dry cough, no fever."),
        assessment=Assessment(primary="Likely viral URI"),
        plan=Plan(patient_education=["rest, fluids, return precautions"]),
    )
    md = note.to_markdown()
    assert "SOAP Note" in md
    assert "Cough" in md
    assert "viral URI" in md
    assert "Requires physician review" in md


def test_patient_minimal():
    p = Patient(patient_id="P-001")
    assert p.known_conditions == []
    assert p.current_medications == []
