from medagent_clinic.safety import (
    detect_drug_interactions,
    detect_red_flags,
    check,
)


def test_red_flag_chest_pain():
    flags = detect_red_flags("Patient reports sudden crushing chest pain radiating to arm.")
    assert flags
    assert flags[0].severity == "urgent"
    assert flags[0].category == "red_flag"


def test_red_flag_no_match():
    assert detect_red_flags("Mild seasonal cough, no fever, sleeping well.") == []


def test_red_flag_dedup():
    flags = detect_red_flags("chest pain, chest pain, chest pain")
    assert len(flags) == 1


def test_drug_interaction_warfarin_aspirin():
    flags = detect_drug_interactions(["aspirin"], ["warfarin"])
    assert flags
    assert flags[0].category == "drug_interaction"


def test_no_interaction():
    assert detect_drug_interactions(["amoxicillin"], ["acetaminophen"]) == []


def test_combined_check():
    flags = check(
        patient_text="patient reports facial droop and slurred speech",
        proposed_prescriptions=["aspirin"],
        current_medications=["warfarin"],
    )
    cats = {f.category for f in flags}
    assert "red_flag" in cats
    assert "drug_interaction" in cats
