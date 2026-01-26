from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any
from fastapi.staticfiles import StaticFiles

from backend.gpt import process_notes, refine_notes
from backend.notion import save_items_to_notion

app = FastAPI()

# ---------- Models ----------

class ProcessPayload(BaseModel):
    notes: str

class RefinePayload(BaseModel):
    items: List[Dict[str, Any]]
    notes: str
    feedback: str

class SavePayload(BaseModel):
    items: List[Dict[str, Any]]
    theme: str

# ---------- API ----------

@app.post("/api/process")
def api_process(p: ProcessPayload):
    theme, preview, items = process_notes(p.notes)
    return {
        "theme": theme,
        "preview": preview,
        "items": items
    }

@app.post("/api/refine")
def api_refine(p: RefinePayload):
    theme, preview, items = refine_notes(
        p.items,
        p.notes,
        p.feedback
    )
    return {
        "theme": theme,
        "preview": preview,
        "items": items
    }

@app.post("/api/save")
def api_save(p: SavePayload):
    saved, failed = save_items_to_notion(p.items, p.theme)
    return {
        "saved": saved,
        "failed": failed
    }

# ---------- Static ----------

app.mount("/", StaticFiles(directory="public", html=True), name="public")
