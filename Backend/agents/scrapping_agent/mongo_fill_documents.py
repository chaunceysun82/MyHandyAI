from pymongo import MongoClient
from fetch_tools_materials import fetch_tools_materials
from dotenv import load_dotenv
from bson import ObjectId
from datetime import datetime
import os
import time
import traceback

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE")

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DATABASE]
col = db["kb_documents"]

SLEEP_SECONDS = 1.0     
DRY_RUN = False   
ONLY_UPDATE_EMPTY = True  

def normalize(name: str) -> str:
    """Normalize a name for dedupe and storage."""
    return name.strip()

def merge_string_lists(existing: list, new_list: list) -> list:
    """Merge existing and new lists (strings). Preserve existing order, append new items.
       Normalizes and deduplicates case-insensitively."""
    existing = existing or []
    new_list = new_list or []

    seen = set()
    merged = []

    for it in existing:
        if not isinstance(it, str):
            continue
        norm = normalize(it).lower()
        if norm and norm not in seen:
            seen.add(norm)
            merged.append(normalize(it))

    for it in new_list:
        if not isinstance(it, str):
            continue
        norm = normalize(it).lower()
        if norm and norm not in seen:
            seen.add(norm)
            merged.append(normalize(it))

    return merged

def process_document(doc):
    doc_id = doc.get("_id")
    url = doc.get("url", "<no-url>")

    if ONLY_UPDATE_EMPTY:
        existing_tools = doc.get("extracted", {}).get("tools", [])
        existing_materials = doc.get("extracted", {}).get("materials", [])
        if existing_tools or existing_materials:
            print(f"[SKIP] {doc_id} ({url}) — already has tools/materials")
            return

    sections = doc.get("extracted", {}).get("sections", []) or []
    if not isinstance(sections, list):
        sections = [sections]

    all_steps = []
    for sec in sections:
        if isinstance(sec, dict):
            steps = sec.get("steps")
            if isinstance(steps, list):
                all_steps.extend([s for s in steps if isinstance(s, str)])
            elif isinstance(steps, str):
                all_steps.append(steps)

    if not all_steps:
        print(f"[SKIP] {doc_id} ({url}) — no steps found")
        return
    steps_text = "\n".join([f"{i+1}. {s}" for i, s in enumerate(all_steps)])

    try:
        tools, materials = fetch_tools_materials(steps_text)

        if tools is None:
            tools = []
        if materials is None:
            materials = []

        if isinstance(tools, str):
            tools = [tools]
        if isinstance(materials, str):
            materials = [materials]

        existing_tools = doc.get("extracted", {}).get("tools", [])
        existing_materials = doc.get("extracted", {}).get("materials", [])

        merged_tools = merge_string_lists(existing_tools, tools)
        merged_materials = merge_string_lists(existing_materials, materials)

        update_doc = {
            "extracted.tools": merged_tools,
            "extracted.materials": merged_materials,
            "extracted.tools_updated_at": datetime.utcnow(),
        }

        if DRY_RUN:
            print(f"[DRY RUN] Would update {doc_id} ({url}) with:")
            print("  tools:", merged_tools)
            print("  materials:", merged_materials)
        else:
            col.update_one({"_id": doc_id}, {"$set": update_doc, "$unset": {"extracted.tools_error": ""}})
            print(f"[OK] Updated {doc_id} ({url}) → tools={len(merged_tools)}, materials={len(merged_materials)}")

    except Exception as e:
        err_msg = "".join(traceback.format_exception_only(type(e), e))[:2000]
        print(f"[ERROR] {doc_id} ({url}) -> {err_msg}")
        if not DRY_RUN:
            col.update_one(
                {"_id": doc_id},
                {"$set": {"extracted.tools_error": {"error": err_msg, "when": datetime.utcnow()}}}
            )

def main():
    query = {"extracted.sections": {"$exists": True}}
    if ONLY_UPDATE_EMPTY:
        query["$or"] = [
            {"extracted.tools": {"$exists": False}},
            {"extracted.tools": []},
            {"extracted.materials": {"$exists": False}},
            {"extracted.materials": []}
        ]

    cursor = col.find(query, {"url": 1, "extracted.sections": 1, "extracted.tools": 1, "extracted.materials": 1})
    count = 0
    for doc in cursor:
        process_document(doc)
        count += 1
        time.sleep(SLEEP_SECONDS)
    print(f"Processed {count} documents.")

if __name__ == "__main__":
    main()
