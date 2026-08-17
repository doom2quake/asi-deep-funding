"""The ASI / Fetch.ai marketplace adapter: publish Ledgerkeep as a callable service.

This is the funder's technology, behind an adapter seam. On the ASI stack a
service is a `uAgents` agent registered on Agentverse: it declares a message
model, listens on an endpoint, and answers requests from other agents. This
module maps the Ledgerkeep service contract onto that shape.

Two transports, one contract:

* **Live** (``uagents`` installed **and** ``LEDGERKEEP_ASI_AGENT_SEED`` set, on a
  test network): build a real ``uagents.Agent`` from the seed, register a
  handler that decodes an incoming message into an ``InvestigationRequest``, runs
  ``run_service``, and replies with the ``InvestigationResponse``. Testnet only
  for the duration of the grant; a non-test network is refused.
* **Offline** (the default, keyless): an in-process transport that accepts the
  exact same request dict and returns the exact same response dict, so the
  service is callable and testable with no SDK and no credentials.

``describe()`` returns the marketplace manifest a caller needs to discover and
call the service: its title, network, contract version, the request/response
model names, and which transport is active. That manifest is what milestone 4
publishes; here it is produced from the same source of truth the adapter uses,
so the published description can never drift from the running service.
"""

from __future__ import annotations

from typing import Any, Optional

from .config import settings as default_settings
from .config import LedgerkeepSettings
from .contract import CONTRACT_VERSION, InvestigationRequest, InvestigationResponse
from .service import run_service


def _uagents_available() -> bool:
    """True if the real ASI/Fetch.ai SDK can be imported (never at import time)."""
    try:
        import uagents  # noqa: F401
        return True
    except Exception:
        return False


class MarketplaceService:
    """A transport-agnostic handle to the published Ledgerkeep service.

    Construct it, then either call ``invoke`` (in-process, always available) or,
    when the live path is configured, ``build_uagent`` to get a registered
    ``uagents.Agent`` ready to run on Agentverse.
    """

    REQUEST_MODEL = "InvestigationRequest"
    RESPONSE_MODEL = "InvestigationResponse"

    def __init__(self, settings: Optional[LedgerkeepSettings] = None) -> None:
        self.settings = settings or default_settings

    # --- transport selection -------------------------------------------------

    @property
    def live_capable(self) -> bool:
        """True only when a real testnet publication is fully configured."""
        return self.settings.marketplace_ready() and _uagents_available()

    @property
    def transport(self) -> str:
        return "uagents:testnet" if self.live_capable else "offline"

    # --- the callable service ------------------------------------------------

    def invoke(self, request: Any) -> InvestigationResponse:
        """Run the service for a request (dict or ``InvestigationRequest``).

        This is the in-process transport. The live uAgents handler funnels
        through the identical call, so a testnet invocation and an offline one
        exercise the same logic and the same guardrails.
        """
        if isinstance(request, InvestigationRequest):
            req = request
        elif isinstance(request, dict):
            req = InvestigationRequest.from_dict(request)
        elif request is None:
            req = InvestigationRequest()
        else:
            raise TypeError(f"unsupported request type: {type(request)!r}")
        return run_service(req, settings=self.settings)

    def invoke_json(self, request_dict: dict[str, Any]) -> dict[str, Any]:
        """Dict in, dict out: the wire shape the marketplace transports exchange."""
        return self.invoke(request_dict).to_dict()

    # --- discovery manifest --------------------------------------------------

    def describe(self) -> dict[str, Any]:
        """The marketplace manifest for discovering and calling this service."""
        missing = self.settings.missing_for_marketplace()
        return {
            "title": self.settings.asi_service_title,
            "ecosystem": "ASI / Fetch.ai (uAgents on Agentverse)",
            "contract_version": CONTRACT_VERSION,
            "network": self.settings.asi_network,
            "request_model": self.REQUEST_MODEL,
            "response_model": self.RESPONSE_MODEL,
            "transport": self.transport,
            "live_capable": self.live_capable,
            "guardrails": ["CONTENT_SAFETY", "DOMAIN_ROUTER", "ACTION_LIMITER"],
            "audit": "AuditObject with content_hash on every response",
            "missing_for_live": missing,
            "testnet_only": True,
        }

    # --- live uAgents path (only assembled when configured) ------------------

    def build_uagent(self):  # pragma: no cover - requires the uagents SDK + a seed
        """Build and return a registered ``uagents.Agent``, or raise if not configured.

        Never called by the offline test suite; the offline suite exercises
        ``invoke`` directly. Kept thin on purpose: the marketplace handler is a
        one-line funnel into ``invoke`` so the live and offline paths cannot
        diverge in behaviour.
        """
        if not self.settings.marketplace_ready():
            raise RuntimeError(
                "ASI marketplace not configured for a live testnet publication: "
                + ", ".join(self.settings.missing_for_marketplace())
            )
        if not _uagents_available():
            raise RuntimeError("the `uagents` SDK is not installed; `pip install uagents`")

        from uagents import Agent, Context, Model  # type: ignore

        class LedgerkeepRequest(Model):  # noqa: D401 - uAgents message model
            metric: str = "settled_revenue"
            z_threshold: float = 2.5
            note: str = ""
            request_id: str = ""

        class LedgerkeepResponse(Model):
            payload: dict

        agent = Agent(
            name="ledgerkeep",
            seed=self.settings.asi_agent_seed,
            network=self.settings.asi_network,
        )

        service = self

        @agent.on_message(model=LedgerkeepRequest, replies=LedgerkeepResponse)
        async def _handle(ctx: "Context", sender: str, msg: "LedgerkeepRequest") -> None:
            response = service.invoke({
                "metric": msg.metric, "z_threshold": msg.z_threshold,
                "note": msg.note, "request_id": msg.request_id,
            })
            await ctx.send(sender, LedgerkeepResponse(payload=response.to_dict()))

        return agent


# Module-level convenience for the common keyless call.
def invoke(request: Any = None, *, settings: Optional[LedgerkeepSettings] = None) -> InvestigationResponse:
    return MarketplaceService(settings).invoke(request)
