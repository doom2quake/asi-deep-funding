# Ledgerkeep: a guardrailed operations agent as a decentralized AI service

**Applicant:** doom2quake (builder collective)
**Programme:** ASI Deep Funding (SingularityNET, Artificial Superintelligence Alliance)
**Programme page:** https://deepfunding.ai/
**Requested:** milestone-based grant, non-dilutive, IP retained by the team
**Project repo:** `github.com/doom2quake/asi-deep-funding` (new repo, purpose-built for this entry)
**Status of this document:** draft grant proposal, testnet-only scope, no mainnet deployment

---

## 0. Grant verification (read this first)

We checked the programme against ASI / SingularityNET's own pages before writing.

**VERIFIED on official ASI / SingularityNET pages:**

- Deep Funding is **non-dilutive, milestone-based** funding: recipients retain
  ownership of their IP and can monetize their AI services. It is not an equity
  investment.
- Funding is up to about **$100,000 per project**, with amounts varying by
  proposal, accessed through **funding rounds or Requests for Proposals**.
- The selection model documented for a prior RFP was **expert review**: experts
  assigned by area, with proposals and reviews made public, weighting alignment
  to the ASI technology stack and AGI roadmap and the proposing team's experience.
- Prior rounds included a $1.25M RFP across 14 challenge areas, an $830K
  Hyperon-focused round, and a $500K BGI Nexus round.
- Deep Funding is explicit about funding decentralized AI **services**: agents
  and tools others can discover, call, and pay for, while the builder keeps
  ownership.

**CONFLICT / GATE we are flagging honestly:** the official application site
(`deepfunding.ai`) returned HTTP 403 to our fetch, so we could not read the live
round state directly. Before submitting, an operator must open `deepfunding.ai`
in a browser and confirm there is an **open round or RFP**, its deadline, its
pool, and its current milestone-payment terms. Treat the per-project amount, the
rolling-versus-round cadence, and any token or on-chain disbursement mechanics as
**operator-verify items**, not settled facts. **This is the single gating check
before we invest applicant time.**

**INFERRED (our mapping, not a verbatim label):** that a guardrailed operations
agent published as a callable service maps onto Deep Funding's decentralized-AI-
service thesis and its MCP composition story. The mapping is ours.

---

## 1. The problem

A payments configuration is pushed at 14:03. It routes one region's card traffic
to a gateway that declines most authorisations. Order volume still looks normal,
because customers keep trying to buy. Settled revenue quietly falls, and nobody
notices until the next morning. The team that suffers this is the on-call
operator: a person paged at 03:00 who has to reconstruct, from a dashboard that
only shows the symptom, which of forty deploys that day moved a number, how much
money has already been lost, and what one line to change. That reconstruction is
slow, it happens under pressure, and it is where the cost lives. A single
mis-routed region can cost six figures per day while it goes unattributed.

The reason this stays unsolved is not detection. Anomaly detection is a solved
commodity. The unsolved part is the step after the alert: an agent that can be
trusted to investigate, attribute the cause to a specific change, quantify the
loss, and propose the exact fix, without being trusted to *execute* anything a
human has not approved. The market is full of demo agents that will happily run
generated SQL against production or act on model text that carries an injection.
The gap between a demo agent and one an operator would let near their systems is
almost entirely guardrails, durable memory, correct routing, and an honest report
of what the agent actually did. That is the layer nobody wants to build twice,
and it is the layer we have already built and tested.

## 2. Why the ASI ecosystem, why now

Deep Funding is explicit about funding decentralized AI *services*: builders who
publish agents and tools that others can discover, call, and pay for, while
retaining ownership of their work. An operations agent that a team must trust is
exactly the kind of component that benefits from being a standalone,
independently callable service with a published, auditable contract, rather than
a black box buried inside one company's stack.

Ledgerkeep maps onto that thesis directly. It is packaged as a marketplace
service: a stable, typed request and response, a guarantee about what it will and
will not do, and an audit object returned on every call so the caller can verify
the chain from *a number moved* to *this proposed fix*. The funder's technology
is load-bearing behind an adapter seam: when a seed phrase and the `uagents` SDK
are present, the service is a real uAgents endpoint on Agentverse (testnet only);
otherwise it answers the identical contract over an in-process transport, keyless.
The Model Context Protocol surface we already implement is the interoperability
seam: the same agent that answers a marketplace call can be consumed as a tool by
another agent in the ASI ecosystem, which is the composition story the Alliance
is built around. The timing is that the tooling to publish and compose agent
services matured in 2026 to the point where an operator can actually call one, and
the guardrail question has moved from academic to urgent as autonomous agents
start touching real systems.

## 3. Evidence we ship

Most Deep Funding applicants arrive with a plan and no artifact. We arrive with
working, tested code. **Milestone 1 is already built and green** in this repo.

Measured facts, reproducible on any machine with no network and no credentials:

- **82 hermetic tests pass in under a second** (`PYTHONPATH=. pytest -q`). The
  suite runs fully offline: service contract (10), the guardrailed loop (7), the
  marketplace adapter (10), the fixture ledger (7), and the vendored `agent_core`
  control plane (48).
- The autonomy is bounded by **named guardrails, each tested without a model**:
  `CONTENT_SAFETY` screens the attribution so a poisoned diagnosis quarantines the
  run with no proposed fix; `ACTION_LIMITER` rate-caps the proposal so a
  zero-cycle cap blocks it and records the block; `DOMAIN_ROUTER` classifies the
  incident for the audit trail. Every guardrail decision is recorded on the run
  document by name, so a claim of enforcement is a count of what happened.
- **Every call returns an `AuditObject`**: the run id, the ordered guardrail
  decisions by name, the classified domain, the recurrence record, and a sha256
  `content_hash` over the decision chain. A response without an audit object is
  not a valid response, and a test pins that.

The reusable control plane is the vendored **`agent_core`** package (guardrails, a
domain-aware router, durable run state with recurrence detection, and an MCP
bridge). It carries its own passing tests here, so the safety layer is exercised
in this repo rather than merely referenced. Ledgerkeep is built on this package,
which is why the safety layer arrives on day one rather than being promised for a
later milestone.

An independent code-review pass over the changed surface is part of our normal
process and will be run and its findings published for each milestone below.

## 4. Milestone roadmap

Funding is requested against milestones. Each states a concrete deliverable, how a
reviewer verifies it independently, and what it unlocks. All Web3 or on-chain
interaction is **testnet only** for the duration of the grant.

**Milestone 1: the re-themed service, its contract, and the audit object (weeks 0 to 4). BUILT.**
Deliverable: the `doom2quake/asi-deep-funding` repository with a documented
marketplace service contract (typed request and response) and the audit object
returned on every call, with the offline loop and guardrail suite green.
Verify: clone the repo, run the suite, confirm 82 tests pass offline with no
network; call the service contract locally and inspect the returned audit object.
**Status: complete and green** (see Section 3). Unlocks: a callable,
self-contained service that later milestones publish and compose.

**Milestone 2: MCP interoperability and composition (weeks 4 to 9).**
Deliverable: Ledgerkeep exposed over the Model Context Protocol so another agent
can call it as a tool, with a worked example of a second agent invoking it and
consuming its audit object, plus a conformance test for the MCP surface.
Verify: run the provided MCP client example against the running server and observe
the tool call, the response, and the recorded guardrail decisions; run the
conformance test. Unlocks: the composition story the ASI ecosystem is built
around, and the seam other builders integrate against.

**Milestone 3: testnet-anchored audit provenance (weeks 9 to 15).**
Deliverable: an optional, env-gated path that anchors the hash of each run's audit
object to a public testnet, so a caller can verify after the fact that a returned
audit trail was not edited. This is a tamper-evidence feature, not a custody
feature; it degrades to a labelled no-op when unconfigured.
Verify: run a cycle with anchoring on against the testnet, then independently
recompute the audit hash and confirm it matches the anchored value; run the same
cycle with anchoring off and confirm a labelled no-op and no external call.
Unlocks: verifiable provenance for a service other parties are trusting.

**Milestone 4: Agentverse / marketplace publication and documentation (weeks 15 to 20).**
Deliverable: Ledgerkeep published as a discoverable service on Agentverse / the
ASI marketplace (per the platform's current publication process), with a public
quickstart, the service contract reference, and a limitations document that
separates what has run from what has not by evidence class.
Verify: locate the published service listing, follow the quickstart to make a call
end to end, and confirm the limitations document is present and specific.
Unlocks: real discovery and third-party calls, the point at which usage and
feedback can begin to accumulate.

**After the grant.** The repository and the `agent_core` control plane stay
open-source under doom2quake ownership. The service remains published and
callable. The immediate post-grant work is hardening the marketplace path from
testnet to whatever mainnet publication the operator decides on, and widening the
domain library beyond the payments and infrastructure scenarios shipped during the
grant. None of that requires further grant money to keep the delivered artifact
alive.

## 5. Ecosystem impact

The durable, reusable output is not one agent, it is the safety layer under it.
The **`agent_core`** package (guardrails, router, durable state, MCP bridge) is
MIT-licensed and separable, and every improvement made for Ledgerkeep lands there,
so other ASI builders can vendor the exact tested control plane rather than
re-implementing guardrails from a blog post. The MCP surface delivered in
Milestone 2 is documented as an integration seam, so a Ledgerkeep call is a worked
reference for how to publish and compose a guardrailed agent service on the
platform. The testnet audit-anchoring path from Milestone 3 is a general pattern
for verifiable agent provenance, liftable by any builder who needs a caller to
trust a returned audit trail. All of it is documented, tested, and open.

## 6. Sustainability and honest limits

**What keeps it alive after the money ends:** the delivered artifact does not
depend on the grant to run. The offline loop and the test suite are reproducible
on any machine at zero cost; the published service is small and scale-to-zero; the
control plane it depends on is a library we maintain for our own other builds
regardless. There is no server we must keep paying for to stop the work from
evaporating.

**What is NOT built, deployed, or measured (state plainly):**

- **No users, no revenue, no partnerships.** Nothing here should be read as
  traction. The evidence we offer is tested code, not adoption.
- **No live ASI / Fetch.ai publication.** The marketplace adapter builds a real
  `uagents.Agent` only when a seed phrase is set and the `uagents` SDK is present,
  on a test network. Neither is present in this repo's test environment, so the
  live `build_uagent` path has never been exercised against Agentverse.
- **No mainnet deployment, and none planned under this grant.** All on-chain
  interaction is testnet only. The audit-anchoring feature is tamper-evidence, not
  custody, and it is off by default.
- **No durable state in the tested path.** The suite runs in-memory by design. A
  Firestore backend exists in `agent_core.state` but is not configured or
  exercised here.
- **No audit.** No third-party security review has been performed on our code.
- **The content-safety and read-only-SQL screens are deny-list text screens, not
  parsers.** They are defence in depth and documented as such; the real boundary
  for any generated query is a read-only credential with a server-side cost cap.
- **This is not a SingularityNET / Hyperon-native build.** The programme states a
  preference for proposals that leverage its stack and AGI roadmap. Ledgerkeep
  leverages the ecosystem at the service and interoperability layer (marketplace
  publication, uAgents on Agentverse, MCP composition), not at the OpenCog Hyperon
  / MeTTa layer. We state this openly so reviewers can weigh it.
- **No partnership with the ASI Alliance** and no endorsement. This is an
  application.

---

*Cite:*

```bibtex
@software{sarkar_ledgerkeep_2026,
  author  = {Dipankar Sarkar},
  title   = {Ledgerkeep: A Guardrailed Autonomous Operations Agent as a Decentralized AI Service},
  year    = {2026},
  url     = {https://github.com/doom2quake/asi-deep-funding},
  license = {MIT}
}
```

License: MIT, held by doom2quake. Testnet only; no mainnet, no real funds.
