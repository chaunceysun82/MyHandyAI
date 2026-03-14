from pydantic import BaseModel, Field
from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class FetchToolsMaterialsModel(BaseModel):
    tools: List[str]
    materials: List[str]


parser = JsonOutputParser()

llm = ChatOpenAI(
    model="gpt-5-nano",
    api_key=OPENAI_API_KEY,
)

prompt = PromptTemplate(
    template="""
Given the following steps, extract the tools and materials needed to complete the steps. 
Tools are reusable instruments used to shape, cut, or manipulate materials, such as hammers or saws, 
while materials are the consumable substances or ingredients that become part of the final product, such as wood or paint.
But dont include any items that cannot be bought like water, electricity, air, etc. Dont add anything as optional.


Steps:
{steps}

Return JSON only in this format:

{{
 "tools": [],
 "materials": []
}}
""",
    input_variables=["steps"]
)

chain = prompt | llm | parser


def fetch_tools_materials(steps: str):
    output = chain.invoke({"steps": steps})

    data = FetchToolsMaterialsModel(**output)

    return data.tools, data.materials
