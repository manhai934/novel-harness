"""
scanner.py - 知识源文件扫描器。

扫描本地知识包、skill 规则/参考文档和项目模板，
输出相对路径与标准化 source_type。
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

INCLUDE_PATTERNS = [
    ".harness/knowledge/builtin/**/*.md",
    ".harness/knowledge/remote/**/*.md",
    ".harness/skills/**/references/*.md",
    ".harness/skills/**/rules/*.md",
    ".harness/project-templates/*.md",
]

EXCLUDE_PATTERNS = [
    "*planning*",
    "*legacy-skills*",
    ".harness/knowledge/user/*",
    "*agents*",
    "*/current-project/*",
    "*/README*",
    "*memory*",
    "*cases*",
    ".harness/rules/*",
]


def _glob_to_regex(pattern):
    """把本项目使用的简单 glob 模式转换成正则。"""
    parts = pattern.split("/")
    regex_parts = []
    for part in parts:
        if part == "**":
            regex_parts.append("(.+/)?")
        elif part == "*":
            regex_parts.append("[^/]*")
        else:
            escaped = re.escape(part).replace(r"\*", "[^/]*").replace(r"\?", ".")
            regex_parts.append(escaped)
    return "^" + "/".join(regex_parts) + "$"


def _path_matches(path, pattern_list):
    path_str = str(path).replace("\\", "/")
    for pattern in pattern_list:
        if re.match(_glob_to_regex(pattern), path_str):
            return True
    return False


def _infer_source_type(pattern):
    if "/knowledge/" in pattern:
        return "knowledge"
    if "/rules/" in pattern:
        return "rule"
    if "/references/" in pattern:
        return "reference"
    if "/project-templates/" in pattern:
        return "project"
    return "reference"


def scan_knowledge_files():
    """扫描所有可索引的知识文件。"""
    results = []

    for pattern in INCLUDE_PATTERNS:
        source_type = _infer_source_type(pattern)
        matched_files = [p for p in PROJECT_ROOT.glob(pattern) if p.is_file()]

        for file_path in matched_files:
            rel_path = str(file_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
            if _path_matches(rel_path, EXCLUDE_PATTERNS):
                continue

            results.append({
                "rel_path": rel_path,
                "source_type": source_type,
            })

    seen = set()
    unique = []
    for item in results:
        if item["rel_path"] not in seen:
            seen.add(item["rel_path"])
            unique.append(item)

    unique.sort(key=lambda x: x["rel_path"])
    print(f"[scanner] 扫描到 {len(unique)} 个知识文件")
    return unique
