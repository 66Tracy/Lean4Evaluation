import os
from dataclasses import dataclass, field
from dotenv import load_dotenv


@dataclass
class APIConfig:
    test_api_url: str = ""
    test_model_name: str = ""
    test_api_key: str = ""

    judge_api_url: str = ""
    judge_model_name: str = ""
    judge_api_key: str = ""

    lean_api_url: str = "http://localhost:8000/run"

    @classmethod
    def from_env(cls, env_path: str = ".env") -> "APIConfig":
        load_dotenv(env_path, override=True)

        test_api_url = os.getenv("TEST_API_URL", "")
        test_model_name = os.getenv("TEST_MODEL_NAME", "")
        test_api_key = os.getenv("TEST_API_KEY", "")

        judge_api_url = os.getenv("JUDGE_API_URL", "") or test_api_url
        judge_model_name = os.getenv("JUDGE_MODEL_NAME", "") or test_model_name
        judge_api_key = os.getenv("JUDGE_API_KEY", "") or test_api_key

        lean_api_url = os.getenv("LEAN_API_URL", "http://localhost:8000/run")

        return cls(
            test_api_url=test_api_url,
            test_model_name=test_model_name,
            test_api_key=test_api_key,
            judge_api_url=judge_api_url,
            judge_model_name=judge_model_name,
            judge_api_key=judge_api_key,
            lean_api_url=lean_api_url,
        )
