import argparse
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.core.config import APIConfig
from src.core.client import LLMClient
from src.core.utils import read_jsonl, write_jsonl
from src.tasks.task1 import run_task1


def parse_args():
    parser = argparse.ArgumentParser(description="Task1: Translation Quality Evaluation")
    parser.add_argument("--data", required=True, help="Path to benchmark JSONL file")
    parser.add_argument("--output", required=True, help="Path to output JSONL file")
    parser.add_argument("--prompt", default="prompts/task1_translate.txt", help="Translation prompt template")
    parser.add_argument("--judge-prompt", default="prompts/task1_judge.txt", help="Judge prompt template")
    parser.add_argument("--judge-model", default=None, help="Judge model name (defaults to tested model)")
    parser.add_argument("--judge-url", default=None, help="Judge model API URL")
    parser.add_argument("--judge-key", default=None, help="Judge model API key")
    parser.add_argument("--concurrency", type=int, default=5, help="Max concurrent API calls")
    parser.add_argument("--env", default=".env", help="Path to .env file")
    return parser.parse_args()


async def main():
    args = parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = APIConfig.from_env(args.env)

    test_client = LLMClient(
        base_url=config.test_api_url,
        api_key=config.test_api_key,
        model=config.test_model_name,
    )

    judge_url = args.judge_url or config.judge_api_url
    judge_key = args.judge_key or config.judge_api_key
    judge_model = args.judge_model or config.judge_model_name

    judge_client = LLMClient(
        base_url=judge_url,
        api_key=judge_key,
        model=judge_model,
    )

    records = read_jsonl(args.data)
    logging.info(f"Loaded {len(records)} records from {args.data}")

    # Create output directory if needed
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    results = await run_task1(
        test_client=test_client,
        judge_client=judge_client,
        records=records,
        translate_prompt_path=args.prompt,
        judge_prompt_path=args.judge_prompt,
        concurrency=args.concurrency,
    )

    write_jsonl(args.output, results)
    logging.info(f"Results written to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
