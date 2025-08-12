import os
import re
import json
import requests
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import HTTPException

# Import utility functions from agents.py
from chatbot.agents import load_prompt, clean_and_parse_json, minutes_to_human, extract_number_from_maybe_price

tools_prompt_text = load_prompt("tools_prompt.txt")
steps_prompt_text = load_prompt("steps_prompt.txt")


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


class ToolsAgentJSON:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate(self, summary: str, user_answers: Dict[int, str] = None, questions: List[str] = None) -> Dict[str, Any]:
        """
        Generate tools and materials in JSON format.
        Returns a dictionary with tools array and total cost estimation.
        """
        system_prompt = (
            "You are an assistant that converts a DIY problem summary into a structured list of tools and materials. "
            "Produce a JSON array ONLY (no extra text) where each item is an object with the following keys:\n"
            " - tool_name (string)\n"
            " - description (string)\n"
            " - dimensions (string, OPTIONAL)\n"
            " - risk_factor (string)\n"
            " - safety_measure (string)\n\n"
            "Return 3-5 relevant tools when possible. Return JSON only."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Summary:\n{summary}\n\nReturn the JSON array now."}
        ]

        tools = None
        try:
            r = requests.post(self.api_url, headers=self.headers,
                              json={"model": "gpt-5-mini", "messages": messages, "max_completion_tokens": 1000,"reasoning_effort": "low"},
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
            # Fallback tools
            tools = self._get_fallback_tools(summary)

        # Calculate total cost (if available)
        total_cost = 0.0
        found_any_price = False
        
        # For now, we'll use placeholder pricing since we're not doing Amazon lookups here
        # In a real implementation, you might want to integrate with a pricing API
        
        return {
            "tools": tools,
            "total_cost": total_cost,
            "cost_available": found_any_price,
            "summary": summary
        }

    def _get_fallback_tools(self, summary_text: str) -> List[Dict[str, str]]:
        """Fallback tools if generation fails"""
        low = summary_text.lower()
        
        if "mirror" in low or "hang" in low:
            return [
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
                    "dimensions": "",
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
            return [
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


class StepsAgentJSON:
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

        # Parse step blocks
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

    def generate(self, summary: str, user_answers: Dict[int, str] = None, questions: List[str] = None) -> Dict[str, Any]:
        """
        Generate step-by-step plan in JSON format.
        Returns a dictionary with steps array and time estimation.
        """
        # Prepare enhanced context including user answers and handling skipped questions
        enhanced_context = summary
        
        if user_answers and questions:
            # Add user answers to the context
            answers_context = "\n\nUser's Answers to Questions:\n"
            skipped_questions = []
            
            for idx, answer in user_answers.items():
                if idx < len(questions):
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
        
        base_prompt = (
            "You are an expert DIY planner.\n"
            "Return a concise step-by-step plan as plain text (no JSON).\n"
            "Start with an intro line summarizing total steps and estimated time if possible.\n\n"
            "IMPORTANT: If any questions were skipped, consider all reasonable possibilities for those questions and provide comprehensive steps that cover different scenarios.\n\n"
            "Then for each step return EXACTLY this format (use the same labels and punctuation):\n"
            "Step No. : <Step No.>\n"
            "Step Title : <step title>\n"
            "Time : <Total time needed>\n"
            "Description : <Informative Description of the step in 2-3 lines>\n\n"
        )

        payload = {
            "model": "gpt-5-mini",
            "messages": [
                {"role": "system", "content": base_prompt},
                {"role": "user", "content": enhanced_context + "\n\nReturn the plan as plain text in the exact format."}
            ],
            "max_completion_tokens": 1000,
            "reasoning_effort": "low",
        }

        try:
            r = requests.post(self.api_url, headers=self.headers, json=payload)
            if r.status_code == 200:
                content = r.json()["choices"][0]["message"]["content"].strip()
                print (content)
                print("Headers:", r.headers)
                print("Body:", r.text)
                steps_plan = self._parse_steps_text(content)
                return self._convert_to_json_format(steps_plan)
            else:
                print(f"❌ Error {r.status_code}")
                print("Headers:", r.headers)
                print("Body:", r.text)
        except Exception as e:
            print("❌ ERROR:", str(e))
            raise HTTPException(status_code=500, detail="LLM personality generation")

        # # Enhanced fallback that considers skipped questions
        # if user_answers and questions:
        #     fallback_text = (
        #         "Here is your comprehensive step-by-step plan (considering all possibilities for skipped questions):\n\n"
        #         "Step No. : 1\nStep Title : Assess the situation\nTime : 15-20 min\nDescription : Evaluate all possible scenarios and determine the best approach based on available information.\n\n"
        #         "Step No. : 2\nStep Title : Prepare materials and tools\nTime : 10-15 min\nDescription : Gather all necessary tools and materials for the most comprehensive solution.\n\n"
        #         "Step No. : 3\nStep Title : Execute primary solution\nTime : 20-30 min\nDescription : Implement the main solution while being prepared for alternative approaches.\n\n"
        #         "Step No. : 4\nStep Title : Verify and adjust\nTime : 10-15 min\nDescription : Test the solution and make adjustments if needed for different scenarios.\n\n"
        #         "Step No. : 5\nStep Title : Final inspection\nTime : 5-10 min\nDescription : Ensure everything is properly completed and safe."
        #     )
        # else:
        #     fallback_text = (
        #         "Here is your step-by-step plan:\n\n"
        #         "Step No. : 1\nStep Title : Locate studs\nTime : 10-15 min\nDescription : Find studs for secure mounting.\n\n"
        #         "Step No. : 2\nStep Title : Mark mounting points\nTime : 10-15 min\nDescription : Measure and mark bracket positions.\n\n"
        #         "Step No. : 3\nStep Title : Install brackets\nTime : 15-20 min\nDescription : Drill pilot holes and mount wall brackets.\n\n"
        #         "Step No. : 4\nStep Title : Attach item\nTime : 5-10 min\nDescription : Mount securely and check level."
        #     )
        
        # steps_plan = self._parse_steps_text(fallback_text)
        # return self._convert_to_json_format(steps_plan)

    def _convert_to_json_format(self, steps_plan: StepsPlan) -> Dict[str, Any]:
        """Convert StepsPlan to JSON format"""
        steps_json = []
        for step in steps_plan.steps:
            steps_json.append({
                "order": step.step_no,
                "title": step.step_title,
                "est_time_min": step.time,
                "time_text": step.time_text,
                "summary": step.description,
                "status": "pending"
            })
        
        return {
            "steps": steps_json,
            "total_est_time_min": steps_plan.estimated_time,
            "total_steps": steps_plan.total_steps,
            "notes": f"Total estimated time: {minutes_to_human(steps_plan.estimated_time)}"
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
        self.tools_agent = ToolsAgentJSON()
        self.steps_agent = StepsAgentJSON()
        self.estimation_agent = EstimationAgent()
    
    def generate_complete_plan(self, summary: str, user_answers: Dict[int, str] = None, questions: List[str] = None) -> Dict[str, Any]:
        """
        Generate complete DIY plan including tools, steps, and estimations.
        Returns comprehensive JSON with all planning information.
        """
        try:
            # Generate tools and materials
            tools_data = self.tools_agent.generate(summary, user_answers, questions)
            
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

