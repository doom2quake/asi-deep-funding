"""Serve Ledgerkeep as a Model Context Protocol tool (`python -m ledgerkeep.mcp_server`).

MCP is the interoperability seam the ASI ecosystem composes over: the same
service that answers a marketplace call can be consumed as a tool by another
agent. Milestone 2 delivers the full MCP surface and a conformance test; this
module is the thin, working starting point it builds on, so the seam already
exists in milestone 1.

It exposes one tool, ``investigate_operations``, which funnels straight into the
marketplace service (identical guardrails, identical audit object). Requires the
optional ``mcp`` extra; without it the module still imports and the offline test
suite exercises the tool function directly.
"""

from __future__ import annotations

from typing import Any

from .contract import InvestigationRequest
from .marketplace import MarketplaceService


def investigate_operations(metric: str = "settled_revenue", z_threshold: float = 2.5,
                           note: str = "", request_id: str = "") -> dict[str, Any]:
    """Investigate an operations KPI and return the typed audited response.

    Detects an anomaly in the metric, attributes it to a specific change,
    quantifies the loss, and proposes a fix (returned unapproved). The response
    carries the audit object with every guardrail decision and a content hash.
    """
    request = InvestigationRequest(metric=metric, z_threshold=z_threshold,
                                   note=note, request_id=request_id)
    return MarketplaceService().invoke(request).to_dict()


def main() -> None:  # pragma: no cover - requires the mcp extra + a live stdio loop
    from .agent_core.mcp import serve_stdio

    serve_stdio([investigate_operations], name="ledgerkeep-mcp")


if __name__ == "__main__":
    main()
