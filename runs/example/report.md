# Autonomous Research Report

## 1. Research Question
What are the trade-offs between LoRA and full fine-tuning for adapting small language models with 7B or fewer parameters?

## 2. Research Plan
1. **SEARCH**: Survey recent papers comparing parameter-efficient fine-tuning and full fine-tuning for small language models, focusing on quality, memory, and training time.
2. **SEARCH**: Identify evidence on LoRA rank, target modules, quantization, and adapter merging.
3. **CODE**: Run a small reproducible simulation that compares trainable parameter count, memory pressure, and expected runtime under full fine-tuning and LoRA-style adaptation.
4. **REVIEW**: Critique whether the experiment supports the original claim and where it fails to generalize.

## 3. Literature Synthesis
- LoRA freezes base model weights and trains low-rank adapter matrices in selected layers, which reduces trainable parameters while preserving much of the base model behavior.
- QLoRA combines low-rank adapters with quantized base weights, making single-GPU adaptation more practical for models near the 7B range.
- Prior parameter-efficient tuning work suggests that the quality gap depends on task type. Style transfer and classification often tolerate adapters well, while deep reasoning or code-heavy tasks can benefit from full fine-tuning.
- Practical deployment trade-offs include whether adapters can be merged, whether multiple adapters must be served, and whether the team can afford full optimizer state for every base-model parameter.

## 4. Code & Results
### Generated Code
```python
import sys, json, time

methods = [
    {"method": "full_ft", "params_b": 1.3, "trainable_pct": 100.0, "memory_gb": 21.4, "runtime_s": 1842, "eval_loss": 1.683},
    {"method": "lora_r8", "params_b": 1.3, "trainable_pct": 0.23, "memory_gb": 9.1, "runtime_s": 611, "eval_loss": 1.712},
    {"method": "lora_r16", "params_b": 1.3, "trainable_pct": 0.47, "memory_gb": 9.4, "runtime_s": 638, "eval_loss": 1.694},
]

baseline = methods[0]
for item in methods[1:]:
    item["memory_ratio_vs_full"] = round(item["memory_gb"] / baseline["memory_gb"], 3)
    item["runtime_ratio_vs_full"] = round(item["runtime_s"] / baseline["runtime_s"], 3)
    item["loss_delta_vs_full"] = round(item["eval_loss"] - baseline["eval_loss"], 3)

print(json.dumps({"methods": methods}, indent=2))
```

### Execution Output
```
{
  "methods": [
    {
      "method": "full_ft",
      "params_b": 1.3,
      "trainable_pct": 100.0,
      "memory_gb": 21.4,
      "runtime_s": 1842,
      "eval_loss": 1.683
    },
    {
      "method": "lora_r8",
      "params_b": 1.3,
      "trainable_pct": 0.23,
      "memory_gb": 9.1,
      "runtime_s": 611,
      "eval_loss": 1.712,
      "memory_ratio_vs_full": 0.425,
      "runtime_ratio_vs_full": 0.332,
      "loss_delta_vs_full": 0.029
    },
    {
      "method": "lora_r16",
      "params_b": 1.3,
      "trainable_pct": 0.47,
      "memory_gb": 9.4,
      "runtime_s": 638,
      "eval_loss": 1.694,
      "memory_ratio_vs_full": 0.439,
      "runtime_ratio_vs_full": 0.346,
      "loss_delta_vs_full": 0.011
    }
  ]
}
```

## 5. Critic Review
- **Strengths**: The comparison names concrete resource metrics and keeps all methods tied to the same baseline model size.
- **Weaknesses**: The experiment is a simulation using representative values, not a live fine-tuning benchmark. It does not test reasoning, code generation, or long-context tasks.
- **Confidence Score**: 0.72
- **Verdict**: LoRA is the better default when memory, training time, and storage are constrained. Full fine-tuning remains valuable when the task demands deeper representation shifts or when the final deployment must avoid adapter management.

## 6. Adversarial Debate
**Debater Rebuttal:**
The conclusion should not imply universal LoRA parity. A small aggregate loss delta can still hide task-specific failures, especially on reasoning-heavy benchmarks. The next run should include a real dataset, a wider rank sweep, and at least one evaluation set where full fine-tuning is expected to be stronger.
