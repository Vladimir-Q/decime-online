#!/usr/bin/env python3
"""Stage 0: cheap availability probe for eval pilot models (LangChain ChatOpenAI).

From apps/api (venv active):

  python scripts/eval_stage0_probe.py

Writes JSON+MD under evals/reports/pilot-2026-10/stage0/.
Does NOT enable LangSmith tracing. Uses ~3 tiny chat completions.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Locked in docs/llm_eval_pilot_spec.md
DEFAULT_MODELS = {
    "A": "gpt-5.6-luna",
    "B": "gpt-6-luna",
    "judge": "gpt-5-mini",
}

# Mid OpenAI Standard short-context $/1M (for estimate only; Stage 0 records actual usage).
RATE_TABLE: dict[str, tuple[float, float]] = {
    "gpt-5.6-luna": (0.20, 1.20),
    "gpt-6-luna": (0.10, 0.50),
    "gpt-5-mini": (0.25, 2.00),
    "gpt-6.1-sol": (2.00, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
}


def _usage_from_message(response: Any) -> dict[str, int | None]:
    meta = getattr(response, "response_metadata", None) or {}
    usage = meta.get("token_usage") or meta.get("usage") or {}
    if not usage and hasattr(response, "usage_metadata") and response.usage_metadata:
        um = response.usage_metadata
        return {
            "prompt_tokens": getattr(um, "input_tokens", None) or um.get("input_tokens"),
            "completion_tokens": getattr(um, "output_tokens", None) or um.get("output_tokens"),
            "total_tokens": getattr(um, "total_tokens", None) or um.get("total_tokens"),
        }
    return {
        "prompt_tokens": usage.get("prompt_tokens") or usage.get("input_tokens"),
        "completion_tokens": usage.get("completion_tokens") or usage.get("output_tokens"),
        "total_tokens": usage.get("total_tokens"),
    }


def _estimate_usd(model: str, prompt_tokens: int | None, completion_tokens: int | None) -> float | None:
    rates = RATE_TABLE.get(model)
    if not rates or prompt_tokens is None or completion_tokens is None:
        return None
    inp, out = rates
    return (prompt_tokens * inp + completion_tokens * out) / 1_000_000


async def probe_model(
    *,
    role: str,
    model: str,
    api_key: str,
    base_url: str | None,
) -> dict[str, Any]:
    from decime_api.services.ai.lc.openai_backend import build_chat_openai

    started = time.perf_counter()
    row: dict[str, Any] = {
        "role": role,
        "model": model,
        "ok": False,
        "latency_ms": None,
        "preview": None,
        "error": None,
        "usage": {},
        "estimated_usd": None,
    }
    try:
        # Omit temperature: some models (e.g. gpt-6-luna) only allow the API default.
        llm = build_chat_openai(
            api_key=api_key,
            model=model,
            temperature=None,
            base_url=base_url,
        )
        # Tiny prompt — Stage 0 only (availability + Structured Outputs later).
        response = await llm.ainvoke(
            [
                ("system", "Reply with exactly one word: pong"),
                ("human", "ping"),
            ]
        )
        content = getattr(response, "content", None)
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part) for part in content
            )
        text = (content or "").strip()
        usage = _usage_from_message(response)
        row.update(
            {
                "ok": True,
                "preview": text[:80],
                "usage": usage,
                "estimated_usd": _estimate_usd(
                    model,
                    usage.get("prompt_tokens") if isinstance(usage.get("prompt_tokens"), int) else None,
                    usage.get("completion_tokens")
                    if isinstance(usage.get("completion_tokens"), int)
                    else None,
                ),
            }
        )
    except Exception as exc:  # noqa: BLE001 — probe must collect failures
        row["error"] = f"{type(exc).__name__}: {exc}"
    row["latency_ms"] = int((time.perf_counter() - started) * 1000)
    return row


def _pilot_cost_projection(probe_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Scale Stage 0 per-call cost to full pilot inventory (120 translate + 60 judge)."""
    by_role = {r["role"]: r for r in probe_rows}
    # Pessimistic: assume pilot calls use ~8× probe tokens if probe was tiny.
    scale = 8.0
    translate_a = by_role.get("A", {}).get("estimated_usd")
    translate_b = by_role.get("B", {}).get("estimated_usd")
    judge = by_role.get("judge", {}).get("estimated_usd")
    if translate_a is None or translate_b is None or judge is None:
        return {
            "method": "rate_table_fallback",
            "note": "Probe did not return usage; using public rate table + assumed tokens.",
            "assumed_translate_tokens": {"in": 1500, "out": 500},
            "assumed_judge_tokens": {"in": 3000, "out": 800},
            "projected_usd": {
                "translate_A_60": round(60 * _estimate_usd("gpt-5.6-luna", 1500, 500) or 0, 4),
                "translate_B_60": round(60 * _estimate_usd("gpt-6-luna", 1500, 500) or 0, 4),
                "judge_60": round(60 * _estimate_usd("gpt-5-mini", 3000, 800) or 0, 4),
            },
        }
    proj = {
        "method": "scaled_from_probe",
        "scale_factor": scale,
        "projected_usd": {
            "translate_A_60": round(60 * translate_a * scale, 4),
            "translate_B_60": round(60 * translate_b * scale, 4),
            "judge_60": round(60 * judge * scale, 4),
        },
    }
    total = sum(proj["projected_usd"].values())
    proj["projected_usd"]["total_plus_buffer_0_25"] = round(total + 0.25, 4)
    proj["under_usd_4"] = (total + 0.25) <= 4.0
    return proj


async def main() -> int:
    parser = argparse.ArgumentParser(description="Decime eval Stage 0 model probe")
    parser.add_argument("--model-a", default=DEFAULT_MODELS["A"])
    parser.add_argument("--model-b", default=DEFAULT_MODELS["B"])
    parser.add_argument("--model-judge", default=DEFAULT_MODELS["judge"])
    parser.add_argument(
        "--output-dir",
        default="",
        help="Default: apps/api/evals/reports/pilot-2026-10/stage0",
    )
    args = parser.parse_args()

    from decime_api.config import settings

    if not settings.openai_api_key:
        print("ERROR: OPENAI_API_KEY missing in environment / .env")
        return 2

    out_dir = (
        Path(args.output_dir)
        if args.output_dir
        else Path(__file__).resolve().parents[1] / "evals" / "reports" / "pilot-2026-10" / "stage0"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    roles = [
        ("A", args.model_a),
        ("B", args.model_b),
        ("judge", args.model_judge),
    ]
    rows: list[dict[str, Any]] = []
    for role, model in roles:
        print(f"Probing {role}={model} ...", flush=True)
        row = await probe_model(
            role=role,
            model=model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_text_base_url,
        )
        rows.append(row)
        status = "OK" if row["ok"] else f"FAIL {row['error']}"
        print(f"  {status} latency_ms={row['latency_ms']} preview={row.get('preview')!r}")

    report = {
        "stage": 0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "budget_usd_ceiling": 4.0,
        "openai_text_base_url": settings.openai_text_base_url or None,
        "langsmith_key_present": bool(
            settings.langsmith_api_key
            or __import__("os").environ.get("LANGSMITH_API_KEY")
            or __import__("os").environ.get("LANGCHAIN_API_KEY")
        ),
        "probes": rows,
        "pilot_projection": _pilot_cost_projection(rows),
        "gates": {
            "all_models_ok": all(r["ok"] for r in rows),
            "ready_for_dataset_drafts": all(r["ok"] for r in rows),
            "langsmith_configured": False,  # Stage 0 expects greenfield; flip after owner setup
        },
    }
    # Flip langsmith_configured if key present (account still needs manual project setup).
    report["gates"]["langsmith_key_present"] = report["langsmith_key_present"]

    json_path = out_dir / "stage0_probe.json"
    md_path = out_dir / "stage0_probe.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Stage 0 — Model probe",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Budget ceiling: USD {report['budget_usd_ceiling']}",
        f"- LangSmith API key present: **{report['langsmith_key_present']}**",
        "",
        "## Probe results",
        "",
        "| Role | Model | OK | Latency ms | Est. USD (this call) | Preview / error |",
        "|------|-------|----|------------|----------------------|-----------------|",
    ]
    for r in rows:
        err = r.get("error") or r.get("preview") or ""
        err = str(err).replace("|", "\\|")[:60]
        lines.append(
            f"| {r['role']} | `{r['model']}` | {r['ok']} | {r['latency_ms']} | "
            f"{r.get('estimated_usd')} | {err} |"
        )
    lines.extend(
        [
            "",
            "## Pilot cost projection",
            "",
            "```json",
            json.dumps(report["pilot_projection"], indent=2),
            "```",
            "",
            "## Manual checks for owner",
            "",
            "1. Confirm each probe row `ok: true`.",
            "2. Create LangSmith account + API key (see `docs/llm_eval_stage0.md`).",
            "3. Approve moving to Stage 1 (draft `ru_esuy_judge_v1` dataset) only if gates pass.",
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0 if report["gates"]["all_models_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
