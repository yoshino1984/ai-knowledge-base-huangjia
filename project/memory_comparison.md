# 有 Memory vs 无 Memory 对比实验

## 实验目标

验证 `project/AGENTS.md` 作为项目 Memory 时，AI 生成代码是否更符合项目约定。

## 实验过程

- 有 Memory：基于 `project/AGENTS.md` 生成 `project/utils/github_api.py`。
- 无 Memory：不实际移除 `AGENTS.md`，避免污染项目；用课程结论记录裸提示下常见的不稳定表现。

## 对比结果

| 维度 | 有 Memory 实际表现 | 无 Memory 常见表现 |
| --- | --- | --- |
| 命名风格 | 使用 `snake_case`，如 `get_repository_info`、`_build_headers` | 可能出现 `getRepoInfo`、`fetchGithubData` 等混合风格 |
| docstring | 模块、异常类、公开函数均有说明，公开函数使用 Google 风格参数和返回说明 | 可能只有简单注释，或者没有参数、异常说明 |
| 日志方式 | 使用 `logging` 记录 HTTP、网络、JSON 解析错误 | 可能直接 `print()` 错误信息 |
| 错误处理 | 区分 `ValueError`、`HTTPError`、`URLError`、`JSONDecodeError`，统一抛出 `GitHubApiError` | 可能只捕获通用异常，或直接让异常向外泄漏 |
| 文件位置 | 放在 `project/utils/github_api.py`，作为可复用工具函数 | 可能放在根目录，或文件位置随提示词漂移 |

## 结论

Memory 的作用不是让 AI “更聪明”，而是让 AI 在生成代码前先获得项目约束。`AGENTS.md` 明确了编码规范、目录结构、日志规则和红线，因此有 Memory 时产出更稳定、可维护，也更容易接入后续 pipeline。无 Memory 时，模型仍然可能写出能运行的代码，但风格、文件位置、错误处理和安全边界更依赖一次性提示词，长期协作成本更高。
