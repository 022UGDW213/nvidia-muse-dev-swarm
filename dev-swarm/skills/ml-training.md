# ML Training Skill

Runbook for fine-tuning and MLOps work. Grounded in 150 HF docs:
`odyn-network/lora-hyperparameter-benchmark-v1` (the dataset's full 50 LoRA
configs — `/size` reports `num_rows: 50`) + 100 monitoring-log records sampled
from `pgurazada1/machine-failure-mlops-demo-logs` (a 3,088-row dataset).

## LoRA / QLoRA recipe (what the benchmark corpus actually uses)

Distributions counted over all 50 rows of the benchmark dataset — use these as
your defaults. Counts below were tallied on 2026-09-26 from
`https://datasets-server.huggingface.co/rows?dataset=odyn-network%2Flora-hyperparameter-benchmark-v1&config=default&split=train&offset=0&length=50`;
`NR` = the row does not report that field.

| Hyperparam | Observed values (of 50) | Default pick |
|---|---|---|
| `lora_rank` | 32 (20), 8 (10), 16 (6), 128 (4), 256 (3), 64 (3), 4 (3), 2 (1) | **16 or 32** |
| `lora_alpha_effective` | 16 (27), 32 (8), 128 (6), 64 (3), 512 (2), 256 (1), NR (3) | **32 with rank 16** |
| `lora_dropout` | 0.05 (27), 0.0 (10), 0.1 (2), NR (11) | **0.05** |
| `learning_rate` | 2e-4 (34), 1e-4 (9), 1e-5 (2), others (4) | **2e-4** |
| `num_epochs` | 1 (18), 2 (11), 4 (10), 3 (7), 5 (3) | **3** |
| `seq_len` | 2048 (18), 4096 (12), 512 (5), 1024 (5), 8192 (2), others (4), NR (4) | **4096** if VRAM allows |
| `gradient_checkpointing` | `true` (31), `false` (1), other (2), NR (16) | **on** |
| `base_precision` | full (22), 4bit (20), 8bit (5), awq-4bit / gptq-4bit / aqlm-2bit (1 each) | **4-bit QLoRA** on consumer GPUs |

Effective batch = `batch_size × grad_accum` — the corpus mostly runs tiny
per-device batches (`batch_size` 1 (16), 2 (15), 8 (4), 6 (3), 4 (2), with a
handful of larger outliers; `grad_accum` 4 (20), 8 (8), 2 (3), 1 (2), 32 (1),
NR (16)) — don't mistake per-device batch for the real one. The row
`ax-llama3.2-1b-lora` (Llama-3.2-1B, GPT4-LLM-Cleaned) is a proven working
point: rank 16 / alpha 32 / lr 2e-4 / 1 epoch / **54,568 dataset samples**.

## Quick config template (Unsloth/TRL style)

```python
r, lora_alpha, lora_dropout = 16, 32, 0.05
lr, epochs = 2e-4, 3
max_seq_length = 4096
use_gradient_checkpointing = True
load_in_4bit = True          # QLoRA on limited VRAM
```

## Pitfalls

- **Alpha/rank mismatch:** alpha ≪ rank starves the adapter; alpha ≫ 4×rank
  destabilizes. Corpus sweet spot: alpha ∈ {rank, 2×rank}.
- **lr too low on short runs:** 5e-6–1e-5 only appeared with long schedules;
  for 1–3 epoch SFT runs, 2e-4 is the proven default.
- **No dropout on tiny data:** with <1k samples some configs use dropout 0.0 —
  with ≥10k samples, 0.05 is safer.
- **Forgetting checkpointing:** without it, seq_len 4096 on 8–24GB VRAM OOMs.
  The corpus has it on in nearly every reporting config.
- **Juan's Kaggle context:** TRL has crashed his runs before — pin the TRL
  version, save adapter checkpoints every 500 steps, never rely on a full
  2000-step run completing.

## MLOps monitoring (from the failure-prediction demo logs)

Production failure classification on machine telemetry: air temp, process temp,
rotational speed (rpm), torque (Nm), tool wear (min), machine type → binary
failure prediction. Takeaways for any monitoring setup:

- Log **features and predictions together** (the demo rows carry the model
  output in the same record) so drift/degradation is auditable.
- Alert on **input distribution shift** (rpm/torque drift), not just on
  prediction flips — models go stale silently.
- Keep a labeled evaluation slice; retrain triggers should be data-driven.
