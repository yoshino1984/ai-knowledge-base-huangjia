"""AI 知识库四步流水线：采集、分析、整理、保存。"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import httpx

try:
    import yaml
except ImportError:
    yaml = None

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

sys.path.insert(0, str(Path(__file__).parent))
from model_client import chat_with_retry, create_provider, estimate_cost, tracker

if load_dotenv:
    load_dotenv()

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "knowledge" / "raw"
ARTICLES_DIR = PROJECT_ROOT / "knowledge" / "articles"
RSS_CONFIG = Path(__file__).parent / "rss_sources.yaml"


def utc_now() -> str:
    """返回 UTC ISO 时间。"""

    return datetime.now(timezone.utc).isoformat()


def slugify(text: str, max_length: int = 48) -> str:
    """把标题转换为稳定文件名片段。"""

    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return (slug or "item")[:max_length].strip("-") or "item"


def clean_xml_text(text: str) -> str:
    """清理 RSS 简易解析得到的文本。"""

    text = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    return (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .strip()
    )


def collect_github(limit: int = 10) -> list[dict[str, Any]]:
    """从 GitHub Search API 采集 AI 相关热门仓库。"""

    token = os.getenv("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    query = "topic:ai topic:llm pushed:>2026-03-01"
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": min(limit, 30),
    }

    results: list[dict[str, Any]] = []
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                "https://api.github.com/search/repositories",
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        today = datetime.now().strftime("%Y-%m-%d")
        for index, repo in enumerate(data.get("items", [])[:limit], start=1):
            results.append(
                {
                    "id": f"{today}-github-{slugify(repo['full_name'])}",
                    "title": repo["full_name"],
                    "source": "github",
                    "source_url": repo["html_url"],
                    "author": repo["owner"]["login"],
                    "published_at": repo.get("pushed_at", ""),
                    "raw_description": repo.get("description", "") or "",
                    "stars": repo.get("stargazers_count", 0),
                    "language": repo.get("language") or "",
                    "topics": repo.get("topics", []),
                    "rank": index,
                    "collected_at": utc_now(),
                }
            )
    except httpx.HTTPError as exc:
        logger.error("GitHub API 调用失败: %s", exc)

    logger.info("GitHub 采集完成: %d 条", len(results))
    return results


def load_rss_sources() -> list[dict[str, Any]]:
    """读取已启用的 RSS 数据源。"""

    if not RSS_CONFIG.exists():
        logger.warning("RSS 配置文件不存在: %s", RSS_CONFIG)
        return []
    if yaml is None:
        raise RuntimeError("缺少 PyYAML，请先安装 pyyaml")

    data = yaml.safe_load(RSS_CONFIG.read_text(encoding="utf-8")) or {}
    return [source for source in data.get("sources", []) if source.get("enabled", True)]


def collect_rss(limit: int = 10) -> list[dict[str, Any]]:
    """从 RSS 源采集 AI 技术内容。"""

    sources = load_rss_sources()
    results: list[dict[str, Any]] = []

    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        for source in sources:
            if len(results) >= limit:
                break
            try:
                response = client.get(source["url"])
                response.raise_for_status()
            except httpx.HTTPError as exc:
                logger.warning("RSS 源 [%s] 获取失败: %s", source.get("name"), exc)
                continue

            item_pattern = re.compile(r"<item\b.*?</item>", re.DOTALL | re.IGNORECASE)
            for item_xml in item_pattern.findall(response.text):
                if len(results) >= limit:
                    break

                title_match = re.search(
                    r"<title[^>]*>(.*?)</title>",
                    item_xml,
                    re.DOTALL | re.IGNORECASE,
                )
                link_match = re.search(
                    r"<link[^>]*>(.*?)</link>",
                    item_xml,
                    re.DOTALL | re.IGNORECASE,
                )
                description_match = re.search(
                    r"<description[^>]*>(.*?)</description>",
                    item_xml,
                    re.DOTALL | re.IGNORECASE,
                )
                if not title_match or not link_match:
                    continue

                title = clean_xml_text(title_match.group(1))
                link = clean_xml_text(link_match.group(1))
                description = (
                    clean_xml_text(description_match.group(1))
                    if description_match
                    else ""
                )
                if not title or not link:
                    continue

                today = datetime.now().strftime("%Y-%m-%d")
                results.append(
                    {
                        "id": f"{today}-rss-{slugify(source['name'])}-{slugify(title)}",
                        "title": title,
                        "source": f"rss:{source['name']}",
                        "source_url": link,
                        "author": source.get("name", "unknown"),
                        "published_at": utc_now(),
                        "raw_description": description,
                        "category": source.get("category", "general"),
                        "collected_at": utc_now(),
                    }
                )

    logger.info("RSS 采集完成: %d 条", len(results))
    return results


def step_collect(sources: list[str], limit: int) -> list[dict[str, Any]]:
    """Step 1：按数据源采集原始数据。"""

    all_items: list[dict[str, Any]] = []
    if "github" in sources:
        all_items.extend(collect_github(limit))
    if "rss" in sources:
        all_items.extend(collect_rss(limit))

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_file = RAW_DIR / f"raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    raw_file.write_text(
        json.dumps(all_items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("采集到 %d 条原始数据，保存到 %s", len(all_items), raw_file)
    return all_items


ANALYZE_PROMPT_TEMPLATE = """请分析以下 AI 技术内容，返回 JSON 格式的分析结果。

内容信息：
- 标题：{title}
- 来源：{source}
- 描述：{description}

请只返回 JSON，不要包含 markdown 代码块：
{{
  "summary": "2-3 句话说明核心内容和价值",
  "score": 7,
  "tags": ["tag1", "tag2"],
  "audience": "beginner/intermediate/advanced"
}}
"""


def parse_analysis(content: str) -> dict[str, Any]:
    """从模型输出中解析 JSON 分析结果。"""

    cleaned = content.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def step_analyze(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Step 2：调用 LLM 对每条内容进行分析。"""

    provider = create_provider()
    analyzed: list[dict[str, Any]] = []
    total_cost = 0.0

    try:
        for index, item in enumerate(items, start=1):
            logger.info("[%d/%d] 分析: %s", index, len(items), item.get("title", ""))
            prompt = ANALYZE_PROMPT_TEMPLATE.format(
                title=item.get("title", ""),
                source=item.get("source", ""),
                description=item.get("raw_description", "无描述"),
            )
            try:
                response = chat_with_retry(
                    provider,
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一个 AI 技术分析专家，请严格返回 JSON。",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=700,
                )
                total_cost += estimate_cost(provider.model, response.usage)
                analysis = parse_analysis(response.content)
                analyzed.append(
                    {
                        **item,
                        **analysis,
                        "status": "draft",
                        "analyzed_at": utc_now(),
                    }
                )
            except (json.JSONDecodeError, KeyError, RuntimeError) as exc:
                logger.warning("分析失败，使用降级结果: %s - %s", item.get("title"), exc)
                analyzed.append(
                    {
                        **item,
                        "summary": item.get("raw_description", "")[:200],
                        "score": 5,
                        "tags": ["ai"],
                        "audience": "intermediate",
                        "status": "review_pending",
                        "analyzed_at": utc_now(),
                    }
                )
    finally:
        provider.close()

    logger.info("分析完成: %d 条，估算成本: $%.6f", len(analyzed), total_cost)
    return analyzed


def step_organize(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Step 3：去重、格式标准化。"""

    seen_urls: set[str] = set()
    if ARTICLES_DIR.exists():
        for article_file in ARTICLES_DIR.glob("*.json"):
            try:
                article = json.loads(article_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            source_url = article.get("source_url")
            if source_url:
                seen_urls.add(source_url)

    organized: list[dict[str, Any]] = []
    duplicated = 0
    for item in items:
        source_url = item.get("source_url", "")
        if source_url in seen_urls:
            duplicated += 1
            continue
        seen_urls.add(source_url)

        score = item.get("score", 5)
        if not isinstance(score, int | float):
            score = 5
        normalized_score = max(1, min(10, int(score)))
        tags = item.get("tags", [])
        audience = item.get("audience", "intermediate")
        summary = item.get("summary", "")
        technical_category = item.get("technical_category") or item.get("category")
        if not technical_category:
            technical_category = "open-source" if item.get("source") == "github" else "general"
        innovation = item.get(
            "innovation",
            "基于项目描述和来源信息进行初步判断，适合进入后续人工复核。",
        )
        difficulty = item.get("difficulty", "medium")
        difficulty_map = {
            "beginner": "low",
            "intermediate": "medium",
            "advanced": "high",
        }
        difficulty = difficulty_map.get(str(difficulty), str(difficulty))
        article = {
            "id": item.get("id", f"unknown-{slugify(item.get('title', 'item'))}"),
            "title": item.get("title", ""),
            "source": item.get("source", "unknown"),
            "source_url": source_url,
            "author": item.get("author", "unknown"),
            "published_at": item.get("published_at", ""),
            "collected_at": item.get("collected_at", ""),
            "summary": summary,
            "score": normalized_score,
            "tags": tags,
            "audience": audience,
            "analysis": {
                "summary": summary,
                "score": normalized_score,
                "tags": tags,
                "audience": audience,
                "technical_category": technical_category,
                "innovation": innovation,
                "difficulty": difficulty,
            },
            "status": item.get("status", "draft"),
            "updated_at": utc_now(),
        }
        organized.append(article)

    logger.info("去重移除 %d 条，整理后 %d 条", duplicated, len(organized))
    return organized


def step_save(items: list[dict[str, Any]], dry_run: bool = False) -> list[Path]:
    """Step 4：将文章保存为独立 JSON 文件。"""

    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    saved_files: list[Path] = []
    for item in items:
        file_path = ARTICLES_DIR / f"{item['id']}.json"
        saved_files.append(file_path)
        if dry_run:
            logger.info("[dry-run] 将保存: %s", file_path)
            continue
        file_path.write_text(
            json.dumps(item, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("已保存: %s", file_path)
    return saved_files


def run_pipeline(
    sources: list[str],
    limit: int = 20,
    dry_run: bool = False,
    steps: list[int] | None = None,
) -> dict[str, Any]:
    """运行四步流水线。"""

    run_steps = set(steps) if steps else {1, 2, 3, 4}
    started_at = datetime.now()

    raw_items: list[dict[str, Any]] = []
    analyzed_items: list[dict[str, Any]] = []
    organized_items: list[dict[str, Any]] = []
    saved_files: list[Path] = []

    if 1 in run_steps:
        raw_items = step_collect(sources, limit)
        if not raw_items:
            return {"collected": 0, "analyzed": 0, "organized": 0, "saved": 0}

    if 2 in run_steps and raw_items:
        analyzed_items = step_analyze(raw_items)

    if 3 in run_steps and analyzed_items:
        organized_items = step_organize(analyzed_items)

    if 4 in run_steps and organized_items:
        saved_files = step_save(organized_items, dry_run=dry_run)

    elapsed = (datetime.now() - started_at).total_seconds()
    stats = {
        "collected": len(raw_items),
        "analyzed": len(analyzed_items),
        "organized": len(organized_items),
        "saved": len(saved_files),
        "elapsed_seconds": round(elapsed, 1),
    }
    logger.info("流水线完成: %s", stats)
    provider_name = os.getenv("LLM_PROVIDER", "deepseek")
    tracker.report(provider=provider_name)
    return stats


def parse_sources(value: str) -> list[str]:
    """解析 CLI 传入的数据源列表。"""

    valid_sources = {"github", "rss"}
    sources = [source.strip().lower() for source in value.split(",") if source.strip()]
    invalid_sources = sorted(set(sources) - valid_sources)
    if invalid_sources:
        raise argparse.ArgumentTypeError(f"未知数据源: {', '.join(invalid_sources)}")
    return sources


def main() -> None:
    parser = argparse.ArgumentParser(description="AI 知识库自动化流水线")
    parser.add_argument("--sources", type=parse_sources, default="github,rss")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--step", type=int, action="append")
    parser.add_argument("--provider", type=str, default=None)
    args = parser.parse_args()

    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    sources = args.sources
    if isinstance(sources, str):
        sources = parse_sources(sources)
    run_pipeline(sources=sources, limit=args.limit, dry_run=args.dry_run, steps=args.step)


if __name__ == "__main__":
    main()
