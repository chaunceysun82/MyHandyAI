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

# utility functions
def load_prompt(filename):
    """Load prompt from file, removing comment lines starting with #"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, "./prompts", filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        return "".join(line for line in lines if not line.strip().startswith("#"))
    except FileNotFoundError:
        print(f"❌ Could not find prompt file: {path}")
        return f"Error: Could not load {filename}"
    except Exception as e:
        print(f"❌ Error loading prompt file {filename}: {e}")
        return f"Error: Could not load {filename}"
    
def minutes_to_human(minutes: int) -> str:
    """Convert integer minutes to 'X hr Y min' or 'Y min'."""
    if minutes is None:
        return "unknown"
    try:
        m = int(minutes)
    except Exception:
        return str(minutes)
    if m <= 0:
        return "0 min"
    hrs, mins = divmod(m, 60)
    if hrs and mins:
        return f"{hrs} hr {mins} min"
    if hrs:
        return f"{hrs} hr"
    return f"{mins} min"

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

    PROMPT_TEXT = tools_prompt_text + """
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
    ) -> None:
        self.serpapi_api_key = serpapi_api_key or os.getenv("SERPAPI_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise RuntimeError("OPENAI API key required")

        self.model = openai_model
        self.amazon_affiliate_tag = amazon_affiliate_tag
        self.base_url = openai_base_url.rstrip("/")
        self.timeout = timeout
        
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

        Priority:
        1) Responses API: scan `output` for the first completed "message"
        2) Legacy chat-style: `choices[0].message.content` (string or list of text parts)
        3) Top-level "text"
        4) Deep fallback: search any nested "text" fields
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
                            # Preferred keys/types
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

        # Last resort: stringify full response to aid debugging
        return json.dumps(resp)

    def recommend_tools(self, summary: str, include_json: bool = False) -> Dict[str, Any]:
        prompt = self.PROMPT_TEXT.format(summary=summary)

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
        print(resp)
        raw_text = self._extract_output_text(resp)
        print(raw_text)
        
        try:
            parsed_obj = ToolsLLM(**json.loads(raw_text))
            print(parsed_obj)
            
        except Exception as e:
            # Surface what the model returned to help debugging
            raise ValidationError([e], ToolsLLM)  # or raise RuntimeError(f"Schema parse error: {e}\nRAW: {raw_text}")

        tools_list: List[Dict[str, Any]] = []
        for i in parsed_obj.tools:
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

        out: Dict[str, Any] = {"tools": tools_list, "raw": parsed_obj.model_dump()}
        if include_json:
            out["json"] = json.dumps(tools_list, indent=4)

        return {"tools":out["tools"]}


class StepsAgentJSON:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _parse_list_items(self, text: str) -> List[str]:
        """
        Parse text into a list of items, handling:
        - Standard newline lists with bullets/numbers
        - Inline lists like: '1) foo. 2) bar. 3) baz.'
        """
        if not text or not text.strip():
            return []

        try:
            t = text.strip()

            # 1) If it's already multi-line, process those lines
            lines = [ln.strip() for ln in t.split('\n') if ln.strip()]
            is_multiline = len(lines) > 1

            if is_multiline:
                candidates = lines
            else:
                # 2) It's a single line: try to split inline list markers.
                # We find all positions where a list marker appears and slice between them.
                # Marker forms: 1)  1.  a)  A)  -  *  •
                marker_re = re.compile(r'(?:^|\s)((?:\d+|[A-Za-z])[.)]|[-*•])\s+')
                parts = []
                last_end = 0
                matches = list(marker_re.finditer(t))

                if matches:
                    for i, m in enumerate(matches):
                        # start of actual content follows the marker
                        content_start = m.end()
                        # end at next marker or end of string
                        content_end = matches[i + 1].start() if i + 1 < len(matches) else len(t)
                        parts.append(t[content_start:content_end].strip())
                    candidates = [p for p in parts if p]
                else:
                    # No inline markers found — keep as one candidate
                    candidates = [t]

            cleaned_items = []
            for line in candidates:
                if not line:
                    continue
                # Remove a leading marker if present at the beginning of this candidate
                line = re.sub(r'^(?:[-*•]|(?:\d+|[A-Za-z])[.)])\s*', '', line)
                # Collapse extra whitespace
                line = re.sub(r'\s+', ' ', line).strip()
                if len(line) > 1:
                    cleaned_items.append(line)

            # 3) If still nothing parsed, try gentle fallback splitting on semicolons
            #    (avoid splitting on commas; they appear inside sentences/measurements)
            if not cleaned_items and t:
                for item in re.split(r'\s*;\s*', t):
                    item = item.strip()
                    if item:
                        item = re.sub(r'^(?:[-*•]|(?:\d+|[A-Za-z])[.)])\s*', '', item).strip()
                        if len(item) > 1:
                            cleaned_items.append(item)

            return cleaned_items

        except Exception as e:
            print(f"Warning: Error parsing list items: {e}")
            return [text.strip()] if text and text.strip() else []

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
        enhanced_context = summary

        tools_context = "\n\nTools Context:\n"

        if tools:
            for tool in tools["tools"]:
                tools_context += tool["name"]+"\n"
                tools_context += tool["description"]+"\n"
                tools_context += tool["risk_factors"]+"\n"
                tools_context += tool["safety_measures"]+"\n"
            tools_context +="\n"

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
        
        # Use the prompt from text file
        base_prompt = steps_prompt_text

        messages = [
            {"role": "system", "content": base_prompt},
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
                "tips": step.tips,
                "completed":False
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
        
        if "tools" in tools_data:
            total_cost = sum(tool["price"] for tool in tools_data["tools"])
        else:
            total_cost = 0
            
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
            },
            "total_estimated_time": {
                "minutes": total_time,
                "human_readable": minutes_to_human(total_time)
            },
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



