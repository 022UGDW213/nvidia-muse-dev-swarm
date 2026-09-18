# Swarm Orchestration Skill

Runbook for multi-agent work. Grounded in 410 HF docs:
`Swarm-AI-Research/fable5-traces-sft` (120 agent traces),
`stindardlogic/agentic-workflows-sft-100k` (150 workflow examples),
`LangChainDatasets/multiagent-bidding-dialogue` (40),
`DrDrek/crewai_finetuning_dataset` (100 role profiles).

## What real agent traces look like

From 120 fable5 traces (claude_code_session origin): **avg 26 messages, 9 tool
calls per task**. The role flow is always the same shape:

```
user → assistant → assistant → tool → assistant → tool → assistant …
```

- The loop is **assistant-acts → tool-responds → assistant-continues**. Design
  your orchestrator around this cycle, not around chat.
- Tool results are terse status lines ("File created successfully at …",
  "Exit code 1", "Command running in background with ID"). Parse them as
  structured outcomes, not prose.
- Long traces (100+ messages) are normal for coding tasks. Budget context for
  50–150 turns on hard tasks; summarize tool output aggressively.

## Agent roles (from 100 CrewAI profiles)

Give each worker a **role card**: goal + backstory + expertise. Example shape:

> **Senior Research Analyst** — goal: uncover cutting-edge developments in AI;
> backstory: works at a leading think tank, dissects complex data into
> actionable insights.

Role cards beat generic "you are a helpful assistant" because they anchor the
agent's tool choices and output style. This maps 1:1 onto the dev-swarm's
30 profiles (devops-01..30) — each profile should read like a role card, not
a capability list.

## Workflow patterns (agentic-workflows-sft-100k)

- **Category your workflows** (`multi_agent_systems`, etc.) and keep a
  `context` line per workflow: one sentence on what the agents are
  orchestrating. Future you (and retrieval) will thank present you.
- **Conversation-first spec:** each workflow is defined by its dialogue, not
  by a DAG diagram. Write the expected agent exchange before the code.

## Multi-agent dialogue format (bidding/debate)

The bidding-dialogue corpus shows the setup that makes agent debates work:

1. **Topic** stated once, shared by all agents.
2. **Named agents with descriptions** ("Your name is X. Your description is…").
3. **Turns are full generations**, not one-liners — each agent argues its case.

Use this when agents must converge (design reviews, plan critiques): assign
positions, let them argue, then have a judge agent summarize.

## Orchestrator checklist (dev-swarm mapping)

- **Task queue over direct calls:** sqlite queue with `kind` (shell/fetch/
  python) — agents pull, never get pushed to. Survives worker death.
- **Heartbeats:** workers die quietly (observed: 30/30 dead with no error).
  Check heartbeats before trusting "alive", restart dead ones.
- **skill_context per task:** attach top-3 FTS hits to each task payload so
  every worker acts with retrieved knowledge, not just its prompt.
- **Idempotent tasks:** a worker may die mid-task; another picks it up. Tasks
  must be safe to retry.
- **Hung-task recovery:** nested quoting in submit payloads hangs shells —
  keep payloads simple; use the SQL/down/up recovery path when stuck.
- **One coordinator, N workers:** the coordinator plans and decomposes; workers
  execute. Don't let workers spawn workers (max_depth exists for a reason).

## Pitfalls

- **No shared memory by default:** agents only know what the task payload and
  skill_context carry. Put state in the queue/DB, not in a worker's head.
- **Role drift:** without role cards, agents converge to generic assistant
  behavior within a few turns. Re-inject the role on long traces.
- **Tool-result flooding:** 9 tool calls × verbose output = context death.
  Truncate tool output to what the next decision needs.
- **Silent death:** the #1 dev-swarm failure mode. Monitor, don't assume.
