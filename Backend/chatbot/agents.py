import os
import streamlit as st
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
    # Go up one directory to reach the Test/PMs_Prompts_Test/prompts folder
    prompts_dir = os.path.join(script_dir, "..", "..", "Test", "PMs_Prompts_Test", "prompts")
    path = os.path.join(prompts_dir, filename)
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

class ProblemRecognitionAgent:
    """Agent 1: Recognizes problems and requests relevant photos"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    def analyze_problem(self, user_message: str) -> Dict[str, Any]:
        """Analyze user problem and determine what photos are needed"""
        
        system_prompt = """You are a DIY problem recognition agent. When a user describes a home improvement problem, analyze it and determine what photos would be most helpful.

Return a JSON response with:
- "problem_type": The type of problem (e.g., "hanging_mirror", "clogged_sink", "electrical_issue")
- "photo_requests": List of specific photo requests
- "response_message": A friendly message asking for the photos

Examples:
- "I want to hang a mirror" → Ask for mirror photo and wall photo
- "My sink is clogged" → Ask for sink photo and drain photo
- "Light switch not working" → Ask for switch photo and wiring photo

Be specific about what photos would help diagnose the problem."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User problem: {user_message}"}
        ]
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={"model": "gpt-4.1", "messages": messages, "max_tokens": 500}
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
            f"You are an expert DIY vision agent. Analyse the image for a "
            f"'{problem_type}' problem and {qa_prompt_text}\n\n"
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


class AgenticChatbot:
    """Main chatbot that coordinates between agents"""
    
    def __init__(self):
        self.problem_agent = ProblemRecognitionAgent()
        self.image_agent = ImageAnalysisAgent()
        self.summary_agent = SummaryAgent()
        self.current_state = "waiting_for_problem"
        self.problem_type = None
        self.questions = []
        self.current_question_index = 0
        self.user_answers = {}
        self.image_analysis = None
    
    def process_message(self, user_message: str, uploaded_image: Optional[bytes] = None) -> str:
        """Process user message and return appropriate response"""
        
        if self.current_state == "waiting_for_problem":
            # Agent 1: Problem Recognition
            result = self.problem_agent.analyze_problem(user_message)
            self.problem_type = result["problem_type"]
            self.current_state = "waiting_for_photos"
            
            return result["response_message"]
        
        elif self.current_state == "waiting_for_photos":
            if uploaded_image:
                result = self.image_agent.analyze_image(uploaded_image, self.problem_type)
                
                # Debug: Print the result structure
                print(f"DEBUG: result type: {type(result)}")
                print(f"DEBUG: result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
                print(f"DEBUG: result: {result}")
                
                # Validate result structure
                if not isinstance(result, dict) or "analysis" not in result or "questions" not in result:
                    return "Sorry, I had trouble analyzing the image. Please try uploading it again."
                
                # Handle questions structure - they might be strings or dicts with 'text' key
                questions_raw = result["questions"]
                self.questions = []
                for q in questions_raw:
                    if isinstance(q, str):
                        self.questions.append(q)
                    elif isinstance(q, dict) and "text" in q:
                        self.questions.append(q["text"])
                    else:
                        self.questions.append(str(q))
                
                self.current_question_index = 0
                self.current_state = "asking_questions"

                # analysis might be str or dict → normalise to string
                analysis_text = result.get("analysis", "")
                
                # Debug: Print the type and value
                print(f"DEBUG: analysis_text type: {type(analysis_text)}")
                print(f"DEBUG: analysis_text value: {analysis_text}")
                
                # Force conversion to string with multiple fallbacks
                if not isinstance(analysis_text, str):
                    try:
                        analysis_text = json.dumps(analysis_text, indent=2)
                    except (TypeError, ValueError):
                        try:
                            analysis_text = str(analysis_text)
                        except:
                            analysis_text = "I can see your image and will help you with your project."
                
                # Final safety check - ensure it's a string
                if not isinstance(analysis_text, str):
                    analysis_text = "I can see your image and will help you with your project."
                
                # Debug: Print the final type and value
                print(f"DEBUG: Final analysis_text type: {type(analysis_text)}")
                print(f"DEBUG: Final analysis_text value: {analysis_text}")

                # Store the image analysis for later use
                self.image_analysis = analysis_text
                
                # Safety check for questions
                if not self.questions:
                    return (
                        "Great, thanks for the photo!\n\n"
                        f"{analysis_text}\n\n"
                        "I can see your project. Let me provide you with some general guidance based on what I observe."
                    )
                
                first_question = self.questions[0]
                
                return (
                    f"Great, thanks for the photo!\n\n{analysis_text}\n\n"
                    "I'll ask a few quick questions one-by-one so I can give you "
                    "the safest fix.\n\n" + first_question
                )
            else:
                return "Please upload the requested photo so I can analyse it."
        
        elif self.current_state == "asking_questions":
            # Store user's answer
            self.user_answers[self.current_question_index] = user_message
            
            # Move to next question
            self.current_question_index += 1
            
            if self.current_question_index < len(self.questions):
                return f"Thank you! Next up:\n\n{self.questions[self.current_question_index]}"
            else:
                # All questions answered, create summary
                self.current_state = "showing_summary"
                summary = self.summary_agent.create_summary(
                    self.problem_type, 
                    self.image_analysis, 
                    self.user_answers
                )
                return (
                    f"Perfect! Let me summarize what I understand about your problem:\n\n"
                    f"**{summary}**\n\n"
                    f"Does this sound correct? Please reply with 'yes' if this is accurate, "
                    f"or 'no' if I misunderstood something."
                )
        
        elif self.current_state == "showing_summary":
            user_response = user_message.lower().strip()
            
            if user_response in ['yes', 'y', 'correct', 'right', 'accurate']:
                # User confirms summary, proceed to solution
                self.current_state = "waiting_for_problem"
                return self._generate_solution()
            elif user_response in ['no', 'n', 'incorrect', 'wrong', 'not right']:
                # User disagrees with summary, restart the process
                self.reset()
                return (
                    "I apologize for misunderstanding. Let's start over. "
                    "Please describe your problem again, and I'll make sure to get it right this time."
                )
            else:
                # Unclear response, ask for clarification
                return (
                    "I need a clear yes or no answer. Does my summary of your problem sound correct?\n\n"
                    "Please reply with 'yes' if it's accurate, or 'no' if I misunderstood something."
                )
    
    def _generate_solution(self) -> str:
        """Generate solution based on collected information"""
        # This would integrate with your existing Grok API call
        # For now, return a summary
        answers_summary = "\n".join([f"Q{i+1}: {answer}" for i, answer in self.user_answers.items()])
        
        return f"Perfect! Based on your answers:\n{answers_summary}\n\nI'll now provide you with a detailed step-by-step solution for your {self.problem_type.replace('_', ' ')} project."
    
    def reset(self):
        """Reset the chatbot state"""
        self.current_state = "waiting_for_problem"
        self.problem_type = None
        self.questions = []
        self.current_question_index = 0
        self.user_answers = {}
        self.image_analysis = None 