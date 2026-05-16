# Knowledge Bot 扩展说明

第 15.1 扩展当前实现轻量版本，目标是增强本地可测的知识检索内核，而不是引入重型模型依赖。

## 已实现

- 查询同义词扩展：默认读取 `project/bot/synonyms.json`，并保留内置兜底词表。
- 搜索历史：每次 `/search` 追加写入 `search_history.jsonl`，记录用户、查询词、命中数和日期。
- 分页：`/search` 保存最近一次搜索会话，`/next` 返回下一页。
- LLM rerank 接口：`KnowledgeSearchEngine` 支持注入 reranker；`LLMReranker` 可显式接入现有模型客户端。

## 尚未实现

- 尚未接入本地 rerank 模型，例如 `bge-reranker-base`。
- 当前 `LocalReranker` 只是接口占位，不会下载模型，也不会占用额外磁盘空间。

## 取舍

本地 reranker 通常需要下载模型文件，`bge-reranker-base` 这类模型会占用较多磁盘空间。现阶段先用规则检索和可选 LLM rerank 满足课程练习；等后续确实需要离线重排，再把 `LocalReranker` 替换为真实模型实现。
