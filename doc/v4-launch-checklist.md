# V4 上线前 Checklist（本地版）

检查日期：2026-05-16

本文件记录第 16 节实操任务 1 的本地验收结果。当前项目目标仍是学习和本机联调；OpenClaw 云端常驻和 Docker 部署暂缓到后续云端环境再做。

## 1. API Keys 环境变量

- [x] `.env` 已加入 `.gitignore`
- [x] `.env` 未被 Git 跟踪
- [x] `.env.example` 已补齐必需变量
- [ ] 本机 `.env` 文件未创建；当前仍主要通过 shell 环境变量运行

## 2. 权限策略

- [x] `knowledge-query` Skill 显式声明 `allowed-tools: Read`
- [x] `top-rated` Skill 显式声明 `allowed-tools: Read`
- [x] Skill 只读 `project/knowledge/articles`，不写入知识库
- [x] 写入知识库仍集中在 pipeline
- [ ] OpenClaw CLI 当前依赖异常，`tools.alsoAllow` 需要云端部署时复查

## 3. 备份策略

- [x] `project/knowledge/articles` 已有知识条目
- [x] Git 远程仓库已配置：`origin`
- [x] 最新采集数据已提交到 Git
- [ ] Docker 镜像版本标签暂缓

## 4. 日志轮转

- [x] `logs/` 已在 `.gitignore` 中，不进入仓库
- [ ] Docker 日志轮转暂缓到 Docker 部署时配置

## 5. 成本预算

- [x] `CostGuard` 已实现预算和预警阈值
- [x] `RateLimiter` 已实现 `max_calls`
- [x] 本地采集成本可通过 `project/knowledge/cost-report.json` 查看

## 6. 版本固定

- [x] `project/requirements.txt` 已固定版本号
- [ ] Docker 基础镜像版本暂缓

## 7. 测试通道

- [x] 单元测试通过：`39 passed`
- [x] Pipeline 已在 2026-05-15 跑通过并入库
- [x] OpenClaw Weixin 推送链路本机验证通过
- [ ] OpenClaw Bot 云端常驻未验证

## 8. 回滚方案

- [x] Git 提供代码和数据回滚能力
- [x] 采集数据以 JSON 文件提交，可按 commit 回退
- [ ] Docker 镜像回滚暂缓

## 9. OpenClaw Bot 接管微信

- [x] 本机 OpenClaw Weixin 曾完成连接和消息接收验证
- [x] `knowledge-query` 和 `top-rated` Skill 已同步到 OpenClaw workspace
- [ ] 当前 OpenClaw CLI 报缺少 `@mariozechner/pi-ai`，本机 CLI 检查暂不通过
- [ ] 云端 OpenClaw 常驻后再复查 daemon、模型和 workspace

## 10. GitHub Actions 自动采集

- [x] `.github/workflows/daily-collect.yml` 已使用 `project/` 路径
- [x] `.github/workflows/daily-collect-v4.yml` 已从参考答案路径改为 `project/`
- [ ] GitHub Secrets 和最近运行状态需要在 GitHub UI 中确认

## 本地结论

本地学习版 V4 已具备：自动采集、知识入库、测试验证、成本记录、OpenClaw Skill 联调和微信推送验证。

暂缓项集中在生产部署：云端 OpenClaw、Docker 镜像、容器日志轮转、Docker 回滚和 GitHub Actions 线上运行状态。等 OpenClaw 迁到云端后，再按本清单复查这些项。
