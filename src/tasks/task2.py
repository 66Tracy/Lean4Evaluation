import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from math import comb
from typing import Any, Dict, List

from src.core.client import LLMClient
from src.core.utils import extract_code_from_markdown, load_prompt
from src.lean_runner_api import run_lean_code

logger = logging.getLogger(__name__)


def build_lean_module(header: str, formal_statement: str, proof_code: str) -> str:
    # Replace 'sorry' in formal_statement with 'by\n  {proof_code}'
    proof_lines = proof_code.strip().splitlines()

    # Check if proof already starts with 'by'
    if proof_lines and proof_lines[0].strip().startswith("by"):
        # proof_code already includes 'by', use it directly
        proof_block = proof_code.strip()
    else:
        # Wrap in 'by' block with proper indentation
        indented = "\n".join("  " + line for line in proof_lines)
        proof_block = "by\n" + indented

    full_statement = formal_statement.replace(":= sorry", ":= " + proof_block)

    return header.strip() + "\n\n" + full_statement


def is_success(result: Dict) -> bool:
    if not result["ok"]:
        return False
    resp = result["response"]
    if isinstance(resp, dict):
        # Check common success indicators
        if resp.get("success") is True:
            return True
        if resp.get("error") is not None and resp.get("error") != "":
            return False
        # If there's an 'env' field or empty error, consider success
        if "error" in resp and (resp["error"] is None or resp["error"] == "" or resp["error"] == 0):
            return True
        # If 'messages' field exists with no errors
        if "messages" in resp:
            messages = resp["messages"]
            if isinstance(messages, list):
                return not any(
                    m.get("severity") == "error"
                    for m in messages
                    if isinstance(m, dict)
                )
        # Fallback: if ok is True and no obvious error field
        return True
    if isinstance(resp, str):
        lower = resp.lower()
        return "error" not in lower and "sorry" not in lower
    return False


def compute_pass_at_k(n: int, c: int, k: int) -> float:
    if n < k:
        return 0.0
    if c == 0:
        return 0.0
    if n - c < k:
        return 1.0
    return 1.0 - comb(n - c, k) / comb(n, k)


async def generate_proofs(
    client: LLMClient,
    records: List[Dict],
    prompt_template_path: str,
    k: int = 5,
    temperature: float = 0.7,
    seed_base: int | None = None,
    concurrency: int = 5,
) -> Dict[str, List[str]]:
    """Generate k proof attempts for each record. Returns {id: [proof1, proof2, ...]}."""
    all_prompts = []
    prompt_map = []  # (record_id, attempt_index)

    for rec in records:
        prompt = load_prompt(prompt_template_path, formal_statement=rec["formal_statement"])
        for i in range(k):
            all_prompts.append(prompt)
            prompt_map.append((rec["id"], i))

    kwargs: Dict[str, Any] = {"temperature": temperature}
    if seed_base is not None:
        # We can't pass per-prompt seeds via batch_generate easily,
        # so we just set a base seed for the batch
        kwargs["seed"] = seed_base

    results = await client.batch_generate(all_prompts, max_concurrency=concurrency, **kwargs)

    proofs: Dict[str, List[str]] = {}
    for (rec_id, _), raw in zip(prompt_map, results):
        if rec_id not in proofs:
            proofs[rec_id] = []
        # Extract lean code from potential markdown
        code = extract_code_from_markdown(raw, language="lean")
        proofs[rec_id].append(code)

    return proofs


def execute_proofs(
    records: List[Dict],
    proofs: Dict[str, List[str]],
    lean_api_url: str,
    lean_timeout: int = 60,
    lean_concurrency: int = 5,
) -> Dict[str, List[Dict]]:
    """Execute all proofs via Lean runner. Returns {id: [{success, elapsed_sec, error?, proof}]}."""
    tasks = []  # (rec_id, attempt_idx, full_code, proof_code)

    for rec in records:
        rec_id = rec["id"]
        header = rec.get("header", "")
        formal = rec["formal_statement"]
        for idx, proof_code in enumerate(proofs.get(rec_id, [])):
            full_code = build_lean_module(header, formal, proof_code)
            tasks.append((rec_id, idx, full_code, proof_code))

    all_results: Dict[str, List[Dict]] = {rec["id"]: [] for rec in records}

    def _run_one(task_item):
        rec_id, idx, full_code, proof_code = task_item
        result = run_lean_code(code=full_code, api=lean_api_url, timeout_sec=lean_timeout)
        success = is_success(result)
        detail = {
            "proof": proof_code,
            "success": success,
            "elapsed_sec": result["elapsed_sec"],
        }
        if not success:
            resp = result.get("response", {})
            if isinstance(resp, dict):
                detail["error"] = resp.get("error", str(resp))
            else:
                detail["error"] = str(resp)
        return rec_id, detail

    with ThreadPoolExecutor(max_workers=lean_concurrency) as pool:
        futures = [pool.submit(_run_one, t) for t in tasks]
        for future in futures:
            rec_id, detail = future.result()
            all_results[rec_id].append(detail)

    return all_results


async def run_task2(
    client: LLMClient,
    records: List[Dict],
    prompt_template_path: str,
    k: int = 5,
    temperature: float = 0.7,
    seed_base: int | None = None,
    concurrency: int = 5,
    lean_api_url: str = "http://localhost:8000/run",
    lean_timeout: int = 60,
    lean_concurrency: int = 5,
) -> List[Dict]:
    logger.info(f"Running Task2 on {len(records)} records with k={k}...")

    proofs = await generate_proofs(
        client, records, prompt_template_path,
        k=k, temperature=temperature, seed_base=seed_base, concurrency=concurrency,
    )

    logger.info("Executing proofs via Lean runner...")
    execution_results = execute_proofs(
        records, proofs, lean_api_url,
        lean_timeout=lean_timeout, lean_concurrency=lean_concurrency,
    )

    output = []
    for rec in records:
        rec_id = rec["id"]
        details = execution_results.get(rec_id, [])
        success_count = sum(1 for d in details if d["success"])
        n = len(details)
        pass_k = compute_pass_at_k(n, success_count, k)

        output.append({
            "id": rec_id,
            "formal_statement": rec["formal_statement"],
            "k": k,
            "success_count": success_count,
            "pass_at_k": pass_k,
            "details": details,
        })

    total_pass = sum(r["pass_at_k"] for r in output)
    avg_pass = total_pass / len(output) if output else 0
    logger.info(f"Task2 complete. Average Pass@{k}: {avg_pass:.4f}")

    return output
