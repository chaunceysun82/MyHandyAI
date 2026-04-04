from pymongo import MongoClient
from fetch_tools_materials import fetch_tools_materials
from dotenv import load_dotenv
from datetime import datetime
import os
import time
import traceback
import json

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE")

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DATABASE]
col = db["kb_documents"]

SLEEP_SECONDS = 1.0
WRITE_TO_MONGO = True
TEST_ONE_DOC = True


def format_summary(summary_obj) -> str:
    """
    Convert the nested summary object into a single string:
    Category : ...
    Issue : ...
    Location : ...
    Duration : ...
    Specific_symptoms : ...
    safety_concerns : ...
    """
    if hasattr(summary_obj, "model_dump"):
        summary_obj = summary_obj.model_dump()

    if not isinstance(summary_obj, dict):
        return str(summary_obj)

    return "\n".join([
        f"Category : {summary_obj.get('Category', 'Unknown')}",
        f"Issue : {summary_obj.get('Issue', 'Unknown')}",
        f"Location : {summary_obj.get('Location', 'Unknown')}",
        f"Duration : {summary_obj.get('Duration', 'Unknown')}",
        f"Specific_symptoms : {summary_obj.get('Specific_symptoms', 'Unknown')}",
        f"safety_concerns : {summary_obj.get('safety_concerns', 'None reported')}",
    ])


def process_document(doc):
    doc_id = doc.get("_id")
    url = doc.get("url", "<no-url>")

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
        return False

    steps_text = "\n".join([f"{i+1}. {s}" for i, s in enumerate(all_steps)])

    try:
        output = fetch_tools_materials(steps_text)

        tools = output.tools or []
        materials = output.materials or []
        warnings = output.safety_warnings or []
        summary_text = format_summary(output.summary)

        if isinstance(tools, str):
            tools = [tools]
        if isinstance(materials, str):
            materials = [materials]
        if isinstance(warnings, str):
            warnings = [warnings]

        update_doc = {
            "extracted.tools": tools,
            "extracted.materials": materials,
            "extracted.warnings": warnings,
            "extracted.summary": summary_text,
            "extracted.tools_updated_at": datetime.utcnow(),
            "extracted.materials_updated_at": datetime.utcnow(),
            "extracted.warnings_updated_at": datetime.utcnow(),
            "extracted.summary_updated_at": datetime.utcnow(),
        }

        update_query = {
            "$set": update_doc,
            "$unset": {
                "extracted.safety_warnings": ""
            }
        }

        if WRITE_TO_MONGO:
            result = col.update_one({"_id": doc_id}, update_query)

            updated_doc = col.find_one(
                {"_id": doc_id},
                {
                    "extracted.tools": 1,
                    "extracted.materials": 1,
                    "extracted.warnings": 1,
                    "extracted.summary": 1,
                    "extracted.safety_warnings": 1,
                }
            )

            ok = (
                updated_doc is not None
                and updated_doc.get("extracted", {}).get("tools") == tools
                and updated_doc.get("extracted", {}).get("materials") == materials
                and updated_doc.get("extracted", {}).get("warnings") == warnings
                and updated_doc.get("extracted", {}).get("summary") == summary_text
                and "safety_warnings" not in updated_doc.get("extracted", {})
            )

            if ok:
                print(f"[OK] Updated {doc_id} ({url})")
            else:
                print(f"[FAIL] Updated {doc_id} ({url}) but verification did not fully match")

            print(json.dumps({
                "matched_count": result.matched_count,
                "modified_count": result.modified_count,
                "tools_count": len(tools),
                "materials_count": len(materials),
                "warnings_count": len(warnings),
                "summary_preview": summary_text[:200]
            }, indent=2, default=str))

        else:
            print(f"[DRY RUN] {doc_id} ({url})")
            print(json.dumps({
                "extracted.tools": tools,
                "extracted.materials": materials,
                "extracted.warnings": warnings,
                "extracted.summary": summary_text,
                "unset": ["extracted.safety_warnings"]
            }, indent=2, default=str, ensure_ascii=False))

        return True

    except Exception as e:
        err_msg = "".join(traceback.format_exception_only(type(e), e))[:2000]
        print(f"[ERROR] {doc_id} ({url}) -> {err_msg}")
        if WRITE_TO_MONGO:
            col.update_one(
                {"_id": doc_id},
                {"$set": {"extracted.tools_error": {"error": err_msg, "when": datetime.utcnow()}}}
            )
        return False


def main():
    query = {"extracted.sections": {"$exists": True}}

    cursor = col.find(
        query,
        {
            "url": 1,
            "extracted.sections": 1,
            "extracted.tools": 1,
            "extracted.materials": 1,
            "extracted.warnings": 1,
            "extracted.summary": 1,
        },
    )

    count = 0
    for doc in cursor:
        done = process_document(doc)
        count += 1
        if count>=15:
            break
        time.sleep(SLEEP_SECONDS)

    print(f"Processed {count} document(s).")


if __name__ == "__main__":
    main()
