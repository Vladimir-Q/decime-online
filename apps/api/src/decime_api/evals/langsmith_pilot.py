"""Upload Decime pilot eval results to LangSmith (Stage 3).

Creates/updates a dataset of case inputs, then logs an experiment whose target
reads precomputed outputs keyed by ``case_id`` (so Decime's own LLM path runs
first; LangSmith stores comparable A/B experiments for pairwise later).

Token usage and estimated USD cost from the local runner are attached as
LangSmith ``usage_metadata`` on a child ``run_type=llm`` span so experiment
cost columns are non-zero even though the target only replays outputs.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _ensure_langsmith_env() -> str:
    from decime_api.config import settings

    key = (
        settings.langsmith_api_key
        or os.environ.get("LANGSMITH_API_KEY")
        or os.environ.get("LANGCHAIN_API_KEY")
        or ""
    ).strip()
    if not key:
        raise ValueError("LANGSMITH_API_KEY missing — add to local .env")
    os.environ["LANGSMITH_API_KEY"] = key
    os.environ["LANGCHAIN_API_KEY"] = key
    project = (settings.langsmith_project or "decime-eval-pilot").strip()
    os.environ["LANGSMITH_PROJECT"] = project
    os.environ["LANGCHAIN_PROJECT"] = project
    return project


def usage_metadata_for_langsmith(usage: dict[str, Any] | None) -> dict[str, Any]:
    """Map Decime eval ``usage`` row → LangSmith ``usage_metadata`` fields."""
    usage = usage or {}
    prompt = int(usage.get("prompt_tokens") or 0)
    completion = int(usage.get("completion_tokens") or 0)
    total = int(usage.get("total_tokens") or (prompt + completion))
    meta: dict[str, Any] = {
        "input_tokens": prompt,
        "output_tokens": completion,
        "total_tokens": total,
    }
    # Explicit costs: Luna models may not be in LangSmith's price table yet.
    if usage.get("input_cost_usd") is not None:
        meta["input_cost"] = float(usage["input_cost_usd"])
    if usage.get("output_cost_usd") is not None:
        meta["output_cost"] = float(usage["output_cost_usd"])
    if usage.get("estimated_cost_usd") is not None:
        meta["total_cost"] = float(usage["estimated_cost_usd"])
    return meta


def ensure_dataset(
    *,
    dataset_name: str,
    cases: list[dict[str, Any]],
    description: str,
) -> Any:
    """Create dataset if needed; replace examples to match current JSONL."""
    from langsmith import Client
    from langsmith.utils import LangSmithNotFoundError

    _ensure_langsmith_env()
    client = Client()
    try:
        dataset = client.read_dataset(dataset_name=dataset_name)
    except LangSmithNotFoundError:
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description=description,
        )
        logger.info("Created LangSmith dataset=%s", dataset_name)
    else:
        # Clear stale examples so case_ids stay aligned with JSONL.
        # Auth and network errors must surface; only a missing dataset is created.
        for example in client.list_examples(dataset_id=dataset.id):
            client.delete_example(example.id)
        logger.info("Cleared examples on existing dataset=%s", dataset_name)

    examples = []
    for case in cases:
        inp = dict(case.get("input") or {})
        examples.append(
            {
                "inputs": {"case_id": case["id"], **inp},
                "metadata": {
                    "suite": case.get("suite"),
                    "tags": case.get("tags") or [],
                    "tests": case.get("tests"),
                },
            }
        )
    client.create_examples(dataset_id=dataset.id, examples=examples)
    logger.info("Uploaded %s examples to dataset=%s", len(examples), dataset_name)
    return dataset


def upload_experiment_from_results(
    *,
    dataset_name: str,
    results: list[dict[str, Any]],
    experiment_prefix: str,
    metadata: dict[str, Any],
    model: str | None = None,
) -> Any:
    """Create a LangSmith experiment from local runner rows (keyed by case_id)."""
    from langsmith import get_current_run_tree, traceable
    from langsmith.evaluation import evaluate

    _ensure_langsmith_env()
    by_id = {row["id"]: row for row in results if row.get("id")}
    model_name = (
        model
        or metadata.get("model")
        or next(
            (
                (row.get("usage") or {}).get("model")
                for row in results
                if (row.get("usage") or {}).get("model")
            ),
            "unknown",
        )
    )
    provider = str(metadata.get("provider") or "openai")

    @traceable(
        run_type="llm",
        name="decime_eval_replay",
        metadata={"ls_provider": provider, "ls_model_name": model_name},
    )
    def _replay_llm(case_id: str) -> dict[str, Any]:
        row = by_id[case_id]
        out = dict(row.get("output") or {})
        run = get_current_run_tree()
        if run is not None:
            extra_meta: dict[str, Any] = {"decime_case_id": case_id}
            latency_ms = row.get("latency_ms")
            if latency_ms is not None:
                extra_meta["latency_ms"] = latency_ms
            run.set(
                usage_metadata=usage_metadata_for_langsmith(row.get("usage")),
                metadata=extra_meta,
            )
        return out

    def target(inputs: dict[str, Any]) -> dict[str, Any]:
        case_id = inputs.get("case_id")
        row = by_id.get(case_id)
        if row is None:
            raise KeyError(f"No local result for case_id={case_id!r}")
        if row.get("error"):
            raise RuntimeError(f"case {case_id}: {row['error']}")
        out = _replay_llm(str(case_id))
        out["case_id"] = case_id
        return out

    return evaluate(
        target,
        data=dataset_name,
        experiment_prefix=experiment_prefix,
        metadata={**metadata, "model": model_name},
        max_concurrency=2,
        num_repetitions=1,
    )
