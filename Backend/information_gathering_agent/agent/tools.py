from bson import ObjectId
from langchain.tools import tool, ToolRuntime
from loguru import logger
from pydantic import Field
from pymongo.collection import Collection
from pymongo.database import Database

from agents.information_gathering_agent.agent.embeddings_generation import embed_and_store_project_summary, find_similar_projects_single_chunk
from agents.information_gathering_agent.agent.utils import extract_qa_pairs_from_messages
from database.enums.project import InformationGatheringConversationStatus
from database.mongodb import mongodb

database: Database = mongodb.get_database()
project_collection: Collection = database.get_collection("Project")

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"

@tool(
    description="Call this tool AFTER identifying the problem category but BEFORE beginning focused information gathering. This establishes the diagnostic framework and stores your information gathering strategy."
)
def store_home_issue(
        runtime: ToolRuntime,
        category: str = Field(
            description="The category from the Home Issue Knowledge Base. Must be one of: Plumbing, Electrical, HVAC (Heating/Cooling), Roofing & Gutters, Drywall & Painting, Flooring, Doors & Windows, Appliances, Carpentry & Woodwork, Exterior (Decks, Fences, Siding), Landscaping & Yard Work, Pest Control & Wildlife, Insulation & Weatherproofing, Smart Home / Low Voltage, General / Unknown Issue.",
            examples=["Electrical", "Plumbing", "HVAC (Heating/Cooling)"]
        ), issue: str = Field(
            description="A concise description of the user's specific problem. Be clear and specific.",
            examples=["Dead outlet", "Leaky kitchen faucet", "AC not cooling"]
        ), user_description: str = Field(
            description="The original problem description provided by the user at the start of the conversation.",
            examples=["My kitchen outlet stopped working yesterday", "The faucet in my bathroom is leaking"]
        )
        , information_gathering_plan: str = Field(
            description="A detailed plan describing which key information you will now collect based on the Knowledge Base checklist for this category. Reference the specific points from the 'Key Information to Collect' section.",
            examples=[
                "I will now ask about: 1. Any sparks/smell (IMMEDIATE SAFETY CHECK), 2. Breaker or GFCI status, 3. Location and scope of the problem, 4. Recent installations"]
        )
) -> str:
    """Store the home issue category, user description, and information gathering plan."""
    logger.info(f"Stored home issue - Category: {category}, Issue: {issue}")
    logger.info(f"User description: {user_description}")
    logger.info(f"Information gathering plan: {information_gathering_plan}")

    # Get project_id from config
    project_id = runtime.config.get("configurable", {}).get("project_id")

    if project_id:
        try:
            # Store initial data in project and update status to IN_PROGRESS
            update_data = {
                "category": category,
                "issue": issue,
                "user_description": user_description,
                "information_gathering_plan": information_gathering_plan,
                "information_gathering_conversation_status": InformationGatheringConversationStatus.IN_PROGRESS.value
            }
            project_collection.update_one(
                {"_id": ObjectId(project_id)},
                {"$set": update_data}
            )
            logger.info(f"Stored home issue data in project {project_id} and set status to IN_PROGRESS")
        except Exception as e:
            logger.error(f"Error storing home issue data: {e}")

    return f"✓ Stored: {category} - {issue}. Starting information gathering."


@tool(
    description="Call this tool at the END of the conversation, AFTER the user has confirmed your summary. This finalizes the diagnostic phase and hands off to the Solution Generation Agent."
)
def store_summary(
        runtime: ToolRuntime,
        summary: str = Field(
            description="A comprehensive, structured summary of ALL facts gathered during the information gathering phase. Include: Category, Issue, Location, Duration, Specific symptoms/details, Safety concerns, Material/equipment info (if applicable). Format clearly with bullet points or structured text.",
            examples=[
                "Category: Electrical. Issue: Dead outlet. Location: Kitchen countertop, near sink. Details: No visible discoloration initially, GFCI reset did not resolve issue, breaker not tripped. Single outlet affected, others on circuit working fine."]
        ), hypotheses: str = Field(
            description="Your expert hypothesis about the root cause. Be professional but informative. Include risk level assessment if relevant.",
            examples=[
                "Hypothesis: Likely a loose wire connection or faulty outlet mechanism. Medium risk due to location near water source. May need outlet replacement.",
                "Hypothesis: GFCI outlet failure or upstream connection problem. Low immediate risk, but should be addressed to prevent future hazards."]
        )) -> str:
    """Store the final summary and hypotheses before handoff to Solution Generation Agent."""
    logger.info("Stored final summary:")
    logger.info(f"Summary: {summary}")
    logger.info(f"Hypotheses: {hypotheses}")

    # Get project_id from config
    project_id = runtime.config.get("configurable", {}).get("project_id")

    if not project_id:
        logger.warning("No project_id found in config, cannot save to project")
        return "✓ Summary stored. Ready for handoff to Solution Generation Agent."

    try:
        # Get messages from state to extract Q&A pairs
        # In LangGraph, state is typically a dict with 'messages' key
        state = runtime.state if hasattr(runtime, 'state') else {}
        if isinstance(state, dict):
            messages = state.get("messages", [])
        else:
            # If state is not a dict, try to get messages directly
            messages = getattr(state, "messages", []) if hasattr(state, "messages") else []

        # Extract Q&A pairs from conversation history
        questions, answers, image_analysis = extract_qa_pairs_from_messages(messages)

        logger.info(f"Extracted {len(questions)} questions and {len(answers)} answers from conversation")

        # Prepare update data matching old system format
        # Store both 'answers' and 'user_answers' for compatibility (generation code checks both)
        update_data = {
            "summary": summary,
            "hypotheses": hypotheses,
            "questions": questions if questions else [],
            "answers": answers if answers else {},  # Primary field (old system format)
            "user_answers": answers if answers else {},  # Alternative field name (generation code fallback)
            "image_analysis": image_analysis or "",  # Default empty string if no image analysis
            "information_gathering_conversation_status": InformationGatheringConversationStatus.COMPLETED.value
        }

        # Update project with all collected data
        result = project_collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            logger.warning(f"Project {project_id} not found, could not save summary")
            project_doc = {**update_data, "_id": ObjectId(project_id)}
        else:
            logger.info(f"Successfully saved summary and Q&A data to project {project_id} and set status to COMPLETED")
            project_doc = project_collection.find_one({"_id": ObjectId(project_id)})

        do_embeddings = True
        embedding_result = None
        if do_embeddings:
            try:
                embedding_model = DEFAULT_EMBEDDING_MODEL
                if project_doc is None:
                    project_doc = {**update_data, "_id": ObjectId(project_id)}

                summary_text= project_doc.get("summary", "")
                if summary_text.strip() == "":
                    logger.warning("No summary text available for embedding generation.")
                else:
                    result=find_similar_projects_single_chunk(summary_text)
                    for p in result["projects"][:1]:
                        logger.info(f"Similar project found - ID: {p['project_id']}, Score: {p['score']}")
                        logger.info(p["text"] or "")
                embedding_result = embed_and_store_project_summary(project_doc, model=embedding_model)
                print(embedding_result)
                logger.info(f"Embeddings stored: {embedding_result}")
            except Exception as e:
                logger.error(f"Error creating/storing embeddings: {e}")

    except Exception as e:
        logger.error(f"Error storing summary data: {e}")

    if do_embeddings:
        if embedding_result and embedding_result.get("status") == "ok":
            return "✓ Summary stored. Embeddings created and saved to Qdrant. Ready for handoff to Solution Generation Agent."
        else:
            return "✓ Summary stored. Embeddings were attempted but failed — check logs. Ready for handoff to Solution Generation Agent."
    return "✓ Summary stored. Ready for handoff to Solution Generation Agent."
