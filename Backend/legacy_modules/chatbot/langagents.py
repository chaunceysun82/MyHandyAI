import os

from dotenv import load_dotenv
from langchain.chains import LLMChain
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate

load_dotenv()


def load_prompt(filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, "../prompts", filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return "".join(line for line in lines if not line.strip().startswith("#"))
    except Exception as e:
        print(f"❌ Could not load {filename}: {e}")
        return ""


# ---- PROMPT TEMPLATES ----
qa_prompt_text = load_prompt("qa_prompt.txt")
summary_prompt_text = load_prompt("summary_prompt.txt")
question_clarification_prompt_text = load_prompt("question_clarification_prompt.txt")
problem_recognition_prompt_text = load_prompt("problem_recognition_prompt.txt")
image_analysis_prompt_text = load_prompt("image_analysis_prompt.txt")
description_assessment_prompt_text = load_prompt("description_assessment_prompt.txt")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def LLM(model):  # shortcut
    return OpenAI(model=model, api_key=OPENAI_API_KEY)


# ---- LLM CHAINS ----
greetings_prompt = PromptTemplate(
    input_variables=[],
    template="You are a DIY customer service agent called MyHandyAI. Greet the user, introduce yourself, and ask the user to describe the project/repair/fix to be done."
)
greetings_chain = LLMChain(prompt=greetings_prompt, llm=LLM("gpt-4.1-nano"))

problem_recognition_prompt = PromptTemplate(
    input_variables=["user_message"],
    template=problem_recognition_prompt_text or "Classify the user's DIY issue and suggest next step. User: {user_message}"
)
problem_recognition_chain = LLMChain(prompt=problem_recognition_prompt, llm=LLM("gpt-4.1-mini"))

valid_description_prompt = PromptTemplate(
    input_variables=["message"],
    template="You are a DIY customer service agent, your task is to determine if the description/context of the repair/fix/project is coherent. Respond only 'True' or 'False'.\n{message}"
)
valid_description_chain = LLMChain(prompt=valid_description_prompt, llm=LLM("gpt-4.1-nano"))

skip_image_prompt = PromptTemplate(
    input_variables=["message"],
    template="Detect if the user doesn't have an image or want to skip the image upload (e.g 'skip','I dont have an image', etc...) Respond only with 'True' or 'False'.\nUser: {message}"
)
skip_image_chain = LLMChain(prompt=skip_image_prompt, llm=LLM("gpt-4.1-nano"))


# Custom function/tool for image analysis (example: wraps your vision API logic)
def analyze_image_tool(image_data: bytes, problem_type: str):
    # -- implement your base64 + vision API logic here --
    return {
        "analysis": "Fallback analysis: cannot process image in this mock.",
        "questions": ["What are you trying to fix here?"],
        "first_question": "What are you trying to fix here?"
    }


# Analyze problem description (no image)
image_analysis_no_image_prompt = PromptTemplate(
    input_variables=["problem_type", "user_description"],
    template=(
        f"{image_analysis_prompt_text or 'Analyze the DIY problem.'}\n\n"
        "Problem type: {problem_type}\n"
        "User description: {user_description}\n"
        f"Additional context: {qa_prompt_text}\n\n"
        "Since no image was provided, analyze the problem description and generate relevant questions.\n"
        "Return JSON with:\n"
        '- \"analysis\": brief description based on the problem description\n'
        '- \"questions\": list of questions (ask one-by-one)\n'
        '- \"first_question\": the first question to ask'
    )
)
image_analysis_no_image_chain = LLMChain(prompt=image_analysis_no_image_prompt, llm=LLM("gpt-4.1-mini"))

question_clarification_prompt = PromptTemplate(
    input_variables=["question", "user_response"],
    template=(
                         question_clarification_prompt_text or "Given the question and the user's response, decide if we should accept, ask follow-up, or rephrase.")
             + "\nQuestion: {question}\nUser response: {user_response}"
)
question_clarification_chain = LLMChain(prompt=question_clarification_prompt, llm=LLM("gpt-4.1-mini"))

summary_prompt = PromptTemplate(
    input_variables=["problem_type", "image_analysis", "answers_text"],
    template=(
        f"{summary_prompt_text or 'Summarize the DIY issue and context.'}\n\n"
        "Problem type: {problem_type}\n"
        "Image analysis: {image_analysis}\n"
        "User's answers to clarifying questions:\n"
        "{answers_text}\n"
        "Please create a summary of this DIY problem."
    )
)
summary_chain = LLMChain(prompt=summary_prompt, llm=LLM("gpt-4.1"))

description_assessment_prompt = PromptTemplate(
    input_variables=["description"],
    template=f"{description_assessment_prompt_text or 'Assess this description.'}\nDescription: \"\"\"{{description}}\"\"\""
)
description_assessment_chain = LLMChain(prompt=description_assessment_prompt, llm=LLM("gpt-4.1-mini"))

affirmative_negative_prompt = PromptTemplate(
    input_variables=["message"],
    template="You are an affirmative/negative detector. Determine if the user answer is affirmative to proceed with next steps or negative to not continue. Answer only '1' for affirmative, '2' for negative, '0' if you cannot determine.\n{message}"
)
affirmative_negative_chain = LLMChain(prompt=affirmative_negative_prompt, llm=LLM("gpt-4.1-nano"))


# ---- SIMPLE STATE MACHINE ----
class ChatState(dict):
    """Mutable dict for state."""
    pass


def _coerce_bool(text: str) -> bool:
    return (text or "").strip().lower() == "true"


def node_greetings(state: ChatState):
    try:
        state["response_message"] = greetings_chain.run({})
    except Exception:
        state["response_message"] = "Hi! I’m MyHandyAI. Tell me what you’d like to fix or build."
    state["current_state"] = "greetings"
    return "waiting_for_problem", state


def node_waiting_for_problem(state: ChatState):
    user_message = state.get("user_message", "")
    try:
        is_valid = _coerce_bool(valid_description_chain.run({"message": user_message}))
    except Exception:
        is_valid = bool(user_message and len(user_message) > 8)

    if not is_valid:
        state["response_message"] = "I didn’t quite get that. Can you re-describe the issue, repair, or project?"
        state["current_state"] = "waiting_for_problem"
        return "waiting_for_problem", state

    try:
        result = problem_recognition_chain.run({"user_message": user_message}) or ""
    except Exception:
        result = ""

    state["problem_recognition"] = result
    state["problem_type"] = state.get("problem_type") or "general"
    state["response_message"] = "Please upload a photo of the area you're working on, or type 'skip'."
    state["current_state"] = "waiting_for_problem"
    return "waiting_for_photos", state


def node_waiting_for_photos(state: ChatState):
    user_message = state.get("user_message", "")
    try:
        skip = _coerce_bool(skip_image_chain.run({"message": user_message}))
    except Exception:
        skip = (user_message or "").strip().lower() in {"skip", "no image", "dont have image", "i don't have an image"}

    if skip:
        problem_type = state.get("problem_type", "general")
        user_description = state.get("user_message", "")
        try:
            _ = image_analysis_no_image_chain.run({
                "problem_type": problem_type,
                "user_description": user_description
            }) or ""
        except Exception:
            _ = ""

        state["image_analysis"] = "Image analysis (no image): based on your description."
        state["questions"] = ["What exactly is broken or not working?", "When did this start?",
                              "What tools do you have available?"]
        state["response_message"] = "Let’s clarify a few things: " + state["questions"][0]
        state["current_question_index"] = 0
        state["current_state"] = "waiting_for_photos"
        return "asking_questions", state

    if state.get("uploaded_image"):
        try:
            image_result = analyze_image_tool(state["uploaded_image"], state.get("problem_type", "general"))
        except Exception:
            image_result = {"analysis": "Couldn’t process the image.", "questions": ["What are you trying to fix?"],
                            "first_question": "What are you trying to fix?"}

        state["image_analysis"] = image_result.get("analysis") or "No analysis."
        state["questions"] = image_result.get("questions") or ["What are you trying to fix?"]
        state["response_message"] = "Let’s clarify a few things: " + state["questions"][0]
        state["current_question_index"] = 0
        state["current_state"] = "waiting_for_photos"
        return "asking_questions", state

    state[
        "response_message"] = "Please upload the requested photo so I can analyze it, or type 'skip' if you prefer not to share photos."
    state["current_state"] = "waiting_for_photos"
    return "waiting_for_photos", state


def node_asking_questions(state: ChatState):
    idx = state.get("current_question_index", 0)
    questions = state.get("questions", [])

    if idx >= len(questions):
        answers_text = "\n".join(f"Q{i + 1}: {state.get('answer_' + str(i), '')}" for i in range(len(questions)))
        try:
            summary = summary_chain.run({
                "problem_type": state.get("problem_type", "general"),
                "image_analysis": state.get("image_analysis", ""),
                "answers_text": answers_text
            })
        except Exception:
            summary = "Summary unavailable. We collected your details and will proceed."

        state["summary"] = summary
        state[
            "response_message"] = f"Perfect! Here’s what I’ve got so far:\n\n**{summary}**\n\nDoes that look right? Reply 'yes' or 'no'."
        state["current_state"] = "asking_questions"
        return "showing_summary", state

    # capture the previous answer (for the previous question)
    if idx > 0:
        prev_idx = idx - 1
        state[f"answer_{prev_idx}"] = state.get("user_message", "")

        # Optional: run clarification chain (non-blocking robustness)
        try:
            _ = question_clarification_chain.run({
                "question": questions[prev_idx],
                "user_response": state.get("user_message", "")
            })
        except Exception:
            pass

    # ask current question
    question = questions[idx]
    state["response_message"] = question
    state["current_question_index"] = idx + 1
    state["current_state"] = "asking_questions"
    return "asking_questions", state


def node_showing_summary(state: ChatState):
    user_message = state.get("user_message", "")
    try:
        resp = (affirmative_negative_chain.run({"message": user_message}) or "").strip()
    except Exception:
        resp = "0"

    if resp == "1":
        state["response_message"] = "Perfect! Now we can proceed with your step-by-step guide."
        state["current_state"] = "showing_summary"
        return "done", state
    if resp == "2":
        state["response_message"] = "Got it. Let’s start from scratch — please describe your problem again."
        state["current_state"] = "showing_summary"
        return "waiting_for_problem", state

    state["response_message"] = "Please reply 'yes' if the summary looks correct, or 'no' if it doesn’t."
    state["current_state"] = "showing_summary"
    return "showing_summary", state


# ---- DISPATCHER ----
_NODE_MAP = {
    "greetings": node_greetings,
    "waiting_for_problem": node_waiting_for_problem,
    "waiting_for_photos": node_waiting_for_photos,
    "asking_questions": node_asking_questions,
    "showing_summary": node_showing_summary,
    "done": lambda s: ("done", s),
}


def run_chat_step(current_state, chat_state: dict):
    """
    Single-step transition runner that mirrors the old signature.
    Returns (next_state, new_state_dict).
    """
    state = ChatState(chat_state or {})
    # Unknown/None state? Start at greetings.
    state_name = current_state or "greetings"
    node_fn = _NODE_MAP.get(state_name, node_greetings)
    next_state, new_state = node_fn(state)
    return next_state, dict(new_state)
