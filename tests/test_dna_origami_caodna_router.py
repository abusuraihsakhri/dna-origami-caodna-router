"""
Automated Pytest Test Suite for Dna Origami Caodna Router.
Domain: AI Drug Discovery, Structural Biology & Wet-Lab Robotics
Standard: wwPDB / IUPAC / OpenSMILES / ISAC Standards
"""
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agents.base import PHIGuard, AuditLogger, SecurityException, AuditTrail
from agents.models import SystemTaskPayload, UrgencyLevel, SystemIntegrityStatus
from agents.workers import InvariantQCWorker, SafetyEscalationWorker, ProtocolConformanceWorker
from agents.supervisor import SystemSupervisor
from cli import main


def test_phi_guard_enforcement():
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("Patient MRN-994827 blood culture positive for Staphylococcus")

    # Clean text passes
    PHIGuard.assert_no_phi("Analytical assay specimen KEY-001 optimal")


def test_specialized_workers():
    # Worker 1: QC Invariant
    p1 = SystemTaskPayload(task_id="T1", target_identifier="KEY-01", primary_metric=35.0)
    alerts1 = InvariantQCWorker.evaluate(p1)
    assert len(alerts1) == 1
    assert alerts1[0].urgency == UrgencyLevel.ELEVATED

    # Worker 2: Safety
    p2 = SystemTaskPayload(task_id="T2", target_identifier="KEY-02", primary_metric=10.0, is_critical_flag=True)
    alerts2 = SafetyEscalationWorker.evaluate(p2)
    assert len(alerts2) == 1
    assert alerts2[0].urgency == UrgencyLevel.CRITICAL_STAT

    # Worker 3: Protocol Conformance
    p3 = SystemTaskPayload(task_id="T3", target_identifier="KEY-03", primary_metric=10.0, status_descriptor="DISCORDANT_ANOMALY")
    alerts3 = ProtocolConformanceWorker.evaluate(p3)
    assert len(alerts3) == 1


def test_supervisor_consensus_and_audit():
    supervisor = SystemSupervisor(model_provider="mock")
    payload = SystemTaskPayload(
        task_id="TASK-PROD-01",
        target_identifier="KEY-PROD-01",
        primary_metric=12.0,
        secondary_metric=4.0,
        status_descriptor="NOMINAL"
    )
    dossier = supervisor.process_task(payload)
    assert dossier.overall_urgency == UrgencyLevel.ROUTINE
    assert dossier.integrity_status == SystemIntegrityStatus.VALIDATED
    assert dossier.audit_hash != ""

    # Verify cryptographic audit trail
    assert AuditLogger.verify_integrity() is True

    # CLI tests
    assert main(["audit", "--task-id", "CLI-TEST-01"]) == 0
    assert main(["chat", "Explain", "specifications"]) == 0
    assert main(["verify-audit"]) == 0


def test_input_validation_rejects_nan():
    """Test that NaN metric values are rejected."""
    with pytest.raises(ValueError, match="finite"):
        SystemTaskPayload(task_id="T-NAN", target_identifier="KEY-01", primary_metric=float("nan"))


def test_input_validation_rejects_infinity():
    """Test that Infinity metric values are rejected."""
    with pytest.raises(ValueError, match="finite"):
        SystemTaskPayload(task_id="T-INF", target_identifier="KEY-01", primary_metric=float("inf"))


def test_input_validation_rejects_empty_strings():
    """Test that empty string identifiers are rejected."""
    with pytest.raises(ValueError, match="empty"):
        SystemTaskPayload(task_id="", target_identifier="KEY-01", primary_metric=10.0)


def test_input_validation_strips_whitespace():
    """Test that string fields are stripped of whitespace."""
    payload = SystemTaskPayload(task_id="  T1  ", target_identifier="  KEY-01  ", primary_metric=10.0)
    assert payload.task_id == "T1"
    assert payload.target_identifier == "KEY-01"


def test_audit_trail_requires_secret_key(monkeypatch):
    """Test that AuditTrail requires a secret key."""
    monkeypatch.delenv("AUDIT_SECRET_KEY", raising=False)
    with pytest.raises(SecurityException, match="AUDIT_SECRET_KEY"):
        AuditTrail(secret_key="")
    with pytest.raises(SecurityException, match="AUDIT_SECRET_KEY"):
        AuditTrail(secret_key=None)


def test_audit_trail_rejects_short_key():
    """Test that AuditTrail rejects short secret keys."""
    with pytest.raises(SecurityException, match="32 characters"):
        AuditTrail(secret_key="short-key")


def test_audit_trail_verifies_signatures():
    """Test that audit trail verifies cryptographic signatures."""
    trail = AuditTrail(secret_key="test-secret-key-that-is-32-chars-long!!")
    entry = trail.log("test_actor", "test_tier", "TEST_EVENT", {"data": "test"})
    assert entry["current_hash"] != ""
    assert trail.verify_integrity() is True


def test_batch_cli_handles_missing_file():
    """Test that batch CLI handles missing input file gracefully."""
    result = main(["batch", "-i", "nonexistent_file.csv"])
    assert result == 1


def test_batch_cli_handles_invalid_csv():
    """Test that batch CLI handles invalid CSV gracefully."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("invalid csv content\nno,proper,headers\n")
        temp_path = f.name
    try:
        result = main(["batch", "-i", temp_path])
        # Should succeed but may skip rows with errors
        assert result == 0
    finally:
        os.unlink(temp_path)
