# 云端部署说明

本项目云端部署拆成两部分：

1. OpenClaw 作为宿主机服务运行，负责微信连接、消息发送和技能加载。
2. AI 知识库项目通过 Docker 镜像运行，负责采集、分析、整理和本地知识库检索。

这样做的原因是 OpenClaw 已经通过 systemd 管理，并且依赖宿主机上的账号、设备和本地配置。知识库项目只需要把 `project/knowledge` 作为持久化目录暴露出来，让 OpenClaw 的 Skill 能读取即可。

## 镜像构建位置

- `Dockerfile`：定义镜像如何构建。
- `.dockerignore`：定义构建镜像时哪些本地文件不进入镜像。
- `docker-compose.yml`：定义云端如何运行容器任务。

当前镜像只打包运行项目所需的 Python 依赖和 `project/` 代码，不打包课程资料、参考答案目录和本地临时数据。

## 首次部署

在云服务器上进入项目目录：

```bash
cd /opt/ai-knowledge-base-huangjia
git checkout local
git pull origin local
cp .env.example .env
```

然后编辑 `.env`，至少填入一个模型供应商的配置。例如使用 OpenAI 兼容接口：

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=你的云端模型API_KEY
OPENAI_BASE_URL=https://你的兼容接口地址/v1
OPENAI_MODEL=你的模型名
```

构建镜像：

```bash
docker compose --profile manual build
```

准备容器可写目录：

```bash
mkdir -p project/knowledge/raw project/knowledge/articles logs
chown -R 10001:10001 project/knowledge logs
```

镜像内的默认运行用户是 `appuser`，uid/gid 固定为 `10001:10001`。因为 `project/knowledge` 和 `logs` 是从宿主机挂载进容器的目录，所以云端首次运行前需要把这些目录授权给容器用户，否则会出现 `PermissionError: [Errno 13] Permission denied`。

运行容器冒烟测试：

```bash
docker compose --profile manual run --rm smoke
```

手动运行一次知识库流水线：

```bash
docker compose --profile manual run --rm pipeline
```

如果不想把运行时配置放在项目目录，可以使用外部 env 文件：

```bash
cat > /opt/ai-knowledge-base.env <<'EOF'
LLM_PROVIDER=openai
OPENAI_API_KEY=你的云端模型API_KEY
OPENAI_BASE_URL=https://你的兼容接口地址/v1
OPENAI_MODEL=你的模型名
KB_PIPELINE_SOURCES=github,rss
KB_PIPELINE_LIMIT=5
EOF

KB_ENV_FILE=/opt/ai-knowledge-base.env docker compose --profile manual run --rm pipeline
```

`KB_ENV_FILE` 默认值是 `.env`。也就是说，普通本地运行用 `.env`；云端可以把密钥放在 `/opt/ai-knowledge-base.env` 这类项目目录外的位置。

## 对接 OpenClaw

OpenClaw 继续运行在宿主机上：

```bash
systemctl --user status openclaw-gateway.service --no-pager
```

知识库数据由 Docker 容器写入宿主机项目目录：

```text
/opt/ai-knowledge-base-huangjia/project/knowledge
```

OpenClaw 的知识库查询 Skill 应该读取这个目录。云端可以把 Skill 放入 OpenClaw 工作区，或者在 Skill 中使用该目录的绝对路径。

## 真实推送

`project.distribution.publisher` 依赖宿主机的 `openclaw message send`。因此真实微信推送建议直接在宿主机执行，而不是放进 Python 容器：

```bash
cd /opt/ai-knowledge-base-huangjia
python3 -m project.distribution.publisher \
  --knowledge-dir project/knowledge/articles \
  --channel weixin \
  --target "你的微信目标ID"
```

后续如果要把发布也容器化，需要单独做一个包含 Node.js、OpenClaw CLI 和账号配置挂载的发布镜像。
