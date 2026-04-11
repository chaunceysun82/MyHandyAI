from pydantic import BaseModel, Field
from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class SummaryModel(BaseModel):
    Category: str=Field(description="Category of the DIY work.")
    Issue: str=Field(description="Main DIY issue in one line.")
    Location: str=Field(description="Probable location of the DIY issue.")
    Duration: str=Field(description="Mention duration if mentioned otherwise put Unknown")
    Specific_symptoms: str=Field(description="Provide 5-6 symptoms or details about the problem like its features, etc")
    safety_concerns: str=Field(description="Provide any safety concerns mentioned to carry on with the DIY task.")
    
class FetchToolsMaterialsModel(BaseModel):
    tools: List[str]=Field(description="List the name of the tools needed to complete the steps.")
    materials: List[str]=Field(description="List the name of the materials needed to complete the steps.")
    safety_warnings: List[str]=Field(description="List the safety measures, the users need to follow to work on the steps.")
    summary: SummaryModel


parser = PydanticOutputParser(pydantic_object=FetchToolsMaterialsModel)

llm = ChatOpenAI(
    model="gpt-5-nano",
    api_key=OPENAI_API_KEY,
)

prompt = PromptTemplate(
    template="""
    Background : You are an expert DIY analysis and information extraction assistant. The input contains only the steps, solution, or repair guidance for a DIY task. Your job is to infer the likely problem description from those steps and return a structured output.

    Task (Detailed) : From the given DIY solution/steps, infer and extract:
    1. tools: reusable instruments used to shape, cut, or manipulate materials, such as hammers or saws, etc.
    2. materials: consumable substances or ingredients that become part of the final product, such as wood or paint.
    3. safety_warnings: all safety precautions or hazards implied or mentioned in the steps.
    4. summary: a structured problem summary inferred from the solution steps with:
    - Category: the most relevant DIY category.
    - Issue: the likely main problem being solved, in one line.
    - Location: the probable location or area where the issue occurs.
    - Duration: mention duration only if the steps explicitly imply it; otherwise use "Unknown".
    - Specific_symptoms: 5–6 concise symptoms/details that describe the problem being solved.
    - safety_concerns: any safety concern mentioned or strongly implied; otherwise use "None reported".

    Instructions:
    - The input does NOT contain the original problem statement, only the solution steps.
    - Reconstruct the most likely problem description from the steps.
    - Use only grounded inference from the solution text. Do not invent unrelated details.
    - Prefer the most probable interpretation when multiple are possible.
    - Keep the summary concise, realistic, and usable as a problem description.
    - tools and materials should include all items directly needed by the solution steps.
    - Specific_symptoms should describe the problem as if it were the original issue, based on evidence from the solution.
    - If the duration cannot be inferred, use "Unknown".

    Guardrails:
    - Do not add extra troubleshooting advice.
    - Do not explain your reasoning.
    - Do not mention uncertainty unless the input is genuinely ambiguous.
    - Do not copy the solution verbatim unless needed for exact item names.
    - Do not hallucinate tools, materials, or safety concerns.
    - Output must strictly match the schema.

    Example Summary:
    Category: Carpentry & Woodwork
    Issue: Hanging a mirror on a wall
    Location: Office room (interior wall)
    Duration: Unknown
    Specific symptoms/details:
    - Mirror size: ~24 in x 24 in
    - Mirror weight: ~30 lb
    - Mirror hanging hardware: D-rings, 20 in center-to-center
    - Wall type: interior painted drywall (based on user photo)
    - Desired height: center of mirror at ~66 in from floor (eye level for 5'10")
    - Stud finder: user will purchase a stud finder and prefers mounting into studs
    Safety concerns: Electrical outlets on the wall

    Category: Plumbing
    Issue: Kitchen sink slow drain with active leak at P-trap and food-related clog affecting both sink and dishwasher.
    Location: Kitchen sink in a house in Orange County.
    Duration: Started today, same day as heavy rice cooking.
    Specific symptoms/details:
    - Single basin kitchen sink with garbage disposal.
    - Sink drains very slowly and leaves some standing water in the basin.
    - When garbage disposal is turned on, water churns and can rise back up in the sink.
    - Visible leak under the sink from the bottom area of the P-trap or its connections on PVC piping.
    - Leak continues dripping for a while even after the sink finishes draining.
    - Water has pooled on the bottom of the under-sink cabinet; surface appears wet but not yet swollen or badly damaged.
    - Noticeable rotten food odor from the drain / under-sink area.
    - Dishwasher is tied to this drain line and has had water backing up into it.
    - No other fixtures in the home are showing drainage issues; problem seems localized to this kitchen branch.
    - No previous DIY attempts yet (no plungers, snakes, or chemicals used so far).
    - First time this sink has had a clog or leak that the homeowner is aware of.
    Safety concerns: Active leak under sink that can cause cabinet and possibly structural water damage if sink or dishwasher are used. Odor from decomposing food in drain, but no indication of sewer gas or gas line involvement. User is currently able to avoid using the sink and has been advised to do so, which limits immediate risk.
    Material/equipment info:
    - PVC drain piping with P-trap configuration under the sink.
    - Garbage disposal unit connected to single-basin sink.
    - Dishwasher connected to the same kitchen drain line.

    Steps:
    {steps}

    {format_instructions}
""",
    input_variables=["steps"],
    partial_variables={"format_instructions": parser.get_format_instructions()}
)

chain = prompt | llm | parser


def fetch_tools_materials(steps: str):
    output = chain.invoke({"steps": steps})
    return output

