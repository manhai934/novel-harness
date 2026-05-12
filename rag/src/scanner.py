"""
scanner.py — 知识源文件扫描器

职责：
- 扫描 .harness/skills/**/references/*.md, rules/*.md, projects/*.md
- 排除 planning/, legacy-skills/, agents/, memory/, cases/ 等路径
- 输出相对路径 + source_type（rule/reference/project）
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# 包含模式（转换为正则）
INCLUDE_PATTERNS = [
    ".harness/skills/**/references/*.md",
    ".harness/skills/**/rules/*.md",
    ".harness/projects/*.md",
]

# 排除模式
EXCLUDE_PATTERNS = [
    "*planning*",
    "*legacy-skills*",
    "*agents*",
    "*/current-project/*",
    "*/README*",
    "*memory*",
    "*cases*",
    ".harness/rules/*",
]

# 将 glob 模式转换为正则表达式
def _glob_to_regex(pattern):
    """将简单 glob 模式转换为正则表达式"""
    parts = pattern.split("/")
    regex_parts = []
    for part in parts:
        if part == "**":
            regex_parts.append("(.+/)?"  )
        elif part == "*":
            regex_parts.append("[^/]*")
        else:
            # 转义正则特殊字符，然后将 * 转换为 [^/]*
            escaped = re.escape(part).replace(r"\*", "[^/]*").replace(r"\?", ".")
            regex_parts.append(escaped)
    return "^" + "/".join(regex_parts) + "$"


def _path_matches(path, pattern_list):
    """检查路径是否匹配模式列表中的任一模式"""
    path_str = str(path).replace("\\", "/")
    for pattern in pattern_list:
        regex = _glob_to_regex(pattern)
        if re.match(regex, path_str):
            return True
    return False


def scan_knowledge_files():
    """扫描所有知识源文件

    Returns:
        list of {"rel_path": str, "source_type": str}
    """
    results = []

    for pattern in INCLUDE_PATTERNS:
        # 确定 source_type
        if "/rules/" in pattern:
            source_type = "rule"
        elif "/references/" in pattern:
            source_type = "reference"
        elif "/projects/" in pattern:
            source_type = "project"
        else:
            source_type = "reference"

        # 构建完整 glob 路径
        full_pattern = str(PROJECT_ROOT / pattern)
        matched_files = [p for p in Path(PROJECT_ROOT).glob(pattern) if p.is_file()]

        for file_path in matched_files:
            rel_path = str(file_path.relative_to(PROJECT_ROOT)).replace("\\", "/")

            # 检查排除
            if _path_matches(rel_path, EXCLUDE_PATTERNS):
                continue

            results.append({
                "rel_path": rel_path,
                "source_type": source_type,
            })

    # 去重
    seen = set()
    unique = []
    for r in results:
        if r["rel_path"] not in seen:
            seen.add(r["rel_path"])
            unique.append(r)

    unique.sort(key=lambda x: x["rel_path"])
    print(f"[scanner] 扫描到 {len(unique)} 个知识文件")
    return unique
