"""The ASI / Fetch.ai marketplace adapter: the funder's technology behind an
adapter seam. The offline transport must answer the exact same contract the live
uAgents transport would, the manifest must be honest about which transport is
active, and the live path must refuse to publish off-testnet or without a seed.
"""

from __future__ import annotations

import pytest

from ledgerkeep.config import LedgerkeepSettings
from ledgerkeep.contract import InvestigationRequest, InvestigationResponse
from ledgerkeep.marketplace import MarketplaceService, invoke


def test_offline_transport_is_default_and_keyless():
    svc = MarketplaceService()
    assert svc.transport == "offline"
    assert svc.live_capable is False


def test_invoke_accepts_a_dict_and_returns_the_contract():
    svc = MarketplaceService()
    resp = svc.invoke({"metric": "settled_revenue"})
    assert isinstance(resp, InvestigationResponse)
    assert resp.anomaly_found is True
    assert resp.audit.content_hash


def test_invoke_accepts_a_request_object_and_none():
    svc = MarketplaceService()
    assert svc.invoke(InvestigationRequest()).status == "acted"
    assert svc.invoke(None).status == "acted"


def test_invoke_json_is_dict_in_dict_out():
    out = MarketplaceService().invoke_json({"metric": "settled_revenue"})
    assert isinstance(out, dict)
    assert out["audit"]["content_hash"]
    assert out["delivery_mode"] == "offline_fixture"


def test_module_level_invoke_helper():
    resp = invoke({"metric": "settled_revenue"})
    assert resp.status == "acted"


def test_invoke_rejects_an_unsupported_request_type():
    with pytest.raises(TypeError):
        MarketplaceService().invoke(42)


def test_manifest_names_the_models_guardrails_and_transport():
    m = MarketplaceService().describe()
    assert m["request_model"] == "InvestigationRequest"
    assert m["response_model"] == "InvestigationResponse"
    assert m["transport"] == "offline"
    assert m["testnet_only"] is True
    assert set(m["guardrails"]) == {"CONTENT_SAFETY", "DOMAIN_ROUTER", "ACTION_LIMITER"}
    assert "LEDGERKEEP_ASI_AGENT_SEED" in m["missing_for_live"]


def test_manifest_reports_live_capable_only_when_seed_present_on_testnet(monkeypatch):
    # A seed on testnet makes the settings marketplace-ready; live_capable then
    # additionally requires the uagents SDK, which is not installed here, so the
    # transport stays offline and that is reported honestly.
    settings = LedgerkeepSettings(env_prefix="LEDGERKEEP")
    object.__setattr__(settings, "asi_agent_seed", "test-seed-phrase")
    object.__setattr__(settings, "asi_network", "testnet")
    svc = MarketplaceService(settings)
    assert settings.marketplace_ready() is True
    # uagents absent -> not live_capable, transport still offline
    assert svc.live_capable is False
    assert svc.transport == "offline"


def test_settings_refuse_mainnet_for_the_live_path():
    settings = LedgerkeepSettings(env_prefix="LEDGERKEEP")
    object.__setattr__(settings, "asi_agent_seed", "seed")
    object.__setattr__(settings, "asi_network", "mainnet")
    assert settings.marketplace_ready() is False
    assert any("testnet only" in m for m in settings.missing_for_marketplace())


def test_build_uagent_raises_without_configuration():
    with pytest.raises(RuntimeError):
        MarketplaceService().build_uagent()
