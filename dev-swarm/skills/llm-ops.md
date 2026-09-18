# LLM Ops Skill — Function/Tool Calling

Runbook for wiring LLMs to tools. Grounded in 650 HF docs:
`NousResearch/hermes-function-calling-v1` (200), `glaiveai/glaive-function-calling-v2`
(150), `nvidia/Nemotron-RL-Agentic-Function-Calling-Pivot-v1` (150),
`stindardlogic/tool-calling-english-100k` (150).

## Tool schema design (the part that matters most)

Every working example follows this shape — name, plain-language description,
typed parameters with `required`:

```json
{"name": "get_exchange_rate",
 "description": "Get the exchange rate between two currencies",
 "parameters": {"type": "object",
   "properties": {
     "base_currency": {"type": "string", "description": "The currency to convert from"},
     "target_currency": {"type": "string", "description": "The currency to convert to"}},
   "required": ["base_currency", "target_currency"]}}
```

- **Descriptions are load-bearing.** The model selects tools by description
  text alone — vague descriptions are the #1 cause of wrong-tool calls.
- **Name tools as verbs** (`get_weather`, `create_calendar_event`,
  `execute_python` — all from the 100k corpus). Noun names confuse selection.
- **Keep the tool list small per call.** Hermes examples hand the model 2–5
  tools per task, not 50. If you have many tools, route first, then present
  the shortlist.

## System-prompt patterns (two proven styles)

1. **Hermes style (XML tags):** "You are a function calling AI model. You are
   provided with function signatures within `<tools> </tools>` XML tags. You
   may call one or more functions… Don't make assumptions about what values
   to plug into functions." — explicit, works with chat templates.
2. **Glaive style (JSON in system):** "You are a helpful assistant with access
   to the following functions. Use them if required - {…schema…}". Simpler,
   single-turn oriented.

Both end with the same instruction: use tools when required, otherwise answer
directly.

## Call patterns from the corpora

- **Single vs multi-turn:** stindardlogic is mostly single-turn (only 16/150
  multiturn). For multi-step tasks, expect to loop: model → tool result →
  model, and budget context for it.
- **Parallel calls:** 21/150 stindard examples issue parallel tool calls
  (e.g. `get_stock_price` + `get_exchange_rate` together). Enable parallel
  calling when tools are independent — it halves latency on fan-out tasks.
- **`no_tool_needed`:** the corpus explicitly labels chit-chat where no tool
  should fire. Always give the model a clean "answer directly" path, or it
  will force-fit tools onto casual messages.
- **Refusals are features:** glaive examples show the assistant declining
  ("I don't have the capability to book flights") when no tool covers the
  request. A model that says "can't" beats one that hallucinates a booking.

## The Nemotron lesson (agentic trajectories)

From 150 NVIDIA agentic trajectories: when the available tools **cannot** do
the job, the correct expected action is an explicit limitation statement, not
a guessed result. Build this into your agent loop:

1. Before acting, check: does any tool cover this request?
2. If no → say so, name the closest available tool, ask for clarification.
3. Never emit a confident answer synthesized from nothing.

## Categories that work well (by corpus frequency)

Travel, finance, calendar, weather, database, navigation, developer_tools,
translation, IoT/home automation, e-commerce, model APIs. If your domain is
here, there are hundreds of proven examples to mirror.

## Pitfalls

- **Assuming argument values:** Hermes's system prompt explicitly forbids it.
  Missing arg → ask the user or use a default, don't invent.
- **Tool-result blindness:** after a tool returns, re-read the original user
  request before composing the final answer — models drift.
- **Unbounded loops:** cap tool-call rounds (e.g. 5); a confused model will
  call tools forever without a budget.
- **Juan's stack:** his Kimi K3 CLI and local Qwen work uses tool calling —
  keep schemas OpenAI-compatible (function.name/arguments) for max portability.
