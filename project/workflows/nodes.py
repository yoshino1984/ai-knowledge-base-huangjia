"""LangGraph 工作流节点：采集、分析、整理和保存。"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTICLES_DIR = PROJECT_ROOT / "knowledge" / "articles"
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))
from model_client import chat, tracker

from project.workflows.state import KBState


def parse_json_object(text: str) -> Any:
    """从模型输出中解析 JSON。"""

    cleaned = text.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def slugify(text: str, max_length: int = 48) -> str:
    """生成稳定文件名片段。"""

    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return (slug or "item")[:max_length].strip("-") or "item"


def update_cost_tracker(cost_state: dict) -> dict:
    """把全局 tracker 的当前统计写回 KBState。"""

    return {
        **cost_state,
        "prompt_tokens": tracker.total_input_tokens,
        "completion_tokens": tracker.total_output_tokens,
        "total_tokens": tracker.total_input_tokens + tracker.total_output_tokens,
        "call_count": tracker.call_count,
        "total_cost_yuan": tracker.estimated_cost(os.getenv("LLM_PROVIDER", "deepseek")),
    }


def collect_node(state: KBState) -> dict:
    """采集节点：调用 GitHub Search API 获取 AI 相关仓库。"""

    print("[Collector] 开始采集")
    plan = state.get("plan", {}) or {}
    per_source_limit = int(plan.get("per_source_limit", 10))
    query = urllib.parse.quote("topic:ai topic:llm")
    url = (
        "https://api.github.com/search/repositories"
        f"?q={query}&sort=stars&order=desc&per_page={per_source_limit}"
    )
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.getenv("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    sources: list[dict] = []
    try:
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
        for repo in data.get("items", []):
            sources.append(
                {
                    "source": "github",
                    "title": repo["full_name"],
                    "url": repo["html_url"],
                    "description": repo.get("description") or "",
                    "stars": repo.get("stargazers_count", 0),
                    "language": repo.get("language") or "",
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                }
            )
    except Exception as exc:
        sources.append(
            {
                "source": "github",
                "title": "[ERROR]",
                "url": "",
                "description": str(exc),
                "collected_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    print(f"[Collector] 采集到 {len(sources)} 条原始数据")
    return {"sources": sources}


def analyze_node(state: KBState) -> dict:
    """分析节点：用 LLM 对采集数据生成结构化报告。"""

    print("[Analyzer] 开始分析")
    analyses: list[dict] = []
    for item in state["sources"]:
        if item.get("title", "").startswith("[ERROR]"):
            continue
        prompt = f"""请分析以下 AI 技术项目，返回严格 JSON：
项目名：{item.get("title", "")}
描述：{item.get("description", "")}

返回格式：
{{
  "summary": "120字以内中文摘要",
  "tags": ["tag1", "tag2"],
  "relevance_score": 0.8,
  "category": "技术分类",
  "key_insight": "一句话洞察"
}}"""
        try:
            result = chat(prompt, system="你是 AI 技术分析师，只返回 JSON。")
            analysis = parse_json_object(str(result["content"]))
            analyses.append({**item, **analysis})
        except Exception as exc:
            analyses.append(
                {
                    **item,
                    "summary": f"分析失败: {exc}",
                    "tags": [],
                    "relevance_score": 0.0,
                    "category": "unknown",
                    "key_insight": "",
                }
            )

    print(f"[Analyzer] 完成 {len(analyses)} 条分析")
    return {
        "analyses": analyses,
        "cost_tracker": update_cost_tracker(state.get("cost_tracker", {})),
    }


def organize_node(state: KBState) -> dict:
    """整理节点：过滤、去重，并转换为可保存的知识条目。"""

    print("[Organizer] 开始整理")
    plan = state.get("plan", {}) or {}
    relevance_threshold = float(plan.get("relevance_threshold", 0.5))
    analyses = state["analyses"]
    iteration = state.get("iteration", 0)
    qualified = [
        item
        for item in analyses
        if float(item.get("relevance_score", 0)) >= relevance_threshold
    ]

    seen_urls: set[str] = set()
    unique: list[dict] = []
    for item in qualified:
        url = item.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(item)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    articles: list[dict] = []
    for index, item in enumerate(unique, start=1):
        score = max(1, min(10, int(float(item.get("relevance_score", 0.7)) * 10)))
        tags = item.get("tags", [])
        summary = item.get("summary", "")
        articles.append(
            {
                "id": f"{today}-workflow-{slugify(item.get('title', str(index)))}",
                "title": item.get("title", ""),
                "source": item.get("source", "github"),
                "source_url": item.get("url", ""),
                "summary": summary,
                "score": score,
                "tags": tags,
                "status": "draft",
                "analysis": {
                    "summary": summary,
                    "score": score,
                    "tags": tags,
                    "audience": "intermediate",
                    "technical_category": item.get("category", "general"),
                    "innovation": item.get("key_insight", "待进一步人工复核。"),
                    "difficulty": "medium",
                },
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    print(f"[Organizer] 整理出 {len(articles)} 条知识条目 (迭代 {iteration})")
    return {
        "articles": articles,
        "cost_tracker": update_cost_tracker(state.get("cost_tracker", {})),
    }


def review_node(state: KBState) -> dict:
    """审核节点：用 LLM 做四维度质量审核。"""

    print("[Reviewer] 开始审核")
    articles = state.get("articles", [])
    iteration = state.get("iteration", 0)
    if not articles:
        return {
            "review_passed": True,
            "review_feedback": "没有条目需要审核",
            "iteration": iteration + 1,
        }

    prompt = f"""你是知识库质量审核员。请审核以下条目：
{json.dumps(articles[:3], ensure_ascii=False, indent=2)}

评分维度（1-5分）：摘要质量、标签准确性、分类合理性、整体一致性。
overall_score >= 3.5 即通过。当前是第 {iteration + 1} 次审核。

返回 JSON：
{{"passed": true, "overall_score": 4.0, "feedback": "具体建议", "scores": {{}}}}"""
    try:
        result = chat(prompt, system="你是严格但公正的知识库审核员，只返回 JSON。")
        review = parse_json_object(str(result["content"]))
        passed = bool(review.get("passed", False))
        score = float(review.get("overall_score", 0))
        feedback = str(review.get("feedback", ""))
        if score >= 3.5:
            passed = True
        if iteration >= 2:
            passed = True
            feedback += "\n[系统] 已达最大审核次数，强制通过。"
    except Exception as exc:
        passed = True
        score = 0
        feedback = f"审核失败: {exc}，自动通过"

    print(f"[Reviewer] 得分: {score}, 通过: {passed} (迭代 {iteration + 1}/3)")
    return {
        "review_passed": passed,
        "review_feedback": feedback,
        "iteration": iteration + 1,
        "cost_tracker": update_cost_tracker(state.get("cost_tracker", {})),
    }


def review_node_test(state: KBState) -> dict:
    """审核节点测试版：持续失败，用于验证 revise 和 human_flag 路由。"""

    iteration = state.get("iteration", 0)
    plan = state.get("plan", {}) or {}
    max_iterations = int(plan.get("max_iterations", 3))
    feedbacks = [
        "摘要过于简短，需要补充技术细节和实际应用场景。",
        "标签不够精确，建议增加具体框架名称作为标签。",
        "质量已达标，准予通过。",
    ]
    if iteration >= max_iterations:
        passed = True
        feedback = feedbacks[2]
    else:
        passed = False
        feedback = feedbacks[min(iteration, len(feedbacks) - 1)]

    print(f"[Reviewer-Test] 迭代 {iteration + 1}/{max_iterations}, passed={passed}")
    print(f"  反馈: {feedback}")
    return {
        "review_passed": passed,
        "review_feedback": feedback,
        "iteration": iteration + 1,
    }


def save_node(state: KBState) -> dict:
    """保存节点：写入 JSON 文件并更新 index。"""

    print("[Saver] 开始保存")
    articles = state.get("articles", [])
    if not articles:
        print("[Saver] 没有条目需要保存")
        return {}

    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    for article in articles:
        file_path = ARTICLES_DIR / f"{article['id']}.json"
        file_path.write_text(
            json.dumps(article, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    index_path = ARTICLES_DIR / "index.json"
    if index_path.exists():
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            index = []
    else:
        index = []
    existing_ids = {entry.get("id") for entry in index if isinstance(entry, dict)}
    for article in articles:
        if article["id"] not in existing_ids:
            index.append(
                {
                    "id": article["id"],
                    "title": article.get("title", ""),
                    "category": article.get("analysis", {}).get("technical_category", ""),
                }
            )
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Saver] 保存 {len(articles)} 篇文章")
    return {}
