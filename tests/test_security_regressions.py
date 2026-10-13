"""Focused security, API and deployment regressions."""
import pytest
from fastapi.testclient import TestClient

from agents.api import app
from agents.base import AuditTrail, SecurityException
from agents.llm_factory import LLMFactory
from agents.models import SystemTaskPayload
from agents.supervisor import SystemSupervisor

client = TestClient(app)


def test_nested_metadata_with_identifier_pattern_is_blocked():
    payload = SystemTaskPayload(
        task_id="T-123", target_identifier="SYNTHETIC",
        primary_metric=1.0, attributes={"nested": {"contact": "test@hospital.example"}},
    )
    with pytest.raises(SecurityException):
        SystemSupervisor().process_task(payload)


def test_api_rejects_nested_identifier_patterns(monkeypatch):
    monkeypatch.setenv("AUDIT_SECRET_KEY", "tests-only-very-long-signing-key-0123456789")
    res = client.post("/api/audit", json={
        "task_id": "T-1", "target_identifier": "SYNTHETIC",
        "primary_metric": 1, "attributes": {"note": "MRN:987654"},
    })
    assert res.status_code == 422


def test_audit_log_requires_independent_access_token(monkeypatch):
    monkeypatch.delenv("AUDIT_LOG_READ_TOKEN", raising=False)
    assert client.get("/api/audit/logs").status_code == 403
    token = "tests-only-independent-log-token-0123456789"
    monkeypatch.setenv("AUDIT_LOG_READ_TOKEN", token)
    assert client.get("/api/audit/logs").status_code == 403
    res = client.get("/api/audit/logs", headers={"Authorization": "Bearer " + token})
    assert res.status_code == 200
    assert "verified" in res.json()


def test_audit_log_copy_cannot_mutate_signed_records():
    trail = AuditTrail(secret_key="local-test-signing-key-012345678901234")
    trail.log("tester", "unit", "CHECK", {"key": "value"})
    exported = trail.get_trail()
    exported[0]["current_hash"] = "invalid"
    assert trail.verify_integrity()
    assert trail.get_trail()[0]["current_hash"] != "invalid"


def test_unsupported_inference_provider_is_not_misrepresented():
    with pytest.raises(ValueError, match="Unsupported model provider"):
        LLMFactory.create("openai")
    reply = LLMFactory.create("mock").invoke("test query")
    assert "No model inference or scientific validation" in reply


def test_health_degrades_without_signing_key(monkeypatch):
    monkeypatch.delenv("AUDIT_SECRET_KEY", raising=False)
    assert client.get("/health").status_code == 503


def test_web_ui_and_api_evaluation(monkeypatch):
    monkeypatch.setenv("AUDIT_SECRET_KEY", "tests-only-very-long-signing-key-0123456789")
    page = client.get("/")
    assert page.status_code == 200
    assert "Browser preview" in page.text
    result = client.post("/api/audit", json={
        "task_id": "T-2", "target_identifier": "SYNTHETIC",
        "primary_metric": 26, "secondary_metric": 13, "status_descriptor": "NOMINAL",
        "is_critical_flag": False,
    })
    assert result.status_code == 200
    data = result.json()
    assert data["overall_urgency"] == "ELEVATED_RISK"
    assert data["total_alerts"] == 2
    assert len(data["audit_hash"]) == 64
