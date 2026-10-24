# Stage 0 — Model probe

- Generated: `2026-10-17T21:06:55.779179+00:00`
- Budget ceiling: USD 4.0
- LangSmith API key present: **True**

## Probe results

| Role | Model | OK | Latency ms | Est. USD (this call) | Preview / error |
|------|-------|----|------------|----------------------|-----------------|
| A | `gpt-5.6-luna` | True | 3343 | 2.52e-05 | pong |
| B | `gpt-6-luna` | True | 1267 | 1.13e-05 | pong |
| judge | `gpt-5-mini` | True | 1325 | 2.45e-05 | pong |

## Pilot cost projection

```json
{
  "method": "scaled_from_probe",
  "scale_factor": 8.0,
  "projected_usd": {
    "translate_A_60": 0.0121,
    "translate_B_60": 0.0054,
    "judge_60": 0.0118,
    "total_plus_buffer_0_25": 0.2793
  },
  "under_usd_4": true
}
```

## Manual checks for owner

1. Confirm each probe row `ok: true`.
2. Create LangSmith account + API key (see `docs/llm_eval_stage0.md`).
3. Approve moving to Stage 1 (draft `ru_esuy_judge_v1` dataset) only if gates pass.
