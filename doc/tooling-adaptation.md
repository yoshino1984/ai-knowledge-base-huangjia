# 课程工具替换约定

课程资料默认使用 OpenCode 演示。我们的实践版本默认使用 Codex 完成同类任务。

## 为什么可以替换

第 1 节的核心不是 OpenCode 本身，而是验证 AI 编程工具从“裸模型调用”升级到“有状态编排”：

- 能读取项目文件
- 能搜索目录和内容
- 能执行命令
- 能创建和修改文件
- 能根据项目规范持续协作

Codex 当前已经具备这些能力，因此可以作为课程中的 OpenCode 等价执行器。

## 替换规则

| 课程说法 | 我们的实践说法 |
| --- | --- |
| 安装 OpenCode | 使用 Codex 作为 AI 编程编排器 |
| 启动 OpenCode | 在当前 Codex 工作区中执行任务 |
| OpenCode 自动读取 AGENTS.md | Codex 遵守根目录 `AGENTS.md` 和项目内规范 |
| 用 `@collector` 触发 Agent | 在 Codex 中按 `collector` 角色定义委派或执行 |
| OpenCode Skill | 在 `project/.opencode/skills/` 中保留 Skill 规范，Codex 按规范执行 |

## 第 1 节实操任务 1 的完成标准

- Node.js 已可用：`node --version`
- npm 已可用：`npm --version`
- Codex 工作区已可读写：已能读取课程资料、更新 `doc/`、创建 `project/`
- 模型对话已可用：当前会话可正常协作
- 国产模型 API Key 不作为硬性前置；需要做裸 API 对比实验时，再使用已有的 `DEEPSEEK_API_KEY`

## 记录

本任务按 Codex 版本完成，不要求后续必须使用 OpenCode。
