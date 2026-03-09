## 细化 Milestone 计划：结合 `lean_runner_api.py` 的实现

### 总体架构回顾
- **推理框架**：异步并发调用 LLM API（支持任意 base_url/model/api_key），提供响应提取（JSON / 代码块剥离）。
- **测试任务**：
  - **Task1**：翻译评分（使用裁判模型，可配置不同模型）。
  - **Task2**：证明能力评估（调用 `run_lean_code` 执行生成的证明，计算 Pass@k）。
- **解耦设计**：所有任务与核心框架仅通过配置文件、prompt 模板和数据文件交互。

### 针对 `run_lean_code` 的关键决策
`run_lean_code` 返回的字典结构：
```python
{
    "ok": bool,           # 请求是否成功（HTTP 状态码 2xx）
    "status_code": int,   # HTTP 状态码（可能为 None）
    "elapsed_sec": float,
    "response": {...}     # API 返回的响应（JSON 或纯文本）
}
```
- **判断证明成功**：不能仅靠 `ok`，因为即使 HTTP 请求成功，Lean 代码也可能包含编译错误。需要解析 `response` 字段，确定 Lean 执行是否通过。
- **未知的 `response` 格式**：需通过实验或文档确认。我们将采用**可配置的成功判定函数**，允许用户根据实际 API 响应结构调整判断逻辑（默认实现可假设 `response` 包含 `"success": true` 或 `"error": null` 等）。

---

## 里程碑计划（细化版）

### 第 1 阶段：基础环境与推理框架
**目标**：搭建项目骨架，实现可并发的异步推理客户端。

#### 1.1 环境初始化
- 使用 `uv init` 创建项目，配置 `pyproject.toml`，依赖：
  ```toml
  [tool.uv]
  dependencies = [
      "openai>=1.0.0",
      "python-dotenv>=1.0.0",
      "aiohttp>=3.9.0",
      "pydantic>=2.0.0",
      "requests>=2.31.0",  # 用于 run_lean_code
      "tenacity>=8.0.0",   # 重试机制
  ]
  ```
- 创建目录结构：
  ```
  .
  ├── src/
  │   ├── __init__.py
  │   ├── core/               # 推理框架核心
  │   │   ├── client.py
  │   │   ├── config.py
  │   │   └── utils.py
  │   ├── tasks/              # 测试任务
  │   │   ├── task1.py
  │   │   └── task2.py
  │   └── lean_runner_api.py  # 已提供的接口（直接复制）
  ├── prompts/                 # prompt 模板
  ├── data/                    # benchmark 数据
  ├── scripts/                 # 命令行入口
  ├── tests/
  └── .env.example
  ```

#### 1.2 推理客户端实现（`src/core/client.py`）
- 封装 `AsyncOpenAI` 客户端，构造函数接收 `base_url`, `api_key`, `model`。
- 实现 `async generate(prompt: str, **kwargs) -> str`：
  - 处理 `max_tokens`, `temperature`, `seed` 等参数。
  - 自动提取回复内容：若返回包含 markdown 代码块（如 ```json ... ```），则提取内部内容；否则返回完整文本。
  - 添加异常处理和重试（使用 `tenacity` 装饰器）。
- 实现 `async batch_generate(prompts: List[str], max_concurrency: int = 5, **kwargs) -> List[str]`：
  - 使用 `asyncio.Semaphore` 控制并发。
  - 返回结果列表，顺序与输入一致。

#### 1.3 配置加载（`src/core/config.py`）
- 使用 `python-dotenv` 加载 `.env` 文件，提供 `APIConfig` 数据类。
- 支持通过环境变量覆盖（如 `BASE_URL`, `MODEL_NAME`, `API_KEY`）。

#### 1.4 工具函数（`src/core/utils.py`）
- 实现 `load_prompt(template_path: str, **kwargs) -> str`：读取模板并格式化。
- 实现 `read_jsonl(file_path) -> List[dict]` 和 `write_jsonl(file_path, data)`。
- 实现 `extract_code_from_markdown(text: str, language: str = "lean") -> str`：提取指定语言的代码块内容。

#### 1.5 单元测试
- 测试 `generate` 的响应提取（mock API）。
- 测试并发控制逻辑。

**交付物**：
- 可运行的推理框架，支持单条和并发生成。
- 测试通过报告。

---

### 第 2 阶段：Task1 翻译质量评估
**目标**：实现自然语言 → Formal Statement 的翻译测试，使用裁判模型评分。

#### 2.1 数据加载
- 实现 `load_benchmark(data_path: str) -> List[Dict]`，读取 JSONL 文件，每条包含 `id`, `nl_statement`, `formal_statement`。

#### 2.2 Prompt 模板
- 创建 `prompts/task1_translate.txt`，内容示例：
  ```
  请将以下自然语言数学陈述翻译为 Lean 4 形式化定理声明，只输出定理声明本身，不要附加解释：
  {nl_statement}
  ```
- 创建 `prompts/task1_judge.txt`（裁判 prompt）：
  ```
  你是 Lean 4 专家。对比专家答案 `{gt}` 和模型答案 `{pred}`。
  1. 等价性 (0-5分)：逻辑语义是否完全一致？
  2. Mathlib 规范 (0-5分)：命名是否符合 Mathlib 4 风格（如 PascalCase 类型）？
  3. 语法正确性 (0/1)：是否有明显的 Lean 语法错误？
  请以 JSON 格式输出，例如：{{"equivalence": 5, "mathlib_style": 5, "syntax": 1}}
  ```

#### 2.3 翻译执行
- 脚本 `scripts/run_task1.py`：
  - 解析命令行参数：`--data`、`--output`、`--prompt`（可选，默认 `prompts/task1_translate.txt`）、`--judge-model`、`--judge-url`、`--judge-key`（若无则使用环境变量中的待测模型配置）。
  - 加载 benchmark 数据。
  - 构造翻译 prompt 列表。
  - 调用 `batch_generate` 获取模型翻译结果 `pred`。
  - 对每条数据，构造裁判 prompt（填充 `gt` 和 `pred`），调用裁判模型获取评分（期望 JSON）。
  - 解析评分，计算最终得分 `(equivalence + mathlib_style) * syntax`。
  - 输出结果到指定 JSONL，包含所有原始字段和评分详情。

#### 2.4 结果汇总
- 输出文件格式示例：
  ```json
  {"id": "1", "nl_statement": "...", "formal_statement": "...", "pred": "...", "equivalence": 5, "mathlib_style": 4, "syntax": 1, "final_score": 9}
  ```

**交付物**：
- Task1 完整实现，可运行脚本。
- 对小型 benchmark 的测试输出示例。

---

### 第 3 阶段：Task2 证明能力测试（Pass@k）
**目标**：实现定理证明测试，计算 Pass@k，集成 `run_lean_code`。

#### 3.1 数据与 Prompt
- 复用 Task1 的 benchmark 数据，但只需 `formal_statement` 字段。
- 创建 `prompts/task2_prove.txt`：
  ```
  你是 Lean 4 证明助手。给定以下定理声明，请直接给出完整的证明过程（由 `by` 开头的 Tactic 块），不要包含定理声明本身，也不要添加额外解释。
  定理：{formal_statement}
  要求：仅使用 Mathlib 4 中的有效引理，严禁使用 `sorry`。
  ```

#### 3.2 生成 k 个证明
- 脚本 `scripts/run_task2.py`：
  - 参数：`--data`、`--output`、`--prompt`（默认 `prompts/task2_prove.txt`）、`--k`（默认 5）、`--temperature`（默认 0.7）、`--seed-base`（可选，用于控制随机性）。
  - 加载 benchmark 数据。
  - 对每条数据，构造 prompt 列表（每个 prompt 相同，但后续通过 `seed` 或温度保证多样性）。
  - 调用 `batch_generate` 并发生成 k 次，设置 `temperature=0.7`。如果 API 支持 `seed`，则使用 `seed_base + i` 确保可复现性。
  - 返回结果列表（k 个字符串）。

#### 3.3 构建完整 Lean 代码
- 对于每个生成的证明块 `proof_code`，构建完整的 Lean 模块：
  ```lean
  import Mathlib

  theorem task2_proof_{id}_{idx} : {formal_statement} := by
    {proof_code}
  ```
- 注意：`proof_code` 可能包含缩进问题，需确保与 `by` 对齐。可以使用文本处理保证每行前有 2 个空格。
- 如果模型返回了包含额外文本的 markdown，使用 `extract_code_from_markdown` 提取 Lean 代码。

#### 3.4 运行 Lean 代码并判断成功
- 定义成功判定函数 `is_success(result: Dict) -> bool`：
  ```python
  def is_success(result):
      if not result["ok"]:  # HTTP 请求失败
          return False
      # 根据实际 API 响应格式调整以下逻辑
      resp = result["response"]
      if isinstance(resp, dict):
          # 假设 API 返回包含 "success": true 或 "error": null
          if resp.get("success") is True:
              return True
          if resp.get("error") is None and resp.get("output"):
              # 可能需要检查 output 中是否包含 "error" 字样
              return "error" not in resp["output"].lower()
      return False
  ```
- 由于响应格式未知，可允许用户通过 `--success-function` 传入自定义 Python 函数路径，或提供多种预设选项（如 `lean_web`、`lean_api` 等）。默认实现将尝试常见字段。

#### 3.5 并发执行 Lean 运行
- 使用 `concurrent.futures.ThreadPoolExecutor` 并发调用 `run_lean_code`（每个证明一个线程）。
- 设置最大并发数（如 `--lean-concurrency 5`），避免过载。
- 对每个定理的 k 个证明，分别执行并收集成功次数 c。

#### 3.6 Pass@k 计算
- 对于每个定理，有 n = k 次尝试，成功次数 c。
- 计算组合数：`from math import comb`。
- `pass_at_k = 1 - comb(n - c, k) / comb(n, k)`。当 n=k 时，公式简化为 `1 if c>0 else 0`。
- 输出结果到 JSONL：
  ```json
  {"id": "1", "formal_statement": "...", "success_count": 3, "pass_at_k": 1.0, "details": [{"proof": "...", "success": true}, ...]}
  ```
  可选择性包含具体证明内容，或仅保存成功标志。

#### 3.7 错误处理与日志
- 记录生成失败、运行失败的情况。
- 支持断点续传：若程序中断，可根据已保存的输出文件跳过已处理的数据（可选）。

**交付物**：
- Task2 完整实现，可配置 k、温度、并发数。
- 与 `lean_runner_api` 集成，包含成功判定逻辑示例。
- 对少量数据的测试输出。

---

### 第 4 阶段：集成与完善
**目标**：整体测试，性能调优，编写文档。

#### 4.1 集成测试
- 使用小型 benchmark（如 5-10 条数据）运行两个任务，验证流程。
- 测试并发稳定性，处理 API 限流（增加退避重试）。
- 根据 `run_lean_code` 实际返回格式调整成功判定函数，确保准确。

#### 4.2 性能优化
- 调整推理框架的并发数，找到最优吞吐量。
- 使用异步 + 线程池混合模式，避免阻塞事件循环。

#### 4.3 日志与监控
- 使用 `logging` 模块记录 INFO 和 DEBUG 信息，便于追踪。
- 添加进度条（如 `tqdm`）显示任务进度。

#### 4.4 文档完善
- 撰写 `README.md`，包含：
  - 环境配置（`uv sync`、`.env` 设置）。
  - 两个任务的运行命令示例。
  - 配置文件说明（prompt 模板、裁判模型配置）。
  - 扩展指南：如何添加新任务、自定义成功判定函数。
- 代码添加详细 docstring。

**交付物**：
- 完整项目代码，通过所有测试。
- 用户文档和示例命令。
- 演示运行视频或日志截图。

---

### 关键风险与应对措施
| 风险 | 应对 |
|------|------|
| `run_lean_code` 返回格式未知 | 提供可配置的成功判定函数，默认尝试常见字段；在文档中说明如何自定义 |
| API 限流或超时 | 使用退避重试（`tenacity`）和并发控制；记录失败请求便于重试 |
| 模型生成不符合格式（如多余解释） | 在 prompt 中强调输出格式，后处理提取代码块 |
| 裁判模型评分不稳定 | 增加 few-shot 示例或调整 prompt，评分后人工抽样验证 |
| 大规模测试成本高 | 支持从已有输出文件恢复，避免重复生成 |


此计划为**灵活迭代**设计，可根据实际进度调整每个阶段的深度。