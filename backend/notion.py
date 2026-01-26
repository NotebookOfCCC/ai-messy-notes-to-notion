import os
import sys
from datetime import date
from typing import List, Dict, Any
from notion_client import Client

notion = Client(auth=os.getenv("NOTION_TOKEN"))
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# First, let's check what properties the database has
def get_database_schema():
    try:
        db = notion.databases.retrieve(database_id=DATABASE_ID)
        props = list(db["properties"].keys())
        print(f"Database properties: {props}", file=sys.stderr)
        return props
    except Exception as e:
        print(f"Failed to get database: {e}", file=sys.stderr)
        return []

def save_items_to_notion(items: List[Dict[str, Any]], theme: str):
    # Log database schema on first save
    get_database_schema()

    saved = 0
    failed = 0

    for it in items:
        try:
            notion.pages.create(
                parent={"database_id": DATABASE_ID},
                properties={
                    "English": {
                        "title": [{"text": {"content": it["english"]}}]
                    },
                    "Chinese": {
                        "rich_text": [{"text": {"content": it["chinese"]}}]
                    },
                    "Example": {
                        "rich_text": [{
                            "text": {
                                "content": f'{it["example_en"]} {it["example_zh"]}'
                            }
                        }]
                    },
                    "Theme": {
                        "select": {"name": theme}
                    },
                    "Date": {
                        "date": {"start": date.today().isoformat()}
                    }
                }
            )
            saved += 1
        except Exception as e:
            print(f"Notion error: {e}", file=sys.stderr)
            failed += 1

    return saved, failed
