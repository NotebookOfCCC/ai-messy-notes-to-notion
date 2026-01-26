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
