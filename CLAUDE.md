# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A web app that processes messy English notes (mixed Chinese/English, various formats) using Claude AI, structures them into vocabulary items with examples, allows iterative refinement, and saves to Notion.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server (port 5173)
uvicorn backend.main:app --reload --port 5173

# Access at http://127.0.0.1:5173
```

## Architecture

```
backend/
  main.py    - FastAPI app with 3 endpoints: /api/process, /api/refine, /api/save
  gpt.py     - Claude API integration for processing and refining notes
  notion.py  - Notion API client for saving structured items

public/
  index.html - Single page UI
  app.js     - Frontend logic (state: items, theme, originalNotes)
  style.css  - Light theme styling
```

## Data Flow

1. **Process**: User pastes notes → `/api/process` → Claude extracts structured JSON → returns preview + items
2. **Refine**: User gives feedback → `/api/refine` → Claude modifies existing items based on feedback
3. **Save**: User clicks save → `/api/save` → items saved to Notion database

## Item Structure

Each vocabulary item has: `english`, `chinese`, `example_en`, `example_zh`

Theme must be Chinese. Output format per item:
```
1. English phrase 中文解释
例句: English example —— 中文翻译
```

## Environment Variables (.env)

- `ANTHROPIC_API_KEY` - Claude API key
- `NOTION_TOKEN` - Notion integration token
- `NOTION_DATABASE_ID` - Target Notion database ID

## Notion Database Schema

Required properties:
- `English` (title)
- `Chinese` (rich_text)
- `Example` (rich_text)
- `Theme` (select)
- `Date` (date) - optional

## Key Implementation Details

- `extract_json()` in gpt.py handles Claude responses wrapped in markdown code blocks
- Frontend auto-detects new notes vs refinement based on text length (>200) or double newlines
- Refine operates on previous items, not original input
- `ensure_theme()` defaults to "短语与例句" if theme lacks Chinese characters
