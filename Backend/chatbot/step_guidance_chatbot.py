# step_guidance_chatbot.py
# Step-by-Step Guidance Chatbot for DIY Task Execution
import os
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

def load_prompt(filename):
    """Load prompt from file, removing comment lines starting with #"""
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(backend_dir, "prompts", filename)
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


def _extract_response_text(data: Dict[str, Any]) -> str:
    """Extract response text from OpenAI API responses (handles both Responses API and chat/completions)"""
    # Primary: responses API
    if "output_text" in data and data["output_text"]:
        return data["output_text"]
    # Secondary: structured tokens
    if "output" in data and isinstance(data["output"], list):
        # Find first text segment
        for part in data["output"]:
            for c in (part.get("content") or []):
                if c.get("type") == "output_text" and c.get("text"):
                    return c["text"]
                if c.get("type") == "text" and c.get("text"):
                    return c["text"]
    # Fallback: chat.completions style (just in case)
    if "choices" in data and data["choices"]:
        msg = data["choices"][0].get("message", {})
        if isinstance(msg, dict) and msg.get("content"):
            return msg["content"]
    return ""


class StepContextAgent:
    """Manages and tracks the current execution context"""
    
    def __init__(self):
        self.current_step = 1
        self.total_steps = 4
        self.task_name = ""
        self.user_progress = {}
        self.current_tools = []
        self.current_materials = []
        self.step_start_time = None
        self.step_completion_status = {}
        self.steps_data: Dict[int, Dict[str, Any]] = {}  # Store actual step data from planner as dict
        self.tools_data: Dict[str, Dict[str, Any]] = {}  # Store actual tools data from planner as dict
        self.problem_summary = ""  # Store problem summary from agents
        
    def set_task_context(self, task_name: str, total_steps: int, steps_data: Optional[Dict[int, Dict[str, Any]]] = None, tools_data: Optional[Dict[str, Dict[str, Any]]] = None, problem_summary: str = ""):
        """Set the overall task context with real data from planner and agents"""
        self.task_name = task_name
        self.total_steps = total_steps
        self.current_step = 1
        self.user_progress = {}
        self.step_completion_status = {}
        self.steps_data = steps_data or {}
        self.tools_data = tools_data or {}
        self.problem_summary = problem_summary
        
        # Extract tools from steps data
        if self.steps_data:
            all_tools = set()
            for step in self.steps_data.values():
                all_tools.update(step.get('tools_needed', []))
            self.current_tools = list(all_tools)
        
    def move_to_step(self, step_number: int):
        """Move to a specific step"""
        if 1 <= step_number <= self.total_steps:
            self.current_step = step_number
            self.step_start_time = datetime.now()
            
            # Update current tools and materials for this step
            step = self.steps_data.get(step_number, {})
            self.current_tools = step.get('tools_needed', [])
            self.current_materials = step.get('materials_needed', [])
            
            return True
        return False
        
    def mark_step_complete(self, step_number: int, completion_notes: str = ""):
        """Mark a step as completed"""
        self.step_completion_status[step_number] = {
            "completed": True,
            "completion_time": datetime.now(),
            "notes": completion_notes
        }
        
    def get_current_context(self) -> Dict[str, Any]:
        """Get current execution context"""
        current_step_data = self.steps_data.get(self.current_step)
        
        return {
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "task_name": self.task_name,
            "current_tools": self.current_tools,
            "current_materials": self.current_materials,
            "step_start_time": self.step_start_time.isoformat() if self.step_start_time else None,
            "completion_status": self.step_completion_status,
            "current_step_data": current_step_data,
            "problem_summary": self.problem_summary
        }
        
    def get_step_instructions(self, step_number: int) -> Optional[Dict[str, Any]]:
        """Get detailed instructions for a specific step"""
        step = self.steps_data.get(step_number)
        if not step:
            return None
        return {
            "step_no": step_number,
            "title": step.get('title', f'Step {step_number}'),
            "instructions": step.get('instructions', ''),
            "time": step.get('estimated_time', ''),
            "time_text": step.get('estimated_time', ''),
            "tools_needed": step.get('tools_needed', []),
            "safety_warnings": step.get('safety_warnings', []),
            "tips": step.get('tips', [])
        }
        
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific tool - case-insensitive lookup"""
        for k, v in self.tools_data.items():
            if k.lower() == tool_name.lower():
                return v
        return None


class StepInstructionAgent:
    """Provides detailed guidance for step-by-step instructions"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        # Use Responses API for GPT-5 models
        self.api_url = "https://api.openai.com/v1/responses"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
    def _post_with_retry(self, payload: Dict[str, Any], tries: int = 2, timeout: int = 15):
        """Post with retry on timeouts/5xx errors"""
        last_err = None
        for _ in range(tries):
            try:
                r = requests.post(self.api_url, headers=self.headers, json=payload, timeout=timeout)
                if r.status_code >= 500:
                    last_err = r.text
                    continue
                return r
            except requests.Timeout as e:
                last_err = str(e)
                continue
        # Return None to indicate failure
        return None
        
    def get_step_guidance(self, step_data: Dict[str, Any], user_message: str = "", context: Dict[str, Any] = None) -> str:
        """Get detailed guidance for a specific step"""
        
        # Check API key presence
        if not self.api_key:
            return "❌ Missing OPENAI_API_KEY; cannot generate guidance right now."
        
        # Load step instruction prompt template
        step_prompt_template = load_prompt("chat2_step_instruction_prompt.txt")
        
        # Format the prompt with step data and context
        step_prompt = step_prompt_template.format(
            step_title=step_data.get('title', ''),
            step_instructions=step_data.get('instructions', ''),
            step_time=step_data.get('time_text', ''),
            step_tools=", ".join(step_data.get('tools_needed', [])),
            step_safety="\n".join(step_data.get('safety_warnings', [])),
            step_tips="\n".join(step_data.get('tips', [])),
            user_message=user_message if user_message else "How do I complete this step?",
            problem_summary=context.get('problem_summary', '') if context else '',
            current_step=context.get('current_step', 1) if context else 1,
            total_steps=context.get('total_steps', 4) if context else 4
        )
        
        try:
            response = self._post_with_retry({
                "model": "gpt-5-mini",
                "input": step_prompt,
                "max_output_tokens": 400,
                "reasoning": {"effort": "medium"}
            })
            
            if response is None:
                return "❌ Step Instruction API Error: Request failed after retries"
            
            if response.status_code == 200:
                data = response.json()
                text = _extract_response_text(data)
                if not text:
                    return "❌ API returned an empty response."
                return text
            else:
                return f"❌ Step Instruction API Error: HTTP {response.status_code}. Response: {response.text}"
                
        except Exception as e:
            print(f"Step instruction error: {e}")
            return f"❌ Step Instruction API Error: {str(e)}"
            


class SafetyValidationAgent:
    """Ensures user safety and compliance with best practices"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        # Use Responses API for GPT-5 models
        self.api_url = "https://api.openai.com/v1/responses"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
    def _post_with_retry(self, payload: Dict[str, Any], tries: int = 2, timeout: int = 15):
        """Post with retry on timeouts/5xx errors"""
        last_err = None
        for _ in range(tries):
            try:
                r = requests.post(self.api_url, headers=self.headers, json=payload, timeout=timeout)
                if r.status_code >= 500:
                    last_err = r.text
                    continue
                return r
            except requests.Timeout as e:
                last_err = str(e)
                continue
        # Return None to indicate failure
        return None
        
    def validate_step_safety(self, step_context: Dict[str, Any], user_message: str = "") -> Dict[str, Any]:
        """Validate safety requirements for current step"""
        
        # Check API key presence
        if not self.api_key:
            return {"safety_level": "unknown", "warnings": ["Missing API key"], "required_equipment": [], "precautions": [], "emergency_info": "Cannot assess safety without API access"}
        
        # Load safety prompt template
        safety_prompt_template = load_prompt("chat2_safety_prompt.txt")
        
        # Get current step data for more specific safety assessment
        current_step_data = step_context.get('current_step_data', {})
        
        # Format the prompt with context
        safety_prompt = safety_prompt_template.format(
            task_name=step_context.get('task_name', 'Unknown'),
            current_step=step_context.get('current_step', 1),
            total_steps=step_context.get('total_steps', 4),
            tools=', '.join(step_context.get('current_tools', [])),
            materials=', '.join(step_context.get('current_materials', [])),
            user_message=user_message,
            step_title=current_step_data.get('title', ''),
            step_safety_warnings='\n'.join(current_step_data.get('safety_warnings', [])),
            problem_summary=step_context.get('problem_summary', '')
        )
        
        try:
            response = self._post_with_retry({
                "model": "gpt-5-nano",
                "input": safety_prompt,
                "max_output_tokens": 300,
                "reasoning": {"effort": "minimal"}
            })
            
            if response is None:
                return {
                    "safety_level": "medium",
                    "warnings": ["Safety assessment unavailable due to API failure"],
                    "required_equipment": ["Basic PPE (gloves/eye protection)"],
                    "precautions": ["Proceed slowly", "Follow instructions carefully"],
                    "emergency_info": "API request failed after retries"
                }
            
            if response.status_code == 200:
                data = response.json()
                content = _extract_response_text(data)
                
                if not content:
                    # Use step's own safety warnings when API returns empty
                    warnings = current_step_data.get('safety_warnings', [])
                    return {
                        "safety_level": "medium",
                        "warnings": ["Automatic assessment unavailable."] + warnings,
                        "required_equipment": ["Basic PPE (gloves/eye protection)"],
                        "precautions": ["Proceed slowly", "Follow instructions carefully"],
                        "emergency_info": "API returned empty response"
                    }
                
                # Try to parse JSON response
                try:
                    safety_data = json.loads(content)
                    return safety_data
                except json.JSONDecodeError:
                    # Return structured error response with step's safety warnings
                    warnings = current_step_data.get('safety_warnings', [])
                    return {
                        "safety_level": "medium",
                        "warnings": ["Automatic assessment unavailable."] + warnings,
                        "required_equipment": ["Basic PPE (gloves/eye protection)"],
                        "precautions": ["Proceed slowly", "Follow instructions carefully"],
                        "emergency_info": f"Raw response parsing failed: {content[:120]}..."
                    }
            else:
                return {
                    "safety_level": "medium",
                    "warnings": [f"Safety API error: HTTP {response.status_code}"],
                    "required_equipment": ["Basic PPE (gloves/eye protection)"],
                    "precautions": ["Proceed slowly", "Follow instructions carefully"],
                    "emergency_info": f"API error: {response.text[:100]}..."
                }
                
        except Exception as e:
            print(f"Safety validation error: {e}")
            return {
                "safety_level": "medium",
                "warnings": [f"Safety check failed: {str(e)}"],
                "required_equipment": ["Basic PPE (gloves/eye protection)"],
                "precautions": ["Proceed slowly", "Follow instructions carefully"],
                "emergency_info": "Safety assessment unavailable due to error"
            }
            


class ToolGuidanceAgent:
    """Provides tool-specific guidance and troubleshooting"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        # Use Responses API for GPT-5 models
        self.api_url = "https://api.openai.com/v1/responses"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
    def _post_with_retry(self, payload: Dict[str, Any], tries: int = 2, timeout: int = 15):
        """Post with retry on timeouts/5xx errors"""
        last_err = None
        for _ in range(tries):
            try:
                r = requests.post(self.api_url, headers=self.headers, json=payload, timeout=timeout)
                if r.status_code >= 500:
                    last_err = r.text
                    continue
                return r
            except requests.Timeout as e:
                last_err = str(e)
                continue
        # Return None to indicate failure
        return None
        
    def get_tool_guidance(self, tool_name: str, current_step: int, user_message: str = "", context: Dict[str, Any] = None) -> str:
        """Get guidance for using a specific tool"""
        
        # Check API key presence
        if not self.api_key:
            return "❌ Missing OPENAI_API_KEY; cannot generate guidance right now."
        
        # Load tool guidance prompt template
        tool_prompt_template = load_prompt("chat2_tool_guidance_prompt.txt")
        
        # Get tool info from context if available - fix dict access
        tool_info = None
        if context and context.get('current_step_data'):
            step_data = context['current_step_data']
            tools_lower = [t.lower() for t in step_data.get('tools_needed', [])]
            if tool_name.lower() in tools_lower:
                tool_info = {
                    'name': tool_name,
                    'context': f"Step {current_step} of {context.get('total_steps', 4)}",
                    'step_title': step_data.get('title', ''),
                    'safety_warnings': step_data.get('safety_warnings', [])
                }
        
        # Format the prompt with context
        tool_prompt = tool_prompt_template.format(
            tool_name=tool_name,
            current_step=current_step,
            user_message=user_message if user_message else "How to use this tool effectively?",
            task_context=f"Step {current_step} of DIY project",
            step_title=tool_info.get('step_title', '') if tool_info else '',
            safety_warnings='\n'.join(tool_info.get('safety_warnings', [])) if tool_info else '',
            problem_summary=context.get('problem_summary', '') if context else ''
        )
        
        try:
            response = self._post_with_retry({
                "model": "gpt-5-mini",
                "input": tool_prompt,
                "max_output_tokens": 300,
                "reasoning": {"effort": "medium"}
            })
            
            if response is None:
                return "❌ Tool API Error: Request failed after retries"
            
            if response.status_code == 200:
                data = response.json()
                text = _extract_response_text(data)
                if not text:
                    return "❌ API returned an empty response."
                return text
            else:
                return f"❌ Tool API Error: HTTP {response.status_code}. Response: {response.text}"
                
        except Exception as e:
            print(f"Tool guidance error: {e}")
            return f"❌ Tool API Error: {str(e)}"
            


class TaskExecutionAgent:
    """Main agent that provides real-time guidance during task execution"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        # Use Responses API for GPT-5 models
        self.api_url = "https://api.openai.com/v1/responses"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # Initialize other agents
        self.context_agent = StepContextAgent()
        self.safety_agent = SafetyValidationAgent()
        self.tool_agent = ToolGuidanceAgent()
        self.step_instruction_agent = StepInstructionAgent()
        
        # Conversation history - cap at 50 turns to prevent memory leaks
        self.conversation_history = []
        self.max_history = 50
        
    def _post_with_retry(self, payload: Dict[str, Any], tries: int = 2, timeout: int = 10):
        """Post with retry on timeouts/5xx errors"""
        last_err = None
        for _ in range(tries):
            try:
                r = requests.post(self.api_url, headers=self.headers, json=payload, timeout=timeout)
                if r.status_code >= 500:
                    last_err = r.text
                    continue
                return r
            except requests.Timeout as e:
                last_err = str(e)
                continue
        # Return None to indicate failure
        return None
        
    def start_task(self, task_name: str, total_steps: int, steps_data: Optional[Dict[int, Dict[str, Any]]] = None, tools_data: Optional[Dict[str, Dict[str, Any]]] = None, problem_summary: str = "") -> str:
        """Start a new task and provide initial guidance"""
        self.context_agent.set_task_context(task_name, total_steps, steps_data, tools_data, problem_summary)
        # Ensure step 1 context is populated
        self.context_agent.move_to_step(1)
        
        welcome_message = f"""
🎯 **Welcome to {task_name}!**

I'm your MyHandyAI Assistant, here to guide you through {total_steps} steps to complete this project safely and successfully.

**Current Status**: Ready to begin Step 1
**Safety Level**: {self._get_initial_safety_level()}

What would you like to know about getting started? You can ask me about:
• **Step Instructions**: "What do I do for step 1?"
• **Safety Requirements**: "Is this step safe?"
• **Tools Needed**: "How do I use the [tool name]?"
• **General Help**: "I'm stuck, can you help?"
• **Progress**: "What's my current status?"
"""
        
        self.conversation_history.append({"role": "assistant", "content": welcome_message})
        return welcome_message
        
    def process_user_message(self, user_message: str) -> str:
        """Process user message and provide appropriate guidance"""
        
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": user_message})
        
        # Get current context
        context = self.context_agent.get_current_context()
        
        # Analyze user message and provide response
        response = self._generate_guidance_response(user_message, context)
        
        # Add response to history and cap length
        self.conversation_history.append({"role": "assistant", "content": response})
        if len(self.conversation_history) > self.max_history:
            # Keep last 50 turns (25 user + 25 assistant)
            self.conversation_history = self.conversation_history[-self.max_history:]
        
        return response
        
    def _generate_guidance_response(self, user_message: str, context: Dict[str, Any]) -> str:
        """Generate appropriate guidance response based on user message and context"""
        
        # Use intelligent LLM-based intent detection
        intent = self._detect_intent_with_llm(user_message, context)
        
        # Debug: Print the detected intent
        print(f"🔍 Detected intent: '{intent}' for message: '{user_message}'")
        
        # Route based on detected intent
        if intent == "step_instructions":
            return self._handle_step_instruction_request(user_message, context)
        elif intent == "safety_check":
            safety_info = self.safety_agent.validate_step_safety(context, user_message)
            return self._format_safety_response(safety_info)
        elif intent == "tool_guidance":
            tool_name = self._identify_tool_from_message(user_message, context)
            if tool_name:
                tool_guidance = self.tool_agent.get_tool_guidance(tool_name, context["current_step"], user_message, context)
                return f"🔧 **Tool Guidance for {tool_name.title()}:**\n\n{tool_guidance}"
            else:
                return "🔧 **Tool Question:** I'd be happy to help with tool guidance! Which specific tool are you asking about?"
        elif intent == "step_progression":
            return self._handle_step_progression(user_message, context)
        elif intent == "general_help":
            return self._provide_general_help(context)
        elif intent == "status_check":
            return self._get_current_status_summary(context)
        else:  # clarification
            return self._ask_for_clarification(context)
        
    def _handle_step_instruction_request(self, user_message: str, context: Dict[str, Any]) -> str:
        """Handle requests for step-by-step instructions"""
        current_step_data = context.get('current_step_data')
        
        if not current_step_data:
            return "I don't have detailed instructions for this step yet. Please ask about safety, tools, or general help!"
        
        # Get detailed step guidance
        step_guidance = self.step_instruction_agent.get_step_guidance(current_step_data, user_message, context)
        
        return f"📋 **Step {context['current_step']} Instructions:**\n\n{step_guidance}"
        
    def _format_safety_response(self, safety_info) -> str:
        """Format safety information into a readable response"""
        
        # Guard against non-dict responses
        if not isinstance(safety_info, dict):
            return f"❌ Safety check failed: {safety_info}"
        
        safety_level_emoji = {
            "low": "🟢",
            "medium": "🟡", 
            "high": "🔴"
        }
        
        emoji = safety_level_emoji.get(safety_info.get("safety_level", "medium"), "🟡")
        
        response = f"""
{emoji} **Safety Assessment: {safety_info.get('safety_level', 'medium').title()} Risk**

⚠️ **Warnings:**
{chr(10).join(f"• {warning}" for warning in safety_info.get('warnings', []))}

🛡️ **Required Safety Equipment:**
{chr(10).join(f"• {equipment}" for equipment in safety_info.get('required_equipment', []))}

💡 **Precautions:**
{chr(10).join(f"• {precaution}" for precaution in safety_info.get('precautions', []))}

"""
        
        if safety_info.get("emergency_info"):
            response += f"🚨 **Emergency Info:** {safety_info['emergency_info']}\n\n"
            
        response += "**Are you ready to proceed with these safety measures in place?**"
        
        return response
        
    def _detect_intent_with_llm(self, user_message: str, context: Dict[str, Any]) -> str:
        """Use LLM to intelligently detect user intent"""
        
        # Check API key presence
        if not self.api_key:
            print("❌ Missing API key, falling back to keyword detection")
            return self._detect_intent_fallback(user_message)
        
        # Load intent detection prompt template
        intent_prompt_template = load_prompt("chat2_intent_detection_prompt.txt")
        
        # Get current step data for context
        current_step_data = context.get('current_step_data', {})
        step_title = current_step_data.get('title', f'Step {context.get("current_step", 1)}') if current_step_data else f'Step {context.get("current_step", 1)}'
        
        # Format the prompt with context
        intent_prompt = intent_prompt_template.format(
            task_name=context.get('task_name', 'Unknown'),
            current_step=context.get('current_step', 1),
            total_steps=context.get('total_steps', 4),
            step_title=step_title,
            available_tools=', '.join(context.get('current_tools', [])),
            safety_warnings='\n'.join(current_step_data.get('safety_warnings', [])) if current_step_data else '',
            problem_summary=context.get('problem_summary', ''),
            user_message=user_message
        )
        
        try:
            # Debug: Print the prompt being sent
            print(f"🔍 Sending intent detection prompt: {intent_prompt[:200]}...")
            print(f"🔍 API URL: {self.api_url}")
            # Do not print full headers with secrets
            print(f"🔍 Auth header present: {'Authorization' in self.headers}")
            
            response = self._post_with_retry({
                "model": "gpt-5-nano",
                "input": intent_prompt,
                "max_output_tokens": 50,
                "reasoning": {"effort": "minimal"}
            })
            
            if response is None:
                print("❌ Intent detection API failed after retries, falling back to keyword detection")
                return self._detect_intent_fallback(user_message)
            
            if response.status_code == 200:
                data = response.json()
                text = _extract_response_text(data)
                
                if not text:
                    print("❌ Intent detection API returned empty response, falling back to keyword detection")
                    return self._detect_intent_fallback(user_message)
                
                intent = text.strip().lower()
                
                # Validate intent
                valid_intents = ["step_instructions", "safety_check", "tool_guidance", 
                               "step_progression", "general_help", "status_check", "clarification"]
                
                if intent in valid_intents:
                    print(f"🔍 Intent detected: {intent} for message: '{user_message[:50]}...'")
                    return intent
                else:
                    print(f"⚠️ Invalid intent detected: {intent}")
                    return "clarification"
            else:
                print(f"❌ Intent detection API error: {response.status_code}")
                print(f"❌ Response: {response.text}")
                # Fallback to keyword-based detection when LLM fails
                print("🔄 Falling back to keyword-based intent detection")
                return self._detect_intent_fallback(user_message)
                
        except Exception as e:
            print(f"❌ Intent detection error: {e}")
            # Fallback to keyword-based detection when LLM fails
            print("🔄 Falling back to keyword-based intent detection")
            return self._detect_intent_fallback(user_message)
            
    def _detect_intent_fallback(self, user_message: str) -> str:
        """Fallback keyword-based intent detection when LLM fails"""
        message_lower = user_message.lower()
        print(f"🔄 Fallback intent detection for: '{user_message}' -> '{message_lower}'")
        
        # Safety-related keywords
        safety_keywords = ["safe", "safety", "dangerous", "risk", "warning", "precaution", "protection", "gear", "equipment"]
        if any(keyword in message_lower for keyword in safety_keywords):
            print(f"🔄 Safety keyword detected: 'safe' in '{message_lower}'")
            return "safety_check"
        
        # Tool-related keywords - narrowed to be more specific
        tool_keywords = [
            "stud finder", "drill", "hammer", "screwdriver", "saw", "level",
            "tape measure", "pencil", "wrench", "pliers", "how to use", "use the"
        ]
        if any(keyword in message_lower for keyword in tool_keywords):
            return "tool_guidance"
        
        # Step completion keywords
        completion_keywords = ["done", "finished", "complete", "next", "continue", "move on"]
        if any(keyword in message_lower for keyword in completion_keywords):
            return "step_progression"
        
        # Step instruction keywords
        instruction_keywords = ["what do i do", "how do i", "instructions", "guide", "help", "stuck", "confused"]
        if any(keyword in message_lower for keyword in instruction_keywords):
            return "step_instructions"
        
        # Status check keywords
        status_keywords = ["where am i", "status", "progress", "position", "current"]
        if any(keyword in message_lower for keyword in status_keywords):
            return "status_check"
        
        # Default to general help
        return "general_help"
        
    def _identify_tool_from_message(self, message: str, context: Dict[str, Any]) -> Optional[str]:
        """Try to identify which tool the user is asking about"""
        # Get tools from current context (from planner data)
        available_tools = context.get('current_tools', [])
        
        # Also check all tools from the task - fix dict access
        all_tools = []
        if context.get('current_step_data'):
            step_data = context['current_step_data']
            all_tools.extend(step_data.get('tools_needed', []))
        
        # Combine and deduplicate
        all_tools.extend(available_tools)
        all_tools = list(set(all_tools))
        
        message_lower = message.lower()
        for tool in all_tools:
            if tool.lower() in message_lower:
                return tool
                
        # Fallback to common tools if none found in context
        common_tools = ["stud finder", "level", "tape measure", "pencil", "hammer", "drill", "screwdriver", "saw"]
        for tool in common_tools:
            if tool in message_lower:
                return tool
                
        return None
        
    def _handle_step_progression(self, user_message: str, context: Dict[str, Any]) -> str:
        """Handle user wanting to move to next step"""
        
        if "done" in user_message.lower() or "complete" in user_message.lower() or "finished" in user_message.lower():
            # Mark current step as complete
            just_finished = context["current_step"]
            self.context_agent.mark_step_complete(just_finished, user_message)
            
            if context["current_step"] < context["total_steps"]:
                # Move to next step
                next_step = context["current_step"] + 1
                self.context_agent.move_to_step(next_step)
                
                # Get next step data for context
                next_step_data = self.context_agent.get_step_instructions(next_step)
                
                if next_step_data:
                    return f"""
✅ **Step {just_finished} Completed!**

🎯 **Moving to Step {next_step}: {next_step_data.get('title', '')}**

**Estimated Time:** {next_step_data.get('time_text', 'Unknown')}
**Tools Needed:** {', '.join(next_step_data.get('tools_needed', []))}

You're making great progress! What would you like to know about Step {next_step}?
• Step instructions
• Safety requirements  
• Tool guidance
• General help
"""
                else:
                    return f"""
✅ **Step {just_finished} Completed!**

🎯 **Moving to Step {next_step}**

You're making great progress! What would you like to know about Step {next_step}?

**Current Status**: Step {next_step} of {context['total_steps']}
"""
            else:
                return """
🎉 **Congratulations! You've completed all steps!**

Your project is finished! Is there anything else you'd like help with, or would you like to start a new project?
"""
        else:
            return "I'm ready to help you move to the next step! Are you finished with the current step, or do you need help with something specific?"
            
    def _provide_general_help(self, context: Dict[str, Any]) -> str:
        """Provide general help based on current context"""
        
        current_step_data = context.get('current_step_data', {})
        step_title = current_step_data.get('title', f'Step {context["current_step"]}') if current_step_data else f'Step {context["current_step"]}'
        
        return f"""
🤔 **I'm here to help!**

**Current Status**: {step_title} ({context['current_step']} of {context['total_steps']})
**Task**: {context['task_name']}

**How can I assist you?**
• **Step Instructions**: "What do I do for this step?"
• **Safety**: Ask about safety requirements and precautions
• **Tools**: Get guidance on using specific tools
• **Troubleshooting**: Help solve problems you're encountering
• **Progress**: Check your current status

**What specific help do you need right now?**
"""
        
    def _get_current_status_summary(self, context: Dict[str, Any]) -> str:
        """Get a summary of current status and progress"""
        current_step_data = context.get('current_step_data', {})
        step_title = current_step_data.get('title', f'Step {context["current_step"]}') if current_step_data else f'Step {context["current_step"]}'
        
        completed_steps = len([s for s in context['completion_status'].values() if s.get('completed')])
        # Guard against division by zero
        total = max(1, context['total_steps'])
        progress_percentage = (completed_steps / total) * 100
        
        status_emoji = "🟢" if progress_percentage >= 75 else "🟡" if progress_percentage >= 50 else "🔴"
        
        return f"""
📊 **Current Status Summary**

{status_emoji} **Progress**: {completed_steps}/{context['total_steps']} steps completed ({progress_percentage:.0f}%)

**Current Step**: {step_title}
**Step Number**: {context['current_step']} of {context['total_steps']}
**Task**: {context['task_name']}

**Tools for Current Step**: {', '.join(context['current_tools']) if context['current_tools'] else 'None specified'}

**What would you like to do next?**
• Continue with current step
• Get step instructions
• Ask about safety
• Get tool guidance
• Move to next step
"""
        
    def _ask_for_clarification(self, context: Dict[str, Any]) -> str:
        """Ask user to clarify their question"""
        
        current_step_data = context.get('current_step_data', {})
        step_title = current_step_data.get('title', f'Step {context["current_step"]}') if current_step_data else f'Step {context["current_step"]}'
        
        return f"""
🤷 **I want to help, but I need to understand better!**

**Current Context**: {step_title} ({context['current_step']} of {context['total_steps']}) - {context['task_name']}

**What would you like to know?**
• Are you asking about **step instructions** for this step?
• Are you asking about **safety** for this step?
• Do you need **tool guidance**?
• Are you **stuck** on something specific?
• Do you want to **move to the next step**?
• Something else?

Please let me know what you need help with!
"""
        
    def _get_initial_safety_level(self) -> str:
        """Get initial safety level for the task"""
        return "Medium - Standard safety precautions required"
        
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get conversation history"""
        return self.conversation_history
        
    def reset_conversation(self):
        """Reset conversation history"""
        self.conversation_history = []
        self.context_agent = StepContextAgent()


# Main chatbot class that coordinates all agents
class StepGuidanceChatbot:
    """Main chatbot class that coordinates all step guidance agents"""
    
    def __init__(self):
        self.execution_agent = TaskExecutionAgent()
        self.current_task = None
        
    def start_new_task(self, task_name: str, total_steps: int, steps_data: Optional[Dict[int, Dict[str, Any]]] = None, tools_data: Optional[Dict[str, Dict[str, Any]]] = None, problem_summary: str = "") -> str:
        """Start a new task with real data from planner and agents"""
        self.current_task = task_name
        return self.execution_agent.start_task(task_name, total_steps, steps_data, tools_data, problem_summary)
        
    def chat(self, user_message: str) -> str:
        """Process user message and get response"""
        if not self.current_task:
            return "Please start a task first using start_new_task()"
            
        return self.execution_agent.process_user_message(user_message)
        
    def get_current_status(self) -> Dict[str, Any]:
        """Get current task status"""
        if not self.current_task:
            return {"status": "No task active"}
            
        context = self.execution_agent.context_agent.get_current_context()
        return {
            "status": "Task active",
            "task": self.current_task,
            "context": context,
            "conversation_length": len(self.execution_agent.get_conversation_history())
        }
        
    def get_current_step_data(self) -> Optional[Dict[str, Any]]:
        """Get current step data for easier access"""
        if not self.current_task:
            return None
        return self.execution_agent.context_agent.get_step_instructions(
            self.execution_agent.context_agent.current_step
        )
        
    def reset(self):
        """Reset the chatbot"""
        self.execution_agent.reset_conversation()
        self.current_task = None


# Example usage and testing
if __name__ == "__main__":
    # Test the chatbot
    chatbot = StepGuidanceChatbot()
    
    print("🧪 Testing Step Guidance Chatbot...")
    print("=" * 50)
    
    # Start a task
    response = chatbot.start_new_task("Locate Studs", 4)
    print(f"🤖 Bot: {response}")
    print()
    
    # Test user interactions
    test_messages = [
        "What do I do for step 1?",
        "Is this step safe?",
        "How do I use the stud finder?",
        "I'm stuck, can you help?",
        "What's my current status?",
        "I'm done with this step"
    ]
    
    for message in test_messages:
        print(f"👤 User: {message}")
        response = chatbot.chat(message)
        print(f"🤖 Bot: {response}")
        print()
        
    # Show status
    status = chatbot.get_current_status()
    print(f"📊 Status: {status}")
