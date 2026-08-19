"""`python -m ledgerkeep` - the whole guardrailed loop, offline, in about a second.

Runs one investigation through the marketplace service contract and narrates
each stage, then prints the guardrails enforced, the proposed fix (unapproved),
and the audit ``content_hash`` a caller would verify. Everything below comes from
the in-repo fixture ledger, not a live source, and the banner says so.
"""

from __future__ import annotations

import json
import os

from .contract import InvestigationRequest
from .marketplace import MarketplaceService

_BOLD = "\033[1m"
_DIM = "\033[2m"
_LIME = "\033[38;5;155m"
_RED = "\033[38;5;203m"
_OFF = "\033[0m"


def _colour() -> bool:
    return os.getenv("NO_COLOR") is None and os.getenv("LEDGERKEEP_PLAIN") is None


def _c(code: str, text: str) -> str:
    return f"{code}{text}{_OFF}" if _colour() else text


def run_demo(request: InvestigationRequest | None = None, verbose: bool = True) -> dict:
    """Run one investigation and return the response dict."""
    service = MarketplaceService()
    manifest = service.describe()
    response = service.invoke(request or InvestigationRequest(note="on-call demo"))
    r = response.to_dict()

    if not verbose:
        return r

    print(_c(_BOLD, "\nLedgerkeep - guardrailed autonomous operations agent"))
    print(_c(_DIM, f"      ASI / Fetch.ai service - transport={manifest['transport']} "
                   f"- {r['delivery_mode']} - run {r['audit']['run_id']}"))

    if not r["anomaly_found"]:
        print("\n  no anomaly in the window; nothing to do")
        return r

    a = r["anomaly"]
    print(f"\n{_c(_LIME, '[1/5]')} {_c(_BOLD, 'Detect')}  {a['metric']} on {a['date']}")
    print(f"      value ${a['value']:,.0f} vs baseline ${a['baseline_mean']:,.0f}  "
          f"z={a['z_score']}  " + _c(_RED, f"{a['pct_change'] * 100:.1f}%"))

    att = r["attribution"]
    print(f"\n{_c(_LIME, '[2/5]')} {_c(_BOLD, 'Attribute')}")
    print(f"      {att['cause']}")

    print(f"\n{_c(_LIME, '[3/5]')} {_c(_BOLD, 'Quantify')}")
    print(f"      {r['impact']['headline']}")

    fix = r["proposed_fix"]
    print(f"\n{_c(_LIME, '[4/5]')} {_c(_BOLD, 'Propose (unapproved - a human owns the merge)')}")
    print(f"      {fix['title']}")
    print(_c(_DIM, f"      {fix['change']}"))

    print(f"\n{_c(_LIME, '[5/5]')} {_c(_BOLD, 'Verify')}")
    print(f"      {r['verification']}")

    audit = r["audit"]
    print(f"\n{_c(_LIME, 'guardrails enforced')}  {', '.join(sorted({g['name'] for g in audit['guardrails']}))} "
          f"({len(audit['guardrails'])} decisions recorded)")
    print(f"{_c(_LIME, 'domain')}             {audit['domain']}")
    print(f"{_c(_LIME, 'status')}             {audit['status']}")
    print(f"{_c(_LIME, 'audit content_hash')} {audit['content_hash']}")
    print(_c(_DIM, "\nEvery figure above came from the fixture ledger in ledgerkeep/ledger.py, "
                   "not a live source.\nSee docs/LIMITATIONS.md for what has and has not run here.\n"))
    return r


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="ledgerkeep",
        description="Ledgerkeep - a guardrailed autonomous operations agent as an ASI service.",
    )
    parser.add_argument("--json", action="store_true", help="Print the response dict as JSON.")
    parser.add_argument("--describe", action="store_true", help="Print the marketplace manifest and exit.")
    parser.add_argument("--metric", default="settled_revenue", help="KPI to investigate.")
    args = parser.parse_args()

    if args.describe:
        print(json.dumps(MarketplaceService().describe(), indent=2))
        return

    r = run_demo(InvestigationRequest(metric=args.metric), verbose=not args.json)
    if args.json:
        print(json.dumps(r, indent=2, default=str))


if __name__ == "__main__":
    main()
