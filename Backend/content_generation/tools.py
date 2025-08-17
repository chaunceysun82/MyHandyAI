import os
import re
import json
import time
from typing import List, Optional, Dict, Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from serpapi.google_search import GoogleSearch
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

load_dotenv()

class LLMTool(BaseModel):
    name: str=Field(description="Name of the recommended tool or material")
    description: str=Field(description="A small 1-2 lines description for why and how to use the tool for the conditions provided. Also provide the required dimension if needed like radius, height, length, head type, etc")
    price: float=Field(description="Estimated price of the tool or material in Dollar")
    risk_factors: str=Field(description="Possible risk factors of using the tool or material")
    safety_measures: str=Field(description="Safety Measures needed to follow to use the tool or material")
    image_link: Optional[str]=None

class ToolsLLM(BaseModel):
    tools: List[LLMTool] = Field(description="List of Recommended Tools and materials. LLM chooses the length")


class ToolsAgent:
    """Encapsulates the tool recommendation flow you provided.

    Usage example:
        agent = ToolsAgent()
        tools = agent.recommend_tools("Short project summary here")

    The agent will attempt to read API keys from the environment if you don't pass them
    explicitly. You can pass serpapi_api_key or google_api_key to the constructor to override.
    """

    PROMPT_TEXT = """
You are an expert Tools & Materials recommender.

Given the project summary below, return a single JSON object that matches the Pydantic schema exactly (no surrounding text):
{format_instructions}

Rules:
- `tools` should be a JSON array containing the recommended tools. Let the LLM decide how many tools are appropriate.
- For each tool include: name, description (1-2 sentences), price (numeric USD), risk_factors, safety_measures.
- Keep descriptions concise.
- Do not image_link in the LLM output (those will be added by the program).
- Limit recommendations to practical, procurable items.

Project summary:
{summary}
"""

    def __init__(
        self,
        serpapi_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        openai_model: str="gpt-5",
        amazon_affiliate_tag: str="myhandyai-20",
    ) -> None:
        self.serpapi_api_key=serpapi_api_key or os.getenv("SERPAPI_API_KEY")
        self.openai_api_key=openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise RuntimeError("OPENAI API key required")

        self.model = ChatOpenAI(model=openai_model, api_key=self.openai_api_key)
        self.amazon_affiliate_tag = amazon_affiliate_tag

        self.parser = PydanticOutputParser(pydantic_object=ToolsLLM)
        self.prompt = PromptTemplate(
            template=self.PROMPT_TEXT,
            input_variables=["summary"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )

    def _get_image_url(self, query: str, retries: int = 2, pause: float = 0.3) -> Optional[str]:
        """Query SerpAPI Google Images and return the top thumbnail URL (or None).

        Uses the serpapi key provided to the constructor or environment.
        """
        if not self.serpapi_api_key:
            return None

        params = {
            "q": query,
            "engine": "google_images",
            "ijn": "0",
            "api_key": self.serpapi_api_key,
        }

        for attempt in range(1, retries + 1):
            try:
                search = GoogleSearch(params)
                results = search.get_dict()
                images = results.get("images_results") or []
                if images:
                    return images[0].get("thumbnail") or images[0].get("original") or None
                return None
            except Exception:
                if attempt < retries:
                    time.sleep(pause)
                else:
                    return None

    @staticmethod
    def _sanitize_for_amazon(name: str) -> str:
        s = re.sub(r"&", "", name)
        s = re.sub(r"[^A-Za-z0-9\s+\-]", "", s)
        s = s.strip().replace(" ", "+")
        return s

    def _build_chain(self):
        return self.prompt|self.model|self.parser

    def recommend_tools(self, summary: str, include_json: bool = False) -> Dict[str, Any]:
        """Generate tool recommendations for the provided project summary.

        Returns a dict with keys:
            - tools: list of tool dicts (name, description, price, risk_factors, safety_measures, image_link, amazon_link)
            - raw: the raw pydantic-parsed ToolsLLM object
            - json: optional JSON string (if include_json True)

        The function is defensive about missing fields and will attempt to populate image and amazon links.
        """
        chain = self._build_chain()

        try:
            result = chain.invoke({"summary": summary})
        except ValidationError as e:  
            raise
        except Exception as e:
            raise RuntimeError(f"LLM invocation failed: {e}")

        tools_list: List[Dict[str, Any]] = []
        for i in result.tools:
            tool: Dict[str, Any] = {
                "name": i.name,
                "description": i.description,
                "price": i.price,
                "risk_factors": i.risk_factors,
                "safety_measures": i.safety_measures,
                "image_link": None,
                "amazon_link": None,
            }

            try:
                img = self._get_image_url(i.name)
                tool["image_link"] = img
            except Exception:
                tool["image_link"] = None

            safe = self._sanitize_for_amazon(i.name)
            tool["amazon_link"] = f"https://www.amazon.com/s?k={safe}&tag={self.amazon_affiliate_tag}"

            tools_list.append(tool)

        out: Dict[str, Any] = {"tools": tools_list, "raw": result}
        if include_json:
            out["json"] = json.dumps(tools_list, indent=4)

        return out


if __name__ == "__main__":
    example_summary=(
        '''
    The user wants to hang a moderately heavy, decorated mirror sized 60cm x 40cm x 10cm on a drywall in the living room. The mirror has D-rings on the back for hanging. There are studs behind the drywall with 1.5 to 2 inches gap between them. The user has some experience hanging medium sized mirrors but is concerned about the weight and is working alone.
    Since you already provided full details up front, here's a summary:
    You’d like to hang a moderately heavy, decorated mirror (60cm x 40cm x 10cm) with D-rings on the back onto your living room drywall, and there are studs located behind the wall where you want to hang it, spaced about 1.5-2 inches apart. You have some experience hanging medium-sized mirrors, but you’re concerned about safely mounting this heavier mirror on your own. Please let me know if I’ve captured your situation correctly before we move on to solutions!
    '''
    )

    try:
        agent = ToolsAgent()
    except RuntimeError as e:
        print("API keys missing or misconfigured:", e)
        agent = None

    if agent:
        try:
            res = agent.recommend_tools(example_summary, include_json=True)
            print(res["json"])
        except Exception as e:
            print("Failed to generate recommendations:", e)
