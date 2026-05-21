"""
chunker.py — Markdown 文档分块器

职责：
- 按 heading 级别（#, ##, ###）做语义边界分割
- 检测 chunk_type（definition/rule/checklist/procedure/anti_pattern/template/example/navigation）
- 控制块长度在 300-900 字之间
- 超出 900 字的块在子项处分割
- 输出统一的 chunk 结构
"""

import re
from pathlib import Path


def _detect_chunk_type(text, heading_level):
    """检测块类型"""
    lower = text.lower()

    # 导航/索引
    if heading_level >= 2 and (
        re.search(r"^[\s]*(?:目录|index|导航|概览|总览|一览)", text, re.MULTILINE)
        or re.search(r"(?:^|\n)(?:[\d.]+\s*[-—]\s*.+){5,}", text)
        and len(text) < 300
    ):
        return "navigation"

    # 模板
    if re.search(r"(?:模板|示例|例子|范例|示例：)", lower) and re.search(
        r"\{|【|\[.*\]", text
    ):
        return "template"

    # 规则
    if re.search(r"(?:^|\n)\s*(?:规则|原则|规范|必须|不要|禁止|避免|可以|建议)", lower):
        return "rule"

    # 步骤/流程
    if re.search(r"(?:^|\n)\s*(?:步骤|流程|方法|做法|如何|操作|方式|过程)", lower) or (
        re.search(r"(?:首先|第一步|第二步|最后|然后)", lower)
        and re.search(r"\d+[.、]", text)
    ):
        return "procedure"

    # 检查清单
    if re.search(r"(?:^|\n)\s*(?:清单|检查|检查点|核对|审核|验收)", lower) or re.search(
        r"(?:^|\n)\s*[-*]\s*\[[\sx]\]", text
    ):
        return "checklist"

    # 反模式
    if re.search(r"(?:反模式|禁忌|陷阱|误区|避免|不要)", lower) and re.search(
        r"(?:^|\n)\s*(?:不要|避免|禁忌|陷阱)", lower
    ):
        return "anti_pattern"

    # 示例
    if re.search(r"(?:^|\n)\s*(?:举例|示例|例如|比如|譬如)", lower):
        return "example"

    return "definition"


def _split_long_section(text, max_chars=900):
    """将过长的文本在子项处分割

    参数：
        text: 段文本
        max_chars: 最大字符数

    返回：
        字符串列表
    """
    if len(text) <= max_chars:
        return [text]

    chunks = []
    # 尝试在 markdown 列表项、空行或句号处分割
    lines = text.split("\n")
    current = []

    for line in lines:
        current_len = sum(len(l) for l in current) + len(current) - 1  # 换行符数量

        if current_len + len(line) > max_chars and current:
            # 在列表项处分割
            content = "\n".join(current)
            if content.strip():
                chunks.append(content.strip())

            # 保留列表项前缀（如果是列表继续项）
            stripped = line.lstrip()
            if stripped.startswith("-") or stripped.startswith("*") or re.match(r"^\d+[.、]", stripped):
                current = [line]
            else:
                current = [line]
        else:
            current.append(line)

    if current:
        content = "\n".join(current)
        if content.strip():
            chunks.append(content.strip())

    return chunks if chunks else [text]


def _clean_text(text):
    """清理文本，去掉多余空行"""
    # 去掉开头和结尾的空白
    text = text.strip()
    # 将连续 3 个以上空行压缩为 2 个
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text


def chunk_markdown(document):
    """将 document 按 heading 分割为 chunks

    参数：
        document: normalize_document 返回的字典（含 _raw_content）

    返回：
        chunk 字典列表
    """
    content = document.get("_raw_content", "")
    if not content:
        return []

    chunks = []
    lines = content.split("\n")
    current_section_lines = []
    current_heading = document["title"]
    current_level = 1

    def flush_section():
        """把当前累积的 section 输出为一个或多个 chunk"""
        nonlocal current_section_lines
        if not current_section_lines:
            return

        text = "\n".join(current_section_lines).strip()
        if not text:
            return

        chunk_type = _detect_chunk_type(text, current_level)

        # 如果文本过长，在子项处分割
        sub_sections = _split_long_section(text, max_chars=900)

        for i, sub_text in enumerate(sub_sections):
            sub_text = _clean_text(sub_text)
            if len(sub_text) < 20:
                continue

            chunk_id = f"{document['doc_id']}.sec{len(chunks) + 1}"
            if i > 0:
                chunk_id += f".{i + 1}"

            chunks.append({
                "chunk_id": chunk_id,
                "doc_id": document["doc_id"],
                "title": current_heading,
                "chunk_type": chunk_type,
                "text": sub_text,
                "category": document["category"],
                "stage": document["stage"],
                "scope": document["scope"],
                "tags": document["tags"],
                "priority": document["priority"],
                "source_type": document["source_type"],
                "source_path": document["source_path"],
                "heading_level": current_level,
            })

        current_section_lines = []

    for line in lines:
        heading_match = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading_match:
            # flush 上一段
            flush_section()

            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()

            # 跳过标题行自身（它已经被识别为分割标记）
            current_level = level
            current_heading = heading_text
            # 不把标题行本身加入内容
            continue

        current_section_lines.append(line)

    # flush 最后一段
    flush_section()

    # 如果没分出 chunk（可能整个文档没有 heading），则整个作为一块
    if not chunks and content.strip():
        text = _clean_text(content)
        if len(text) >= 20:
            chunks.append({
                "chunk_id": f"{document['doc_id']}.sec1",
                "doc_id": document["doc_id"],
                "title": document["title"],
                "chunk_type": _detect_chunk_type(text, 1),
                "text": text,
                "category": document["category"],
                "stage": document["stage"],
                "scope": document["scope"],
                "tags": document["tags"],
                "priority": document["priority"],
                "source_type": document["source_type"],
                "source_path": document["source_path"],
                "heading_level": 1,
            })

    return chunks
