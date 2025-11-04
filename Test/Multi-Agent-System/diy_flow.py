from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import TypedDict, Annotated, List, Literal
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
import json
load_dotenv()

llm=ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7)

class ProblemSchema(BaseModel):
    problem: Literal["Greeetings", "DIY Based", "Not DIY Based"] = Field(description="Whether the message contains greetings or a DIY based problem or not a DIY based problem")
    reply: str = Field(description="A response to the user's message")

class DIYSchema(BaseModel):
    diy_classified: Literal["Plumbing", "Electrical", "HVAC (Heating, Ventilation, and Air Conditioning)", "Roofing & Gutters", "Drywall & Painting", "Flooring", "Doors & Windows", "Appliances", "Carpentry & Woodwork", "Exterior (Decks, Fences, Sliding)", "Landscaping & Yard Work","Pest Control & Wildlife", "Insulation & Weatherproofing", "Smart Home/Low Voltage", "General/Unknown Issue"] = Field(description="The DIY category the problem belongs to")
    reply: str = Field(description="A response to the user's message that includes confirmation that the DIY problem is understood in a natural human styled reply without mentioning the category and explanation.")

class FieldsSchema(BaseModel):
    fields: List[str] = Field(description="A list of important data fields to gather from the user to better understand and address their DIY problem")

class QuestionSchema(BaseModel):
    question: str = Field(description="A relevant question to ask the user to gather more information about their DIY problem")

class AnswerSchema(BaseModel):
    answer_classified: Literal['Skip', 'Answers Found', 'Cant Understand'] = Field(description="Whether the user's answer is trying to mean skip the question, provide relevant answers to the question, or cannot be understood")
    reply: str = Field(description="A response to the user's answer")

class AnswerRelevancySchema(BaseModel):
    answer_relevant: Literal['Relevant', 'Irrelevant'] = Field(description="Whether the user's answer is relevant to the question asked or not")
    reply: str = Field(description="A response to the user's answer relevancy")

class SummarySchema(BaseModel):
    summary: str = Field(description="A concise summary of the information gathered from the user regarding their DIY problem")

problem_llm=llm.with_structured_output(ProblemSchema)
diy_llm=llm.with_structured_output(DIYSchema)
fields_llm=llm.with_structured_output(FieldsSchema)
question_llm=llm.with_structured_output(QuestionSchema)
answer_llm=llm.with_structured_output(AnswerSchema)
answer_relevancy_llm=llm.with_structured_output(AnswerRelevancySchema)
summary_llm=llm.with_structured_output(SummarySchema)

class DIYState(TypedDict):
    message: str
    messages_history: Annotated[List[BaseMessage], add_messages]
    problem_classified: Literal["Greetings", "DIY Based", "Not DIY Based"]
    diy_classified: Literal["Plumbing", "Electrical", "HVAC (Heating, Ventilation, and Air Conditioning)", "Roofing & Gutters", "Drywall & Painting", "Flooring", "Doors & Windows", "Appliances", "Carpentry & Woodwork", "Exterior (Decks, Fences, Sliding)", "Landscaping & Yard Work","Pest Control & Wildlife", "Insulation & Weatherproofing", "Smart Home/Low Voltage", "General/Unknown Issue"]
    initial_problem: str
    fields_to_gather: List[dict]
    text_classified: Literal['Skip', 'Answers Found', 'Cant Understand']
    cant_understand: Literal['True', 'False']
    answer_relevant: Literal['Relevant', 'Irrelevant']
    information_retrieved: Literal['Questions Left', 'No Questions Left']
    fields_asked: str
    question_generated: str
    summary: str

def check_problem(state: DIYState):
    if state['problem_classified']=="DIY Based":
        return "Data Fields Generator"
    else:
        return "Problem Information"
    
def check_text(state: DIYState):
    if state['text_classified']=="Skip":
        return "Skip Question"
    elif state['text_classified']=="Answers Found":
        return "Answer Relevancy Checker Agent"
    else:
        return "Cant Answer"
    
def check_text_answer_relevancy(state: DIYState):
    if state['answer_relevant']=="Relevant":
        return "Information Retrieval Agent"
    else:
        return "AI Field Gathering"
    
def check_information_retrieval(state: DIYState):
    if state['information_retrieved']=="Questions Left":
        return "AI Field Gathering"
    else:
        return "Summary Generation"

def update_dictionary_with_llm(original_dict, user_answer, ai_question):
    response_schemas = []
    for key, val in original_dict.items():
        if val is None or (isinstance(val, str) and val.strip().lower() == "could not understand"):
            response_schemas.append(ResponseSchema(name=key,
                                                   description=f"Information about {key}",
                                                   type="string"))
    response_schemas.append(ResponseSchema(
        name="reply",
        description="A concise, human-like reply to the user based on the fields extracted. "
                    "Should summarize what was understood, confirm important details. Dont comment or ask any questions on the fields that are yet to be collected.",
        type="string"
    ))

    output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
    format_instructions = output_parser.get_format_instructions()

    prompt = ChatPromptTemplate.from_template("""
    You are an information extraction assistant. Given the following user answer, extract information for the specified fields and the AI question.

    Original dictionary state:
    {original_dict}

    User's answer: {user_answer}
                                              
    AI Question Asked: {ai_question}

    Instructions:
    - Extract information **only** for fields that are currently None or marked as 'Could Not Understand' in the dictionary.
    - Do not change fields that are 'Skipped' or already contain values.
    - If information for a field is not found in the user's answer, return that field as null/empty (the structured output parser will handle missing keys).
    - After extracting fields, generate a natural, human-like reply addressed to the user. The reply should:
        * Summarize the extracted information briefly,
        * Confirm or clarify any ambiguous points,
    - Use the format instructions below exactly.
                                              
    Dont comment or ask any questions on the fields that are yet to be collected or None.

    {format_instructions}

    Return only the structured output as specified.
    """)

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7)


    chain = prompt | llm | output_parser

 
    result = chain.invoke({
        "original_dict": json.dumps(original_dict),
        "user_answer": user_answer,
        "ai_question": ai_question,
        "format_instructions": format_instructions
    })

    updated_dict = original_dict.copy()
    generated_reply = None
    for key, value in result.items():
        if key == "reply":
            generated_reply = value
            continue
        if value is not None and isinstance(value, str) and value.strip() != "":
            updated_dict[key] = value

    return updated_dict, generated_reply


def greetings(state: DIYState):
    ai_msg="Hello! How can I assist you today?"
    print("AI :"+ai_msg+"\n")
    return {'messages_history': [AIMessage(ai_msg)], 'cant_understand': False}


def problem_information(state: DIYState):
    input_msg=input("User :")
    print("User :"+input_msg+"\n")
    return {'message': input_msg, 'messages_history': [HumanMessage(input_msg)]}


def problem_classifier(state: DIYState):
    
    prompt=f"""Classify the following message as either a 'Greetings' or 'DIY' problem or 'No DIY' problem:
    If the message is greeting based, then reply with a greeting message behaving like a helpful DIY assistant.
    If the message is not related to DIY, then reply politely that you can only help with DIY related problems.
    Message: "{state['message']}"
    If the message is not DIY Based, then just reply its not DIY based. Dont need any explanation. Also ask for a DIY related problems.
    """

    result=problem_llm.invoke(prompt)
    if result.problem=="Greeetings":
        print("AI :"+result.reply+"\n")
        return {'problem_classified': result.problem, 'messages_history': [AIMessage(result.reply)], 'initial_problem': state['message']}
    elif result.problem=="Not DIY Based":
        print("AI :"+result.reply+"\n")
        return {'problem_classified': result.problem, 'messages_history': [AIMessage(result.reply)], 'initial_problem': state['message']}
    
    #state['messages_history'].append(AIMessage(result.reply))
    return {'problem_classified': result.problem, 'initial_problem': state['message']}

    
    

def data_fields_generator(state: DIYState):
    prompt=f"""Classify the following DIY problem into one of the following categories:
    "Plumbing", "Electrical", "HVAC (Heating, Ventilation, and Air Conditioning)", "Roofing & Gutters", "Drywall & Painting", "Flooring", "Doors & Windows", "Appliances", "Carpentry & Woodwork", "Exterior (Decks, Fences, Sliding)", "Landscaping & Yard Work","Pest Control & Wildlife", "Insulation & Weatherproofing", "Smart Home/Low Voltage", "General/Unknown Issue"
    Problem: "{state['message']}"
    Respond with the appropriate category.
    In the reply portion dont mention the name of the category and explanation. Reply like a human that I can help you with the problem."""

    result=diy_llm.invoke(prompt)
    #state['messages_history'].append(AIMessage(result.reply))
    print("AI :"+result.reply+"\n")
    print("Classified DIY Problem Category :"+result.diy_classified+"\n")

    
    prompt_fields_gathering=f'''
    Based on the User Problem and the DIY caegory, generate the necessary and specific fields required to gather more information about the problem.
    Problem: "{state['message']}"
    DIY Category: "{result.diy_classified}"

    Instructions :

    The focus would be more on the Problem rather than on DIY Category. Try to generate the fields more depending on the problem provided. The category is just an outline not a must rule to be followed.

    Eg : 
    Category: Plumbing
    Fields:

    1. Specific issue (leak, clog, low pressure)
    2. Leak size/flow (drip, steady, burst; estimate)
    3. Shut-off valve status (open/closed/unknown)
    4. Location (kitchen, bathroom, outdoor, fixture)
    5. Duration (when it started; hours/days/weeks)
    6. Visible damage (stains/mold/warping; photos)
    7. Pipe material (copper, PVC, PEX, unknown)
    8. Recent work/changes (past 30 days)
    9. Water source/type (hot, cold, both)

    Category: Electrical
    Fields:

    1. What’s not working (lights, outlet, breaker)
    2. Breaker/GFCI status (tripped/replaced/checked)
    3. Area affected (single room, multiple, whole house)
    4. Any sparks/smell/smoke (describe; photos if safe)
    5. Wiring age/condition (approx years; visible damage)
    6. Recent electrical work (past 30 days)
    7. Power status (utility outage or isolated)
    8. Device model/error codes (appliance/fixture specifics)

    Category: HVAC (Heating, Ventilation, and Air Conditioning)
    Fields:

    1. System type (split, furnace, boiler, heat pump)
    2. Problem type (no heat, no cool, noisy, leak)
    3. Thermostat reading/error (set/actual; error codes)
    4. Last service/filter change (date or months)
    5. Indoor vs outdoor unit affected (specify)
    6. Brand/model and age (label/photo if available)
    7. Noise/vibration details (when and where)
    8. Recent power/events (surge, outage, storm)

    Category: Roofing & Gutters
    Fields:

    1. Problem type (leak, missing shingles, clogged gutter)
    2. Location on roof (north/south/eave/ridge; photo)
    3. Roof material (asphalt, metal, tile, unknown)
    4. Roof age (years or install date)
    5. Interior leaks/damage (stains, sagging; photos)
    6. Attic access/inspection results (moisture, mold)
    7. Recent weather event (storm, hail; date)
    8. Gutter condition (ure, sagging, downspout blocked)

    Category: Drywall & Painting
    Fields:

    1. Type of damage (crack, hole, bubble, stain)
    2. Size/extent (cm/in or small/medium/large)
    3. Moisture presence (damp, dry, water source)
    4. Location (wall, ceiling, room)
    5. Paint type/finish (latex, oil, matte, gloss)
    6. Need full repainting (yes/no)
    7. Photos (close-up + context view)

    Category: Flooring
    Fields:

    1. Material (hardwood, tile, laminate, carpet)
    2. Issue type (lift, crack, stain, squeak)
    3. Area affected (m² or room dimensions)
    4. Subfloor condition (soft, uneven, unknown)
    5. Water exposure history (recent or past)
    6. Age of flooring (years since install)
    7. Matching material availability (yes/no/photo)

    Category: Doors & Windows
    Fields:

    1. Problem type (stick, draft, broken glass, lock)
    2. Interior or exterior (specify)
    3. Material/frame type (wood, uPVC, aluminum)
    4. Measurements (width × height; photos)
    5. Moisture/rot or seal failure (describe)
    6. Pane type (single, double, triple; gas fill)
    7. Security/lock condition (working/damaged)

    Category: Appliances
    Fields:

    1. Appliance type (washer, fridge, oven, etc.)
    2. Brand/model and age (label/photo)
    3. Problem description (won’t start, leaking, noise)
    4. Error code or display message (exact text)
    5. Power/gas supply status (connected, tripped)
    6. Recent repairs/parts replaced (past 6 months)
    7. Photos of control panel and connections

    Category: Carpentry & Woodwork
    Fields:

    1. Repair or custom build (repair/modify/new)
    2. Dimensions and load requirements (L×W×H, weight)
    3. Material preference (pine, oak, plywood, metal)
    4. Indoor or outdoor use (specify exposure)
    5. Structural vs cosmetic (support vs finish)
    6. Finish/stain preference (paint, varnish, natural)
    7. Photos/sketch (measurement labels)

    Category: Exterior (Decks, Fences, Siding)
    Fields:

    1. Problem type (rot, loose boards, leaning fence)
    2. Material (wood, composite, vinyl, metal)
    3. Area/length affected (m² or linear meters)
    4. Foundation/posts condition (stable, rotted, loose)
    5. Insect or moisture damage signs (describe/photos)
    6. Recent changes or impacts (storms, vehicles)
    7. Desired outcome (repair, replace, reinforce)

    Category: Landscaping & Yard Work
    Fields:

    1. Issue type (drainage, erosion, overgrowth, planting)
    2. Area size (m² or dimensions)
    3. Soil/drainage details (clay, sandy, soggy)
    4. Plant/tree species involved (if known)
    5. Irrigation presence (none, drip, sprinkler)
    6. Utility lines/obstructions (known locations)
    7. Desired timeline (immediate/seasonal)

    Category: Pest Control & Wildlife
    Fields:

    1. Pest type (rodent, insect, bird, wildlife)
    2. Location and entry points (rooms, exterior)
    3. Duration and frequency (single sighting/ongoing)
    4. Damage observed (chew marks, droppings, nests)
    5. DIY attempts already tried (traps, sprays)
    6. Activity times (day/night; photos/video)
    7. Pets/children presence (yes/no)

    Category: Insulation & Weatherproofing
    Fields:

    1. Location (attic, wall, crawlspace, windows)
    2. Problem type (drafts, cold spots, condensation)
    3. Insulation type present (batts, blown, foam)
    4. Home age and recent renovations (years)
    5. Moisture or mold presence (yes/no; photos)
    6. Access difficulty (easy, limited, none)
    7. Energy goal (comfort, reduce bills, code upgrade)

    Category: Smart Home / Low Voltage
    Fields:

    1. Device type (thermostat, camera, light switch)
    2. Brand/model and firmware (label/photo)
    3. Install or troubleshoot (new install/troubleshoot)
    4. Network details (Wi-Fi, Zigbee, Z-Wave; SSID type)
    5. App/error messages (exact text/screenshots)
    6. Power source (battery, wired, POE)
    7. Other integrated systems (Alexa, Google Home)

    Category: General / Unknown Issue
    Fields:

    1. Symptom description (concise problem statement)
    2. Start time and progression (when and how changed)
    3. Location and accessibility (where and how to access)
    4. Urgency level (safety, emergency, cosmetic)
    5. Previous repairs or diagnostics (what was done)
    6. Tools/equipment available (handy, none, professional)

    Note: These are just examples. Generate specific and relevant fields based on the exact problem and category provided above.
    Respond with only the fields required in a numbered list format.
    '''
    result_fields_gathering=fields_llm.invoke(prompt_fields_gathering)
    print(result_fields_gathering.fields)
    fields=[]
    field_dict={}
    for field in result_fields_gathering.fields:
        field_dict[field]=None
    fields.append(field_dict)
    print(fields)

    return {'diy_classified': result.diy_classified, 'fields_to_gather': fields, 'messages_history': [AIMessage(result.reply)]}

def ai_field_gathering(state: DIYState):

    if state['cant_understand']==True:
        print("Here")
        prompt = f'''You are helping the user answer a specific question related to their DIY problem. The user is confused about how to respond, so provide a clear and friendly explanation along with a few practical examples.

        Guidelines:
        - Keep the explanation short and easy to understand.
        - Give direct and relevant examples that show how the user can answer the question.
        - Avoid vague or overly generic statements.
        - Make the tone human-like, supportive, and practical.

        Question: "{state['question_generated']}"
        User's DIY Problem: "{state['initial_problem']}"

        Now, explain how the user can answer this question clearly, using simple language and good examples.
        '''

        question=llm.invoke(prompt)
        print("AI: "+question.content+"\n")

        return {'messages_history': [AIMessage(question.content)], 'question_generated': question.content}



    question_to_ask=''
    field_dict=state['fields_to_gather'][0]
    for field in field_dict:
        if field_dict[field] is None:
            question_to_ask=field
            break

    print("Next Question to Ask :"+question_to_ask+"\n")

    prompt = f'''You are a helpful DIY assistant. Your goal is to ask the user a clear, natural-sounding question to gather a specific piece of information related to their DIY problem.

    Make sure:
    - The question feels human-like and conversational.
    - It is not too short or blunt — it should have a proper tone and context.
    - It should directly focus on the field that needs to be clarified.
    - Avoid unnecessary complexity, but maintain clarity and impact.

    User Problem: "{state['initial_problem']}"
    Information Needed: "{question_to_ask}"

    Now, based on this, ask the user a well-framed and thoughtful question.
    '''

    question=question_llm.invoke(prompt)
    print("AI :"+question.question+"\n")
    #state['messages_history'].append(AIMessage(question.question))
    return {'messages_history': [AIMessage(question.question)], 'fields_asked': question_to_ask, 'question_generated': question.question}
    

def text_answer(state: DIYState):
    user_answer=input("User :")
    print("User :"+user_answer+"\n")
    #state['messages_history'].append(HumanMessage(user_answer))
    return {'message': user_answer, 'messages_history': [HumanMessage(user_answer)]}

def text_classifier(state: DIYState):
    prompt=f'''Classify the following user answer to the question as either 'Skip', 'Answers Found', or 'Cant Understand'.

    If the user cannot understand the question or does not know how to answer, classify as 'Cant Understand'.
    If the user is trying to skip the question by mentioning skip, classify as 'Skip'.
    If the user is providing answers to the question, classify as 'Answers Found'.
    User Answer: "{state['message']}"
    Respond with the appropriate label.
    If the category is Skip, reply like this : its okay to skip the question and moving on to the next question...
    '''

    result=answer_llm.invoke(prompt)
    if result.answer_classified=="Skip":
        state['cant_understand']='False'
        print("AI :"+result.reply+"\n")
        return {'text_classified': result.answer_classified, 'cant_understand': state['cant_understand'], 'messages_history': [AIMessage(result.reply)]}

    elif result.answer_classified=="Cant Understand":
        state['cant_understand']='True'
        print("AI :"+result.reply+"\n")
        return {'text_classified': result.answer_classified, 'cant_understand': state['cant_understand']}

    else:
        state['cant_understand']='False'

    #state['messages_history'].append(AIMessage(result.reply))

    
    return {'text_classified': result.answer_classified, 'cant_understand': state['cant_understand']}

def skip_question(state: DIYState):
    state['fields_to_gather'][0][state['fields_asked']]="Skipped"
    state_changes="No Questions Left"
    fields_dict=state['fields_to_gather'][0]
    for field in fields_dict:
        if fields_dict[field] is None:
            state_changes="Questions Left"
            break

    return {'information_retrieved':state_changes}

def cant_answer(state: DIYState):
    state['fields_to_gather'][0][state['fields_asked']]="Could Not Understand"
    return {'cant_understand': True}

def answer_relevancy_checker_agent(state: DIYState):
    prompt=f'''Check if the following user answer is relevant to the question asked.
    Try to understand the context of the question and the answer provided by the user.
    Question Asked: "{state['question_generated']}"
    User Answer: "{state['message']}"
    If the answer is relevant, respond with 'Relevant'.
    If the answer is not relevant, respond with 'Irrelevant' and reply normally like a human with very brief why the answer looks irrelevant. Also re-ask the question with examples to answer in relevant way.
    Respond with the appropriate label.'''
    result=answer_relevancy_llm.invoke(prompt)
    if result.answer_relevant=="Irrelevant":
        print("AI :"+result.reply+"\n")
        #state['messages_history'].append(AIMessage(result.reply))
        return {'answer_relevant': result.answer_relevant, 'messages_history': [AIMessage(result.reply)]}
    
    return {'answer_relevant': result.answer_relevant}

def information_retrieval_agent(state: DIYState):
    fields_dict=state['fields_to_gather'][0]
    user_answer=state['message']
    ai_question=state['question_generated']
    state_changes="No Questions Left"
    updated_fields_dict, reply=update_dictionary_with_llm(fields_dict, user_answer, ai_question)
    state['fields_to_gather'][0]=updated_fields_dict

    
    fields_dict=state['fields_to_gather'][0]
    for field in fields_dict:
        if fields_dict[field] is None:
            state_changes="Questions Left"
            break


    print(state)
            
    
    return {'information_retrieved':state_changes, 'messages_history':[AIMessage(reply)]}

def summary_generation(state: DIYState):
    prompt = f'''You are a professional DIY assistant. Based on the details provided by the user, generate a clear and well-structured summary of their DIY problem.

    Requirements:
    - The summary should sound natural, calm, and professional — as if written by a human.
    - It should be at least 100 words.
    - Include only the relevant details from the information gathered.
    - Do not mention or comment on any fields marked as "Skipped."
    - Avoid vague or generic statements — be specific and precise about the details provided.
    - Maintain a smooth flow in the description, without listing points mechanically.

    Chat History: "{state['messages_history']}"
    Fields Gathered: "{state['fields_to_gather']}"

    Now, write the final summary.
    '''

    result=summary_llm.invoke(prompt)
    print(f"Summary Generation : \n\n{result.summary}")
    
    return {'summary': result.summary}

graph=StateGraph(DIYState)
graph.add_node("Greetings", greetings)
graph.add_node("Problem Information", problem_information)
graph.add_node("Problem Classifier", problem_classifier)
graph.add_node("Data Fields Generator", data_fields_generator)
graph.add_node("AI Field Gathering", ai_field_gathering)
graph.add_node("Text Answer", text_answer)
#graph.add_node("Image/Video", image_video)
graph.add_node("Text Classifier", text_classifier)
graph.add_node("Skip Question", skip_question)
graph.add_node("Cant Answer", cant_answer)
graph.add_node("Answer Relevancy Checker Agent", answer_relevancy_checker_agent)
graph.add_node("Information Retrieval Agent", information_retrieval_agent)
graph.add_node("Summary Generation", summary_generation)
#graph.add_node("Image Relevancy Checker Agent", image_relevancy_checker_agent)
#graph.add_node("Image Analysis Agent", image_analysis_agent)

graph.add_edge(START, "Greetings")
graph.add_edge("Greetings", "Problem Information")
graph.add_edge("Problem Information", "Problem Classifier")
graph.add_conditional_edges("Problem Classifier", check_problem, {"Data Fields Generator": "Data Fields Generator", "Problem Information": "Problem Information"})
graph.add_edge("Data Fields Generator", "AI Field Gathering")
graph.add_edge("AI Field Gathering", "Text Answer")
graph.add_edge("Text Answer", "Text Classifier")
graph.add_conditional_edges("Text Classifier", check_text, {"Skip Question": "Skip Question", "Answer Relevancy Checker Agent": "Answer Relevancy Checker Agent", "Cant Answer": "Cant Answer"})
graph.add_conditional_edges("Skip Question", check_information_retrieval, {"AI Field Gathering": "AI Field Gathering", "Summary Generation": "Summary Generation"})
graph.add_edge("Cant Answer", "AI Field Gathering")
graph.add_conditional_edges("Answer Relevancy Checker Agent", check_text_answer_relevancy, {"Information Retrieval Agent": "Information Retrieval Agent", "AI Field Gathering": "Text Answer"})
graph.add_conditional_edges("Information Retrieval Agent", check_information_retrieval, {"AI Field Gathering": "AI Field Gathering", "Summary Generation": "Summary Generation"})
graph.add_edge("Summary Generation", END)
workflow=graph.compile()

workflow.invoke({}, {"recursion_limit": 100})
