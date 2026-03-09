import asyncio
import logging
from typing import Any, Dict, List

from src.core.client import LLMClient
from src.core.utils import extract_json_from_response, load_prompt

logger = logging.getLogger(__name__)


async def run_translation(
    client: LLMClient,
    records: List[Dict],
    prompt_template_path: str,
    concurrency: int = 5,
    **kwargs: Any,
) -> List[str]:
    prompts = []
    for rec in records:
        prompt = load_prompt(prompt_template_path, nl_statement=rec["nl_statement"])
        prompts.append(prompt)

    results = await client.batch_generate(prompts, max_concurrency=concurrency, **kwargs)
    return results


async def run_judge(
    judge_client: LLMClient,
    records: List[Dict],
    predictions: List[str],
    judge_prompt_path: str,
    concurrency: int = 5,
    **kwargs: Any,
) -> List[Dict]:
    prompts = []
    for rec, pred in zip(records, predictions):
        prompt = load_prompt(
            judge_prompt_path,
            gt=rec["formal_statement"],
            pred=pred,
        )
        prompts.append(prompt)

    judge_responses = await judge_client.batch_generate(
        prompts, max_concurrency=concurrency, **kwargs
    )

    scored = []
    for rec, pred, resp in zip(records, predictions, judge_responses):
        try:
            scores = extract_json_from_response(resp)
            equivalence = int(scores.get("equivalence", 0))
            mathlib_style = int(scores.get("mathlib_style", 0))
            syntax = int(scores.get("syntax", 0))
        except (ValueError, KeyError, TypeError) as e:
            logger.warning(f"Failed to parse judge response for {rec['id']}: {e}")
            equivalence = 0
            mathlib_style = 0
            syntax = 0

        final_score = (equivalence + mathlib_style) * syntax

        scored.append({
            "id": rec["id"],
            "nl_statement": rec["nl_statement"],
            "formal_statement": rec["formal_statement"],
            "pred": pred,
            "equivalence": equivalence,
            "mathlib_style": mathlib_style,
            "syntax": syntax,
            "final_score": final_score,
        })

    return scored


async def run_task1(
    test_client: LLMClient,
    judge_client: LLMClient,
    records: List[Dict],
    translate_prompt_path: str,
    judge_prompt_path: str,
    concurrency: int = 5,
) -> List[Dict]:
    logger.info(f"Running Task1 on {len(records)} records...")

    predictions = await run_translation(
        test_client, records, translate_prompt_path, concurrency=concurrency
    )

    results = await run_judge(
        judge_client, records, predictions, judge_prompt_path, concurrency=concurrency
    )

    avg_score = sum(r["final_score"] for r in results) / len(results) if results else 0
    logger.info(f"Task1 complete. Average final_score: {avg_score:.2f}")

    return results
