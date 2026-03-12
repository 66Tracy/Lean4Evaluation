## 优化计划
项目使用后提供一些优化建议。

### 优化点一：针对task2的优化
- 在 `run_task2.py` 的args中新增 `max_tokens` 参数，默认为32768，最终传递给clint.generate
- 在 `run_task2.py` 的args中新增 `reasoning_effort` 参数，默认为none，从['low','medium','high']中选择，这是为了适配gpt系列模型在调用时，需要传递reasoning_effort。举个例子：
```python
response = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "user", "content": prompt}
    ],
    extra_body={
        "reasoning_effort": "high"   # 可以设为 "low", "medium", "high"
    }
)
```

### 优化点二：针对底层client的优化
- 增加一个`timeout`的默认时长参数，因为在测试一些高难度的lean4证明题时，往往需要推理几万的token长度，可能回传时间会比较慢，我希望设置为120秒。


### 优化点三：针对task2测试逻辑的优化
- 学习项目`C:\work_dir\Goedel-Prover`的测试方法，请阅读代码后，对他的Evaluation过程做一个总结，包括：使用的 __prompt__，__如果增加检查防止模型作弊__，__是否有可以参考借鉴的函数__。然后我在决定是否引入哪些特性。


## 在作上述优化时，与之前的流程保持一致：
- 更新feature_list.json，更新代码后要保证测试通过。