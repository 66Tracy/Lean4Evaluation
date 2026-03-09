import requests
import time
from typing import Optional, Dict, Any

DEFAULT_API = "http://localhost:8000/run"
DEFAULT_TIMEOUT_SEC = 60

def run_lean_code(
    code: str,
    api: str = DEFAULT_API,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    module_hint: Optional[str] = None,
    prebuild: bool = False,
    cleanup: bool = True,
    http_connect_timeout: float = 30.0,
) -> Dict[str, Any]:
    """
    运行 Lean 4 代码字符串

    Args:
        code: Lean 代码
        api: Lean 运行 API 地址
        timeout_sec: 执行超时时间（秒）
        module_hint: 模块名（可选）
        prebuild: 是否预构建
        cleanup: 是否清理工作目录
        http_connect_timeout: HTTP 连接超时

    Returns:
        {
            "ok": bool,           # 请求是否成功
            "status_code": int,   # HTTP 状态码
            "elapsed_sec": float, # 执行耗时
            "response": {...}     # API 返回的响应
        }
    """
    payload: Dict[str, Any] = {
        "code": code,
        "timeout_sec": timeout_sec,
        "prebuild": prebuild,
        "cleanup": cleanup,
    }
    if module_hint:
        payload["module_hint"] = module_hint

    http_read_timeout = timeout_sec + 30
    t0 = time.perf_counter()

    try:
        resp = requests.post(
            api,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=(http_connect_timeout, http_read_timeout),
        )
        elapsed = time.perf_counter() - t0
        try:
            body = resp.json()
        except ValueError:
            body = resp.text

        ok = 200 <= resp.status_code < 300
        return {
            "ok": ok,
            "status_code": resp.status_code,
            "elapsed_sec": round(elapsed, 3),
            "response": body,
        }
    except requests.RequestException as e:
        elapsed = time.perf_counter() - t0
        return {
            "ok": False,
            "status_code": None,
            "elapsed_sec": round(elapsed, 3),
            "response": {"error": f"{type(e).__name__}: {e}"},
        }


if __name__ == "__main__":
    # Example: run a simple Lean4 program
    lean_code = r"""
#check Nat.add
#eval 2 + 3
theorem test : 1 + 1 = 2 := by norm_num
"""
    result = run_lean_code(lean_code)
    print(f"OK: {result['ok']}")
    print(f"Status: {result['status_code']}")
    print(f"Elapsed: {result['elapsed_sec']}s")
    print(f"Response: {result['response']}")