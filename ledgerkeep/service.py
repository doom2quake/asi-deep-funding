"""The Ledgerkeep service: one guardrailed investigation, contract in, contract out.

``run_service`` is the whole product for milestone 1. It takes an
``InvestigationRequest``, runs the deterministic offline loop against the fixture
ledger, enforces every guardrail from the vendored ``agent_core`` control plane,
records each decision by name on a durable run document, and returns an
``InvestigationResponse`` whose ``AuditObject`` lets the caller verify the chain
from *a number moved* to *this proposed fix*.

The loop, in order:

1. **Detect** the settled-revenue drop by trailing z-score (fixture ledger).
2. **Attribute** it to a specific change via a deterministic rule over the
   change-event log. That attribution text is screened by ``CONTENT_SAFETY``
   before anything downstream is allowed to trust it; a flagged run is
   quarantined and returns with no proposed fix.
3. **Route** the incident through the domain classifier so the audit trail
   records the classified domain (finance / infra / security ...).
4. **Quantify** the loss to the dollar.
5. **Propose** the one-line fix. It is returned ``approved=False``: a human owns
   the merge. Recording the proposal passes the ``ACTION_LIMITER`` guardrail.
6. **Verify** by re-reading the metric after a fixture failover, exactly as the
   next live cycle would after a real remediation.

Nothing in this module reaches the network. The ASI / Fetch.ai marketplace
adapter wraps this function; it does not replace any of the logic here.
"""

from __future__ import annotations

from typing import Optional

from .agent_core import (
    ActionLimiter,
    ActionPolicy,
    KeywordClassifier,
    StateStore,
    screen_content,
)
from .config import settings as default_settings
from .config import LedgerkeepSettings
from .contract import (
    Attribution,
    AuditObject,
    GuardrailDecision,
    Impact,
    InvestigationRequest,
    InvestigationResponse,
    ProposedFix,
)
from . import ledger

# One process-wide limiter, so a scheduled deployment is throttled across calls.
_limiter = ActionLimiter(ActionPolicy.from_env("LEDGERKEEP"))
_classifier = KeywordClassifier()


def _store(settings: LedgerkeepSettings) -> StateStore:
    """A durable run store. In-memory by default (offline, keyless)."""
    return StateStore.create(settings)


def _guardrail_objects(run_doc: dict) -> list[GuardrailDecision]:
    return [
        GuardrailDecision(name=g.get("name", ""), outcome=g.get("outcome", ""),
                          detail=g.get("detail", ""))
        for g in run_doc.get("guardrails", []) or []
    ]


def run_service(
    request: Optional[InvestigationRequest] = None,
    *,
    settings: Optional[LedgerkeepSettings] = None,
) -> InvestigationResponse:
    """Run one guardrailed investigation and return the typed response.

    Deterministic and offline: given the same fixture ledger and request, the
    response (including the audit ``content_hash``) is reproducible.
    """
    request = request or InvestigationRequest()
    settings = settings or default_settings
    store = _store(settings)

    ledger.reset()

    run_id = store.start_run(trigger={"source": "run_service", "metric": request.metric,
                                      "request_id": request.request_id, "note": request.note})
    _limiter.reset_cycle(run_id)

    audit = AuditObject(run_id=run_id, started_at=store.get(run_id).get("started_at", ""))

    def _finish(status: str, **kw) -> InvestigationResponse:
        store.set_status(run_id, status)
        run_doc = store.get(run_id) or {}
        audit.status = status
        audit.domain = kw.pop("domain", audit.domain)
        audit.finished_at = run_doc.get("updated_at", "")
        audit.guardrails = _guardrail_objects(run_doc)
        audit.recurrence = run_doc.get("recurrence")
        extra = {
            "anomaly": kw.get("anomaly"),
            "attribution": kw["attribution"].__dict__ if kw.get("attribution") else None,
            "impact": kw["impact"].__dict__ if kw.get("impact") else None,
            "proposed_fix": kw["proposed_fix"].__dict__ if kw.get("proposed_fix") else None,
        }
        audit.content_hash = audit.compute_hash(extra)
        return InvestigationResponse(
            audit=audit, status=status, request_id=request.request_id,
            delivery_mode="offline_fixture" if settings.offline else "live", **kw,
        )

    # --- 1. detect -----------------------------------------------------------
    anomaly = ledger.detect_anomaly(z_threshold=request.z_threshold)
    if not anomaly:
        return _finish("no_anomaly", anomaly_found=False)
    store.set_data(run_id, "anomaly", anomaly)

    # --- 2. attribute --------------------------------------------------------
    cells = ledger.breakdown_by_cell()
    worst = max(cells, key=lambda c: (c["declined"] / c["attempted"]) if c["attempted"] else 0.0)
    fail_rate = worst["declined"] / worst["attempted"] if worst["attempted"] else 0.0
    events = ledger.change_events(on_date=anomaly["date"], region=worst["region"])
    culprit = next((e for e in events if e.get("gateway") == worst["gateway"]), None)

    cause_text = (
        f"{worst['region']} settled revenue collapsed because the {worst['gateway']} "
        f"gateway is declining {fail_rate * 100:.0f}% of {worst['region']} authorisations."
    )
    if culprit:
        cause_text += (f" Attributed to the {culprit['event_ts']} {culprit['kind']} by "
                       f"{culprit['actor']}: {culprit['description']}.")

    # CONTENT_SAFETY: screen the diagnosis before anything downstream trusts it.
    safe, reason = screen_content(cause_text)
    store.record_guardrail(run_id, "CONTENT_SAFETY", "clean" if safe else "flagged",
                           f"attribution: {reason}")
    if not safe:
        return _finish("quarantined", anomaly_found=True, anomaly=anomaly)

    attribution = Attribution(
        cause=cause_text,
        change_ts=(culprit or {}).get("event_ts", ""),
        change_kind=(culprit or {}).get("kind", ""),
        actor=(culprit or {}).get("actor", ""),
        component=(culprit or {}).get("component", ""),
        confidence="deterministic",
    )
    store.set_data(run_id, "attribution", attribution.__dict__)

    # --- 3. route (classify the domain for the audit trail) ------------------
    domain = _classifier.classify({
        "summary": cause_text,
        "metric": anomaly["metric"],
        "description": (culprit or {}).get("description", ""),
    })
    store.record_guardrail(run_id, "DOMAIN_ROUTER", "classified", f"domain: {domain}")

    # --- 4. quantify ---------------------------------------------------------
    lost = round(anomaly["baseline_mean"] - anomaly["value"], 2)
    impact = Impact(
        headline=(f"{worst['region']} settled revenue is {abs(anomaly['pct_change']) * 100:.0f}% "
                  f"below baseline: about ${lost:,.0f} unsettled on {anomaly['date']}."),
        lost_revenue=lost, currency="USD",
        basis=f"baseline_mean {anomaly['baseline_mean']:,.0f} minus settled {anomaly['value']:,.0f}",
    )
    store.set_data(run_id, "impact", impact.__dict__)

    # --- 5. propose (ACTION_LIMITER gates recording the recommendation) ------
    allowed, limit_reason = _limiter.check(run_id, "propose")
    store.record_guardrail(run_id, "ACTION_LIMITER", "allowed" if allowed else "blocked",
                           f"propose: {limit_reason}")
    proposed = None
    if allowed:
        proposed = ProposedFix(
            title=f"Fail EMEA card authorisations back to {ledger.HEALTHY_GATEWAY}",
            change=(f"payments-router: route(region={worst['region']}) -> {ledger.HEALTHY_GATEWAY}  "
                    f"# revert the 14:03 migration step that moved it to {worst['gateway']}"),
            domain=domain,
            approved=False,
            rationale=f"Reverting the attributed change settles the {worst['declined']:,} "
                      f"declined {worst['region']} authorisations.",
        )
        store.set_data(run_id, "proposed_fix", proposed.__dict__)
        store.append(run_id, "actions", {"text": f"Proposed: {proposed.title}", "approved": False})

    # --- 6. verify (re-read after a fixture failover) ------------------------
    ledger.apply_failover(worst["region"], ledger.HEALTHY_GATEWAY)
    healed = ledger.detect_anomaly(z_threshold=request.z_threshold)
    verification = ("Re-read after the proposed failover: settled revenue is back within "
                    "the normal band; the incident would clear." if healed is None
                    else "Re-read after the proposed failover: still anomalous; escalate.")
    ledger.reset()

    return _finish(
        "acted" if proposed else "detected",
        anomaly_found=True, anomaly=anomaly, attribution=attribution, impact=impact,
        proposed_fix=proposed, verification=verification, domain=domain,
    )
