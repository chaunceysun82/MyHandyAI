import os
import streamlit as st
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import base64
from PIL import Image
import io

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

# Load the qa_prompt
qa_prompt_text = load_prompt("qa_prompt.txt")

class ProblemRecognitionAgent:
    """Agent 1: Recognizes problems and requests relevant photos"""
    
    def __init__(self):
        self.api_key = os.getenv("GROK_API_KEY")
        self.api_url = "https://api.x.ai/v1/chat/completions"
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
                json={"model": "grok-3", "messages": messages, "max_tokens": 500}
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
                json={"model": "grok-3-mini", "messages": messages, "max_tokens": 300}
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
    """Agent 2: Analyzes images and generates specific questions"""
    
    def __init__(self):
        self.api_key = os.getenv("GROK_API_KEY")
        self.api_url = "https://api.x.ai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    def analyze_image(self, image_data: bytes, problem_type: str) -> Dict[str, Any]:
        """Analyze uploaded image and generate specific questions"""
        
        # Convert image to base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        system_prompt = f"""You are an expert DIY image analysis agent. Analyze the uploaded image for a {problem_type} problem and {qa_prompt_text}

Return a JSON response with:
- "analysis": Brief analysis of what you see in the image
- "questions": List of specific questions to ask (one by one)
- "first_question": The first question to ask immediately

Be specific and practical. Ask about things that would help provide better DIY advice."""

        messages = [
            {
                "role": "system", 
                "content": system_prompt
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Please analyze this image for a {problem_type} problem:"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ]
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={"model": "grok-4", "messages": messages, "max_tokens": 800}
            )
            
            if response.status_code == 200:
                data = response.json()
                text = data["choices"][0]["message"]["content"].strip()
                
                try:
                    import json
                    result = json.loads(text)
                    return result
                except:
                    return self._get_fallback_questions(problem_type)
            else:
                return self._get_fallback_questions(problem_type)
                
        except Exception as e:
            return self._get_fallback_questions(problem_type)
    
    def analyze_image_without_image(self, problem_type: str) -> Dict[str, Any]:
        """Analyze problem type and generate questions without actual image"""
        
        system_prompt = f"""You are an expert DIY analysis agent. Based on the problem type "{problem_type}", {qa_prompt_text}

Return a JSON response with:
- "analysis": Brief analysis of the problem type
- "questions": List of 3-5 specific questions to ask (one by one)
- "first_question": The first question to ask immediately

Be specific and practical. Ask about things that would help provide better DIY advice."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Generate questions for a {problem_type} problem"}
        ]
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={"model": "grok-3", "messages": messages, "max_tokens": 600}
            )
            
            if response.status_code == 200:
                data = response.json()
                text = data["choices"][0]["message"]["content"].strip()
                
                try:
                    import json
                    result = json.loads(text)
                    return result
                except:
                    return self._get_fallback_questions(problem_type)
            else:
                return self._get_fallback_questions(problem_type)
                
        except Exception as e:
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

class AgenticChatbot:
    """Main chatbot that coordinates between agents"""
    
    def __init__(self):
        self.problem_agent = ProblemRecognitionAgent()
        self.image_agent = ImageAnalysisAgent()
        self.current_state = "waiting_for_problem"
        self.problem_type = None
        self.questions = []
        self.current_question_index = 0
        self.user_answers = {}
    
    def process_message(self, user_message: str, uploaded_image: Optional[bytes] = None) -> str:
        """Process user message and return appropriate response"""
        
        if self.current_state == "waiting_for_problem":
            # Agent 1: Problem Recognition
            result = self.problem_agent.analyze_problem(user_message)
            self.problem_type = result["problem_type"]
            self.current_state = "waiting_for_photos"
            
            return result["response_message"]
        
        elif self.current_state == "waiting_for_photos":
            # Check if user says they uploaded an image or wants to proceed
            if uploaded_image or any(phrase in user_message.lower() for phrase in ["image uploaded", "photo uploaded", "uploaded", "image", "photo", "picture", "yes", "ok", "proceed", "continue"]):
                # Agent 2: Image Analysis (simulated for now)
                result = self.image_agent.analyze_image_without_image(self.problem_type)
                self.questions = result["questions"]
                self.current_question_index = 0
                self.current_state = "asking_questions"
                
                return f"Thank you! Now let's properly address your {self.problem_type.replace('_', ' ')}. MyHandyAI will ask a few questions to better understand your project.\n\nLet's start with one question at a time.\n\n{self.questions[0]}"
            else:
                return "Please upload a photo so I can better understand your project, or type 'image uploaded' to proceed."
        
        elif self.current_state == "asking_questions":
            # Store user's answer
            self.user_answers[self.current_question_index] = user_message
            
            # Move to next question
            self.current_question_index += 1
            
            if self.current_question_index < len(self.questions):
                return f"Thank you! Next up:\n\n{self.questions[self.current_question_index]}"
            else:
                # All questions answered, provide solution
                self.current_state = "waiting_for_problem"
                return self._generate_solution()
    
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