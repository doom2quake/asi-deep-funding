"""The Ledgerkeep marketplace service contract.

Milestone 1 delivers Ledgerkeep as a callable decentralized service, which means
the interface is the product. This module is that interface: a stable, typed
request and response, plus the audit object returned on **every** call so the
caller can verify the chain from *a number moved* to *this proposed fix* without
trusting the agent's prose.

Everything here is a plain dataclass with an explicit JSON round-trip
(``to_dict`` / ``from_dict``), so the contract is transport-agnostic. The ASI /
Fetch.ai adapter (``ledgerkeep.marketplace``) maps a uAgents message onto
``InvestigationRequest`` and maps ``InvestigationResponse`` back onto the reply;
the same objects are what an MCP tool or a local call exchange. One contract,
many transports.

Design rules the schema enforces:

* The response is self-describing about honesty. ``delivery_mode`` is always
  present and is ``"offline_fixture"`` when the figures came from the in-repo
  ledger rather than a live source, so a reviewer never has to guess.
* The ``AuditObject`` is not optional. A response without an audit trail is not a
  valid response. It carries the run id, the ordered guardrail decisions by name,
  the classified domain, the recurrence record, and a content hash of the
  decision chain, so a caller can pin what the agent actually did.
* The agent proposes; it never asserts it executed. ``proposed_fix`` is a
  recommendation with an ``approved`` flag that is always ``False`` on return.
  The merge button stays with a human.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

CONTRACT_VERSION = "1.0"


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


# --- request -----------------------------------------------------------------

@dataclass(frozen=True)
class InvestigationRequest:
    """A typed marketplace request to investigate an operations KPI.

    The whole request is optional-with-defaults so the simplest possible call is
    ``InvestigationRequest()``: watch settled revenue with the default detector.
    A caller who wants a specific KPI or a tighter threshold sets those fields.
    """

    metric: str = "settled_revenue"
    #: z-score magnitude at which the latest day counts as an anomaly.
    z_threshold: float = 2.5
    #: free-text hint recorded on the run for the audit trail (never executed).
    note: str = ""
    #: caller-supplied idempotency / correlation id, echoed back on the response.
    request_id: str = ""
    contract_version: str = CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InvestigationRequest":
        fields = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in (data or {}).items() if k in fields})


# --- response payload pieces -------------------------------------------------

@dataclass
class Attribution:
    """The specific change the anomaly is attributed to."""

    cause: str = ""
    change_ts: str = ""
    change_kind: str = ""
    actor: str = ""
    component: str = ""
    confidence: str = "deterministic"  # rule over the change log, not a model guess


@dataclass
class Impact:
    """The quantified loss."""

    headline: str = ""
    lost_revenue: float = 0.0
    currency: str = "USD"
    basis: str = ""


@dataclass
class ProposedFix:
    """A recommendation. Always returned unapproved: a human owns the merge."""

    title: str = ""
    change: str = ""
    domain: str = ""
    approved: bool = False  # invariant: never True on a returned response
    rationale: str = ""


@dataclass
class GuardrailDecision:
    """One named guardrail decision, in the order it was made."""

    name: str
    outcome: str
    detail: str = ""


@dataclass
class AuditObject:
    """The verifiable record returned with every call.

    ``content_hash`` is a sha256 over the canonical JSON of the decision chain
    (run id, guardrail decisions, domain, status, attribution and proposed fix).
    A caller can recompute it from the visible fields and confirm the audit trail
    was not edited. Milestone 3 anchors this same hash to a public testnet; here
    it is computed and returned so the tamper-evidence surface already exists.
    """

    run_id: str
    contract_version: str = CONTRACT_VERSION
    started_at: str = ""
    finished_at: str = ""
    status: str = ""
    domain: str = ""
    guardrails: list[GuardrailDecision] = field(default_factory=list)
    recurrence: Optional[dict[str, Any]] = None
    content_hash: str = ""

    def guardrail_names(self) -> list[str]:
        return sorted({g.name for g in self.guardrails})

    def compute_hash(self, extra: Optional[dict[str, Any]] = None) -> str:
        """Deterministic sha256 over the decision chain. Excludes the hash itself."""
        payload = {
            "run_id": self.run_id,
            "contract_version": self.contract_version,
            "status": self.status,
            "domain": self.domain,
            "guardrails": [asdict(g) for g in self.guardrails],
            "recurrence": self.recurrence,
            "extra": extra or {},
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class InvestigationResponse:
    """The typed marketplace response. ``audit`` is never absent."""

    audit: AuditObject
    status: str = ""
    anomaly_found: bool = False
    anomaly: Optional[dict[str, Any]] = None
    attribution: Optional[Attribution] = None
    impact: Optional[Impact] = None
    proposed_fix: Optional[ProposedFix] = None
    verification: str = ""
    #: "offline_fixture" | "live"; always present so a stub is never mistaken live.
    delivery_mode: str = "offline_fixture"
    request_id: str = ""
    contract_version: str = CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: Optional[int] = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InvestigationResponse":
        data = dict(data or {})
        audit_raw = dict(data.pop("audit", {}) or {})
        guardrails = [GuardrailDecision(**g) for g in audit_raw.pop("guardrails", []) or []]
        audit = AuditObject(guardrails=guardrails, **audit_raw)
        attribution = data.pop("attribution", None)
        impact = data.pop("impact", None)
        proposed = data.pop("proposed_fix", None)
        fields = {f.name for f in dataclasses.fields(cls)}
        kept = {k: v for k, v in data.items() if k in fields}
        return cls(
            audit=audit,
            attribution=Attribution(**attribution) if attribution else None,
            impact=Impact(**impact) if impact else None,
            proposed_fix=ProposedFix(**proposed) if proposed else None,
            **{k: v for k, v in kept.items()
               if k not in {"audit", "attribution", "impact", "proposed_fix"}},
        )


__all__ = [
    "CONTRACT_VERSION",
    "InvestigationRequest",
    "InvestigationResponse",
    "AuditObject",
    "GuardrailDecision",
    "Attribution",
    "Impact",
    "ProposedFix",
]
