# Muse Code SDK Skill

Runbook for building clients that drive Muse Code agent sessions over the
Muse Session Protocol (MSP), and for running code-agent workflows in the
repo's own style. Grounded in the public repo
[`meta-models/muse-code-sdk`](https://github.com/meta-models/muse-code-sdk)
(Developer Preview, MIT) plus ~800 HF
docs across 5 agentic-coding datasets, FTS-queryable from the shared index
(`agent_id = 'muse-code-sdk'`):

| Dataset | Docs | What it contributes |
|---|---|---|
| `meta-models/muse-code-sdk` (repo) | 10 | Hand-written: SDK identity, facade API surface, MSP wire concepts, session/turn lifecycle, approval + userInput dual-channel patterns, resume/durability, idempotent retry, conformance-fixture testing model, cookbook recipe map, protocol types |
| `glaiveai/glaive-function-calling-v2` | 160 | Tool-calling trajectories (system + chat): function schema first, structured call second, result third — the same shape as agent tool calls routed through approvals |
| `microsoft/orca-agentinstruct-1M-v1` | 160 | Agentic coding instructions (`code_` split): understand → plan → act → verify turn structure |
| `nvidia/OpenCodeReasoning` | 160 | Reasoning traces before solutions: explore approaches and edge cases internally, emit the compact solution |
| `nvidia/OpenCodeInstruct` | 160 | Instruction pairs with unit tests: the verify-by-tests loop |
| `SWE-Gym/SWE-Gym` | 160 | Real issue → patch workflows: reproduce, minimal patch, FAIL_TO_PASS / PASS_TO_PASS |

Index queries: `SELECT text FROM docs WHERE agent_id='muse-code-sdk' AND docs MATCH '<terms>'`.

## What the SDK is

`@muse-code/sdk` (npm, MIT, `engines: node >=20`, zero runtime
dependencies; latest **1.3.0**, published 2026-09-18; maintained by
`mjdouglas_meta`): a typed
facade over the Muse Session Protocol. You do not build an agent — you
spawn a host child process, handshake, open sessions, stream turns, answer
approval/userInput requests, survive host death, and resume.

## The client lifecycle (do this in order)

1. **Spawn + handshake**: `spawnMspConnection` starts the host; you cannot
   send traffic before the handshake completes (type-enforced). Read
   `sessionDurability` off the handshake immediately — it is the durability
   fork you must get right.
2. **Fingerprint check**: compare the host's schema fingerprint against
   `EXPECTED_SCHEMA_FINGERPRINT`. Mismatch = WARNING, never an error;
   additive-optional schema evolution means an older SDK keeps working.
3. **Session**: `session/new` with explicit `clientInfo {name, version}` —
   never let an identity be inherited by omission. `session/list` carries
   display metadata (title, first user prompt, branch); `session/rename`,
   `session/setReasoningEffort` as needed.
4. **Turn**: submit prompt → stream `item/delta` frames (append, keyed by
   `itemId`) → trust only `item/completed` (authoritative full text:
   replace your accumulation) and `turn/completed` (terminal + usage).
5. **End**: classify exits — `MuseServeChild.exit` → `ExitClassification`.
   stderr is evidence (capture, never parse); exit code is the contract you
   branch on.

## The dual-channel rule (approvals AND user input)

When the agent needs permission or a structured answer, the host asks twice:

- `approval/requested` / `userInput/requested` — notification for your UI.
- `approval/request` / `userInput/request` — JSON-RPC request your client
  MUST answer. No registered handler = SDK answers "method not found".

Answer with `approval/decide` (a `choiceId` the host OFFERED in
`availableChoices` — never invent one) or `userInput/answer` (a
`selectedLabel` the host offered). **The ack is not the outcome**:
`approval/resolved` / `userInput/settled` carry the decision, policy
result, and recorded answers. Denying is a normal answer — the turn keeps
running and the agent narrates what it did not do.

On resume, check `pendingRequests` first: pending questions survive the
client and the host re-issues them to the late joiner. A tool approval
still waiting after a crash shows as UNRESOLVED on resume — never as
already executed.

## Retry and ordering

Request ids correlate replies; acks echo the recorded commandId
(`Connection.command` verifies it). Writes around a server request stay
ordered — a command overtaking the reply is a frame divergence, not a
tolerated reordering. Cancel a running turn with a real cancel command;
queue/steer/reclaim follow the multi-turn traffic rules. Retry must never
double-submit the user's turn.

## Test like the repo does

Golden transcripts + fixture host + spec-pinned assertions. The cookbook
pattern: `muse-conformance serve-fixture` plays committed transcripts
from `schema/msp/transcripts/` — deterministic, no credentials, no model.
Quickstart journey rules worth copying: every assertion states
spec-correct behavior (never freeze a known-wrong result); expect-blocks
name the issue AND the failure signature, and a blocked segment that
starts passing FAILS the run so it gets promoted (blocks cannot rot).
For acceptance without a provider, use a loopback fake first-party
endpoint — real model turns, nothing leaves the machine.

## The agent workflow (from the datasets)

- **Think before code** (OpenCodeReasoning): explore approaches, edge
  cases, and tests internally; emit the compact solution.
- **Understand → plan → act → verify** (orca-agentinstruct): every turn
  ends with verification, not narration.
- **Verify by tests** (OpenCodeInstruct): every generated solution ships
  with unit tests; treat tests as the contract.
- **Reproduce → minimal patch → flip the tests** (SWE-Gym): read the
  issue, reproduce, write the smallest patch that flips FAIL_TO_PASS
  while keeping PASS_TO_PASS green.
- **Tool calls are structured** (glaive): schema first, call second,
  result third — mirror the approval dual-channel rule on your side.

## Cookbook map (12 recipes in `clients/sdk-cookbook/src/recipes/`)

stream-a-turn, answer-user-input, approve-or-deny (play BOTH arms),
cancel-mid-turn, classify-serve-exits, fingerprint-mismatch,
list-models-and-switch-mid-session, queue-steer-reclaim,
resume-and-verify (two hosts, real failure shape), retry-without-double-submitting,
survive-the-host-dying. When you need a behavior, copy the recipe's shape first.
