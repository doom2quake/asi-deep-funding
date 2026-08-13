"""The fixture ledger: a deterministic, offline stand-in for a live warehouse.
Pinned so the seeded incident is stable and the failover/verify round-trip works.
"""

from __future__ import annotations

from ledgerkeep import ledger


def test_detect_finds_the_seeded_drop():
    a = ledger.detect_anomaly()
    assert a is not None
    assert a["direction"] == "drop"
    assert a["z_score"] < -2.5
    assert a["value"] == ledger.ANOMALY_REVENUE


def test_detect_respects_the_threshold():
    assert ledger.detect_anomaly(z_threshold=99.0) is None


def test_worst_cell_is_the_failing_gateway():
    cells = ledger.breakdown_by_cell()
    worst = max(cells, key=lambda c: c["declined"] / c["attempted"])
    assert worst["region"] == ledger.FAILING_REGION
    assert worst["gateway"] == ledger.FAILING_GATEWAY


def test_change_log_carries_the_1403_config_push():
    events = ledger.change_events(region="EMEA")
    culprit = [e for e in events if e["kind"] == "config_push"]
    assert culprit and "14:03" in culprit[0]["event_ts"]
    assert culprit[0]["gateway"] == ledger.FAILING_GATEWAY


def test_failover_heals_the_day_then_reset_restores_the_incident():
    assert ledger.is_remediated() is False
    ledger.apply_failover("EMEA", ledger.HEALTHY_GATEWAY)
    assert ledger.is_remediated() is True
    assert ledger.detect_anomaly() is None  # healed day reads normal
    ledger.reset()
    assert ledger.detect_anomaly() is not None  # incident is back


def test_healed_breakdown_moves_the_cell_to_the_healthy_gateway():
    ledger.apply_failover("EMEA", ledger.HEALTHY_GATEWAY)
    cells = ledger.breakdown_by_cell()
    emea = [c for c in cells if c["region"] == "EMEA" and c["declined"] == 0]
    assert any(c["gateway"] == ledger.HEALTHY_GATEWAY for c in emea)
    ledger.reset()


def test_series_is_deterministic():
    s1 = ledger.revenue_series()
    s2 = ledger.revenue_series()
    assert s1 == s2
    assert len(s1) == ledger.LOOKBACK_DAYS + 1
