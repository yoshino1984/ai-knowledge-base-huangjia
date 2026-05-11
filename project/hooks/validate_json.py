#!/usr/bin/env python3
"""Validate knowledge article JSON files.

Usage:
    python3 project/hooks/validate_json.py project/knowledge/articles/*.json
    python3 project/hooks/validate_json.py "project/knowledge/articles/*.json"

Exit codes:
    0: all checked files passed validation
    1: at least one checked file failed validation
"""

from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path
from typing import Any

REQUIRED_FIELDS: dict[str, type] = {
    "id": str,
    "title": str,
    "source": str,
    "source_url": str,
    "summary": str,
    "analysis": dict,
    "tags": list,
    "status": str,
}

PROJECT_ID_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z][a-z0-9-]*-[a-z0-9-]+$")
COURSE_ID_PATTERN = re.compile(r"^[a-z][\w:-]+-\d{8}-\d{3}$")
URL_PATTERN = re.compile(r"^https?://\S+$")

VALID_STATUSES = {"draft", "review", "review_pending", "published", "archived"}
VALID_DIFFICULTIES = {"low", "medium", "high"}
VALID_AUDIENCES = {"beginner", "intermediate", "advanced"}
SUMMARY_MIN_LENGTH = 20
SCORE_MIN = 1
SCORE_MAX = 10


def validate_article(data: dict[str, Any]) -> list[str]:
    """Validate a single knowledge article object.

    Args:
        data: Parsed JSON object for one knowledge article.

    Returns:
        A list of validation errors. An empty list means the article is valid.
    """
    errors: list[str] = []

    for field_name, field_type in REQUIRED_FIELDS.items():
        if field_name not in data:
            errors.append(f"缺少必填字段: {field_name}")
            continue
        if not isinstance(data[field_name], field_type):
            actual_type = type(data[field_name]).__name__
            errors.append(
                f"字段类型错误: {field_name} 应为 {field_type.__name__}, "
                f"实际为 {actual_type}"
            )

    if errors:
        return errors

    article_id = data["id"]
    if not _is_valid_id(article_id):
        errors.append(
            f"ID 格式错误: {article_id!r}, 应为 "
            "{YYYY-MM-DD}-{source}-{slug} 或 {source}-{YYYYMMDD}-{NNN}"
        )

    if not data["title"].strip():
        errors.append("标题不能为空")

    if not URL_PATTERN.match(data["source_url"]):
        errors.append(f"URL 格式错误: {data['source_url']!r}")

    if len(data["summary"].strip()) < SUMMARY_MIN_LENGTH:
        errors.append(
            f"摘要太短: {len(data['summary'].strip())} 字, "
            f"至少需要 {SUMMARY_MIN_LENGTH} 字"
        )

    tags = data["tags"]
    if not tags:
        errors.append("至少需要 1 个标签")
    for tag in tags:
        if not isinstance(tag, str) or not tag.strip():
            errors.append(f"标签格式错误: {tag!r}")

    status = data["status"]
    if status not in VALID_STATUSES:
        errors.append(
            f"无效的 status: {status!r}, "
            f"允许值: {', '.join(sorted(VALID_STATUSES))}"
        )

    errors.extend(_validate_analysis(data["analysis"]))
    errors.extend(_validate_optional_fields(data))

    return errors


def validate_file(path: Path) -> list[str]:
    """Validate a JSON file as one knowledge article.

    Args:
        path: Path to the JSON file.

    Returns:
        A list of validation errors. An empty list means the file is valid.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"JSON 解析失败: {exc}"]
    except OSError as exc:
        return [f"文件读取失败: {exc}"]

    if not isinstance(data, dict):
        return ["顶层 JSON 必须是 object"]

    return validate_article(data)


def expand_inputs(arguments: list[str]) -> list[Path]:
    """Expand CLI file and glob arguments into JSON file paths.

    Args:
        arguments: Command-line file or glob arguments.

    Returns:
        Sorted unique JSON file paths.
    """
    paths: list[Path] = []
    for argument in arguments:
        matches = glob.glob(argument)
        if matches:
            paths.extend(Path(match) for match in matches)
        else:
            paths.append(Path(argument))

    unique_paths = sorted({path for path in paths})
    return [path for path in unique_paths if path.name != "index.json"]


def main(argv: list[str] | None = None) -> int:
    """Run the JSON validator CLI.

    Args:
        argv: Optional argument list. Defaults to `sys.argv[1:]`.

    Returns:
        Process exit code.
    """
    arguments = sys.argv[1:] if argv is None else argv
    if not arguments:
        print("用法: python3 project/hooks/validate_json.py <json_file> [json_file2 ...]")
        return 1

    paths = expand_inputs(arguments)
    total_files = 0
    failed_files = 0
    skipped_files = 0

    for path in paths:
        if not path.exists():
            print(f"[SKIP] 文件不存在: {path}")
            skipped_files += 1
            continue
        if path.suffix != ".json":
            print(f"[SKIP] 非 JSON 文件: {path}")
            skipped_files += 1
            continue

        total_files += 1
        errors = validate_file(path)
        if errors:
            failed_files += 1
            print(f"[FAIL] {path}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"[ OK ] {path}")

    passed_files = total_files - failed_files
    print(
        "\n汇总: "
        f"checked={total_files}, passed={passed_files}, "
        f"failed={failed_files}, skipped={skipped_files}"
    )

    return 1 if failed_files else 0


def _is_valid_id(article_id: str) -> bool:
    """Return whether an article id matches a supported format."""
    return bool(PROJECT_ID_PATTERN.match(article_id) or COURSE_ID_PATTERN.match(article_id))


def _validate_analysis(analysis: dict[str, Any]) -> list[str]:
    """Validate the nested analysis object."""
    errors: list[str] = []
    required_analysis_fields: dict[str, type] = {
        "technical_category": str,
        "innovation": str,
        "difficulty": str,
        "score": int,
    }

    for field_name, field_type in required_analysis_fields.items():
        if field_name not in analysis:
            errors.append(f"analysis 缺少必填字段: {field_name}")
            continue
        if not isinstance(analysis[field_name], field_type):
            actual_type = type(analysis[field_name]).__name__
            errors.append(
                f"analysis 字段类型错误: {field_name} 应为 "
                f"{field_type.__name__}, 实际为 {actual_type}"
            )

    if errors:
        return errors

    difficulty = analysis["difficulty"]
    if difficulty not in VALID_DIFFICULTIES:
        errors.append(
            f"无效的 analysis.difficulty: {difficulty!r}, "
            f"允许值: {', '.join(sorted(VALID_DIFFICULTIES))}"
        )

    score = analysis["score"]
    if not (SCORE_MIN <= score <= SCORE_MAX):
        errors.append(f"analysis.score 超出范围: {score}, 允许范围: {SCORE_MIN}-{SCORE_MAX}")

    return errors


def _validate_optional_fields(data: dict[str, Any]) -> list[str]:
    """Validate optional article fields when they are present."""
    errors: list[str] = []

    if "score" in data:
        score = data["score"]
        if not isinstance(score, (int, float)):
            errors.append(f"score 应为数字, 实际为 {type(score).__name__}")
        elif not (SCORE_MIN <= score <= SCORE_MAX):
            errors.append(f"score 超出范围: {score}, 允许范围: {SCORE_MIN}-{SCORE_MAX}")

    if "audience" in data:
        audience = data["audience"]
        if audience not in VALID_AUDIENCES:
            errors.append(
                f"无效的 audience: {audience!r}, "
                f"允许值: {', '.join(sorted(VALID_AUDIENCES))}"
            )

    return errors


if __name__ == "__main__":
    raise SystemExit(main())
