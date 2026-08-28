# Ledgerkeep — demo runbook

Ninety seconds, no credentials, no network. The whole point is that a reviewer
can reproduce every number on their own laptop.

## 0. Setup

```bash
cd app
python -m ledgerkeep --describe    # sanity: the marketplace manifest, transport=offline
```

## 1. The hero: one guardrailed investigation

```bash
python -m ledgerkeep
```

Watch the five-stage chain narrate itself:

1. **Detect** — settled revenue is $262,400 against a $408,414 baseline, z = −3.81.
2. **Attribute** — the `gw-adyen-v2` gateway is declining 85% of EMEA
   authorisations; attributed to the 14:03 `config_push` by `deploy-bot`.
3. **Quantify** — about $146,014 unsettled on the day.
4. **Propose** — fail EMEA back to `gw-stripe`, returned **unapproved**.
5. **Verify** — re-read after the proposed failover: the incident would clear.

The footer prints the guardrails enforced and the audit `content_hash`. Point at
the hash: that is the verifiable object every call returns.

## 2. The contract, as JSON

```bash
python -m ledgerkeep --json | python -m json.tool | less
```

Show three things in the payload:

- `audit.guardrails` — three decisions, each recorded by name.
- `proposed_fix.approved` is `false`. The agent proposes; a human owns the merge.
- `delivery_mode` is `offline_fixture`, so a stub is never mistaken for a live figure.

## 3. The guardrails actually bite

```bash
python -m pytest tests/test_service.py -q -k "quarantine or limiter"
```

Two tests: a poisoned attribution quarantines the run with no fix
(`CONTENT_SAFETY`), and a zero-cycle cap blocks the proposal
(`ACTION_LIMITER`). Neither needs a model.

## 4. The whole suite, hermetic and fast

```bash
python -m pytest tests -q
```

The suite cuts the network before importing the package, so nothing can reach an
external service even by accident. Record the count you see.

## 5. The console

Open `ui/index.html` in a browser (it is a static file, no server). The hero
shows the number that moved and the fix it produced; the rail shows the
guardrails, the audit object with its hash, and the service event history.

## What to say, and not say

Say: this is a callable, tested, self-contained service; the audit object is
verifiable; the ASI/Fetch.ai path is real behind an adapter seam and testnet
only. Do **not** say: there are users, a deployment, revenue, or a mainnet.
There are none, and `docs/LIMITATIONS.md` says so plainly.
