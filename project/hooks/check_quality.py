#!/usr/bin/env python3
"""按五个维度评估知识条目质量。

用法：
    python3 project/hooks/check_quality.py project/knowledge/articles/*.json
    python3 project/hooks/check_quality.py "project/knowledge/articles/*.json"

退出码：
    0：所有检查文件都是 A 或 B
    1：至少一个检查文件为 C、无效或不可读取
"""

from __future__ import annotations

import glob
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HOLLOW_WORDS_ZH = [
    "赋能",
    "抓手",
    "闭环",
    "打通",
    "全链路",
    "底层逻辑",
    "颗粒度",
    "对齐",
    "拉通",
    "沉淀",
    "强大的",
    "革命性的",
]

HOLLOW_WORDS_EN = [
    "groundbreaking",
    "revolutionary",
    "game-changing",
    "cutting-edge",
    "state-of-the-art",
    "leverage",
    "synergy",
    "paradigm shift",
    "disruptive",
    "next-generation",
    "world-class",
]

HOLLOW_WORDS = HOLLOW_WORDS_ZH + HOLLOW_WORDS_EN

STANDARD_TAGS = {
    "agent",
    "agent-framework",
    "agent-workflow",
    "autonomous-agent",
    "backend",
    "chatgpt",
    "coding-agent",
    "dify",
    "huggingface",
    "java",
    "llm",
    "llm-app-platform",
    "llm-ui",
    "local-llm",
    "mcp",
    "memory",
    "model-framework",
    "model-runtime",
    "ollama",
    "openclaw",
    "prompt-engineering",
    "prompt-library",
    "python",
    "rag",
    "self-hosted",
    "skills",
    "transformer",
    "workflow",
    "workflow-automation",
}

TECH_KEYWORDS = {
    "agent",
    "api",
    "embedding",
    "framework",
    "llm",
    "mcp",
    "model",
    "rag",
    "token",
    "transformer",
    "向量",
    "工作流",
    "微调",
    "推理",
    "模型",
    "框架",
    "训练",
}


@dataclass
class DimensionScore:
    """单个质量维度的评分。"""

    name: str
    score: float
    max_score: float
    details: str

    @property
    def percentage(self) -> float:
        """返回该维度的百分比得分。"""
        if self.max_score == 0:
            return 0.0
        return self.score / self.max_score * 100


@dataclass
class QualityReport:
    """单个知识条目文件的质量报告。"""

    filepath: str
    dimensions: list[DimensionScore]

    @property
    def total_score(self) -> float:
        """返回 100 分制的加权总分。"""
        return sum(dimension.score for dimension in self.dimensions)

    @property
    def grade(self) -> str:
        """返回 A、B、C 质量等级。"""
        if self.total_score >= 80:
            return "A"
        if self.total_score >= 60:
            return "B"
        return "C"


def score_summary_quality(data: dict[str, Any]) -> DimensionScore:
    """计算摘要质量得分，满分 25。"""
    max_score = 25.0
    summary = str(data.get("summary", "")).strip()
    if not summary:
        return DimensionScore("摘要质量", 0.0, max_score, "无摘要")

    length = len(summary)
    if length >= 50:
        base_score = 20.0
        detail = f"长度充足 ({length} 字)"
    elif length >= 20:
        base_score = 15.0
        detail = f"长度基本 ({length} 字)"
    else:
        base_score = 5.0
        detail = f"摘要太短 ({length} 字)"

    lower_summary = summary.lower()
    keyword_count = sum(1 for keyword in TECH_KEYWORDS if keyword.lower() in lower_summary)
    bonus = min(5.0, keyword_count * 1.0)
    if bonus:
        detail += f", 含 {keyword_count} 个技术关键词"

    return DimensionScore("摘要质量", min(max_score, base_score + bonus), max_score, detail)


def score_technical_depth(data: dict[str, Any]) -> DimensionScore:
    """根据 1-10 分文章评分计算技术深度得分，满分 25。"""
    max_score = 25.0
    article_score = _extract_article_score(data)
    if article_score is None:
        return DimensionScore("技术深度", 10.0, max_score, "缺少 score, 使用保守分")

    mapped_score = article_score / 10 * max_score
    return DimensionScore(
        "技术深度",
        round(mapped_score, 1),
        max_score,
        f"文章评分 {article_score}/10 -> {mapped_score:.1f}/{max_score}",
    )


def score_format_compliance(data: dict[str, Any]) -> DimensionScore:
    """计算格式规范得分，满分 20。"""
    max_score = 20.0
    score = 0.0
    missing: list[str] = []

    for field_name in ["id", "title", "source_url", "status"]:
        if data.get(field_name):
            score += 4.0
        else:
            missing.append(field_name)

    if data.get("collected_at") or data.get("updated_at") or data.get("organized_at"):
        score += 4.0
    else:
        missing.append("timestamp")

    detail = "格式字段完整" if not missing else "缺失: " + ", ".join(missing)
    return DimensionScore("格式规范", score, max_score, detail)


def score_tag_precision(data: dict[str, Any]) -> DimensionScore:
    """计算标签精度得分，满分 15。"""
    max_score = 15.0
    tags = data.get("tags", [])
    if not isinstance(tags, list) or not tags:
        return DimensionScore("标签精度", 0.0, max_score, "无标签")

    normalized_tags = [tag for tag in tags if isinstance(tag, str) and tag.strip()]
    valid_count = sum(1 for tag in normalized_tags if tag in STANDARD_TAGS)
    total_count = len(normalized_tags)

    if 1 <= total_count <= 3 and valid_count == total_count:
        score = 15.0
        detail = f"{total_count} 个标签, 全部在标准列表"
    elif valid_count:
        score = 10.0
        detail = f"{valid_count}/{total_count} 个标签在标准列表"
    else:
        score = 5.0
        detail = f"{total_count} 个标签均不在标准列表"

    if total_count > 5:
        penalty = min(5.0, (total_count - 5) * 1.0)
        score = max(0.0, score - penalty)
        detail += f", 标签过多扣 {penalty:.0f} 分"

    return DimensionScore("标签精度", score, max_score, detail)


def score_hollow_words(data: dict[str, Any]) -> DimensionScore:
    """计算空洞词检测得分，满分 15。"""
    max_score = 15.0
    text = " ".join(
        [
            str(data.get("title", "")),
            str(data.get("summary", "")),
            str(data.get("analysis", {}).get("innovation", "")),
        ]
    ).lower()
    found_words = [word for word in HOLLOW_WORDS if word.lower() in text]
    if not found_words:
        return DimensionScore("空洞词检测", max_score, max_score, "未发现空洞词")

    penalty = min(max_score, len(found_words) * 3.0)
    score = max(0.0, max_score - penalty)
    return DimensionScore(
        "空洞词检测",
        score,
        max_score,
        "发现空洞词: " + ", ".join(found_words),
    )


def evaluate_article(filepath: Path) -> QualityReport:
    """评估单个知识条目 JSON 文件。

    Args:
        filepath: 知识条目 JSON 文件路径。

    Returns:
        包含五个维度得分的质量报告。
    """
    data = json.loads(filepath.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("顶层 JSON 必须是 object")

    return QualityReport(
        filepath=str(filepath),
        dimensions=[
            score_summary_quality(data),
            score_technical_depth(data),
            score_format_compliance(data),
            score_tag_precision(data),
            score_hollow_words(data),
        ],
    )


def expand_inputs(arguments: list[str]) -> list[Path]:
    """将 CLI 文件和 glob 参数展开为 JSON 文件路径。"""
    paths: list[Path] = []
    for argument in arguments:
        matches = glob.glob(argument)
        if matches:
            paths.extend(Path(match) for match in matches)
        else:
            paths.append(Path(argument))

    unique_paths = sorted({path for path in paths})
    return [path for path in unique_paths if path.name != "index.json"]


def print_report(report: QualityReport) -> None:
    """打印用户可读的质量报告。"""
    print(f"\n{report.filepath}")
    print(f"总分: {report.total_score:.1f}/100  等级: {report.grade}")
    print(_progress_bar(report.total_score))

    for dimension in report.dimensions:
        print(
            f"- {dimension.name}: {dimension.score:.1f}/{dimension.max_score:.0f} "
            f"({dimension.percentage:.0f}%) - {dimension.details}"
        )


def main(argv: list[str] | None = None) -> int:
    """运行质量检查 CLI。"""
    arguments = sys.argv[1:] if argv is None else argv
    if not arguments:
        print("用法: python3 project/hooks/check_quality.py <json_file> [json_file2 ...]")
        return 1

    paths = expand_inputs(arguments)
    total_files = 0
    failed_files = 0
    grade_counts = {"A": 0, "B": 0, "C": 0}

    for path in paths:
        if not path.exists():
            failed_files += 1
            print(f"[FAIL] 文件不存在: {path}")
            continue
        if path.suffix != ".json":
            print(f"[SKIP] 非 JSON 文件: {path}")
            continue

        total_files += 1
        try:
            report = evaluate_article(path)
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            failed_files += 1
            print(f"[FAIL] {path}: {exc}")
            continue

        grade_counts[report.grade] += 1
        if report.grade == "C":
            failed_files += 1
        print_report(report)

    print(
        "\n汇总: "
        f"checked={total_files}, A={grade_counts['A']}, "
        f"B={grade_counts['B']}, C={grade_counts['C']}, failed={failed_files}"
    )
    return 1 if failed_files else 0


def _extract_article_score(data: dict[str, Any]) -> float | None:
    """从顶层字段或 analysis 嵌套字段中提取文章评分。"""
    top_level_score = data.get("score")
    if isinstance(top_level_score, (int, float)):
        return float(top_level_score)

    analysis = data.get("analysis", {})
    if isinstance(analysis, dict):
        nested_score = analysis.get("score")
        if isinstance(nested_score, (int, float)):
            return float(nested_score)

    return None


def _progress_bar(score: float, width: int = 24) -> str:
    """根据 0-100 分返回 ASCII 进度条。"""
    filled = round(score / 100 * width)
    empty = width - filled
    return "[" + "#" * filled + "-" * empty + "]"


if __name__ == "__main__":
    raise SystemExit(main())
