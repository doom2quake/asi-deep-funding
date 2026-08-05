"""Ledgerkeep - a guardrailed autonomous operations agent, published as a
decentralized AI service on the ASI / Fetch.ai stack.

Public surface:
    from ledgerkeep.contract import InvestigationRequest, InvestigationResponse
    from ledgerkeep.service import run_service           # one guardrailed investigation
    from ledgerkeep.marketplace import MarketplaceService  # the ASI/Fetch.ai adapter

Built on the vendored ``agent_core`` control plane (guardrails, domain router,
durable run state, MCP bridge), so the safety layer arrives on day one.
"""

from .config import settings

__all__ = ["settings"]
__version__ = "0.1.0"
