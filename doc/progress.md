# 多 Agent 行动营实践进度

本清单只统计我们在 `project/` 中重新实现的内容。参考答案目录 `v1-skeleton/`、`v2-automation/`、`v3-multi-agent/`、`v4-production/` 中的现有实现不计入进度。

## 当前状态

- 当前进度：从零开始
- 实践目录：`project/`
- 记录目录：`doc/`
- 参考答案：只读参考

## V1：AI 编程核心方法论

- [ ] 创建项目基础目录结构
- [ ] 编写 `project/AGENTS.md`
- [ ] 编写 `project/specs/project-vision.md`
- [ ] 编写 `project/specs/coding-standards.md`
- [ ] 编写 `project/specs/agents-prd.md`
- [ ] 编写 `project/specs/issues/01-collector.md`
- [ ] 编写 `project/specs/issues/02-analyzer.md`
- [ ] 编写 `project/specs/issues/03-organizer.md`
- [ ] 编写 `project/.opencode/agents/collector.md`
- [ ] 编写 `project/.opencode/agents/analyzer.md`
- [ ] 编写 `project/.opencode/agents/organizer.md`
- [ ] 编写 `project/.opencode/skills/github-trending/SKILL.md`
- [ ] 编写 `project/.opencode/skills/tech-summary/SKILL.md`
- [ ] 跑通采集、分析、整理流程
- [ ] 生成第一批 `project/knowledge/raw/*.json`
- [ ] 生成第一批 `project/knowledge/articles/*.json`
- [ ] 记录 V1 复盘

## V2：自动化工程

- [ ] 编写 `project/hooks/validate_json.py`
- [ ] 编写 `project/hooks/check_quality.py`
- [ ] 编写 `project/pipeline/model_client.py`
- [ ] 编写 `project/pipeline/pipeline.py`
- [ ] 添加 RSS 数据源配置
- [ ] 配置 GitHub Actions 或本地定时任务
- [ ] 加入 Token 消耗统计
- [ ] 实现模型路由策略
- [ ] 提交 V2 完整项目

## V3：多 Agent 协作架构

- [ ] 实现 Router 路由模式
- [ ] 实现 Supervisor 监督模式
- [ ] 定义 `KBState`
- [ ] 搭建 LangGraph 工作流
- [ ] 添加审核循环
- [ ] 实现 Reviewer Agent
- [ ] 实现 Planner Agent
- [ ] 实现 CostGuard
- [ ] 编写 Eval 评估测试
- [ ] 编写 Security 安全模块
- [ ] 接入工作流并提交 V3

## V4：全平台上线

- [ ] 连接 Bot 入口
- [ ] 让 Bot 读取知识库
- [ ] 实现 formatter
- [ ] 实现 publisher
- [ ] 实现 knowledge_bot
- [ ] 编写自定义 Skill
- [ ] 完成上线前 Checklist
- [ ] 可选 Docker 部署
- [ ] 提交毕业项目
