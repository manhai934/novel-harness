/**
 * chunker.js — 语义切块器
 *
 * 职责：
 * - 基于标题层级（Markdown headings）切分 chunk
 * - 列表、表格、规则块尽量独立
 * - 每个 chunk 只讲一个核心点
 * - 单块 300-900 汉字
 *
 * chunk_type 枚举：
 *   definition, rule, checklist, procedure, anti_pattern, template, example, navigation
 */

/**
 * 检测 chunk 类型
 */
function detectChunkType(section) {
  const lines = section.split('\n');
  const text = section.toLowerCase();
  const firstHeading = lines.find(l => l.startsWith('#')) || '';

  // 导航/索引
  if (/索引|导航|目录|index/i.test(firstHeading) &&
      (text.includes('├─') || text.includes('└─') || text.includes('|-') || text.includes('---'))) {
    return 'navigation';
  }

  // 模板/选型
  if (text.includes('项目选型') || text.includes('模板') ||
      text.includes('基本信息') || text.includes('| 字段 |')) {
    return 'template';
  }

  // 红线/禁止
  if (text.includes('红线') || text.includes('禁止') || text.includes('不要') ||
      text.includes('不允许') || text.includes('禁区') || text.includes('毒点')) {
    return 'rule';
  }

  // 步骤/流程
  if (text.includes('step') || text.includes('步骤') || text.includes('顺序') ||
      text.includes('第') && text.includes('步')) {
    return 'procedure';
  }

  // 清单/自检
  if (text.includes('检查') || text.includes('清单') || text.includes('自检') ||
      text.includes('评估') || text.includes('检测')) {
    return 'checklist';
  }

  // 反模式
  if (text.includes('常见问题') || text.includes('常见错误') || text.includes('不要') ||
      text.includes('反例') || text.includes('忌讳')) {
    return 'anti_pattern';
  }

  // 示例
  if (text.includes('示例') || text.includes('例子') || text.includes('比如') ||
      text.includes('例如')) {
    return 'example';
  }

  // 定义/原则
  if (text.includes('定义') || text.includes('原则') || text.includes('概述') ||
      text.includes('概念') || text.includes('范围')) {
    return 'definition';
  }

  return 'definition';
}

/**
 * 清理文本：移除多余空行、提取纯文本
 */
function cleanText(text) {
  return text
    .split('\n')
    .map(l => l.trim())
    .filter(l => l.length > 0)
    .join('\n');
}

/**
 * 按标题切分 Markdown 内容
 * @param {string} content - 原始 markdown
 * @returns {Array<{title: string, text: string, heading_level: number, section_ref: string}>}
 */
export function chunkMarkdown(content) {
  const lines = content.split('\n');
  const sections = [];
  let currentSection = null;
  let sectionCounter = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const headingMatch = line.match(/^(#{1,6})\s+(.+)/);

    if (headingMatch) {
      // 保存上一节
      if (currentSection && currentSection.text.length > 5) {
        sections.push(currentSection);
      }

      const level = headingMatch[1].length;
      const title = headingMatch[2].trim();
      sectionCounter++;

      const sectionRef = title
        .toLowerCase()
        .replace(/[^\w一-鿿]+/g, '-')
        .replace(/-+/g, '-')
        .replace(/^-|-$/g, '')
        .substring(0, 60);

      currentSection = {
        title,
        text: '',
        heading_level: level,
        section_ref: sectionRef || `section-${sectionCounter}`
      };
    } else if (currentSection) {
      currentSection.text += (currentSection.text ? '\n' : '') + line;
    } else {
      // 文档开头 (# 之前的内容)
      if (!currentSection) {
        currentSection = {
          title: '文档开头',
          text: '',
          heading_level: 1,
          section_ref: 'doc-intro'
        };
      }
      currentSection.text += (currentSection.text ? '\n' : '') + line;
    }
  }

  // 保存最后一节
  if (currentSection && currentSection.text.length > 5) {
    sections.push(currentSection);
  }

  // 后处理：将过长的 section 再按子标题/序号拆分
  const refined = [];
  for (const section of sections) {
    const charCount = countChars(section.text);
    if (charCount <= 900) {
      refined.push(section);
      continue;
    }

    // 尝试按子结构拆分
    const subSections = splitLongSection(section);
    refined.push(...subSections);
  }

  // 为每个 section 计算 chunk_type
  return refined.map(s => ({
    ...s,
    chunk_type: detectChunkType(s.title + '\n' + s.text),
    text: cleanText(s.text)
  })).filter(s => s.text.length >= 10); // 过滤太短的块
}

/**
 * 计算中文字符数
 */
function countChars(text) {
  // 中文算 1 个，英文/数字算 0.5，折合汉字数
  let count = 0;
  for (const ch of text) {
    if (/[一-鿿]/.test(ch)) count += 1;
    else if (/\S/.test(ch)) count += 0.3;
  }
  return count;
}

/**
 * 拆分过长的 section
 */
function splitLongSection(section) {
  const lines = section.text.split('\n');
  const subSections = [];
  let current = { ...section, text: '', section_ref: section.section_ref + '-a' };
  let subIdx = 'abcdefghij'.split('');

  for (const line of lines) {
    // 尝试在序号项处拆分
    const isSubItem = /^(\d+[\.\)、]|[-*•]\s)/.test(line.trim());
    const isTableRow = /^\|/.test(line.trim());

    if (isSubItem && countChars(current.text) > 300) {
      subSections.push({ ...current, text: cleanText(current.text) });
      const idx = subIdx.shift() || 'x';
      current = {
        ...section,
        title: `${section.title} (${idx})`,
        text: line,
        section_ref: section.section_ref + '-' + idx
      };
    } else {
      current.text += '\n' + line;
    }
  }

  if (current.text.trim().length > 5) {
    subSections.push({ ...current, text: cleanText(current.text) });
  }

  return subSections.filter(s => s.text.length >= 10);
}

export default { chunkMarkdown };
