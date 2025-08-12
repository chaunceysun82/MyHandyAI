# agents.py  (fixed & defensive)
import os
import requests
from typing import List, Dict, Any, Optional, Iterable
from dotenv import load_dotenv
import base64
from PIL import Image
import re
import json

load_dotenv()

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
            "model": "gpt-5-nano",
            "messages": [
                {"role": "system", "content": "You are a DIY customer service agent called MyHandyAI , your task is to greet the user, introduce yourself and ask the user to describe the project/repair/fix to be done"},
            ],
            "max_completion_tokens": 100,
            "reasoning_effort": "low",
        }
        try:
            r = requests.post(self.api_url, headers=self.headers, json=payload, timeout=10)
            return r.json()["choices"][0]["message"]["content"]
        except:
            return "Thanks for using MyHandyAI! Tell me what you'd like to do or fix."

    def valid_description(self, message):
        payload = {
            "model": "gpt-5-nano",
            "messages": [
                {"role": "system", "content": "You are a DIY customer service agent, your task is to determine if the description/context of the repair/fix/project is coherent respond only 'True' or 'False'"},
                {"role": "user", "content": message}
            ],
            "max_completion_tokens": 50,
            "reasoning_effort": "low",
        }
        try:
            r = requests.post(self.api_url, headers=self.headers, json=payload, timeout=10)
            print(r.json()["choices"][0]["message"]["content"])
            print ("testing bot")
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
                json={"model": "gpt-5-mini", "messages": messages, "max_completion_tokens": 500, "reasoning_effort": "low"}
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
                json={"model": "gpt-5-mini", "messages": messages, "max_completion_tokens": 500, "reasoning_effort": "low"}
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
            "model": "gpt-5-nano",
            "messages": [
                {"role": "system", "content": "Detect if the user doesn't have an image or want to skip the image upload (e.g 'skip','I dont have an image', etc...)  Respond only with 'True' or 'False'"},
                {"role": "user", "content": message}
            ],
            "max_completion_tokens": 50,
            "reasoning_effort": "low",
        }
        try:
            r = requests.post(self.api_url, headers=self.headers, json=payload, timeout=10)
            print("skip image ", r.json()["choices"][0]["message"]["content"])
            return r.json()["choices"][0]["message"]["content"] == "True"
        except:
            return True

    def analyze_image(self, image_data: bytes, problem_type: str) -> Dict[str, Any]:
        """Call GPT-5 Vision with a base64-encoded image and get back questions"""

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
                json={"model": "gpt-5-mini", "messages": messages, "max_completion_tokens": 800,"reasoning_effort": "low"},
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
                json={"model": "gpt-5-mini", "messages": messages, "max_completion_tokens": 800, "reasoning_effort": "low"}
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
            "model": "gpt-5-nano",
            "messages": [
                {"role": "system", "content": "You are a affirmative/negative detector, your task is to determine if the user answer is affirmative to proceed with next steps or negative to not continue answer only '1' for affirmative '2' for negative and '0' if you cannot determine with the message"},
                {"role": "user", "content": message}
            ],
            "max_completion_tokens": 50,
            "reasoning_effort": "low",
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
                json={"model": "gpt-5-mini", "messages": messages, "max_completion_tokens": 1000, "reasoning_effort": "low"}
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            pass

        # Fallback summary
        return f"I understand you have a {problem_type.replace('_', ' ')} issue. Based on the image and your answers, I can help you resolve this problem."


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
            "model": "gpt-5-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": "Please classify and respond in JSON."}
            ],
            "max_completion_tokens": 1000,
            "reasoning_effort": "low",
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
                json={"model": "gpt-5-mini", "messages": messages, "max_completion_tokens": 500, "reasoning_effort": "low"}
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
            "model": "gpt-5-nano",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": "Please respond with JSON only."}
            ],
            "max_completion_tokens": 50,
            "reasoning_effort": "low",
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
                # User confirmed the summary; create final summary
                combined = {0: self.user_description}
                for idx, ans in self.user_answers.items():
                    combined[idx + 1] = ans
                final_summary = self.summary_agent.create_summary(
                    self.problem_type,
                    self.image_analysis,
                    combined
                )

                # The tools, steps, and estimations are now handled by the content planner
                # The chatbot's job is complete - hand off to the next webapp page
                reply = (
                    f"Perfect! I've analyzed your {self.problem_type.replace('_', ' ')} project and gathered all the information needed.\n\n"
                    f"**Summary:** {final_summary}\n\n"
                    "Your project plan is ready! The next page will show you:\n"
                    "• Tools and materials required\n"
                    "• Step-by-step instructions\n"
                    "• Time and cost estimates\n\n"
                    "Let's proceed to your personalized project plan!"
                )

                # reset the conversation state after producing the complete solution
                self.current_state = "complete"
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
