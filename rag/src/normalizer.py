"""
normalizer.py - Markdown 文档标准化器。

读取 Markdown 源文件，并根据路径和内容线索生成 RAG 索引需要的
document 元数据结构。
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

SOURCE_TO_CATEGORY = {
    "human-linguistics": {
        "rules": "common.humanization",
        "references": "common.language",
    },
    "plot-review": {
        "rules": "common.outline_review",
        "references": "common.consistency",
    },
    "plot-ideation": {
        "rules": "common.ideation",
        "references": "common.ideation",
    },
    "rhythm-review": {
        "rules": "common.rhythm",
        "references": "common.rhythm",
    },
    "game-datafied": {
        "rules": "common.outline",
        "references": "common.outline",
    },
    "project-templates": {
        "project": "common.project",
    },
    "knowledge": {
        "deslop": "common.humanization",
        "topics": "common.outline",
        "writing": "common.ideation",
        "market": "common.project",
        "cases": "common.consistency",
    },
}

FILE_CATEGORY_OVERRIDES = {
    "章节写前准备清单": "common.prewrite",
    "大纲质量评估清单": "common.outline_review",
    "状态一致性补充清单": "common.consistency",
    "去AI味最小修改指南": "common.humanization",
    "句式节奏档案": "common.rhythm",
    "阅读体验与章节润色检查": "common.rhythm",
}


def _extract_skill_name(rel_path):
    parts = rel_path.replace("\\", "/").split("/")
    try:
        skills_idx = parts.index("skills")
        if skills_idx + 1 < len(parts):
            return parts[skills_idx + 1]
    except ValueError:
        pass
    return None


def _infer_stage(rel_path, content):
    stages = []
    lower = content.lower()
    path_lower = rel_path.lower()

    if any(k in path_lower for k in ("ideation", "灵感", "构思")):
        stages.append("ideation")
    if any(k in path_lower for k in ("outline", "大纲", "结构")):
        stages.append("outline")
    if any(k in path_lower for k in ("prewrite", "写前", "准备")):
        stages.append("prewrite")
    if any(k in path_lower for k in ("rhythm", "节奏", "润色", "阅读体验")):
        stages.extend(["drafting", "revision"])
    if any(k in path_lower for k in ("human", "去ai", "修改", "自然")):
        stages.append("revision")
    if any(k in path_lower for k in ("review", "审查", "评估", "审稿")):
        stages.append("review")

    if any(k in lower for k in ("大纲", "骨架", "结构评估")):
        if "outline" not in stages:
            stages.append("outline")
        if "review" not in stages:
            stages.append("review")
    if any(k in lower for k in ("写前", "准备", "开始写")):
        if "prewrite" not in stages:
            stages.append("prewrite")
    if any(k in lower for k in ("修改", "润色", "去ai", "总结腔")):
        if "revision" not in stages:
            stages.append("revision")

    if not stages:
        stages.extend(["drafting", "review"])

    return list(dict.fromkeys(stages))


def _infer_doc_id(rel_path):
    path = rel_path.replace("\\", "/")
    file_name = Path(rel_path).stem

    skill_name = _extract_skill_name(rel_path)
    if skill_name:
        return f"{skill_name}.{file_name}"

    if path.startswith(".harness/knowledge/"):
        parts = path.split("/")
        if len(parts) >= 5:
            return f"knowledge.{parts[3]}.{file_name}"
        return f"knowledge.{file_name}"

    if path.startswith(".harness/project-templates/"):
        return f"project.{file_name}"

    return file_name


def _infer_category(rel_path):
    path = rel_path.replace("\\", "/")
    file_name = Path(rel_path).stem

    if file_name in FILE_CATEGORY_OVERRIDES:
        return FILE_CATEGORY_OVERRIDES[file_name]

    if path.startswith(".harness/project-templates/"):
        return "common.project"

    if path.startswith(".harness/knowledge/"):
        parts = path.split("/")
        if len(parts) >= 5:
            section = parts[3]
            return SOURCE_TO_CATEGORY["knowledge"].get(section, "common")
        return "common"

    skill_name = _extract_skill_name(rel_path)
    if not skill_name:
        return "common"

    is_rule = "/rules/" in path
    is_ref = "/references/" in path

    mapping = SOURCE_TO_CATEGORY.get(skill_name)
    if mapping:
        if is_rule and "rules" in mapping:
            return mapping["rules"]
        if is_ref and "references" in mapping:
            return mapping["references"]

    return "common"


def _infer_scope(rel_path):
    path = rel_path.replace("\\", "/")
    if path.startswith(".harness/project-templates/"):
        return "project"
    return "common"


def _infer_tags(rel_path, content):
    tags = []
    path = rel_path.replace("\\", "/")
    file_name = Path(rel_path).stem

    tags.append(file_name)

    skill_name = _extract_skill_name(rel_path)
    if skill_name:
        tags.append(skill_name)

    if path.startswith(".harness/knowledge/"):
        parts = path.split("/")
        tags.extend([p for p in parts[2:-1] if p not in ("included", "remote")])

    title_match = re.search(r"^#\s+(.+)", content, re.MULTILINE)
    if title_match:
        tags.append(title_match.group(1).strip())

    return tags


def _infer_priority(rel_path):
    path = rel_path.replace("\\", "/")
    if "/rules/" in path:
        return 1
    if path.startswith(".harness/knowledge/"):
        return 2
    if "/references/" in path:
        return 2
    if path.startswith(".harness/project-templates/"):
        return 3
    return 4


def normalize_document(rel_path, source_type):
    """把单个源文件标准化为 document 字典。"""
    abs_path = PROJECT_ROOT / rel_path

    try:
        content = abs_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"[normalizer] 无法读取文件: {rel_path} ({exc})")
        return None

    title_match = re.search(r"^#\s+(.+)", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else Path(rel_path).stem

    return {
        "doc_id": _infer_doc_id(rel_path),
        "title": title,
        "source_path": rel_path.replace("\\", "/"),
        "source_type": source_type,
        "category": _infer_category(rel_path),
        "stage": _infer_stage(rel_path, content),
        "scope": _infer_scope(rel_path),
        "tags": _infer_tags(rel_path, content),
        "priority": _infer_priority(rel_path),
        "status": "active",
        "_raw_content": content,
    }
