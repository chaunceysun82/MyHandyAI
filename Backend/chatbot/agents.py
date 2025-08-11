# agents.py  (fixed & defensive)
import os
import requests
from typing import List, Dict, Any, Optional, Iterable
from dotenv import load_dotenv
import base64
from PIL import Image
import re
import json
from serpapi.google_search import GoogleSearch
from typing import List, Optional
from pydantic import BaseModel, Field

load_dotenv()

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

def clean_and_parse_json(raw_str: str):
    """
    Cleans code fences (```json ... ```) from a string and parses it as JSON.
    """
    if raw_str is None:
        raise ValueError("No input string")
    cleaned = re.sub(r"```(?:json)?\s*", "", raw_str.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")


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


def extract_number_from_maybe_price(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        for k in ("price", "extracted_price", "amount", "value"):
            if k in value:
                return extract_number_from_maybe_price(value[k])
        for v in value.values():
            n = extract_number_from_maybe_price(v)
            if n is not None:
                return n
        return None
    s = str(value).strip()
    if s == "":
        return None
    m = re.search(r"[-+]?\d{1,3}(?:[,\d{3}]*\d)?(?:\.\d+)?", s.replace(",", ""))
    if m:
        try:
            return float(m.group(0))
        except Exception:
            return None
    return None

def estimation(details: dict) -> str:

    cost = details.get("cost", details.get("Cost", "N/A"))
    if isinstance(cost, (dict, list)):
        
        extracted = extract_number_from_maybe_price(cost)
        cost = extracted if extracted is not None else str(cost)
    
    total_time = details.get("time", details.get("estimated_time", details.get("Time", "N/A")))

    try:
        total_time_int = int(total_time)
    except Exception:
       
        m = re.search(r"(\d+)", str(total_time or ""))
        total_time_int = int(m.group(1)) if m else 0

    lines = []
    lines.append(f"TOTAL ESTIMATED COST (TOOLS & MATERIALS) : $ {cost}\n")
    lines.append(f"TOTAL ESTIMATED TIME (in minutes) : {total_time_int} minutes\n")
    lines.append("")

    for i, step in enumerate(details.get("steps", []), start=1):
        time_text = (
            step.get("time_text")
            or step.get("Time")
            or step.get("TimeText")
            or (str(step.get("Time_val")) + " min" if step.get("Time_val") is not None else None)
            or ""
        )
        lines.append(f"STEP {i} : {time_text}\n")

    result = "\n".join(lines)
    return result


def extract_lines(plan: dict):
   
    lines = []
    
    total = plan.get("steps_no", len(plan.get("steps", [])))
    est = plan.get("time", 0)
    try:
        est_int = int(est)
    except Exception:
        m = re.search(r"(\d+)", str(est or ""))
        est_int = int(m.group(1)) if m else 0

    lines.append(f"Total steps : {total}\n")
    lines.append(f"Estimated time : {est_int} minutes ({minutes_to_human(est_int)})\n")
    lines.append("")  

    for step in plan.get("steps", []):
        no = step.get("Step_No")
        title = step.get("Title", "").strip()
        time_text = step.get("Time", "").strip()
        time_val = step.get("Time_val", 0)
        desc = step.get("Desc", "").strip()

        lines.append(f"Step No. : {no}\n")
        lines.append(f"Step Title : {title}\n")
        lines.append(f"Time : {time_val}  (raw: {time_text})\n")
        lines.append(f"Description : {desc}\n")
        lines.append("\n\n")

    text = "\n\n".join(lines)
    return text

def load_prompt(filename):
    """Load prompt from file, removing comment lines starting with #"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, "prompts", filename)
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


# Load the prompts
qa_prompt_text = load_prompt("qa_prompt.txt")
summary_prompt_text = load_prompt("summary_prompt.txt")
question_clarification_prompt_text = load_prompt("question_clarification_prompt.txt")
problem_recognition_prompt_text = load_prompt("problem_recognition_prompt.txt")
image_analysis_prompt_text = load_prompt("image_analysis_prompt.txt")
description_assessment_prompt_text = load_prompt("description_assessment_prompt.txt")
steps_prompt_text = load_prompt("steps_prompt.txt")

class ProblemRecognitionAgent:
    """Agent 1: Recognizes problems and requests relevant photos"""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def greetings(self):
        payload = {
            "model": "gpt-4.1-nano",
            "messages": [
                {"role": "system", "content": "You are a DIY customer service agent called MyHandyAI , your task is to greet the user, introduce yourself and ask the user to describe the project/repair/fix to be done"},
            ],
            "max_tokens": 50,
            "temperature": 0.7
        }
        try:
            r = requests.post(self.api_url, headers=self.headers, json=payload, timeout=10)
            return r.json()["choices"][0]["message"]["content"]
        except:
            return "Thanks for using MyHandyAI! Tell me what you'd like to do or fix."

    def valid_description(self, message):
        payload = {
            "model": "gpt-4.1-nano",
            "messages": [
                {"role": "system", "content": "You are a DIY customer service agent, your task is to determine if the description/context of the repair/fix/project is coherent respond only 'True' or 'False'"},
                {"role": "user", "content": message}
            ],
            "max_tokens": 50,
            "temperature": 0.0
        }
        try:
            r = requests.post(self.api_url, headers=self.headers, json=payload, timeout=10)
            return r.json()["choices"][0]["message"]["content"] == "True"
        except:
            return False

    def analyze_problem(self, user_message: str) -> Dict[str, Any]:
        """Analyze user problem and determine what photos are needed"""

        system_prompt = problem_recognition_prompt_text

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User problem: {user_message}"}
        ]

        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={"model": "gpt-4.1-mini", "messages": messages, "max_tokens": 500}
            )

            if response.status_code == 200:
                data = response.json()
                text = data["choices"][0]["message"]["content"].strip()

                # Try to parse JSON from response
                try:
                    result = clean_and_parse_json(text)
                    return result
                except Exception:
                    # Fallback if JSON parsing fails
                    return {
                        "problem_type": "general",
                        "photo_requests": ["Please share a photo of the area you're working on"],
                        "response_message": text
                    }
            else:
                return self._get_fallback_response(user_message)

        except Exception:
            return self._get_fallback_response(user_message)

    def _get_fallback_response(self, user_message: str) -> Dict[str, Any]:
        """Fallback response if API fails - use simple AI-based approach"""
        system_prompt = """You are a DIY problem recognition agent. Analyze the user's problem and determine what photos would be most helpful.

Return a JSON response with:
- "problem_type": A descriptive problem type (e.g., "broken_furniture", "leaking_pipe", "electrical_issue")
- "photo_requests": List of 2-3 specific photo requests
- "response_message": A friendly message asking for the photos

Be specific about what photos would help diagnose the problem."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User problem: {user_message}"}
        ]

        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={"model": "gpt-4.1-mini", "messages": messages, "max_tokens": 300}
            )

            if response.status_code == 200:
                data = response.json()
                text = data["choices"][0]["message"]["content"].strip()

                try:
                    result = clean_and_parse_json(text)
                    return result
                except Exception:
                    # If JSON parsing fails, return a generic response
                    return {
                        "problem_type": "general_repair",
                        "photo_requests": ["Photo of the problem area", "Photo showing the context"],
                        "response_message": f"I can help with your issue! Please share:\n1. A photo of the problem area\n2. A photo showing the surrounding context"
                    }
            else:
                # If API fails, return a generic response
                return {
                    "problem_type": "general_repair",
                    "photo_requests": ["Photo of the problem area", "Photo showing the context"],
                    "response_message": f"I can help with your issue! Please share:\n1. A photo of the problem area\n2. A photo showing the surrounding context"
                }

        except Exception:
            return {
                "problem_type": "general_repair",
                "photo_requests": ["Photo of the problem area", "Photo showing the context"],
                "response_message": f"I can help with your issue! Please share:\n1. A photo of the problem area\n2. A photo showing the surrounding context"
            }


class ImageAnalysisAgent:
    """Agent 2: analyses an uploaded image and returns clarifying questions"""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def skip_image(self, message):
        payload = {
            "model": "gpt-4.1-nano",
            "messages": [
                {"role": "system", "content": "Detect if the user doesn't have an image or want to skip the image upload (e.g 'skip','I dont have an image', etc...)  Respond only with 'True' or 'False'"},
                {"role": "user", "content": message}
            ],
            "max_tokens": 50,
            "temperature": 0.0
        }
        try:
            r = requests.post(self.api_url, headers=self.headers, json=payload, timeout=10)
            return r.json()["choices"][0]["message"]["content"] == "True"
        except:
            return True

    def analyze_image(self, image_data: bytes, problem_type: str) -> Dict[str, Any]:
        """Call GPT-4o Vision with a base64-encoded image and get back questions"""

        b64 = base64.b64encode(image_data).decode("utf-8")

        system_prompt = (
            f"{image_analysis_prompt_text}\n\n"
            f"Problem type: {problem_type}\n"
            f"Additional context: {qa_prompt_text}\n\n"
            "Return JSON with:\n"
            '- "analysis": brief description of what you see\n'
            '- "questions": list of questions (ask one-by-one)\n'
            '- "first_question": the first question to ask'
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text",
                     "text": f"Please analyse this image for a {problem_type} issue:"},
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]
            }
        ]

        try:
            r = requests.post(
                self.api_url, headers=self.headers,
                json={"model": "gpt-4o", "messages": messages, "max_tokens": 800},
                timeout=20
            )
            if r.status_code == 200:
                txt = r.json()["choices"][0]["message"]["content"].strip()
                try:
                    result = json.loads(txt)
                   
                    if isinstance(result, dict) and "analysis" in result and "questions" in result:
                        return result
                    else:
                        
                        return self._get_fallback_questions(problem_type)
                except (json.JSONDecodeError, KeyError, TypeError):
                    
                    return self._get_fallback_questions(problem_type)
        except Exception:
            pass  

        # ─── fallback set ───
        return self._get_fallback_questions(problem_type)

    def analyze_image_without_image(self, problem_type: str, user_description: str) -> Dict[str, Any]:
        """Generate questions based on problem description when no image is provided"""

        system_prompt = (
            f"{image_analysis_prompt_text}\n\n"
            f"Problem type: {problem_type}\n"
            f"User description: {user_description}\n"
            f"Additional context: {qa_prompt_text}\n\n"
            "Since no image was provided, analyze the problem description and generate relevant questions.\n"
            "Return JSON with:\n"
            '- "analysis": brief description based on the problem description\n'
            '- "questions": list of questions (ask one-by-one)\n'
            '- "first_question": the first question to ask'
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please analyse this {problem_type} problem based on the description: {user_description}"}
        ]

        try:
            r = requests.post(
                self.api_url, headers=self.headers,
                json={"model": "gpt-4.1-mini", "messages": messages, "max_tokens": 800},
                timeout=20
            )
            if r.status_code == 200:
                txt = r.json()["choices"][0]["message"]["content"].strip()
                try:
                    result = clean_and_parse_json(txt)
                    if isinstance(result, dict) and "analysis" in result and "questions" in result:
                        return result
                    else:
                        return self._get_fallback_questions(problem_type)
                except (json.JSONDecodeError, KeyError, TypeError):
                   
                    return self._get_fallback_questions(problem_type)
        except Exception:
            pass  

        # ─── fallback set ───
        return self._get_fallback_questions(problem_type)

    def _get_fallback_questions(self, problem_type: str) -> Dict[str, Any]:
        """Fallback questions if image analysis fails"""
        question_templates = {
            "hanging_mirror": {
                "analysis": "I can see you want to hang a mirror. Let me ask some specific questions to help you do this safely.",
                "questions": [
                    "What are the mirror's dimensions (height and width)?",
                    "Do you know approximately how heavy it is?",
                    "What kind of wall do you have (drywall, concrete, tile, etc.)?",
                    "Do you want the mirror flush against the wall, or with a gap/hanger?"
                ],
                "first_question": "What are the mirror's dimensions (height and width)?"
            },
            "clogged_sink": {
                "analysis": "I can see you have a sink issue. Let me ask some questions to help diagnose the problem.",
                "questions": [
                    "What type of clog is it (water not draining, slow drain, etc.)?",
                    "Is it affecting just this sink or multiple fixtures?",
                    "Have you tried any DIY solutions already?",
                    "What type of pipes do you have (PVC, metal, etc.)?"
                ],
                "first_question": "What type of clog is it (water not draining, slow drain, etc.)?"
            },
            "electrical_issue": {
                "analysis": "I can see you have an electrical issue. Let me ask some safety-focused questions.",
                "questions": [
                    "What exactly is happening (no power, flickering, etc.)?",
                    "Is this affecting one fixture or multiple?",
                    "Have you checked the circuit breaker?",
                    "When did this problem start?"
                ],
                "first_question": "What exactly is happening (no power, flickering, etc.)?"
            },
            "leaking_pipe": {
                "analysis": "I can see you have a leaking pipe issue. Let me ask some safety-focused questions.",
                "questions": [
                    "Where is the leak located (under sink, basement, bathroom, etc.)?",
                    "What type of pipe is it (copper, PVC, galvanized steel)?",
                    "How severe is the leak (dripping, spraying, or just damp)?",
                    "Can you safely access the area around the leak?"
                ],
                "first_question": "Where is the leak located (under sink, basement, bathroom, etc.)?"
            },
            "broken_furniture": {
                "analysis": "I can see you have a broken furniture issue. Let me ask some specific questions to help you fix it.",
                "questions": [
                    "What type of furniture is it (table, chair, cabinet, etc.)?",
                    "What material is it made of (wood, metal, plastic, etc.)?",
                    "How exactly is it broken (wobbly, cracked, loose joint, etc.)?",
                    "Do you have any experience with furniture repair?"
                ],
                "first_question": "What type of furniture is it (table, chair, cabinet, etc.)?"
            }
        }

        return question_templates.get(problem_type, {
            "analysis": "I can see your project. Let me ask some questions to help you.",
            "questions": [
                "What are the dimensions of the area you're working with?",
                "What materials are involved?",
                "What's your experience level with this type of project?"
            ],
            "first_question": "What are the dimensions of the area you're working with?"
        })


class SummaryAgent:
    """Agent 3: Creates a summary of the problem based on image and user answers"""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def affirmative_negative_response(self, message):
        payload = {
            "model": "gpt-4.1-nano",
            "messages": [
                {"role": "system", "content": "You are a affirmative/negative detector, your task is to determine if the user answer is affirmative to proceed with next steps or negative to not continue answer only '1' for affirmative '2' for negative and '0' if you cannot determine with the message"},
                {"role": "user", "content": message}
            ],
            "max_tokens": 50,
            "temperature": 0.0
        }
        try:
            r = requests.post(self.api_url, headers=self.headers, json=payload, timeout=10)
            return int(r.json()["choices"][0]["message"]["content"])
        except:
            return 0

    def create_summary(self, problem_type: str, image_analysis: str, user_answers: Dict[int, str]) -> str:
        """Create a comprehensive summary of the problem"""

        # Format user answers for the prompt
        answers_text = ""
        for i, answer in user_answers.items():
            answers_text += f"Q{i+1}: {answer}\n"

        system_prompt = f"""{summary_prompt_text}

Problem type: {problem_type}
Image analysis: {image_analysis}
User's answers to clarifying questions:
{answers_text}

Please create a summary of this DIY problem."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Please create a summary of this DIY problem."}
        ]

        try:
            r = requests.post(
                self.api_url, headers=self.headers,
                json={"model": "gpt-4.1", "messages": messages, "max_tokens": 300},
                timeout=20
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            pass

        # Fallback summary
        return f"I understand you have a {problem_type.replace('_', ' ')} issue. Based on the image and your answers, I can help you resolve this problem."


class PydanticToolAgent:
    """
    Updated Agent: Given the final summary, generate a TEXT-formatted list of tools with descriptive fields and dimensions (if available).
    """

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def create_pydantic_output(self, summary_text: str) -> str:
        """
        Returns plain-text string (chat) formatted as requested.
        """
        system_prompt = (
            "You are an assistant that converts a DIY problem summary into a structured list of tools and materials. "
            "Produce a JSON array ONLY (no extra text) where each item is an object with the following keys:\n"
            " - tool_name (string)\n"
            " - description (string)\n"
            " - dimensions (string, OPTIONAL)\n"
            " - risk_factor (string)\n"
            " - safety_measure (string)\n\n"
            "Return 3 relevant tools when possible. Return JSON only."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Summary:\n{summary_text}\n\nReturn the JSON array now."}
        ]

        tools = None
        try:
            r = requests.post(self.api_url, headers=self.headers,
                              json={"model": "gpt-4.1-mini", "messages": messages, "max_tokens": 900},
                              timeout=25)
            if r.status_code == 200:
                raw = r.json()["choices"][0]["message"]["content"].strip()
                try:
                    tools = clean_and_parse_json(raw)
                except Exception:
                 
                    try:
                        m = re.search(r"\[.*\]", raw, flags=re.DOTALL)
                        if m:
                            tools = json.loads(m.group(0))
                    except Exception:
                        tools = None
        except Exception:
            tools = None

        if not isinstance(tools, list) or not tools:
           
            fallback_tools = []
            low = summary_text.lower()
        
            dim_matches = re.findall(r"(\d+\s*(?:cm|mm|in|inch|kg|lb|lbs))", summary_text, flags=re.I)
            inferred_dims = dim_matches[0] if dim_matches else ""

            if "mirror" in low or "hang" in low:
                fallback_tools = [
                    {
                        "tool_name": "Stud Finder",
                        "description": "Handheld electronic device used to detect studs and wiring behind walls; recommended for locating secure mounting points for heavy fixtures.",
                        "dimensions": "",
                        "risk_factor": "If inaccurate, may lead to anchors being placed incorrectly, risking fixture failure or hitting hidden electrical wiring.",
                        "safety_measure": "Scan the wall multiple times and confirm before drilling. Wear safety glasses."
                    },
                    {
                        "tool_name": "Power Drill (with appropriate bits)",
                        "description": "Cordless or corded drill used for pilot holes and installing anchors; choose drill size based on anchor/drywall type and screw diameter.",
                        "dimensions": inferred_dims or "",
                        "risk_factor": "Drilling can penetrate wiring/plumbing causing electrocution or water leaks; bit kickback can injure hands.",
                        "safety_measure": "Wear safety glasses and gloves, ensure drill bits are sharp and correct size."
                    },
                    {
                        "tool_name": "Heavy-duty Wall Anchors (toggle or molly bolts)",
                        "description": "Anchors designed to hold heavy loads on drywall when studs are unavailable; choose anchors rated for the mirror's weight.",
                        "dimensions": "",
                        "risk_factor": "Underrated anchors or improper installation may fail causing the mirror to fall.",
                        "safety_measure": "Select anchors with verified weight rating greater than the object's weight and follow installation instructions."
                    }
                ]
            else:
                # generic fallback
                fallback_tools = [
                    {
                        "tool_name": "Protective Gloves",
                        "description": "Gloves to protect hands from cuts and abrasions during the job.",
                        "dimensions": "",
                        "risk_factor": "Low — ill-fitting gloves may reduce dexterity.",
                        "safety_measure": "Use gloves sized correctly for the task."
                    },
                    {
                        "tool_name": "Measuring Tape",
                        "description": "Tape measure to take accurate measurements and mark mounting points precisely.",
                        "dimensions": "",
                        "risk_factor": "Pinch risk during retraction.",
                        "safety_measure": "Retract tape slowly and keep fingers clear of the edge."
                    }
                ]
            tools = fallback_tools

        lines = []
        lines.append("ASSISTANT : Here are the tools and materials required for your task:\n\n")
        total_cost = 0.0
        found_any_price = False

        for t in tools:
            name = (t.get("tool_name") or t.get("name") or "Unknown Tool").strip()
            desc = (t.get("description") or "").strip()
            dims = (t.get("dimensions") or "").strip()
            risk = (t.get("risk_factor") or t.get("risk") or "").strip()
            safety = (t.get("safety_measure") or t.get("safety") or "").strip()

            lines.append(f"Tool name : {name}\n")

           
            if not SERPAPI_API_KEY:
                lines.append("Note: SERPAPI_API_KEY not configured; skipping product lookup.\n")
            else:
                
                params = {
                    "engine": "amazon",
                    "k": name,
                    "amazon_domain": "amazon.com",
                    "api_key": SERPAPI_API_KEY
                }
                try:
                    search = GoogleSearch(params)
                    results = search.get_dict()
                    organic_results = results.get("organic_results") or []
                except Exception as e:
                    organic_results = []
               

                if organic_results:
                    first = organic_results[0]
                    title = first.get("title") or ""
                    link = first.get("link_clean") or first.get("link") or ""
                    thumbnail = first.get("thumbnail") or first.get("thumbnail_image") or ""
                    
                    price_field = first.get("extracted_price") or first.get("price") or first.get("raw_price") or None
                    price_val = extract_number_from_maybe_price(price_field)
                    if price_val is None:
                        
                        for possible in ("snippet", "rich_snippet", "extracted_data", "inline_links"):
                            candidate = first.get(possible)
                            if candidate:
                                price_val = extract_number_from_maybe_price(candidate)
                                if price_val is not None:
                                    break

                    if price_val is not None:
                        total_cost += price_val
                        found_any_price = True

                    if title:
                        lines.append(f"Title : {title}\n")
                    if link:
                        lines.append(f"Amazon URL : {link}\n")
                    if thumbnail:
                        lines.append(f"Amazon Thumbnail url : {thumbnail}\n")
                    if price_val is not None:
                        lines.append(f"Price : $ {price_val}\n")
                    else:
                        lines.append("Price : Not available\n")
                else:
                    lines.append("No Amazon/organic results found for this tool.\n")

            
            lines.append(f"Tool description : {desc if desc else '<Description not available>'}\n")
            if dims:
                lines.append(f"Tool dimensions : {dims}\n")
            lines.append(f"Risk Factor : {risk if risk else '<Risk Factors>'}\n")
            lines.append(f"Safety Measure: {safety if safety else '<Safety Measures>'}\n")
            lines.append("\n\n\n")

       
        plan = self._generate_steps_with_tools(summary_text)
       
        try:
            total = getattr(plan, "total_steps", None) or len(getattr(plan, "steps", []))
            est_mins = getattr(plan, "estimated_time", 0) or 0
        except Exception:
            total = 0
            est_mins = 0

 
        steps_estimation = {
            "steps_no": total,
            "time": est_mins,
            "steps": []
        }
        steps = []
        for s in getattr(plan, "steps", []):
            steps_des = {}
           
            no = getattr(s, "step_no", None) or (s.get("step_no") if isinstance(s, dict) else "N/A")
            title = getattr(s, "step_title", None) or (s.get("step_title") if isinstance(s, dict) else "")
            time_mins = getattr(s, "time", None) or (s.get("time") if isinstance(s, dict) else 0)
            
            time_text = getattr(s, "time_text", None) or (s.get("time_text") if isinstance(s, dict) else None) or (s.get("Time") if isinstance(s, dict) else "")
            desc = getattr(s, "description", None) or (s.get("description") if isinstance(s, dict) else "")

            steps_des['Step_No'] = no
            steps_des['Title'] = title
            steps_des['Time'] = time_text or ""
            steps_des['Time_val'] = int(time_mins or 0)
            steps_des['Desc'] = desc

            steps.append(steps_des)

        steps_estimation['steps'] = steps

        if found_any_price:
            cost_value = float(total_cost)
        else:
            cost_value = 0.0
        steps_estimation['cost'] = cost_value

        tools_output = "\n".join(lines).rstrip()
        step_txt = extract_lines(steps_estimation)

        combined_output = f"{tools_output}\n\n{'='*50}\n\n📋 **Step-by-Step Plan:**\n{step_txt}"

        estimations = estimation(steps_estimation)

        ttl_output = f"{combined_output}\n\n{'='*200}\n\n{estimations}"

        return ttl_output

    def _generate_steps_with_tools(self, summary_text: str):
        """Generate steps using StepsTextAgent and return StepsPlan (Pydantic)"""
        try:
            steps_agent = StepsTextAgent()
            return steps_agent.create_steps_text(summary_text)
        except Exception as e:
            print(f"Error generating steps: {e}")
            return self._get_fallback_steps()

    def _get_fallback_steps(self) -> str:
        """Fallback steps if generation fails"""
        return (
            "Here is your step-by-step plan:\n\n"
            "Step No. : 1\nStep Title : Locate studs\nTime : 10-15 min\nDescription : Find studs for secure mounting.\n\n"
            "Step No. : 2\nStep Title : Mark mounting points\nTime : 10-15 min\nDescription : Measure and mark bracket positions.\n\n"
            "Step No. : 3\nStep Title : Install brackets\nTime : 15-20 min\nDescription : Drill pilot holes and mount wall brackets.\n\n"
            "Step No. : 4\nStep Title : Attach item\nTime : 5-10 min\nDescription : Mount securely and check level."
        )


class Step(BaseModel):
    step_no: int = Field(..., alias="Step No.")
    step_title: str = Field(..., alias="Step Title")
    time: int = Field(..., alias="Time")          
    time_text: str = Field(..., alias="TimeText") 
    description: str = Field(..., alias="Description")


class StepsPlan(BaseModel):
    total_steps: int
    estimated_time: int = 0   
    steps: List[Step]


class StepsTextAgent:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

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
        # header
        total_steps = None
        estimated_time_minutes = 0

        m_total = re.search(r"Total\s*Steps\s*[:\-]\s*(\d+)", text, re.IGNORECASE)
        if m_total:
            total_steps = int(m_total.group(1))

        m_est = re.search(r"Estimated\s*Time\s*[:\-]\s*(.+)", text, re.IGNORECASE)
        if m_est:
            est_text = m_est.group(1).strip()
            estimated_time_minutes = self._parse_time_to_minutes(est_text)

     
        step_block_re = re.compile(
            r"Step\s*No\.?\s*:\s*(?P<no>\d+)\s*[\r\n]+"
            r"Step\s*Title\s*:\s*(?P<title>.+?)\s*[\r\n]+"
            r"Time\s*:\s*(?P<time>.+?)\s*[\r\n]+"
            r"Description\s*:\s*(?P<desc>.+?)(?=(?:\n\s*\n)|\Z)",
            re.IGNORECASE | re.DOTALL,
        )

        steps = []
        for m in step_block_re.finditer(text):
            no = int(m.group("no").strip())
            title = m.group("title").strip()
            time_text = m.group("time").strip()
            time_mins = self._parse_time_to_minutes(time_text)
            desc = m.group("desc").strip().replace("\n", " ").strip()
            steps.append(Step(**{
                "Step No.": no,
                "Step Title": title,
                "Time": time_mins,
                "TimeText": time_text,
                "Description": desc
            }))

        if total_steps is None:
            total_steps = len(steps)

        if estimated_time_minutes == 0:
            estimated_time_minutes = sum(s.time for s in steps)

        return StepsPlan(total_steps=total_steps, estimated_time=estimated_time_minutes, steps=steps)

    def create_steps_text(self, summary_text: str) -> StepsPlan:
        base_prompt = (
            "You are an expert DIY planner.\n"
            "Return a concise step-by-step plan as plain text (no JSON).\n"
            "Start with an intro line summarizing total steps and estimated time if possible.\n\n"
            "Then for each step return EXACTLY this format (use the same labels and punctuation):\n"
            "Step No. : <Step No.>\n"
            "Step Title : <step title>\n"
            "Time : <Total time needed>\n"
            "Description : <Informative Description of the step in 2-3 lines>\n\n"
        )

        payload = {
            "model": "gpt-4.1-mini",
            "messages": [
                {"role": "system", "content": base_prompt},
                {"role": "user", "content": f"Summary:\n{summary_text}\nReturn the plan as plain text in the exact format."},
            ],
            "max_tokens": 900,
            "temperature": 0.5,
        }

        try:
            r = requests.post(self.api_url, headers=self.headers, json=payload, timeout=25)
            if r.status_code == 200:
                content = r.json()["choices"][0]["message"]["content"].strip()
                return self._parse_steps_text(content)
        except Exception:
            pass

      
        fallback_text = (
            "Here is your step-by-step plan:\n\n"
            "Step No. : 1\nStep Title : Locate studs\nTime : 10-15 min\nDescription : Find studs for secure mounting.\n\n"
            "Step No. : 2\nStep Title : Mark mounting points\nTime : 10-15 min\nDescription : Measure and mark bracket positions.\n\n"
            "Step No. : 3\nStep Title : Install brackets\nTime : 15-20 min\nDescription : Drill pilot holes and mount wall brackets.\n\n"
            "Step No. : 4\nStep Title : Attach item\nTime : 5-10 min\nDescription : Mount securely and check level."
        )
        return self._parse_steps_text(fallback_text)





class QuestionClarificationAgent:
    """Agent 4: Uses an LLM to (1) detect 'skip', (2) detect 'don't know' and rephrase,
                (3) detect irrelevant/unrealistic answers and re-ask, or (4) accept."""

    def __init__(self):
        self.api_key  = os.getenv("OPENAI_API_KEY")
        self.api_url  = "https://api.openai.com/v1/chat/completions"
        self.headers  = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def handle_user_response(self, question: str, user_response: str) -> tuple[str, bool]:
        """
        Returns:
          message: str    – text to send (empty if answer is accepted)
          advance: bool  – True to move to next question, False to re-ask
        """
        # Replace placeholders manually to avoid conflicts with JSON braces in the prompt
        system_prompt = question_clarification_prompt_text.replace("{question}", question).replace("{user_response}", user_response)
        payload = {
            "model": "gpt-4.1-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": "Please classify and respond in JSON."}
            ],
            "max_tokens": 200,
            "temperature": 0.2
        }
        try:
            resp = requests.post(self.api_url, headers=self.headers, json=payload, timeout=15)
            data = resp.json()["choices"][0]["message"]["content"]
            result = clean_and_parse_json(data)
            act = result.get("action")
            msg = result.get("message", "")
            if act == "skip":
                return (msg, True)
            if act == "accept":
                return ("", True)
            
            return (msg, False)
        except Exception:
            
            fallback = (
                f"I didn't quite catch that. Could you clarify your answer to:\n\n**{question}**"
            )
            return (fallback, False)

    def detect_revision_request(self, user_message: str, current_question: str, question_history: List[str]) -> tuple[bool, Optional[int], str]:
        """
        Detects if user wants to revise a previous answer using natural language.
        
        Returns:
            is_revision_request: bool - True if user wants to go back
            target_question_index: Optional[int] - Which question to go back to (None if unclear)
            clarification_message: str - Message to send to user
        """
        
        system_prompt = f"""You are a revision detection agent. The user is currently answering question {len(question_history) + 1}.

Current question: "{current_question}"

Previous questions:
{chr(10).join(f"{i+1}. {q}" for i, q in enumerate(question_history))}

User message: "{user_message}"

Determine if the user wants to:
1. Go back to a specific previous question (using natural language reference)
2. Just clarify their current answer
3. Continue normally

Return JSON with:
- "is_revision_request": true/false
- "target_question_index": number (1-based) or null
- "message": explanation for user
- "action": "go_back", "clarify_current", or "continue"
- "confidence": 0.0-1.0 (how confident you are in the match)

Examples:
- "I want to change my answer about the wall type" → go_back, target=wall question index
- "I made a mistake in the previous question about dimensions" → go_back, target=dimension question index
- "Actually, let me re-answer the question about materials" → go_back, target=materials question index
- "I meant to say..." → clarify_current
- "The answer is..." → continue

Use semantic matching to find the best question match."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        try:
            response = requests.post(
                self.api_url, headers=self.headers,
                json={"model": "gpt-4.1-mini", "messages": messages, "max_tokens": 300},
                timeout=10
            )
            
            if response.status_code == 200:
                result = clean_and_parse_json(response.json()["choices"][0]["message"]["content"])
                
                is_revision = result.get("is_revision_request", False)
                target_index = result.get("target_question_index")
                message = result.get("message", "")
                action = result.get("action", "continue")
                confidence = result.get("confidence", 0.0)
                
                # Only proceed if confidence is high enough
                if confidence >= 0.7:
                    return is_revision, target_index, message
                elif is_revision:
                    # Low confidence - ask user to clarify with dynamic examples
                    if question_history:
                        # Create examples based on actual questions asked
                        examples = []
                        for i, q in enumerate(question_history[:3]):  # Show up to 3 examples
                            # Extract key topic from question
                            topic = self._extract_question_topic(q)
                            examples.append(f"'{topic}'")
                        
                        example_text = " or ".join(examples)
                        return True, None, f"I'm not sure which question you want to re-answer. Could you be more specific? For example: {example_text}"
                    else:
                        return True, None, "I'm not sure which question you want to re-answer. Could you be more specific?"
                
        except Exception:
            pass
        
        # Fallback: simple keyword detection
        revision_keywords = ["change", "mistake", "wrong", "re-answer", "previous", "go back"]
        if any(keyword in user_message.lower() for keyword in revision_keywords):
            if question_history:
                # Create examples based on actual questions asked
                examples = []
                for i, q in enumerate(question_history[:3]):  # Show up to 3 examples
                    # Extract key topic from question
                    topic = self._extract_question_topic(q)
                    examples.append(f"'{topic}'")
                
                example_text = " or ".join(examples)
                return True, None, f"Which question would you like to re-answer? Please be specific, like {example_text}"
            else:
                return True, None, "Which question would you like to re-answer? Please be specific."
        
        return False, None, ""
    
    def _extract_question_topic(self, question: str) -> str:
        """
        Extract a short, descriptive topic from a question for use in examples.
        """
        # Common patterns to extract topics
        topic_patterns = [
            r"what.*?(wall|material|type|size|dimension|weight|color)",
            r"where.*?(clog|leak|problem|issue)",
            r"how.*?(heavy|big|long|wide)",
            r"do you.*?(have|know|experience|access)",
            r"have you.*?(tried|used|checked)",
            r"what.*?(tools|equipment|supplies)",
            r"when.*?(start|happen|notice)",
            r"is it.*?(affecting|causing|damaging)"
        ]
        
        question_lower = question.lower()
        
        for pattern in topic_patterns:
            match = re.search(pattern, question_lower)
            if match:
                # Extract the key word and make it more readable
                key_word = match.group(1)
                if key_word == "wall":
                    return "wall type"
                elif key_word == "material":
                    return "material type"
                elif key_word == "dimension":
                    return "dimensions"
                elif key_word == "clog":
                    return "clog location"
                elif key_word == "leak":
                    return "leak location"
                elif key_word == "tools":
                    return "available tools"
                elif key_word == "experience":
                    return "experience level"
                else:
                    return key_word.replace("_", " ")
        
        # Fallback: extract first few meaningful words
        words = question.split()
        meaningful_words = []
        for word in words[:4]:  # Take first 4 words
            if len(word) > 3 and word.lower() not in ["what", "where", "when", "how", "do", "you", "have", "the", "and", "for", "with", "that", "this"]:
                meaningful_words.append(word)
        
        if meaningful_words:
            return " ".join(meaningful_words[:2])  # Return first 2 meaningful words
        
        # Final fallback
        return "previous question"
        
class DescriptionAssessmentAgent:
    """Agent: Decides if the user’s initial problem description is
       detailed enough to skip clarifying questions."""
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def assess(self, description: str) -> bool:
        """Return True if description is complete enough to skip questions."""
        system_prompt = f"""{description_assessment_prompt_text}

Description: \"\"\"{description}\"\"\" 
"""
        payload = {
            "model": "gpt-4.1-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": "Please respond with JSON only."}
            ],
            "max_tokens": 50,
            "temperature": 0.0
        }
        try:
            r = requests.post(self.api_url, headers=self.headers, json=payload, timeout=10)
            result = r.json()["choices"][0]["message"]["content"]
            return clean_and_parse_json(result).get("skip_questions", False)
        except:
            return False

class AgenticChatbot:
    """Main chatbot that coordinates between agents."""

    def __init__(self):
        self.problem_agent         = ProblemRecognitionAgent()
        self.image_agent           = ImageAnalysisAgent()
        self.summary_agent         = SummaryAgent()
        self.pydantic_agent        = PydanticToolAgent()   # <-- updated agent added here
        self.clarification_agent   = QuestionClarificationAgent()
        self.description_agent     = DescriptionAssessmentAgent()
        self.reset()

    def reset(self):
        self.current_state          = "waiting_for_problem"
        self.problem_type           = None
        self.user_description       = ""
        self.summary                = ""
        self.questions              = []
        self.current_question_index = 0
        self.user_answers           = {}
        self.image_analysis         = None

    def greet(self):
        return self.problem_agent.greetings()


    def process_message(self, user_message: str, uploaded_image: Optional[bytes] = None) -> str:
        # 1) Capture the user's free‐form description
        if self.current_state == "waiting_for_problem":
            if not self.problem_agent.valid_description(user_message):
                return "Not quite understand the description, could you please send again a description of the issue, repair or project you are facing?"
            self.user_description = user_message
            result = self.problem_agent.analyze_problem(user_message)
            self.problem_type = result["problem_type"]
            self.current_state = "waiting_for_photos"
            return result["response_message"]

        # 2) Handle photo upload or skip
        if self.current_state == "waiting_for_photos":
            # Check if user wants to skip photos
            if self.image_agent.skip_image(user_message):
                # Skip photos and go directly to questions based on description
                result = self.image_agent.analyze_image_without_image(self.problem_type, self.user_description)
                if not isinstance(result, dict) or "analysis" not in result or "questions" not in result:
                    return "Sorry, I had trouble processing your request. Please try again."
                
                self.image_analysis = str(result["analysis"])
                return self._prepare_questions_from_result(result)
            
            # Check if image was uploaded
            if uploaded_image:
                result = self.image_agent.analyze_image(uploaded_image, self.problem_type)
                if not isinstance(result, dict) or "analysis" not in result or "questions" not in result:
                    return "Sorry, I had trouble analyzing the image. Please try uploading it again."
                
                self.image_analysis = str(result["analysis"])
                return self._prepare_questions_from_result(result)
            
            # No image uploaded and no skip command
            return "Please upload the requested photo so I can analyse it, or type 'skip' if you prefer not to share photos."

        # 3) Q&A loop
        if self.current_state == "asking_questions":
            current_q = self.questions[self.current_question_index]
            
            # NEW: Check for revision request first
            is_revision, target_index, revision_message = self.clarification_agent.detect_revision_request(
                user_message, current_q, self.questions[:self.current_question_index]
            )
            
            if is_revision:
                if target_index is not None and 1 <= target_index <= len(self.questions):
                    # Go back to specific question
                    self.current_question_index = target_index - 1
                    return f"{revision_message}\n\n**Question {target_index}:**\n{self.questions[target_index - 1]}"
                else:
                    # Ask user to specify which question
                    return revision_message
            
            # Continue with normal clarification logic
            clarification, advance = self.clarification_agent.handle_user_response(
                current_q, user_message
            )

            if advance:
                # store either "skipped" or the real answer
                answer = "skipped" if clarification.startswith("Got it") else user_message
                self.user_answers[self.current_question_index] = answer
                self.current_question_index += 1
                return self._proceed_after_question(preamble=clarification)

            return f"{clarification}\n\n**Please answer:**\n{current_q}"

        # 4) Summary confirmation
        if self.current_state == "showing_summary":
            resp = self.summary_agent.affirmative_negative_response(user_message)
            if resp == 1:
                # User confirmed the summary; create final summary and hand over to PydanticToolAgent
                combined = {0: self.user_description}
                for idx, ans in self.user_answers.items():
                    combined[idx + 1] = ans
                final_summary = self.summary_agent.create_summary(
                    self.problem_type,
                    self.image_analysis,
                    combined
                )

                # Generate TEXT-formatted output using the updated agent
                tools_text = self.pydantic_agent.create_pydantic_output(final_summary)

                reply = (
                    f"{tools_text}\n\n"
                    "If you'd like, I can now provide step-by-step repair instructions using these tools — would you like that?"
                )

                # reset the conversation state after producing the pydantic-style text output
                self.current_state= "complete"
                return reply

            if resp == 2:
                self.reset()
                return (
                    "I’m sorry for the mix-up. Let’s start from scratch – please describe your problem again."
                )

            return (
                "Please reply 'yes' if the summary looks correct, or 'no' if it doesn’t."
            )

    def _proceed_after_question(self, preamble: str = "") -> str:
        """Ask next question or build the interim summary prompt."""
        if self.current_question_index < len(self.questions):
            next_q = self.questions[self.current_question_index]
            return (preamble + "\n\n" if preamble else "") + f"**Next question:**\n{next_q}"

        self.current_state = "showing_summary"
        combined = {0: self.user_description}
        for idx, ans in self.user_answers.items():
            combined[idx + 1] = ans

        summary = self.summary_agent.create_summary(
            self.problem_type,
            self.image_analysis,
            combined
        )
        return (
            (preamble + "\n\n") if preamble else ""
        ) + (
            f"Perfect! Here’s what I’ve got so far:\n\n**{summary}**\n\n"
            "Does that look right? Reply 'yes' or 'no'."
        )

    def _generate_solution(self) -> str:
        answers = "\n".join(f"Q{i+1}: {ans}" for i, ans in self.user_answers.items())
        return (
            f"Perfect! Based on your answers:\n{answers}\n\n"
            f"I'll now provide a detailed step-by-step solution for your "
            f"{self.problem_type.replace('_', ' ')} project."
        )
    
    def _prepare_questions_from_result(self, result: Dict[str, Any]) -> str:
        """Helper method to prepare questions from image analysis result"""
                    
        if self.description_agent.assess(self.user_description):
                
                combined = {0: self.user_description}
                summary = self.summary_agent.create_summary(
                    self.problem_type,
                    self.image_analysis,
                    combined
                )
                self.current_state = "showing_summary"
                
                # Determine the appropriate message based on whether image was provided
                if "photo" in (self.image_analysis or "").lower() or "image" in (self.image_analysis or "").lower():
                    intro_message = f"Great, thanks for the photo!\n\n{self.image_analysis}\n\n"
                else:
                    intro_message = f"Great! Based on your description:\n\n{self.image_analysis}\n\n"
                
                return (
                    f"{intro_message}"
                    f"Since you already provided full details up front, here's a summary:\n\n**{summary}**\n\n"
                    "Does this look right? Reply 'yes' or 'no'."
                )

        # 2b) Otherwise, prepare the questions
        raw_qs = [
            (q["text"] if isinstance(q, dict) and "text" in q else str(q))
            for q in result["questions"]
        ]

        # 2c) Filter out any "dimension" question if the description includes a measurement
        desc = self.user_description.lower()
        has_measure = bool(__import__("re").search(r"\d+\s*(cm|mm|in)", desc))
        if has_measure:
            self.questions = [q for q in raw_qs if "dimension" not in q.lower()]
        else:
            self.questions = raw_qs

        # 2d) If no questions remain, go straight to summary anyway
        if not self.questions:
            combined = {0: self.user_description}
            summary = self.summary_agent.create_summary(
                self.problem_type,
                self.image_analysis,
                combined
            )
            self.current_state = "showing_summary"
            
            # Determine the appropriate message based on whether image was provided
            if "photo" in (self.image_analysis or "").lower() or "image" in (self.image_analysis or "").lower():
                intro_message = f"Great, thanks for the photo!\n\n{self.image_analysis}\n\n"
            else:
                intro_message = f"Great! Based on your description:\n\n{self.image_analysis}\n\n"
            
            return (
                f"{intro_message}"
                f"Your description covered everything, here's a summary:\n\n**{summary}**\n\n"
                "Does this look right? Reply 'yes' or 'no'."
            )

        # 2e) Otherwise start the Q&A loop
        self.current_question_index = 0
        self.current_state = "asking_questions"
        
        # Determine the appropriate message based on whether image was provided
        if "photo" in (self.image_analysis or "").lower() or "image" in (self.image_analysis or "").lower():
            intro_message = f"Great, thanks for the photo!\n\n{self.image_analysis}\n\n"
        else:
            intro_message = f"Great! Based on your description:\n\n{self.image_analysis}\n\n"
        
        return (
            f"{intro_message}"
            "I'll ask a few quick questions one-by-one so I can give you "
            "the safest fix.\n\n"
            "💡 **Tip:** If you don't understand a question or don't know the answer, "
            "just let me know! You can also type 'skip' to move to the next question.\n\n"
            f"**{self.questions[0]}**"
        )
