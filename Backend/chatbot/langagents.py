import os
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langgraph.graph import StateGraph

load_dotenv()

def load_prompt(filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, "prompts", filename)
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
    template=problem_recognition_prompt_text
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
    # Should return dict with "analysis", "questions", etc.
    return {
        "analysis": "Fallback analysis: cannot process image in this mock.",
        "questions": ["What are you trying to fix here?"],
        "first_question": "What are you trying to fix here?"
    }

# Analyze problem description (no image)
image_analysis_no_image_prompt = PromptTemplate(
    input_variables=["problem_type", "user_description"],
    template=(
        f"{image_analysis_prompt_text}\n\n"
        "Problem type: {problem_type}\n"
        "User description: {user_description}\n"
        f"Additional context: {qa_prompt_text}\n\n"
        "Since no image was provided, analyze the problem description and generate relevant questions.\n"
        "Return JSON with:\n"
        '- "analysis": brief description based on the problem description\n'
        '- "questions": list of questions (ask one-by-one)\n'
        '- "first_question": the first question to ask'
    )
)
image_analysis_no_image_chain = LLMChain(prompt=image_analysis_no_image_prompt, llm=LLM("gpt-4.1-mini"))

question_clarification_prompt = PromptTemplate(
    input_variables=["question", "user_response"],
    template=question_clarification_prompt_text.replace("{question}", "{question}").replace("{user_response}", "{user_response}")
)
question_clarification_chain = LLMChain(prompt=question_clarification_prompt, llm=LLM("gpt-4.1-mini"))

summary_prompt = PromptTemplate(
    input_variables=["problem_type", "image_analysis", "answers_text"],
    template=(
        f"{summary_prompt_text}\n\n"
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
    template=f"{description_assessment_prompt_text}\nDescription: \"\"\"{{description}}\"\"\""
)
description_assessment_chain = LLMChain(prompt=description_assessment_prompt, llm=LLM("gpt-4.1-mini"))

affirmative_negative_prompt = PromptTemplate(
    input_variables=["message"],
    template="You are an affirmative/negative detector. Determine if the user answer is affirmative to proceed with next steps or negative to not continue. Answer only '1' for affirmative, '2' for negative, '0' if you cannot determine.\n{message}"
)
affirmative_negative_chain = LLMChain(prompt=affirmative_negative_prompt, llm=LLM("gpt-4.1-nano"))

# ---- LANGGRAPH ORCHESTRATION ----
class ChatState(dict): pass

def node_greetings(state: ChatState):
    state["response_message"] = greetings_chain.run({})
    return "waiting_for_problem", state

def node_waiting_for_problem(state: ChatState):
    user_message = state.get("user_message", "")
    is_valid = valid_description_chain.run({"message": user_message}).strip() == "True"
    if not is_valid:
        state["response_message"] = "Not quite understand the description, could you please send again a description of the issue, repair or project you are facing?"
        return "waiting_for_problem", state
    result = problem_recognition_chain.run({"user_message": user_message})
    # TODO: Parse result as JSON, update state with problem_type, response_message, etc.
    state["problem_recognition"] = result
    state["problem_type"] = "general"  # extract from result
    state["response_message"] = "Please upload a photo of the area you're working on, or type 'skip'."  # extract from result if available
    return "waiting_for_photos", state

def node_waiting_for_photos(state: ChatState):
    user_message = state.get("user_message", "")
    skip = skip_image_chain.run({"message": user_message}).strip() == "True"
    if skip:
        # No image: analyze problem description
        problem_type = state.get("problem_type", "general")
        user_description = state.get("user_message", "")
        result = image_analysis_no_image_chain.run({
            "problem_type": problem_type,
            "user_description": user_description
        })
        # TODO: Parse result as JSON, fill state["image_analysis"], ["questions"]
        state["image_analysis"] = "Image analysis fallback (no image)."  # extract from result
        state["questions"] = ["What are you trying to fix?"]  # extract from result
        state["response_message"] = "Let's clarify a few things: " + state["questions"][0]
        state["current_question_index"] = 0
        return "asking_questions", state
    if "uploaded_image" in state and state["uploaded_image"]:
        # Process image (your function, could use vision API)
        image_result = analyze_image_tool(state["uploaded_image"], state.get("problem_type", "general"))
        state["image_analysis"] = image_result["analysis"]
        state["questions"] = image_result["questions"]
        state["response_message"] = "Let's clarify a few things: " + state["questions"][0]
        state["current_question_index"] = 0
        return "asking_questions", state
    # No image, no skip: prompt again
    state["response_message"] = "Please upload the requested photo so I can analyze it, or type 'skip' if you prefer not to share photos."
    return "waiting_for_photos", state

def node_asking_questions(state: ChatState):
    idx = state.get("current_question_index", 0)
    questions = state.get("questions", [])
    if idx >= len(questions):
        # Done asking, move to summary
        answers_text = "\n".join(f"Q{i+1}: {state.get('answer_'+str(i), '')}" for i in range(len(questions)))
        summary = summary_chain.run({
            "problem_type": state.get("problem_type", "general"),
            "image_analysis": state.get("image_analysis", ""),
            "answers_text": answers_text
        })
        state["summary"] = summary
        state["response_message"] = f"Perfect! Here’s what I’ve got so far:\n\n**{summary}**\n\nDoes that look right? Reply 'yes' or 'no'."
        return "showing_summary", state
    # Ask next question (assume user response is in 'user_message')
    question = questions[idx]
    user_response = state.get("user_message", "")
    # For first Q, just ask; for subsequent Qs, clarify
    if idx > 0:
        clarification_result = question_clarification_chain.run({"question": question, "user_response": user_response})
        # TODO: Parse clarification_result for action (accept/skip/etc.)
        state["answer_"+str(idx-1)] = user_response
    state["response_message"] = f"{question}"
    state["current_question_index"] = idx + 1
    return "asking_questions", state

def node_showing_summary(state: ChatState):
    user_message = state.get("user_message", "")
    resp = affirmative_negative_chain.run({"message": user_message}).strip()
    if resp == "1":
        state["response_message"] = "Perfect! Now we can proceed with your step by step guide."
        return "done", state
    if resp == "2":
        state["response_message"] = "I’m sorry for the mix-up. Let’s start from scratch – please describe your problem again."
        return "waiting_for_problem", state
    state["response_message"] = "Please reply 'yes' if the summary looks correct, or 'no' if it doesn’t."
    return "showing_summary", state

# ---- BUILD THE GRAPH ----
graph = StateGraph()
graph.add_node("greetings", node_greetings)
graph.add_node("waiting_for_problem", node_waiting_for_problem)
graph.add_node("waiting_for_photos", node_waiting_for_photos)
graph.add_node("asking_questions", node_asking_questions)
graph.add_node("showing_summary", node_showing_summary)
graph.add_edge("greetings", "waiting_for_problem")
graph.add_edge("waiting_for_problem", "waiting_for_photos")
graph.add_edge("waiting_for_photos", "asking_questions")
graph.add_edge("asking_questions", "showing_summary")
graph.add_edge("showing_summary", "waiting_for_problem")
graph.add_edge("showing_summary", "done")

def run_chat_step(current_state, chat_state: dict):
    state = ChatState(chat_state)
    next_state, new_state = graph.run(current_state, state)
    return next_state, dict(new_state)

