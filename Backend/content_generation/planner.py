import os
import re
import json
import requests
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError
from fastapi import HTTPException
from serpapi.google_search import GoogleSearch
from dotenv import load_dotenv

load_dotenv()

# Import utility functions from agents.py
from chatbot.agents import load_prompt, clean_and_parse_json, minutes_to_human, extract_number_from_maybe_price

tools_prompt_text = load_prompt("generation_tools_prompt.txt")
steps_prompt_text = load_prompt("generation_steps_prompt.txt")
fallback_tools_text = load_prompt("generation_fallback_tools_prompt.txt")


class Step(BaseModel):
    step_no: int = Field(..., alias="Step No.")
    step_title: str = Field(..., alias="Step Title")
    time: int = Field(..., alias="Time")          
    time_text: str = Field(..., alias="TimeText") 
    instructions: List[str] = Field(..., alias="Instructions")
    tools_needed: List[str] = Field(default=[], alias="Tools Needed")
    safety_warnings: List[str] = Field(default=[], alias="Safety Warnings")
    tips: List[str] = Field(default=[], alias="Tips")


class StepsPlan(BaseModel):
    total_steps: int
    estimated_time: int = 0   
    steps: List[Step]


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

    PROMPT_TEXT = """You are an expert Tools & Materials recommender.

Given the project summary below, return ONLY a JSON object (or array — see instructions) that matches the schema exactly.
Rules:
- `tools` is an array of recommended tools/materials (LLM decides length).
- Each tool must include: name, description (1–2 sentences), price (numeric USD), risk_factors, safety_measures.
- Keep descriptions concise and practical. Do NOT include image links (those are added later).
- Limit to procurable, realistic items.

Project summary:
{summary}
"""

    def __init__(
        self,
        serpapi_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        openai_model: str = "gpt-5-mini",
        amazon_affiliate_tag: str = "myhandyai-20",
        openai_base_url: str = "https://api.openai.com/v1",
        timeout: int = 90,
        new_summary: Optional[str] = None,
        matched_summary: Optional[str] = None,
        matched_tools: Optional[Any] = None,
        matched_steps: Optional[Any] = None,
    ) -> None:
        self.serpapi_api_key = serpapi_api_key or os.getenv("SERPAPI_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise RuntimeError("OPENAI API key required")

        self.model = openai_model
        self.amazon_affiliate_tag = amazon_affiliate_tag
        self.base_url = openai_base_url.rstrip("/")
        self.timeout = timeout
        self.new_summary = new_summary
        self.matched_summary = matched_summary
        self.matched_tools = matched_tools
        self.matched_steps = matched_steps

        # Tool item schema used for validation/normalization (used programmatically below)
        self._tool_required_keys = {"name", "description", "price", "risk_factors", "safety_measures"}

        # JSON schema that accepts either:
        #  - an object with "tools": [ ... ]
        #  - OR a top-level array [ {...}, {...} ]
        # (We won't rely on external jsonschema validation library here, but keep this for reference.)
        self._schema = {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "tools": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "name": {"type": "string"},
                                        "description": {"type": "string"},
                                        "price": {"type": "number"},
                                        "risk_factors": {"type": "string"},
                                        "safety_measures": {"type": "string"},
                                    },
                                    "required": [
                                        "name",
                                        "description",
                                        "price",
                                        "risk_factors",
                                        "safety_measures",
                                    ],
                                },
                            }
                        },
                        "required": ["tools"],
                    }

    def _get_image_url(self, query: str, retries: int = 2, pause: float = 0.3) -> Optional[str]:
        """Query SerpAPI Google Images and return the top thumbnail URL (or None)."""
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
                from serpapi import GoogleSearch  # local import to avoid hard dependency unless used
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

    def _post_openai(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/responses"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
        }
        r = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        if r.status_code >= 400:
            raise RuntimeError(f"OpenAI API error {r.status_code}: {r.text}")
        return r.json()

    @staticmethod
    def _extract_output_text(resp: Dict[str, Any]) -> str:
        """
        Robustly extract text from an OpenAI Responses API payload.
        """
        # 1) Newer Responses API shape
        try:
            output = resp.get("output")
            if isinstance(output, list):
                for part in output:
                    if part.get("type") == "message" and part.get("status") in (None, "completed"):
                        content = part.get("content") or []
                        texts = []
                        for c in content:
                            if not isinstance(c, dict):
                                continue
                            if c.get("type") in ("output_text", "text") and isinstance(c.get("text"), str):
                                texts.append(c["text"])
                            elif isinstance(c.get("text"), str):
                                texts.append(c["text"])
                        if texts:
                            return "".join(texts).strip()
        except Exception:
            pass

        # 2) Legacy/alternate: chat-style responses
        try:
            choice = (resp.get("choices") or [{}])[0]
            msg = choice.get("message") or {}
            content = msg.get("content")
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                texts = [d.get("text") for d in content if isinstance(d, dict) and isinstance(d.get("text"), str)]
                if texts:
                    return "".join(texts).strip()
        except Exception:
            pass

        # 3) Sometimes a plain top-level "text"
        if isinstance(resp.get("text"), str):
            return resp["text"].strip()

        # 4) Deep fallback: walk structure for any "text" strings
        def _walk_text(x):
            if isinstance(x, dict):
                for k, v in x.items():
                    if k == "text" and isinstance(v, str):
                        yield v
                    else:
                        yield from _walk_text(v)
            elif isinstance(x, list):
                for i in x:
                    yield from _walk_text(i)

        texts = list(_walk_text(resp))
        if texts:
            return "".join(texts).strip()

        return json.dumps(resp)

    def _normalize_and_validate_tools(self, parsed_json: Any) -> List[Dict[str, Any]]:
        """
        Accept either:
          - a list of tool dicts
          - or an object with {"tools": [tool dicts]}
        Return a normalized list of tool dicts and validate required keys/types.
        """
        if isinstance(parsed_json, list):
            tools = parsed_json
        elif isinstance(parsed_json, dict) and "tools" in parsed_json and isinstance(parsed_json["tools"], list):
            tools = parsed_json["tools"]
        else:
            raise RuntimeError("Model output JSON must be either an array of tools or an object with a 'tools' array.")

        if not isinstance(tools, list):
            raise RuntimeError("Parsed tools is not a list.")

        normalized = []
        for idx, t in enumerate(tools, start=1):
            if not isinstance(t, dict):
                raise RuntimeError(f"Tool at index {idx} is not an object.")
            missing = self._tool_required_keys - set(t.keys())
            if missing:
                raise RuntimeError(f"Tool at index {idx} is missing required fields: {missing}")
            # Basic type checks
            if not isinstance(t["name"], str):
                raise RuntimeError(f"Tool {idx} 'name' must be a string.")
            if not isinstance(t["description"], str):
                raise RuntimeError(f"Tool {idx} 'description' must be a string.")
            # price should be numeric (int/float) — try to coerce if string numeric
            price = t["price"]
            if isinstance(price, str):
                try:
                    price = float(price)
                except Exception:
                    raise RuntimeError(f"Tool {idx} 'price' must be numeric.")
            elif not isinstance(price, (int, float)):
                raise RuntimeError(f"Tool {idx} 'price' must be numeric.")
            # risk_factors and safety_measures strings
            if not isinstance(t["risk_factors"], str):
                raise RuntimeError(f"Tool {idx} 'risk_factors' must be a string.")
            if not isinstance(t["safety_measures"], str):
                raise RuntimeError(f"Tool {idx} 'safety_measures' must be a string.")
            normalized.append({
                "name": t["name"].strip(),
                "description": t["description"].strip(),
                "price": float(price),
                "risk_factors": t["risk_factors"].strip(),
                "safety_measures": t["safety_measures"].strip(),
            })
        return normalized

    def recommend_tools(self, summary: Optional[str] = None, include_json: bool = False) -> Dict[str, Any]:
        # Use provided summary argument first; fall back to constructor's new_summary if not provided
        summary_to_use = summary if summary is not None else (self.new_summary or "")
        prompt = self.PROMPT_TEXT.format(summary=summary_to_use)

        # If matched_tools or matched_summary exists, instruct the model to modify them
        matched_tools_text = None
        if self.matched_tools:
            try:
                matched_tools_text = json.dumps(self.matched_tools, indent=2)
            except Exception:
                matched_tools_text = str(self.matched_tools)

            # If user provided matched_tools as a list-of-dicts (the new format):
            prompt += (
                "\n\nThe following is an EXISTING list of tools (from a matched project with high similarity). "
                "Modify or adapt these tool objects to suit the new project summary above. Keep the exact field names "
                "(name, description, price, risk_factors, safety_measures). Return ONLY a JSON ARRAY (top-level array) "
                "of tool objects in the same format as provided (i.e., [{name:..., description:..., price:..., ...}, ...]).\n\n"
                f"Existing tools:\n{matched_tools_text}\n"
            )
        elif self.matched_summary:
            # If only matched_summary is present but not matched_tools, include it as context (do not force array output)
            prompt += (
                "\n\nContext: The following MATCHED SUMMARY was highly similar to the new project. Use it as a reference when adapting tools.\n\n"
                f"Matched Summary:\n{self.matched_summary}\n"
            )

        # Always include matched_summary if present (even when matched_tools is present)
        if self.matched_summary and not self.matched_tools:
            prompt += (
                "\n\nContext: The following MATCHED SUMMARY was highly similar to the new project. Use it as a reference when adapting tools.\n\n"
                f"Matched Summary:\n{self.matched_summary}\n"
            )

        payload = {
            "model": self.model,
            "input": [
                {"role": "system", "content": "You return ONLY JSON that matches the provided schema."},
                {"role": "user", "content": prompt},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "ToolsLLM",
                    "strict": True,
                    "schema": self._schema,
                },
            }
        }

        resp = self._post_openai(payload)
        raw_text = self._extract_output_text(resp)

        # Attempt to parse JSON from model output (expecting either array or {"tools": [...]})
        try:
            parsed = json.loads(raw_text)
        except Exception as e:
            # Last-resort: try to locate the first JSON array/object in the text
            try:
                import re as _re
                m = _re.search(r"(\[.*\]|\{.*\})", raw_text, _re.S)
                if m:
                    parsed = json.loads(m.group(1))
                else:
                    raise RuntimeError(f"Failed to parse JSON from model output. RAW: {raw_text}") from e
            except Exception as e2:
                raise RuntimeError(f"Failed to parse JSON from model output. RAW: {raw_text}") from e2

        # Normalize and validate into list of tool dicts
        normalized_tools = self._normalize_and_validate_tools(parsed)

        # Build output tools_list (and augment with image_link and amazon link)
        tools_list: List[Dict[str, Any]] = []
        for i in normalized_tools:
            tool: Dict[str, Any] = {
                "name": i["name"],
                "description": i["description"],
                "price": i["price"],
                "risk_factors": i["risk_factors"],
                "safety_measures": i["safety_measures"],
                "image_link": None,
                "amazon_link": None,
            }

            # Try to fetch an image (best-effort)
            try:
                img = self._get_image_url(i["name"])
                tool["image_link"] = img
            except Exception:
                tool["image_link"] = None

            safe = self._sanitize_for_amazon(i["name"])
            tool["amazon_link"] = f"https://www.amazon.com/s?k={safe}&tag={self.amazon_affiliate_tag}"

            tools_list.append(tool)

        out: Dict[str, Any] = {"tools": tools_list, "raw": parsed}
        if include_json:
            out["json"] = json.dumps(tools_list, indent=4)
        return out


class StepsAgentJSON:
    def __init__(self, new_summary: Optional[str] = None, matched_summary: Optional[str] = None, matched_tools: Optional[Any] = None, matched_steps: Optional[Any] = None):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        self.new_summary = new_summary
        self.matched_summary = matched_summary
        self.matched_tools = matched_tools
        self.matched_steps = matched_steps

    # --- New helper: normalize the various possible tools input shapes ---
    def _normalize_tools_input(self, tools_input: Any) -> List[Dict[str, Any]]:
        """
        Accepts:
          - None
          - A dict from ToolsAgent output: {"tools": [...], "raw": ..., "json": ...}
          - A dict with "tools" key only
          - A raw list of tool dicts: [{name:..., description:..., price:...}, ...]
        Returns a list of tool dicts with guaranteed keys (some may be empty strings).
        """
        if not tools_input:
            return []

        # If it's a dict and has a "tools" key, prefer that
        if isinstance(tools_input, dict):
            if "tools" in tools_input and isinstance(tools_input["tools"], list):
                tools_list = tools_input["tools"]
            else:
                # Maybe the user passed the raw ToolsAgent 'raw' itself or similar; try to interpret
                # If dict looks like a single tool, wrap it
                # If dict looks like {'name':..., ...} assume single tool
                if all(k in tools_input for k in ("name", "description")):
                    tools_list = [tools_input]
                else:
                    # Fallback: try to find any list value in dict that looks like tools
                    found = None
                    for v in tools_input.values():
                        if isinstance(v, list):
                            # check if list items look like tools
                            candidate = v
                            if candidate and isinstance(candidate[0], dict) and "name" in candidate[0]:
                                found = candidate
                                break
                    tools_list = found or []
        elif isinstance(tools_input, list):
            tools_list = tools_input
        else:
            # Unknown type; return empty list
            return []

        normalized = []
        for idx, t in enumerate(tools_list, start=1):
            if not isinstance(t, dict):
                continue
            name = str(t.get("name") or "").strip()
            description = str(t.get("description") or "").strip()
            # price can be numeric or string — coerce to float if possible, else 0.0
            price_raw = t.get("price", 0)
            try:
                price = float(price_raw)
            except Exception:
                # try to extract numeric part from string
                try:
                    price = float(re.sub(r"[^\d\.]", "", str(price_raw) or "0") or 0)
                except Exception:
                    price = 0.0
            risk_factors = str(t.get("risk_factors") or "").strip()
            safety_measures = str(t.get("safety_measures") or "").strip()
            image_link = t.get("image_link") or t.get("image") or None
            amazon_link = t.get("amazon_link") or t.get("amazon") or None

            normalized.append({
                "name": name,
                "description": description,
                "price": price,
                "risk_factors": risk_factors,
                "safety_measures": safety_measures,
                "image_link": image_link,
                "amazon_link": amazon_link
            })
        return normalized

    def _parse_list_items(self, text: str) -> List[str]:
        """
        Parse text into a list of items, handling numbered lists and bullet points.
        More robust parsing with better error handling.
        """
        if not text or not text.strip():
            return []
        
        try:
            # Split by newlines and clean up
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            # Remove common list markers and clean up
            cleaned_items = []
            for line in lines:
                if not line:
                    continue
                    
                # Remove numbered list markers (1., 2., etc.)
                line = re.sub(r'^\d+\.\s*', '', line)
                # Remove bullet points
                line = re.sub(r'^[-•*]\s*', '', line)
                # Remove other common markers
                line = re.sub(r'^[a-z]\)\s*', '', line, flags=re.IGNORECASE)
                # Remove extra whitespace
                line = re.sub(r'\s+', ' ', line).strip()
                
                if line and len(line) > 1:  # Ensure meaningful content
                    cleaned_items.append(line)
            
            # If no items were parsed, try alternative parsing
            if not cleaned_items and text.strip():
                # Try splitting by common separators
                alt_items = re.split(r'[;,]|\band\b', text, flags=re.IGNORECASE)
                for item in alt_items:
                    item = item.strip()
                    if item and len(item) > 1:
                        cleaned_items.append(item)
            
            return cleaned_items
            
        except Exception as e:
            print(f"Warning: Error parsing list items: {str(e)}")
            # Fallback: return the original text as a single item if it's not empty
            if text.strip():
                return [text.strip()]
            return []

    def _parse_time_to_minutes(self, text: str) -> int:
        """
        Parse human time expressions into integer minutes.
        """
        if not text:
            return 0

        s = text.lower().strip()
        s = s.replace("half hour", "30 minutes")
        s = s.replace("half an hour", "30 minutes")
        s = s.replace("an hour", "1 hour")

        def value_to_minutes(value: float, unit: str) -> float:
            unit = unit.lower()
            if unit.startswith("h"):
                return value * 60.0
            return value

        range_match = re.search(r"(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)(?:\s*(hours?|hrs?|h|minutes?|mins?|m))?", s)
        if range_match:
            a = float(range_match.group(1))
            b = float(range_match.group(2))
            unit = (range_match.group(3) or "").strip()
            if unit:
                a = value_to_minutes(a, unit)
                b = value_to_minutes(b, unit)
            return int(round((a + b) / 2.0))

        composite_match = re.search(r"(?:(\d+(?:\.\d+)?)\s*(hours?|hrs?|h))?.*?(?:(\d+(?:\.\d+)?)\s*(minutes?|mins?|m))?", s)
        if composite_match and (composite_match.group(1) or composite_match.group(3)):
            hours = float(composite_match.group(1)) if composite_match.group(1) else 0.0
            minutes = float(composite_match.group(3)) if composite_match.group(3) else 0.0
            total = int(round(hours * 60.0 + minutes))
            return total

        dec_hr = re.search(r"(\d+(?:\.\d+)?)\s*(hours?|hrs?|h)\b", s)
        if dec_hr:
            hrs = float(dec_hr.group(1))
            return int(round(hrs * 60.0))

        min_match = re.search(r"(\d+(?:\.\d+)?)\s*(minutes?|mins?|m)\b", s)
        if min_match:
            mins = float(min_match.group(1))
            return int(round(mins))

        bare_num = re.search(r"^(\d+(?:\.\d+)?)\s*$", s)
        if bare_num:
            return int(round(float(bare_num.group(1))))

        any_num = re.search(r"(\d+(?:\.\d+)?)", s)
        if any_num:
            return int(round(float(any_num.group(1))))

        return 0

    def _parse_steps_text(self, text: str) -> StepsPlan:
        """Parse step-by-step plan text into structured data with robust error handling"""
        if not text or not text.strip():
            raise ValueError("Empty or invalid text provided for parsing")
        
        # Parse header information
        total_steps = None
        estimated_time_minutes = 0

        # Look for total steps in header
        m_total = re.search(r"Total\s*Steps\s*[:\-]\s*(\d+)", text, re.IGNORECASE)
        if m_total:
            try:
                total_steps = int(m_total.group(1))
            except ValueError:
                print(f"Warning: Could not parse total steps: {m_total.group(1)}")

        # Look for estimated time in header
        m_est = re.search(r"Estimated\s*Time\s*[:\-]\s*(.+)", text, re.IGNORECASE)
        if m_est:
            est_text = m_est.group(1).strip()
            estimated_time_minutes = self._parse_time_to_minutes(est_text)

        # Parse step blocks with more flexible regex
        step_block_re = re.compile(
            r"Step\s*No\.?\s*:\s*(?P<no>\d+)\s*[\r\n]+"
            r"Step\s*Title\s*:\s*(?P<title>.+?)\s*[\r\n]+"
            r"Time\s*:\s*(?P<time>.+?)\s*[\r\n]+"
            r"Instructions\s*:\s*(?P<instructions>.+?)\s*[\r\n]+"
            r"Tools\s*Needed\s*:\s*(?P<tools>.+?)\s*[\r\n]+"
            r"Safety\s*Warnings\s*:\s*(?P<safety>.+?)\s*[\r\n]+"
            r"Tips\s*:\s*(?P<tips>.+?)(?=(?:\n\s*\n)|\Z)",
            re.IGNORECASE | re.DOTALL,
        )

        steps = []
        for m in step_block_re.finditer(text):
            try:
                # Parse and validate step number
                no = int(m.group("no").strip())
                if no <= 0:
                    print(f"Warning: Invalid step number {no}, skipping")
                    continue
                
                # Parse and validate title
                title = m.group("title").strip()
                if not title:
                    print(f"Warning: Empty title for step {no}, skipping")
                    continue
                
                # Parse and validate time
                time_text = m.group("time").strip()
                time_mins = self._parse_time_to_minutes(time_text)
                if time_mins <= 0:
                    print(f"Warning: Invalid time for step {no}: {time_text}")
                    time_mins = 10  # Default to 10 minutes
                
                # Parse the new fields and convert them to lists
                instructions_text = m.group("instructions").strip()
                tools_text = m.group("tools").strip()
                safety_text = m.group("safety").strip()
                tips_text = m.group("tips").strip()
                
                # Convert text to lists using the helper method
                instructions = self._parse_list_items(instructions_text)
                tools_needed = self._parse_list_items(tools_text)
                safety_warnings = self._parse_list_items(safety_text)
                tips = self._parse_list_items(tips_text)
                
                # Validate that instructions are not empty
                if not instructions:
                    print(f"Warning: No instructions found for step {no}, using title as instruction")
                    instructions = [title]
                
                steps.append(Step(**{
                    "Step No.": no,
                    "Step Title": title,
                    "Time": time_mins,
                    "TimeText": time_text,
                    "Instructions": instructions,
                    "Tools Needed": tools_needed,
                    "Safety Warnings": safety_warnings,
                    "Tips": tips
                }))
                
            except Exception as e:
                print(f"Warning: Error parsing step {m.group('no') if m.group('no') else 'unknown'}: {str(e)}")
                continue

        # Validate that we found at least one step
        if not steps:
            raise ValueError("No valid steps could be parsed from the text")
        
        # Set defaults if not found in header
        if total_steps is None:
            total_steps = len(steps)
        
        if estimated_time_minutes == 0:
            estimated_time_minutes = sum(s.time for s in steps)
        
        # Validate final data
        if total_steps != len(steps):
            print(f"Warning: Header shows {total_steps} steps but parsed {len(steps)} steps")
            total_steps = len(steps)
        
        if estimated_time_minutes <= 0:
            print(f"Warning: Invalid total time {estimated_time_minutes}, using sum of step times")
            estimated_time_minutes = sum(s.time for s in steps)

        return StepsPlan(total_steps=total_steps, estimated_time=estimated_time_minutes, steps=steps)

    def _assess_complexity(self, total_time: int, total_steps: int) -> str:
        """Assess the complexity level based on time and steps"""
        if total_time <= 60 and total_steps <= 3:
            return "Easy"
        elif total_time <= 180 and total_steps <= 5:
            return "Moderate"
        elif total_time <= 360 and total_steps <= 8:
            return "Challenging"
        else:
            return "Complex"

    def generate(self, tools, summary: str, user_answers: Dict[int, str] = None, questions: List[str] = None) -> Dict[str, Any]:
        """
        Generate step-by-step plan in JSON format.
        Returns a dictionary with steps array and time estimation.
        """
        # Prepare enhanced context including user answers and handling skipped questions
        enhanced_context = summary if summary else (self.new_summary or "")

        # Normalize tools input (accept ToolsAgent output or raw list/dict)
        normalized_tools = self._normalize_tools_input(tools)

        # Build tools context robustly
        tools_context = "\n\nTools Context:\n"
        if normalized_tools:
            for t in normalized_tools:
                tools_context += f"Name: {t.get('name','')}\n"
                tools_context += f"Description: {t.get('description','')}\n"
                tools_context += f"Price (USD): {t.get('price',0.0)}\n"
                tools_context += f"Risk Factors: {t.get('risk_factors','')}\n"
                tools_context += f"Safety Measures: {t.get('safety_measures','')}\n"
                # include any helpful links if present
                if t.get("image_link"):
                    tools_context += f"Image: {t.get('image_link')}\n"
                if t.get("amazon_link"):
                    tools_context += f"Buy Link: {t.get('amazon_link')}\n"
                tools_context += "\n"
        else:
            tools_context += "No specific tools provided.\n"

        if self.matched_steps:
            try:
                matched_steps_text = json.dumps(self.matched_steps, indent=2)
            except Exception:
                matched_steps_text = str(self.matched_steps)


            enhanced_context += "\n\nMatched project summary and steps (adapt these to the new summary):\n"
            if self.matched_summary:
                enhanced_context += f"Matched Summary:\n{self.matched_summary}\n\n"
            enhanced_context += f"Matched Steps:\n{matched_steps_text}\n\n"
            enhanced_context += "When adapting, preserve the same structure and output format the system expects (Step No., Step Title, Time, Instructions, Tools Needed, Safety Warnings, Tips).\n"

        if user_answers and questions:
            # Add user answers to the context
            answers_context = "\n\nUser's Answers to Questions:\n"
            skipped_questions = []
            
            for k, answer in (user_answers or {}).items():
                try:
                    idx = int(k)
                except Exception:
                    idx = k
                if isinstance(idx, int) and idx < len(questions):
                    question = questions[idx]
                    if answer.lower() == "skipped":
                        skipped_questions.append((idx, question))
                        answers_context += f"Q{idx+1}: {question} - SKIPPED (will consider all possibilities)\n"
                    else:
                        answers_context += f"Q{idx+1}: {question} - {answer}\n"
            
            # Add instructions for handling skipped questions
            if skipped_questions:
                answers_context += "\n\nFor skipped questions, consider all reasonable possibilities and provide steps that cover different scenarios.\n"
            
            enhanced_context += answers_context
            enhanced_context += tools_context
        else:
            enhanced_context += tools_context
        
        # Use the prompt from text file
        base_prompt = steps_prompt_text

        adaptation_instructions = ""
        if self.matched_steps:
            try:
                matched_steps_text = json.dumps(self.matched_steps, indent=2)
            except Exception:
                matched_steps_text = str(self.matched_steps)

            adaptation_instructions += (
                "\n\nADAPTATION INSTRUCTIONS:\n"
                "The user provided an EXISTING set of steps from a matched project below. Modify and adapt those steps so they match the NEW project summary and context above. "
                "Strictly preserve the exact output structure and field names expected by this system (Step No., Step Title, Time, Instructions, Tools Needed, Safety Warnings, Tips). "
                "Update time estimates, instructions, tools needed, safety warnings, and tips where appropriate. If a step is no longer relevant, adjust or remove it, but ensure the final output lists steps numbered sequentially starting at 1. "
                "Also if some steps are common to both projects, you can keep them with minor adjustments. "
                "Overall, ensure the final plan is coherent, practical, and tailored to the new project summary and any user answers provided with atleast 6 steps for the whole summary. "
                "Maintain practical ordering and clarity. Return the plan as plain text in the exact format.\n\n"
                f"Existing matched steps:\n{matched_steps_text}\n"
            )

        if self.matched_summary:
            adaptation_instructions += f"\n\nMatched Summary:\n{self.matched_summary}\n"

        if self.matched_tools:
            try:
                matched_tools_text = json.dumps(self.matched_tools, indent=2)
            except Exception:
                matched_tools_text = str(self.matched_tools)
            adaptation_instructions += f"\n\nMatched Tools (for reference):\n{matched_tools_text}\n"

        # Merge the base prompt with adaptation instructions so the system role contains both.
        system_content = base_prompt + adaptation_instructions

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": enhanced_context + "\n\nReturn the plan as plain text in the exact format."}
        ]

        try:
            # Using the same API structure as agents.py
            payload = {
                "model": "gpt-5-mini",
                "messages": messages,
                "max_completion_tokens": 2500,
                "reasoning_effort": "low"
            }
            
            r = requests.post(self.api_url, headers=self.headers, json=payload)
            if r.status_code == 200:
                content = r.json()["choices"][0]["message"]["content"].strip()
                print(f"✅ LLM Response received, length: {len(content)} characters")
                
                try:
                    steps_plan = self._parse_steps_text(content)
                    print(f"✅ Successfully parsed {len(steps_plan.steps)} steps")
                    return self._convert_to_json_format(steps_plan)
                except ValueError as ve:
                    print(f"❌ Parsing error: {str(ve)}")
                    raise HTTPException(status_code=500, detail=f"Failed to parse LLM response: {str(ve)}")
                except Exception as pe:
                    print(f"❌ Unexpected parsing error: {str(pe)}")
                    raise HTTPException(status_code=500, detail=f"Unexpected error during parsing: {str(pe)}")
            else:
                print(f"❌ API Error {r.status_code}")
                print(f"Response: {r.text}")
                raise HTTPException(status_code=r.status_code, detail=f"LLM API error: {r.status_code}")
                
        except requests.exceptions.Timeout:
            print("❌ Request timeout")
            raise HTTPException(status_code=500, detail="LLM request timed out")
        except requests.exceptions.RequestException as re:
            print(f"❌ Request error: {str(re)}")
            raise HTTPException(status_code=500, detail=f"LLM request failed: {str(re)}")
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    def _convert_to_json_format(self, steps_plan: StepsPlan) -> Dict[str, Any]:
        """Convert StepsPlan to JSON format"""
        steps_json = []
        for step in steps_plan.steps:
            steps_json.append({
                "order": step.step_no,
                "title": step.step_title,
                "est_time_min": step.time,
                "time_text": step.time_text,
                "instructions": step.instructions,
                "status": "pending",
                "tools_needed": step.tools_needed,
                "safety_warnings": step.safety_warnings,
                "tips": step.tips
            })
        
        # Generate project summary card
        project_summary = {
            "step_count": f"Step {1}/{steps_plan.total_steps}",
            "estimated_duration": minutes_to_human(steps_plan.estimated_time),
            "status": "Ongoing",
            "complexity": self._assess_complexity(steps_plan.estimated_time, steps_plan.total_steps)
        }
        
        return {
            "steps": steps_json,
            "total_est_time_min": steps_plan.estimated_time,
            "total_steps": steps_plan.total_steps,
            "notes": f"Total estimated time: {minutes_to_human(steps_plan.estimated_time)}",
            "project_status": "pending",
            "current_step": 1,
            "progress_percentage": 0,
            "estimated_completion": "TBD",
            "project_summary": project_summary
        }
class EstimationAgent:
    """Agent for generating cost and time estimations"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate_estimation(self, tools_data: Dict[str, Any], steps_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive estimation including cost and time breakdown.
        Returns JSON with cost estimates, time estimates, and step-by-step breakdown.
        """
        total_cost = tools_data.get("total_cost", 0.0)
        total_time = steps_data.get("total_est_time_min", 0)
        
        # Generate step-by-step time breakdown
        step_breakdown = []
        for step in steps_data.get("steps", []):
            step_breakdown.append({
                "step_number": step.get("order", 0),
                "step_title": step.get("title", ""),
                "estimated_time_min": step.get("est_time_min", 0),
                "time_text": step.get("time_text", "")
            })
        
        estimation_data = {
            "total_estimated_cost": {
                "amount": total_cost,
                "currency": "USD",
                "available": tools_data.get("cost_available", False)
            },
            "total_estimated_time": {
                "minutes": total_time,
                "human_readable": minutes_to_human(total_time)
            },
            "step_breakdown": step_breakdown,
            "summary": {
                "total_steps": steps_data.get("total_steps", 0),
                "tools_required": len(tools_data.get("tools", [])),
                "complexity_level": self._assess_complexity(total_time, len(step_breakdown))
            }
        }
        
        return estimation_data
    
    def _assess_complexity(self, total_time: int, total_steps: int) -> str:
        """Assess the complexity level based on time and steps"""
        if total_time <= 60 and total_steps <= 3:
            return "Easy"
        elif total_time <= 180 and total_steps <= 5:
            return "Moderate"
        elif total_time <= 360 and total_steps <= 8:
            return "Challenging"
        else:
            return "Complex"


class ContentPlanner:
    """Main class that coordinates all content generation agents"""
    
    def __init__(self):
        self.tools_agent = ToolsAgent()
        self.steps_agent = StepsAgentJSON()
        self.estimation_agent = EstimationAgent()
    
    def generate_complete_plan(self, summary: str, user_answers: Dict[int, str] = None, questions: List[str] = None) -> Dict[str, Any]:
        """
        Generate complete DIY plan including tools, steps, and estimations.
        Returns comprehensive JSON with all planning information.
        """
        try:
            # Generate tools and materials
            tools_data = self.tools_agent.recommend_tools(summary, include_json=True)
            
            # Generate step-by-step plan
            steps_data = self.steps_agent.generate(summary, user_answers, questions)
            
            # Generate estimations
            estimation_data = self.estimation_agent.generate_estimation(tools_data, steps_data)
            
            # Combine all data into comprehensive plan
            complete_plan = {
                "project_summary": summary,
                "tools_and_materials": tools_data,
                "step_by_step_plan": steps_data,
                "estimations": estimation_data,
                "metadata": {
                    "generated_at": "2024-01-01T00:00:00Z",  # You can add actual timestamp
                    "version": "1.0",
                    "model_used": "gpt-5"
                }
            }
            
            return complete_plan
            
        except Exception as e:
            return {
                "error": f"Failed to generate plan: {str(e)}",
                "project_summary": summary
            }



