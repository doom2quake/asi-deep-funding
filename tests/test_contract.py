"""The service contract is the milestone-1 product, so it is pinned tightly:
typed request/response round-trip, an audit object on every response, a
tamper-evident content hash, and the invariant that a proposed fix is never
returned pre-approved.
"""

from __future__ import annotations

from ledgerkeep.contract import (
    CONTRACT_VERSION,
    Attribution,
    AuditObject,
    GuardrailDecision,
    Impact,
    InvestigationRequest,
    InvestigationResponse,
    ProposedFix,
)


def test_request_defaults_are_the_simplest_call():
    req = InvestigationRequest()
    assert req.metric == "settled_revenue"
    assert req.z_threshold == 2.5
    assert req.contract_version == CONTRACT_VERSION


def test_request_round_trips_through_dict():
    req = InvestigationRequest(metric="orders", z_threshold=3.0, request_id="abc")
    again = InvestigationRequest.from_dict(req.to_dict())
    assert again == req


def test_request_from_dict_ignores_unknown_keys():
    req = InvestigationRequest.from_dict({"metric": "x", "bogus": 1, "z_threshold": 4.0})
    assert req.metric == "x"
    assert req.z_threshold == 4.0


def _sample_response() -> InvestigationResponse:
    audit = AuditObject(
        run_id="run-1", status="acted", domain="finance",
        guardrails=[GuardrailDecision("CONTENT_SAFETY", "clean", "attribution: clean"),
                    GuardrailDecision("ACTION_LIMITER", "allowed", "propose: ok")],
    )
    audit.content_hash = audit.compute_hash()
    return InvestigationResponse(
        audit=audit, status="acted", anomaly_found=True,
        anomaly={"metric": "settled_revenue"},
        attribution=Attribution(cause="EMEA collapsed"),
        impact=Impact(headline="lost 146k", lost_revenue=146014.0),
        proposed_fix=ProposedFix(title="fail back", domain="finance"),
        verification="clears", request_id="abc",
    )


def test_response_round_trips_through_dict():
    resp = _sample_response()
    again = InvestigationResponse.from_dict(resp.to_dict())
    assert again.audit.run_id == "run-1"
    assert again.attribution.cause == "EMEA collapsed"
    assert again.impact.lost_revenue == 146014.0
    assert again.proposed_fix.title == "fail back"
    assert again.status == "acted"


def test_audit_object_is_mandatory_on_the_response():
    # The dataclass has no default for `audit`; a response cannot be built without it.
    import pytest

    with pytest.raises(TypeError):
        InvestigationResponse()  # type: ignore[call-arg]


def test_content_hash_is_deterministic_and_covers_the_chain():
    audit = AuditObject(run_id="run-1", status="acted", domain="finance",
                        guardrails=[GuardrailDecision("CONTENT_SAFETY", "clean")])
    h1 = audit.compute_hash()
    h2 = audit.compute_hash()
    assert h1 == h2
    assert len(h1) == 64  # sha256 hex


def test_content_hash_changes_when_a_guardrail_decision_is_edited():
    audit = AuditObject(run_id="run-1", status="acted",
                        guardrails=[GuardrailDecision("CONTENT_SAFETY", "clean")])
    before = audit.compute_hash()
    audit.guardrails[0].outcome = "flagged"  # tamper with the recorded decision
    after = audit.compute_hash()
    assert before != after


def test_content_hash_changes_with_the_extra_payload():
    audit = AuditObject(run_id="run-1", status="acted")
    base = audit.compute_hash()
    with_extra = audit.compute_hash({"impact": {"lost_revenue": 146014.0}})
    assert base != with_extra


def test_proposed_fix_defaults_to_unapproved():
    assert ProposedFix().approved is False


def test_guardrail_names_are_sorted_and_unique():
    audit = AuditObject(run_id="r", guardrails=[
        GuardrailDecision("ACTION_LIMITER", "allowed"),
        GuardrailDecision("CONTENT_SAFETY", "clean"),
        GuardrailDecision("ACTION_LIMITER", "allowed"),
    ])
    assert audit.guardrail_names() == ["ACTION_LIMITER", "CONTENT_SAFETY"]
