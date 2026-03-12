import asyncio
import logging
from typing import Any, List, Optional

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: int = 120):
        self.model = model
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        temperature = kwargs.get("temperature", 0.0)
        max_tokens = kwargs.get("max_tokens", 4096)
        seed = kwargs.get("seed", None)
        reasoning_effort = kwargs.get("reasoning_effort", None)

        params: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if seed is not None:
            params["seed"] = seed
        if reasoning_effort and reasoning_effort != "none":
            params["extra_body"] = {"reasoning_effort": reasoning_effort}

        response = await self.client.chat.completions.create(**params)
        content = response.choices[0].message.content or ""
        return content

    async def batch_generate(
        self,
        prompts: List[str],
        max_concurrency: int = 5,
        **kwargs: Any,
    ) -> List[str]:
        semaphore = asyncio.Semaphore(max_concurrency)
        results: List[Optional[str]] = [None] * len(prompts)

        async def _generate_one(index: int, prompt: str) -> None:
            async with semaphore:
                try:
                    result = await self.generate(prompt, **kwargs)
                    results[index] = result
                except Exception as e:
                    logger.error(f"Failed to generate for prompt {index}: {e}")
                    results[index] = f"__ERROR__: {e}"

        tasks = [_generate_one(i, p) for i, p in enumerate(prompts)]
        await asyncio.gather(*tasks)
        return results  # type: ignore
