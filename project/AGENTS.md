# AGENTS.md - AI 知识库实践项目规范

本文件是 `project/` 实践项目的 Memory。后续所有实现默认遵守这里的项目定义、目录边界、数据格式和红线。

## 项目概述

AI 知识库实践项目用于采集 AI/LLM/Agent 相关技术动态，并通过多 Agent 流程完成采集、分析、整理和后续分发。V1 先完成本地手动闭环，V2 引入自动化流水线，V3 引入多 Agent 工作流，V4 接入 Bot 和分发能力。

## 技术栈

- 语言：Python 3.12+
- AI 编排：Codex + DeepSeek/Qwen 等模型
- 工作流：LangGraph（V3 引入）
- 分发：OpenClaw / Telegram / 飞书（V4 引入）
- 数据格式：JSON
- 版本管理：Git

## 编码规范

- 遵循 PEP 8。
- Python 行宽统一为 88，兼容 `black` 默认值。
- 变量、函数、文件名使用 `snake_case`。
- 类名使用 `PascalCase`。
- 公开函数必须写类型注解。
- 公开函数使用 Google 风格 docstring。
- 核心逻辑使用 `logging`，不使用裸 `print()`。
- CLI 入口允许使用 `print()` 输出最终结果或用户可读摘要。
- 禁止 `import *`。
- 文件编码统一 UTF-8。
- 代码注释使用中文；技术术语可保留英文原文。
- 脚本应提供可验证输出，失败时返回明确错误信息。
- 不提交空泛的 `TODO` 或 `FIXME`。允许保留，但必须说明原因和后续动作。
- V1 阶段以 `py_compile` 和手动验证为主；V2 阶段正式引入 `black`、`ruff`、`pytest`。

## 项目结构

```text
project/
├── AGENTS.md
├── .opencode/
│   ├── agents/              # Agent 角色定义
│   └── skills/              # Skill 操作手册
├── specs/                   # SDD 规格文档
│   ├── issues/              # 按 Agent 拆分的任务票
│   └── schemas/             # JSON Schema
├── knowledge/
│   ├── raw/                 # 原始采集数据
│   └── articles/            # 整理后的知识条目
├── hooks/                   # 校验和质量检查脚本
├── pipeline/                # 自动化流水线
├── workflows/               # LangGraph 工作流
├── patterns/                # 多 Agent 设计模式练习
├── bot/                     # 知识库 Bot
├── distribution/            # 格式化与分发模块
└── openclaw/                # OpenClaw / 部署相关配置
```

## 采集范围

- V1 默认采集 GitHub 15 条、Hacker News 10 条、RSS 10 条。
- V1 不纳入 arXiv，后续作为扩展项。
- 只采集 AI/LLM/Agent 相关内容，泛技术内容必须与 AI 工程实践有直接关系。

## 知识条目格式

每条知识以 JSON 存储在 `knowledge/articles/` 中。

```json
{
  "id": "2026-05-10-github-example-project",
  "title": "Example Project",
  "source": "github-trending",
  "source_url": "https://github.com/example/project",
  "collected_at": "2026-05-10T10:00:00Z",
  "summary": "中文摘要，说明它是什么、为什么值得关注。",
  "analysis": {
    "technical_category": "agent-framework",
    "innovation": "说明核心创新点",
    "difficulty": "low | medium | high",
    "score": 8
  },
  "tags": ["agent", "llm", "workflow"],
  "status": "published"
}
```

必填字段：`id`、`title`、`source`、`source_url`、`collected_at`、`summary`、`analysis`、`tags`、`status`。

评分规则：

- `score` 使用 1-10 分。
- 分析维度包括：技术类别、创新点、使用难度。
- `score < 6` 的条目进入待复核队列，不直接发布。

`status` 可选值：

- `draft`
- `review_pending`
- `published`
- `archived`

## Agent 角色概览

| 角色 | 文件 | 职责 |
| --- | --- | --- |
| Collector | `.opencode/agents/collector.md` | 采集 GitHub、HN、RSS 等来源的数据 |
| Analyzer | `.opencode/agents/analyzer.md` | 生成摘要、分析维度、标签和评分 |
| Organizer | `.opencode/agents/organizer.md` | 去重、过滤、归档为标准知识条目 |

## 红线

- 不编造不存在的项目、链接、指标或摘要。
- 不泄露 API Key、Token、Cookie 或其他敏感信息。
- 不执行危险删除命令，例如 `rm -rf`。
- 不修改 `v1-skeleton/`、`v2-automation/`、`v3-multi-agent/`、`v4-production/` 等参考答案目录，除非用户明确要求。
- 不把参考答案目录中的实现计入本项目实践进度。
- 不把 `06_多Agent设计与工程化行动营/` 课程资料提交到 Git。

## 提交规则

每一节课程任务完成后进行一次 Git commit。提交信息应能对应课程阶段和任务内容。
