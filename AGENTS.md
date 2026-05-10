# AGENTS.md - 实践项目协作规范

本仓库用于跟随「多 Agent 设计与工程化行动营」完成自己的实践版本。

## 目录边界

- `project/`：我们的实践主目录。后续功能实现、脚本、配置、测试默认都写在这里。
- `doc/`：我们的实践笔记、待办清单、复盘和设计记录默认写在这里。
- `06_多Agent设计与工程化行动营/`：课程资料目录，只读参考，不提交。
- `v1-skeleton/`、`v2-automation/`、`v3-multi-agent/`、`v4-production/`：参考答案目录，只读参考，默认不修改。

## 工作规则

1. 默认只修改 `project/` 和 `doc/`。
2. 如需查看 `v1-skeleton/` 到 `v4-production/`，先把它们当作参考答案阅读，不直接照搬到实践目录。
3. 如确实需要修改参考答案目录，必须先明确说明原因，并等用户确认。
4. 课程资料目录 `06_多Agent设计与工程化行动营/` 已加入 `.gitignore`，只用于本地学习和任务提取。
5. 每完成一个阶段性实践成果，建议单独提交一次 Git commit，提交信息对应课程阶段，例如 `feat: complete v2 json validation hooks`。
6. 实践进度从零开始计算。`v1-skeleton/` 到 `v4-production/` 中已有的实现、数据和提交都视为参考答案，不计入我们的完成进度。
7. 只有在 `project/` 中实现、并在 `doc/` 中记录的成果，才算我们的实践成果。

## 实践路线

- V1：补齐 specs，完成 Memory、Sub-Agents、Skills 和第一批知识条目。
- V2：实现自动化工程，包括 JSON 校验、质量评分、Pipeline、定时任务、成本统计。
- V3：实现多 Agent 协作架构，包括 Router、Supervisor、LangGraph 工作流、Reviewer、Planner、CostGuard、Eval、Security。
- V4：实现上线能力，包括 Bot、formatter、publisher、knowledge_bot、自定义 Skill、Checklist 和部署。
