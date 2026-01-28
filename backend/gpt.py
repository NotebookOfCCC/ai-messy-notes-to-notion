import os
import json
import re
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv
load_dotenv()
import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

CJK = re.compile(r"[\u4e00-\u9fff]")

def extract_json(text: str) -> dict:
    """Extract JSON from response, handling markdown code blocks."""
    text = text.strip()
    # Remove markdown code blocks if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)

def has_cn(s: str) -> bool:
    return bool(s and CJK.search(s))

def norm(s: str) -> str:
    return (
        (s or "")
        .replace("——", " ")
        .replace("—", " ")
        .replace("–", " ")
        .replace("  ", " ")
        .strip()
    )

def clean_example(en: str, zh: str) -> str:
    return f"{norm(en)} {norm(zh)}"

def build_preview(items: List[Dict[str, str]], theme: str = "") -> str:
    out = []
    if theme:
        out.append(f"【主题】{theme}")
        out.append("")
    for i, it in enumerate(items, 1):
        out.append(f"{i}. {it['english']} {it['chinese']}")
        out.append(f"例句: {it['example_en']} {it['example_zh']}")
        out.append("")
    return "\n".join(out).strip()

def ensure_theme(theme: str, items: List[Dict[str, str]]) -> str:
    if has_cn(theme):
        return theme
    return "短语与例句"

# ---------- PROCESS ----------

def process_notes(notes: str) -> Tuple[str, str, List[Dict[str, str]]]:
    prompt = f"""
只返回 JSON，不要任何解释。

格式：
{{
  "theme": "中文主题",
  "items": [
    {{
      "english": "",
      "chinese": "",
      "example_en": "",
      "example_zh": ""
    }}
  ]
}}

重要规则：
1. 动词短语必须使用原形（base form）：
   - "dug into" → "dig into"
   - "digging into" → "dig into"
   - "ran out" → "run out"
   - "was thinking" → "think"
2. 被动语态短语必须完整，加上 "be"：
   - "attached by" → "be attached by"
   - "known as" → "be known as"
   - "made of" → "be made of"
3. 例句中的动词可以使用适当的时态，但 english 字段必须是原形

内容：
{notes}
"""

    r = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    data = extract_json(r.content[0].text)
    items = []
    for it in data["items"]:
        items.append({
            "english": norm(it["english"]),
            "chinese": norm(it["chinese"]),
            "example_en": norm(it["example_en"]),
            "example_zh": norm(it["example_zh"]),
        })

    theme = ensure_theme(data.get("theme", ""), items)
    preview = build_preview(items, theme)
    return theme, preview, items

# ---------- REFINE（基于上一次 items） ----------

def refine_notes(
    items: List[Dict[str, Any]],
    notes: str,
    feedback: str
) -> Tuple[str, str, List[Dict[str, str]]]:

    # Build numbered list for clarity
    numbered_items = []
    for i, it in enumerate(items, 1):
        numbered_items.append(f"{i}. {it['english']} {it['chinese']}")

    prompt = f"""
你在【已有 items 基础上】修改。
可以删除编号（如：删除 2,3），也可以改表达。
不要新增。

当前 items（带编号）：
{chr(10).join(numbered_items)}

完整数据：
{json.dumps(items, ensure_ascii=False)}

用户反馈：
{feedback}

注意：如果用户说"删除 2"或"remove 2"或"remove item 2"，就删除上面编号为 2 的那一项。

重要规则：
1. 动词短语必须使用原形（base form）：
   - "dug into" → "dig into"
   - "digging into" → "dig into"
2. 被动语态短语必须完整，加上 "be"：
   - "attached by" → "be attached by"
   - "known as" → "be known as"
3. 例句中的动词可以使用适当的时态，但 english 字段必须是原形

只返回 JSON：

{{
  "theme": "中文主题",
  "items": [
    {{
      "english": "",
      "chinese": "",
      "example_en": "",
      "example_zh": ""
    }}
  ]
}}
"""

    r = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    data = extract_json(r.content[0].text)
    new_items = []
    for it in data["items"]:
        new_items.append({
            "english": norm(it["english"]),
            "chinese": norm(it["chinese"]),
            "example_en": norm(it["example_en"]),
            "example_zh": norm(it["example_zh"]),
        })

    theme = ensure_theme(data.get("theme", ""), new_items)
    preview = build_preview(new_items, theme)
    return theme, preview, new_items

# ---------- GRAMMAR CHECK ----------

def check_grammar(items: List[Dict[str, str]]) -> Dict[str, Any]:
    """Check grammar issues in the English phrases and examples."""
    if not items:
        return {"checked": True, "issues": []}

    items_text = "\n".join([
        f"{i+1}. Phrase: {it['english']}\n   Example: {it['example_en']}"
        for i, it in enumerate(items)
    ])

    prompt = f"""
Check the following English phrases and example sentences for grammar issues.

{items_text}

Return ONLY JSON, no explanation:
{{
  "has_issues": true/false,
  "issues": [
    {{
      "item_index": 1,
      "field": "english" or "example_en",
      "original": "the text with issue",
      "corrected": "the corrected text",
      "explanation": "brief explanation in Chinese"
    }}
  ]
}}

Rules:
- Only report actual grammar mistakes (verb tense, subject-verb agreement, articles, etc.)
- Do NOT report style preferences or minor punctuation
- If no issues found, return empty issues array
- item_index starts from 1
"""

    r = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )

    try:
        data = extract_json(r.content[0].text)
        return {
            "checked": True,
            "has_issues": data.get("has_issues", False),
            "issues": data.get("issues", [])
        }
    except:
        return {"checked": True, "has_issues": False, "issues": []}

# ---------- SUGGESTIONS ----------

def generate_suggestions(items: List[Dict[str, str]], theme: str) -> List[Dict[str, str]]:
    """Generate related vocabulary suggestions based on theme and existing items."""
    if not items:
        return []

    existing_words = [it["english"] for it in items]

    prompt = f"""
Based on the theme "{theme}" and the following vocabulary items, suggest 3-5 related English phrases/words that the user might also want to learn.

Existing items:
{json.dumps(existing_words, ensure_ascii=False)}

Return ONLY JSON, no explanation:
{{
  "suggestions": [
    {{
      "english": "suggested phrase",
      "chinese": "中文解释",
      "example_en": "Example sentence in English",
      "example_zh": "例句中文翻译"
    }}
  ]
}}

Rules:
- Suggest phrases related to the same theme/topic
- Do NOT repeat any existing items
- Keep suggestions practical and commonly used
- Chinese explanations should be clear and natural
- Use base form for verbs (e.g., "dig into" not "dug into")
- Complete passive phrases with "be" (e.g., "be known as" not "known as")
"""

    r = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )

    try:
        data = extract_json(r.content[0].text)
        suggestions = []
        for it in data.get("suggestions", []):
            suggestions.append({
                "english": norm(it["english"]),
                "chinese": norm(it["chinese"]),
                "example_en": norm(it["example_en"]),
                "example_zh": norm(it["example_zh"]),
            })
        return suggestions
    except:
        return []
