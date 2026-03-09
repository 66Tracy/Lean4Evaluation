import json
import re
from typing import Any, Dict, List


def load_prompt(template_path: str, **kwargs: Any) -> str:
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()
    return template.format(**kwargs)


def read_jsonl(file_path: str) -> List[dict]:
    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_jsonl(file_path: str, data: List[dict]) -> None:
    with open(file_path, "w", encoding="utf-8") as f:
        for record in data:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def extract_code_from_markdown(text: str, language: str = "lean") -> str:
    pattern = rf"```{re.escape(language)}\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Try generic code block
    pattern_generic = r"```\s*\n(.*?)```"
    match_generic = re.search(pattern_generic, text, re.DOTALL)
    if match_generic:
        return match_generic.group(1).strip()
    return text.strip()


def extract_json_from_response(response: str) -> Dict:
    # Try to find JSON in code block first
    pattern = r"```(?:json)?\s*\n(.*?)```"
    match = re.search(pattern, response, re.DOTALL)
    if match:
        return json.loads(match.group(1).strip())
    # Try to parse the whole response as JSON
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        pass
    # Try to find JSON object in the response
    match = re.search(r"\{[^{}]*\}", response)
    if match:
        return json.loads(match.group(0))
    raise ValueError(f"Cannot extract JSON from response: {response[:200]}")
