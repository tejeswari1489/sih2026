import pytest
from backend.services.urgency_service import check_rule_based_flags, evaluate_urgency

def test_rule_based_flags_cardiac():
    text = "Patient has acute chest pain with shortness of breath and sweating"
    flagged, reason = check_rule_based_flags(text)
    assert flagged is True
    assert "cardiac" in reason.lower() or "chest" in reason.lower()

def test_rule_based_flags_stroke():
    text = "Patient reports sudden slurred speech and facial droop since 1 hour ago"
    flagged, reason = check_rule_based_flags(text)
    assert flagged is True
    assert "stroke" in reason.lower()

def test_rule_based_flags_anaphylaxis():
    text = "Patient ate peanuts and has immediate throat swelling and difficulty breathing"
    flagged, reason = check_rule_based_flags(text)
    assert flagged is True
    assert "anaphylaxis" in reason.lower() or "breathing" in reason.lower()

def test_rule_based_flags_normal():
    text = "Patient has mild headache and mild throat irritation since 2 days. No fever, normal breathing."
    flagged, reason = check_rule_based_flags(text)
    assert flagged is False
    assert reason == ""

def test_evaluate_urgency_rule_priority():
    result = evaluate_urgency("Chest pain with shortness of breath", "Duration 2 hours, radiating to left arm")
    assert result["urgency_flag"] is True
    assert "[Rule]" in result["urgency_reason"]
