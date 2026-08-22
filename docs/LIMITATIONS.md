# Ledgerkeep: what has run, and what has not

This document separates what is verified from what is not, by evidence class, so
diligence finds nothing that was not disclosed. Milestone 1 is a callable,
tested, self-contained service. It is not a deployment, and it has no users.

## What has run, and is tested

- **The full offline loop.** Detect a settled-revenue drop by trailing z-score,
  attribute it to a specific configuration change, quantify the loss, propose the
  one-line fix, and re-read the metric after a fixture failover to confirm the
  incident would clear. This runs on any machine with no network, no cloud
  project, and no credentials, in under a second.
- **The service contract.** A typed `InvestigationRequest` in, a typed
  `InvestigationResponse` out, with an `AuditObject` on every response. The audit
  object carries the run id, the ordered guardrail decisions by name, the
  classified domain, and a sha256 `content_hash` over the decision chain. The
  contract round-trips through JSON and is pinned by tests.
- **The guardrails, each tested without a model.** `CONTENT_SAFETY` (a poisoned
  attribution is quarantined with no proposed fix), `ACTION_LIMITER` (a
  zero-cycle cap blocks the proposal), and `DOMAIN_ROUTER` (the incident is
  classified for the audit trail). Every decision is recorded on the run
  document by name.
- **The vendored control plane.** `agent_core` (guardrails, domain router,
  durable run state with recurrence, MCP bridge) is vendored into the repo and
  carries its own passing tests here, so the safety layer is exercised in this
  repo, not merely referenced.

## What has NOT run

- **No live ASI / Fetch.ai publication.** The marketplace adapter builds a real
  `uagents.Agent` only when a seed phrase is set and the `uagents` SDK is
  installed, on a test network. Neither is present in this repo's test
  environment, so the live `build_uagent` path has never been exercised against
  Agentverse. It is testnet only for the duration of the grant, and it is
  refused on any non-test network.
- **No mainnet, ever, during the grant.** All on-chain interaction is testnet
  only. The `content_hash` on the audit object is computed and returned here;
  anchoring it to a public testnet is milestone 3, and it is off by default.
- **No durable state in the tested path.** The suite runs in-memory by design. A
  Firestore backend is available in `agent_core.state` but is not configured or
  exercised here.
- **No users, no revenue, no partnerships, no audit.** Nothing in this repo
  should be read as traction or as an external security review. The evidence is
  tested code.

## Honest scope of the safety layer

The content-safety screen and the read-only-SQL screen in `agent_core` are
deny-list text screens, not parsers. They are defence in depth and are the last
line, not the only one. The real boundary for any generated query is a
read-only credential with a server-side cost cap. This is documented as such and
not claimed to be a formal guarantee.
