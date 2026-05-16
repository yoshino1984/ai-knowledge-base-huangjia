# AI 知识库实践项目：云端运行镜像

FROM python:3.12-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY project/requirements.txt ./requirements.txt
RUN pip install --prefix=/install -r requirements.txt

FROM python:3.12-slim

LABEL org.opencontainers.image.title="ai-knowledge-base"
LABEL org.opencontainers.image.description="AI knowledge base pipeline and distribution runtime"

ARG APP_UID=10001
ARG APP_GID=10001

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY --from=builder /install /usr/local
COPY project ./project
COPY .env.example ./.env.example

RUN mkdir -p /app/project/knowledge/raw \
    /app/project/knowledge/articles \
    /app/project/bot/data \
    /app/logs \
    && groupadd --gid "${APP_GID}" appuser \
    && useradd --uid "${APP_UID}" --gid appuser --no-create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app

USER appuser

HEALTHCHECK --interval=60s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import project.bot.knowledge_bot; import project.pipeline.pipeline"

CMD ["python", "-m", "project.bot.knowledge_bot"]
