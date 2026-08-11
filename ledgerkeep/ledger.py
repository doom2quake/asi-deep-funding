"""The offline fixture ledger (LEDGERKEEP_OFFLINE=1, the default).

A decentralized operations agent still has to read *some* ledger of what
happened. In a live deployment that is a warehouse of settlement and gateway
events; here it is a small, deterministic, checked-in ledger that answers the
exact question shapes Ledgerkeep asks, so the whole loop (detect the drop,
attribute it to a change, quantify the loss, propose the fix, re-read to
confirm) runs on a laptop with no cloud project, no credentials, and no network.

Two rules keep this honest:

1. Every figure this module returns is offline fixture data. The service
   contract stamps ``delivery_mode="offline_fixture"`` on the response so an
   offline number can never be mistaken for a live one.
2. It is a fixture resolver, not a query engine. It answers the question shapes
   Ledgerkeep itself asks and nothing else.

The seeded scenario is one day of EMEA card-settlement failure: a 14:03 routing
change moves EMEA traffic to a gateway that then declines ~85% of
authorisations, so settled revenue collapses while order volume stays flat. This
is exactly the incident the grant proposal describes.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Optional

# --- the scenario ------------------------------------------------------------

FAILING_REGION = "EMEA"
FAILING_GATEWAY = "gw-adyen-v2"
HEALTHY_GATEWAY = "gw-stripe"

_WEEKDAY_REVENUE = 431_000.0
_WEEKEND_REVENUE = 348_000.0
_AOV = 119.5

# The anomaly day itself: order volume holds, settled revenue collapses, because
# EMEA authorisations are being declined at the new gateway.
ANOMALY_REVENUE = 262_400.0
LOOKBACK_DAYS = 29

# Settled revenue for the anomaly day once the failover has been applied: the
# 1,568 EMEA authorisations that were failing settle instead, at the EMEA
# average order value of ~100.20.
ANOMALY_REVENUE_HEALED = round(ANOMALY_REVENUE + 1_568 * 100.20, 2)

# Whether the fixture ledger has had the failover applied. `run_service` flips
# this so the verification step re-reads a healed day, as a live cycle would.
_STATE: dict[str, Any] = {"remediated": False}


def apply_failover(region: str, to_gateway: str) -> dict[str, Any]:
    """Apply the failover to the fixture ledger (offline stand-in for the change)."""
    _STATE["remediated"] = True
    return {
        "status": "applied",
        "mode": "fixture",
        "orders_rerouted": 1_568,
        "detail": f"{region} card authorisations rerouted to {to_gateway} in the fixture ledger",
    }


def reset() -> None:
    """Return the fixture ledger to its pre-remediation state."""
    _STATE["remediated"] = False


def is_remediated() -> bool:
    return bool(_STATE["remediated"])


def anomaly_date(today: Optional[_dt.date] = None) -> _dt.date:
    """The day the seeded incident lands on (the most recent day in the ledger)."""
    return today or _dt.date.today()


def _wobble(i: int) -> float:
    """Deterministic +/- day-to-day variation (no RNG, no seed drift)."""
    return ((i * 6151) % 17) * 900.0 - 7_200.0


def revenue_series(today: Optional[_dt.date] = None) -> list[tuple[_dt.date, float, int]]:
    """The daily KPI series as [(date, revenue, orders)], oldest first.

    The final entry is the anomaly day. Everything before it is the baseline the
    z-score is computed against.
    """
    day0 = anomaly_date(today)
    rows: list[tuple[_dt.date, float, int]] = []
    for i in range(LOOKBACK_DAYS, 0, -1):
        d = day0 - _dt.timedelta(days=i)
        base = _WEEKEND_REVENUE if d.weekday() >= 5 else _WEEKDAY_REVENUE
        rev = round(base + _wobble(i), 2)
        rows.append((d, rev, int(round(rev / _AOV))))
    rev = ANOMALY_REVENUE_HEALED if _STATE["remediated"] else ANOMALY_REVENUE
    rows.append((day0, rev, int(round(_WEEKDAY_REVENUE / _AOV))))
    return rows


def _stats(values: list[float]) -> tuple[float, float]:
    """(mean, sample stddev) of the baseline window."""
    n = len(values)
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    return mean, var ** 0.5


def detect_anomaly(z_threshold: float = 2.5, today: Optional[_dt.date] = None) -> Optional[dict[str, Any]]:
    """Trailing z-score detector over the settled-revenue series.

    Returns the anomaly record (or None if the latest day is within the
    threshold). Pure arithmetic over the fixture series; no model, no network.
    """
    series = revenue_series(today)
    latest_d, latest_v, _ = series[-1]
    baseline = [v for _, v, _ in series[:-1]]
    mean_v, std_v = _stats(baseline)
    z = (latest_v - mean_v) / std_v if std_v else 0.0
    if abs(z) < z_threshold:
        return None
    return {
        "metric": "settled_revenue",
        "date": latest_d.isoformat(),
        "value": round(latest_v, 2),
        "baseline_mean": round(mean_v, 2),
        "baseline_std": round(std_v, 2),
        "z_score": round(z, 2),
        "pct_change": round((latest_v - mean_v) / mean_v, 4) if mean_v else 0.0,
        "direction": "drop" if z < 0 else "spike",
    }


# Per region/gateway breakdown for the anomaly day: EMEA/gw-adyen-v2 is the only
# cell whose authorisation rate has moved.
LEDGER_BREAKDOWN: list[dict[str, Any]] = [
    {"region": "EMEA", "gateway": "gw-adyen-v2", "attempted": 1_842,
     "settled": 274, "declined": 1_568, "settled_revenue": 32_753.0},
    {"region": "EMEA", "gateway": "gw-stripe", "attempted": 388,
     "settled": 377, "declined": 11, "settled_revenue": 45_051.5},
    {"region": "NA", "gateway": "gw-stripe", "attempted": 1_301,
     "settled": 1_262, "declined": 39, "settled_revenue": 150_809.0},
    {"region": "APAC", "gateway": "gw-adyen-v2", "attempted": 289,
     "settled": 281, "declined": 8, "settled_revenue": 33_786.5},
]


def breakdown_by_cell() -> list[dict[str, Any]]:
    """The region/gateway breakdown for the anomaly day (healed after failover)."""
    rows = [dict(r) for r in LEDGER_BREAKDOWN]
    if _STATE["remediated"]:
        for row in rows:
            if row["region"] == FAILING_REGION and row["gateway"] == FAILING_GATEWAY:
                row.update({"gateway": HEALTHY_GATEWAY, "settled": row["attempted"],
                            "declined": 0,
                            "settled_revenue": round(row["settled_revenue"] + 1_568 * 100.20, 2)})
    return rows


# The change / config-change audit log for the anomaly day. The 14:03 entry is
# the one that explains the incident.
CHANGE_EVENTS: list[dict[str, Any]] = [
    {"event_ts": "09:12", "kind": "deploy", "component": "checkout-service",
     "region": "ALL", "gateway": None,
     "description": "checkout-service v4.11.2 rollout (no payment routing change)",
     "actor": "release-pipeline"},
    {"event_ts": "14:03", "kind": "config_push", "component": "payments-router",
     "region": "EMEA", "gateway": FAILING_GATEWAY,
     "description": "Route EMEA card payments to gw-adyen-v2 gateway (migration step 2/3)",
     "actor": "deploy-bot"},
    {"event_ts": "15:40", "kind": "feature_flag", "component": "cart-ui",
     "region": "ALL", "gateway": None,
     "description": "enable one-tap upsell for 10% of sessions",
     "actor": "growth-team"},
]


def change_events(on_date: str = "", region: str = "") -> list[dict[str, Any]]:
    """Change-event rows for a day, optionally filtered to a region."""
    day = on_date or anomaly_date().isoformat()
    out = []
    for ev in CHANGE_EVENTS:
        if region and ev["region"] not in (region.upper(), "ALL"):
            continue
        row = dict(ev)
        row["event_ts"] = f"{day} {ev['event_ts']}"
        out.append(row)
    return out
