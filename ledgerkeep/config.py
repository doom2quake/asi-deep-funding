"""Ledgerkeep settings, resolved from the environment at import time.

Ledgerkeep subclasses the vendored ``agent_core.BaseSettings`` and adds the
fields that are specific to publishing the agent as a decentralized service on
the ASI / Fetch.ai stack. No secret value lives in code: the ASI agent seed and
any marketplace credential come from the environment, and the whole loop runs
keyless in offline mode when none are present.

The ``env_prefix`` is ``LEDGERKEEP``, so the guardrail and routing toggles the
control plane reads (``LEDGERKEEP_DRY_RUN``, ``LEDGERKEEP_IN_MEMORY_STATE``, ...)
are namespaced to this app.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .agent_core import BaseSettings, env_bool, env_str


@dataclass(frozen=True)
class LedgerkeepSettings(BaseSettings):
    """Runtime settings for the Ledgerkeep service."""

    env_prefix: str = "LEDGERKEEP"
    app_name: str = "ledgerkeep"

    # --- offline / keyless operation -----------------------------------------
    # The whole detect -> attribute -> quantify -> propose loop runs against the
    # in-repo fixture ledger with no network. This is the default so a reviewer
    # can clone and run without any credential.
    offline: bool = field(default_factory=lambda: env_bool("LEDGERKEEP_OFFLINE", True))

    # --- ASI / Fetch.ai marketplace seam -------------------------------------
    # The service is published on Agentverse as a uAgents endpoint. When a seed
    # phrase and the `uagents` SDK are both present the real adapter is used;
    # otherwise the deterministic offline transport answers the same contract.
    asi_agent_seed: str = field(default_factory=lambda: env_str("LEDGERKEEP_ASI_AGENT_SEED"))
    asi_network: str = field(default_factory=lambda: env_str("LEDGERKEEP_ASI_NETWORK", "testnet"))
    asi_service_title: str = field(
        default_factory=lambda: env_str(
            "LEDGERKEEP_ASI_SERVICE_TITLE",
            "Ledgerkeep: guardrailed autonomous operations agent",
        )
    )

    def marketplace_ready(self) -> bool:
        """True only when a real ASI publication path is fully configured.

        Testnet only for the duration of the grant. A missing seed, or a network
        other than a test network, keeps the service on the offline transport.
        """
        return bool(self.asi_agent_seed) and self.asi_network.lower() in {"testnet", "dorado", "local"}

    def missing_for_marketplace(self) -> list[str]:
        """Config that must be provided before the ASI adapter can publish."""
        missing: list[str] = []
        if not self.asi_agent_seed:
            missing.append("LEDGERKEEP_ASI_AGENT_SEED")
        if self.asi_network.lower() not in {"testnet", "dorado", "local"}:
            missing.append("LEDGERKEEP_ASI_NETWORK (testnet only during the grant)")
        return missing


settings = LedgerkeepSettings()
