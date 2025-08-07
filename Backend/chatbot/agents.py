import os
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import base64
from PIL import Image
import io
import json

load_dotenv()

def load_prompt(filename):
    """Load prompt from file, removing comment lines starting with #"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, "prompts", filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Remove lines starting with #
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
            "model": "gpt-4.1-nano",
            "messages": [
                {"role": "system", "content": "You are a DIY customer service agent from MyHandyAI , your task is to greet the user e.g. 'Thanks for using MyHandyAI! Tell me what you'd like to do or fix.' "},
            ],
            "max_tokens": 50,
            "temperature": 0.7
        }
        try:
            r = requests.post(self.api_url, headers=self.headers, json=payload, timeout=10)
            return r.json()["choices"][0]["message"]["content"]
        except:
            return "Thanks for using MyHandyAI! Tell me what you'd like to do or fix."

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
                    import json
                    result = json.loads(text)
                    return result
                except:
                    # Fallback if JSON parsing fails
                    return {
                        "problem_type": "general",
                        "photo_requests": ["Please share a photo of the area you're working on"],
                        "response_message": text
                    }
            else:
                return self._get_fallback_response(user_message)
                
        except Exception as e:
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
                    import json
                    result = json.loads(text)
                    return result
                except:
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
                
        except Exception as e:
            # If any error occurs, return a generic response
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
            "Content-Type":  "application/json",
        }

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
                    # Validate the result has the expected structure
                    if isinstance(result, dict) and "analysis" in result and "questions" in result:
                        return result
                    else:
                        # If structure is wrong, fall back
                        return self._get_fallback_questions(problem_type)
                except (json.JSONDecodeError, KeyError, TypeError):
                    # If JSON parsing fails, fall back
                    return self._get_fallback_questions(problem_type)
        except Exception:
            pass                                # fall through to fallback

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
                json={"model": "gpt-4.1", "messages": messages, "max_tokens": 800},
                timeout=20
            )
            if r.status_code == 200:
                txt = r.json()["choices"][0]["message"]["content"].strip()
                try:
                    result = json.loads(txt)
                    # Validate the result has the expected structure
                    if isinstance(result, dict) and "analysis" in result and "questions" in result:
                        return result
                    else:
                        # If structure is wrong, fall back
                        return self._get_fallback_questions(problem_type)
                except (json.JSONDecodeError, KeyError, TypeError):
                    # If JSON parsing fails, fall back
                    return self._get_fallback_questions(problem_type)
        except Exception:
            pass                                # fall through to fallback

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
            result = json.loads(data)
            act = result.get("action")
            msg = result.get("message", "")
            if act == "skip":
                return (msg, True)
            if act == "accept":
                return ("", True)
            
            return (msg, False)
        except Exception:
            
            fallback = (
                f"I didn’t quite catch that. Could you clarify your answer to:\n\n**{question}**"
            )
            return (fallback, False)
        
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
            return json.loads(result).get("skip_questions", False)
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
        self.questions              = []
        self.current_question_index = 0
        self.user_answers           = {}
        self.image_analysis         = None

    def greet(self):
        return self.problem_agent.greetings()


    def process_message(self, user_message: str, uploaded_image: Optional[bytes] = None) -> str:
        # 1) Capture the user's free‐form description
        if self.current_state == "waiting_for_problem":
            self.user_description = user_message
            result = self.problem_agent.analyze_problem(user_message)
            self.problem_type = result["problem_type"]
            self.current_state = "waiting_for_photos"
            return result["response_message"]

        # 2) Handle photo upload or skip
        if self.current_state == "waiting_for_photos":
            # Check if user wants to skip photos
            if user_message.lower().strip() in ["skip", "I don't have a photo", "no photo", "no image", "skip photos", "no photos"]:
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
            resp = user_message.lower().strip()
            if resp in ["yes", "y", "correct", "right", "accurate"]:
                combined = {0: self.user_description}
                for idx, ans in self.user_answers.items():
                    combined[idx + 1] = ans
                final_summary = self.summary_agent.create_summary(
                    self.problem_type,
                    self.image_analysis,
                    combined
                )
                reply = f"Perfect! Here’s the final summary:\n\n**{final_summary}**\n\n" \
                        f"I'll now provide the detailed steps for your {self.problem_type.replace('_',' ')}."
                self.reset()
                return reply

            if resp in ["no", "n", "incorrect", "wrong", "not right"]:
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
                            # 2a) If the description alone suffices, skip the Q&A loop
        if self.description_agent.assess(self.user_description):
                # combine description as answer #0
                combined = {0: self.user_description}
                summary = self.summary_agent.create_summary(
                    self.problem_type,
                    self.image_analysis,
                    combined
                )
                self.current_state = "showing_summary"
                
                # Determine the appropriate message based on whether image was provided
                if "photo" in self.image_analysis.lower() or "image" in self.image_analysis.lower():
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
            if "photo" in self.image_analysis.lower() or "image" in self.image_analysis.lower():
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
        if "photo" in self.image_analysis.lower() or "image" in self.image_analysis.lower():
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
