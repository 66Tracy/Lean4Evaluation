import argparse
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.core.config import APIConfig
from src.core.client import LLMClient
from src.core.utils import read_jsonl, write_jsonl
from src.tasks.task2 import run_task2


def parse_args():
    parser = argparse.ArgumentParser(description="Task2: Proof Capability Evaluation (Pass@k)")
    parser.add_argument("--data", required=True, help="Path to benchmark JSONL file")
    parser.add_argument("--output", required=True, help="Path to output JSONL file")
    parser.add_argument("--prompt", default="prompts/task2_prove.txt", help="Proof prompt template")
    parser.add_argument("--k", type=int, default=5, help="Number of proof attempts per theorem")
    parser.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature")
    parser.add_argument("--seed-base", type=int, default=None, help="Base seed for reproducibility")
    parser.add_argument("--lean-api", default=None, help="Lean runner API URL")
    parser.add_argument("--lean-concurrency", type=int, default=5, help="Max concurrent Lean executions")
    parser.add_argument("--lean-timeout", type=int, default=60, help="Lean execution timeout (seconds)")
    parser.add_argument("--concurrency", type=int, default=5, help="Max concurrent LLM API calls")
    parser.add_argument("--max-tokens", type=int, default=32768, help="Max tokens for LLM generation")
    parser.add_argument("--reasoning-effort", type=str, default="none",
                        choices=["none", "low", "medium", "high"],
                        help="Reasoning effort level (for reasoning models)")
    parser.add_argument("--env", default=".env", help="Path to .env file")
    return parser.parse_args()


async def main():
    args = parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = APIConfig.from_env(args.env)

    client = LLMClient(
        base_url=config.test_api_url,
        api_key=config.test_api_key,
        model=config.test_model_name,
    )

    lean_api = args.lean_api or config.lean_api_url

    records = read_jsonl(args.data)
    logging.info(f"Loaded {len(records)} records from {args.data}")

    # Create output directory if needed
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    results = await run_task2(
        client=client,
        records=records,
        prompt_template_path=args.prompt,
        k=args.k,
        temperature=args.temperature,
        seed_base=args.seed_base,
        concurrency=args.concurrency,
        lean_api_url=lean_api,
        lean_timeout=args.lean_timeout,
        lean_concurrency=args.lean_concurrency,
        max_tokens=args.max_tokens,
        reasoning_effort=args.reasoning_effort,
    )

    write_jsonl(args.output, results)
    logging.info(f"Results written to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
