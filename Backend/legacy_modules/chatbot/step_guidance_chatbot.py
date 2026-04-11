# chatbot/step_guidance_chatbot.py
from __future__ import annotations

import base64
import json
import math
import re
from typing import Dict, Any, List, Optional

import requests

from config.settings import get_settings

settings = get_settings()
DEFAULT_MODEL = settings.PROJECT_ASSISTANT_AGENT_MODEL
CLASSIFIER_MODEL = settings.STEP_GUIDANCE_CLASSIFIER_MODEL
MAX_TURNS_IN_CONTEXT = settings.STEP_GUIDANCE_MAX_TURNS
MIN_RELEVANCE_TO_ANSWER = settings.STEP_GUIDANCE_MIN_REL


def clean_and_parse_json(raw_str: str):
    """
    Cleans code fences (```json ... ```) from a string and parses it as JSON.
    """
    s = raw_str.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s)  # strip fences
    m = re.search(r"\{.*\}\s*$", s, flags=re.S)  # grab last JSON object
    if m: s = m.group(0)
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")


class StepGuidanceImageAnalyzer:
    """Analyzes images in the context of step guidance and troubleshooting"""

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def analyze_step_image(
            self,
            image_data: bytes,
            current_step: int,
            step_context: str,
            problem_summary: str,
            user_message: str = "",
    ) -> Dict[str, Any]:
        """
        Analyze image in context of current step for guidance or troubleshooting
        
        Returns:
        - analysis: What's seen in the image
        - guidance: Step-specific guidance based on image
        - issues_detected: Any problems or concerns spotted
        - next_actions: Suggested next steps
        - safety_notes: Any safety considerations
        """

        b64 = base64.b64encode(image_data).decode("utf-8")

        system_prompt = f"""You are a helpful DIY step guidance assistant analyzing an image to provide contextual help.

Current Context:
- Step: {current_step}
- User's question/message: "{user_message}"
- Step context: {step_context}
- Problem summary: {problem_summary}

Your task is to analyze the image and provide helpful, step-specific guidance. Look for:
- Progress on the current step
- Potential issues or problems
- Safety concerns
- Whether the user is on the right track
- Specific guidance for what to do next

Provide practical, actionable advice based on what you see in the image.

Return JSON with:
- "analysis": What you see in the image relevant to the step
- "guidance": Specific guidance based on the image and current step
- "issues_detected": Any problems or concerns (list)
- "next_actions": Suggested immediate next steps (list)
- "safety_notes": Any safety considerations (list)
- "progress_assessment": How well the step is progressing ("good", "needs_attention", "problematic")
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text",
                     "text": f"Step {current_step}: {user_message} analyze the image and provide guidance."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]
            }
        ]

        try:
            r = requests.post(
                self.api_url, headers=self.headers,
                json={"model": "gpt-4o", "messages": messages, "max_tokens": 800}
            )
            if r.status_code == 200:
                result = clean_and_parse_json(r.json()["choices"][0]["message"]["content"])

                # Ensure all expected fields exist and are properly typed
                result.setdefault("analysis", "I can see your image related to the current step")
                result.setdefault("guidance", "")
                result.setdefault("issues_detected", [])
                result.setdefault("next_actions", [])
                result.setdefault("safety_notes", [])
                result.setdefault("progress_assessment", "good")

                # Ensure lists are actually lists
                for list_field in ["issues_detected", "next_actions", "safety_notes"]:
                    if not isinstance(result[list_field], list):
                        if isinstance(result[list_field], str):
                            result[list_field] = [result[list_field]] if result[list_field] else []
                        else:
                            result[list_field] = []

                return result
        except Exception as e:
            print(f"Error analyzing step image: {e}")
            pass

        return {
            "analysis": "I can see your image related to the current step",
            "guidance": "Based on your image, let me help you with this step.",
            "issues_detected": [],
            "next_actions": [],
            "safety_notes": [],
            "progress_assessment": "good"
        }


class StepGuidanceChatbot:
    """
    Picklable, minimal step-guidance agent (no navigation in chat).
    - Keeps only plain-Python state (safe to pickle).
    - Injects full guide + current step context on each turn.
    - Verifies user question relevance to the project/step before answering.
    """

    def __init__(self):
        self.total_steps: int = 1
        self.steps_data: Dict[int, Dict[str, Any]] = {1: {"title": "Step 1", "instructions": []}}
        self.tools_data: Dict[str, Any] = {}
        self.problem_summary: str = ""
        self.current_step: int = -1  # stays fixed unless your UI sets it via set_current_step()
        self.history: List[Dict[str, str]] = []
        self.image_analyzer = StepGuidanceImageAnalyzer()

    # ---------- Public API ----------

    def start_new_task(
            self,
            total_steps: int,
            steps_data: Dict[int, Dict[str, Any]],
            tools_data: Optional[Dict[str, Any]] = None,
            problem_summary: str = "",
    ) -> str:
        self.total_steps = max(1, int(total_steps or 1))
        self.steps_data = steps_data or {1: {"title": "Step 1", "instructions": []}}
        self.tools_data = tools_data or {}
        self.problem_summary = problem_summary or ""
        self.current_step = 1
        self.history = []  # reset
        return self._render_welcome()

    def set_current_step(self, idx: int) -> None:
        """Optional: call this from your UI when the user changes steps there."""
        if not isinstance(idx, int):
            return
        self.current_step = max(1, min(self.total_steps, idx))

    def chat(self, user_message: str, step: int, uploaded_image: Optional[bytes] = None) -> str:
        """
        Free-form chat with the LLM using the guide + current step context.
        Before answering, verify relevance; if off-topic, nudge the user.
        Now supports image analysis for step guidance and troubleshooting.
        """
        self.current_step = step
        user_message = (user_message or "").strip()
        self._remember("user", user_message)

        # 1) If image provided, analyze it first for step-specific guidance
        image_analysis_result = None
        if uploaded_image:
            step_context = self._build_step_context_block(self.current_step)
            image_analysis_result = self.image_analyzer.analyze_step_image(
                uploaded_image, self.current_step, step_context, self.problem_summary, user_message
            )

        # 2) Relevance gate (heuristic + micro-classifier)
        if user_message and not image_analysis_result:
            rel_score, rel_label = self._relevance_check(user_message)
        else:
            rel_score, rel_label = 1.0, "relevant"
        if rel_label == "not_relevant" or rel_score < MIN_RELEVANCE_TO_ANSWER:
            step_title = self._step_title(self.current_step)
            msg = (
                f"That question doesn't appear related to the project "
                "Ask me about this project, the tools/materials involved, safety, or troubleshooting. "
            )
            self._remember("assistant", msg)
            return msg

        # 3) Build enhanced response with image context if available
        if image_analysis_result:
            reply = self._build_image_enhanced_response(user_message, image_analysis_result)
        else:
            # 4) Standard text-only response
            reply = self._build_standard_response(user_message)

        if not reply:
            reply = (
                    "I couldn't reach the model just now. Here's a quick overview of the current step:\n\n"
                    + self._render_step(self.current_step)
            )

        self._remember("assistant", reply)
        return reply

    def _build_image_enhanced_response(self, user_message: str, image_analysis: Dict[str, Any]) -> str:
        """Build response that incorporates image analysis with step guidance"""

        analysis = image_analysis.get("analysis", "")
        guidance = image_analysis.get("guidance", "")
        issues = image_analysis.get("issues_detected", [])
        next_actions = image_analysis.get("next_actions", [])
        safety_notes = image_analysis.get("safety_notes", [])
        progress = image_analysis.get("progress_assessment", "good")

        response_parts = []

        # Start with image analysis
        if analysis:
            response_parts.append(f"📸 **Looking at your image:** {analysis}")

        # Add guidance
        if guidance:
            response_parts.append(f"**Guidance:** {guidance}")

        # Add issues if detected
        if issues:
            issues_text = "\n".join(f"• {issue}" for issue in issues)
            response_parts.append(f"⚠️ **Issues noticed:**\n{issues_text}")

        # Add safety notes if any
        if safety_notes:
            safety_text = "\n".join(f"• {note}" for note in safety_notes)
            response_parts.append(f"🔒 **Safety reminders:**\n{safety_text}")

        # Add next actions
        if next_actions:
            actions_text = "\n".join(f"• {action}" for action in next_actions)
            response_parts.append(f"👉 **Next steps:**\n{actions_text}")

        # Add progress assessment
        if progress == "problematic":
            response_parts.append("🔴 **Status:** This needs attention before proceeding.")
        elif progress == "needs_attention":
            response_parts.append("🟡 **Status:** You're on track, but double-check a few things.")
        else:
            response_parts.append("✅ **Status:** Looking good!")

        # Ask if user has more questions
        response_parts.append("Any other questions about this step?")

        return "\n\n".join(response_parts)

    def _build_standard_response(self, user_message: str) -> str:
        """Build standard text-only response using the LLM"""

        # Build messages for the main model (original logic)
        system = self._build_system_prompt()
        guide_context = self._build_guide_context_block(self.current_step)
        step_context = self._build_step_context_block(self.current_step)

        messages = [
            {"role": "system", "content": system},
            {"role": "system", "content": guide_context},
            {"role": "system", "content": step_context},
        ]
        for turn in self.history[-MAX_TURNS_IN_CONTEXT:]:
            messages.append({"role": turn["role"], "content": turn["content"]})
        messages.append({"role": "user", "content": user_message})

        return self._call_llm(messages, model=DEFAULT_MODEL)

    # ---------- Prompt Builders ----------

    def _build_system_prompt(self) -> str:
        return (
            "You are a friendly, concise step-by-step home repair guide.\n"
            "Goals:\n"
            "1) Help the user complete the CURRENT step safely and correctly.If the step is 0 provide guidance about the tools needed. if no step is provide focus on answr general questions the user is in the overview page\n"
            "2) Answer free-form questions using the provided guide context only.\n"
            "3) Offer practical tips and highlight safety warnings when relevant.\n"
            "4) Keep answers actionable and compact; use bullets or short numbered lists when helpful.\n"
            "5) If the user seems stuck, propose troubleshooting checks based on the step.\n"
            "Do not introduce new steps or change the step order.\n"
            "Keep the answer concise and short"
        )

    def _build_guide_context_block(self, step) -> str:
        # tools brief
        tools_brief = "Tools in guide:"
        try:
            tools = (self.tools_data or {}).get("tools") or []
            for t in tools:
                tools_brief += "\n- " + t.get("name", "")
                if step == 0:
                    tools_brief += "\ndescription: " + t.get("description", "")
                    tools_brief += "\nprice: " + t.get("price", "")
                    tools_brief += "\nrisk_factors: " + t.get("risk_factors", "")
                    tools_brief += "\nsafety_measures: " + t.get("safety_measures", "")

        except Exception:
            pass

        parts = []
        if self.problem_summary:
            parts.append(f"Problem summary: {self.problem_summary}")
        if tools_brief:
            parts.append(tools_brief)
        parts.append(f"Total steps: {self.total_steps}")

        return "GUIDE OVERVIEW\n" + "\n".join(parts)

    def _build_step_context_block(self, step_idx: int) -> str:
        if step_idx < 0:
            steps_brief = ""
            try:
                for step_num, step in self.steps_data.items():
                    steps_brief += (step or {}).get("title") or ""
            except Exception:
                pass

        if step_idx == 0:
            pass

        if (step_idx > 0):
            step_idx = step_idx - 1

        step = self.steps_data.get(step_idx, {})
        title = step.get("title", f"Step {step_idx}")
        instr = step.get("instructions") or []
        time_text = step.get("time_text") or ""
        # tips = step.get("tips") or []
        # warns = step.get("safety_warnings") or []
        tools = step.get("tools_needed") or []

        lines = [f"CURRENT STEP = {step_idx}", f"Step title: {title}"]
        if time_text:
            lines.append(f"Estimated time: {time_text}")
        if tools:
            lines.append("Tools needed: " + ", ".join([str(t) for t in tools][:15]))
        # if warns:
        #     lines.append("Safety warnings: " + "; ".join([str(w) for w in warns][:10]))
        if instr:
            lines.append("Instructions:")
            for i, line in enumerate(instr, 1):
                lines.append(f"  {i}. {line}")
        # if tips:
        #     lines.append("Tips:")
        #     for i, line in enumerate(tips, 1):
        #         lines.append(f"  - {line}")

        return "STEP CONTEXT\n" + "\n".join(lines)

    # ---------- Rendering helpers ----------

    def _render_welcome(self) -> str:
        return "I’ll guide you step by step. Ask me anything about the project, steps or tools.\n\n"

    def _render_step(self, step_idx: int) -> str:
        step = self.steps_data.get(step_idx, {})
        title = step.get("title", f"Step {step_idx}")
        body = [f"**Step {step_idx}: {title}**"]

        tools = step.get("tools_needed") or []
        warns = step.get("safety_warnings") or []
        instr = step.get("instructions") or []
        tips = step.get("tips") or []
        time_text = step.get("time_text") or ""

        if time_text:
            body.append(f"⏱️ Estimated time: {time_text}")
        if tools:
            body.append("🔧 Tools: " + ", ".join([str(t) for t in tools]))
        if warns:
            body.append("⚠️ Safety: " + "; ".join([str(w) for w in warns]))
        if instr:
            body.append("📋 Instructions:")
            for i, line in enumerate(instr, 1):
                body.append(f"  {i}. {line}")
        if tips:
            body.append("💡 Tips:")
            for line in tips:
                body.append(f"  • {line}")

        body.append("\nAsk questions about this step, tools, safety, or troubleshooting.")
        return "\n".join(body)

    def _step_title(self, idx: int) -> str:
        return (self.steps_data.get(idx) or {}).get("title", f"Step {idx}")

    # ---------- Relevance Checking ----------

    def _relevance_check(self, user_message: str) -> tuple[float, str]:
        """
        Returns (score 0..1, label in {'relevant','not_relevant','uncertain'}).
        - Fast heuristic term overlap for speed
        - If low/uncertain, use a tiny LLM classifier
        """
        # Heuristic score
        heuristic = self._heuristic_relevance(user_message)
        if heuristic >= 0.6:
            return heuristic, "relevant"

        # Micro-classifier (very cheap)
        label = self._llm_relevance_classifier(user_message)
        if label == "relevant":
            return max(heuristic, 0.6), "relevant"
        if label == "not_relevant":
            return min(heuristic, 0.2), "not_relevant"
        return heuristic, "uncertain"

    def _heuristic_relevance(self, text: str) -> float:
        """Simple token overlap with current step + problem summary + tools."""
        text = (text or "").lower()
        step = self.steps_data.get(self.current_step, {})
        base = " ".join([
            " ".join(step.get("instructions") or []),
            step.get("title", ""),
            self.problem_summary or "",
            " ".join((step.get("tools_needed") or [])),
        ]).lower()

        # tokens: words of length >= 3
        toks = re.findall(r"[a-z0-9]{3,}", text)
        ctx = re.findall(r"[a-z0-9]{3,}", base)
        if not toks or not ctx:
            return 0.0

        toks_set = set(toks)
        ctx_set = set(ctx)
        overlap = len(toks_set & ctx_set)
        score = overlap / max(1, len(toks_set))
        # squash to 0..1, lightly emphasize overlap
        return max(0.0, min(1.0, 1.0 - math.exp(-3.0 * score)))

    def _llm_relevance_classifier(self, user_message: str) -> str:
        """
        Calls a tiny model to label: 'relevant' or 'not_relevant' or 'uncertain'.
        Keeps cost minimal (short prompt + very low max tokens).
        """
        system = (
            "You are a strict relevance classifier for a home-repair step guide.\n"
            "Given the user's question and the project context, answer with exactly one label:\n"
            "relevant, not_relevant, or uncertain."
        )
        ctx = self._build_guide_context_block(self.current_step) + "\n" + self._build_step_context_block(
            self.current_step)
        messages = [
            {"role": "system", "content": system},
            {"role": "system", "content": ctx},
            {"role": "user",
             "content": f"Is this question relevant to the current step?\nQ: {user_message}\nAnswer with one word."},
        ]
        out = self._call_llm(messages, model=CLASSIFIER_MODEL)
        label = (out or "").strip().lower()
        if "relevant" == label:
            return "relevant"
        if "not_relevant" in label:
            return "not_relevant"
        if "uncertain" in label:
            return "uncertain"
        # Fallback interpretation
        if "relevant" in label:
            return "relevant"
        return "uncertain"

    # ---------- Memory ----------

    def _remember(self, role: str, content: str) -> None:
        self.history.append({"role": "assistant" if role == "assistant" else "user", "content": content})
        if len(self.history) > 4:
            self.history = self.history[-4:]

    # ---------- LLM Calls ----------

    def _call_llm(self, messages: List[Dict[str, str]], model: str) -> str:
        """
        Responses API preferred; fallback to Chat Completions. No client stored on self.
        """

        print("reach call_llm")
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            return ""
        print("api_key: ", api_key)
        # Try Responses API
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            resp = client.responses.create(
                model=model,
                input=messages,
                reasoning={"effort": "low"},
                text={"verbosity": "low"}
            )
            try:
                print("🔎 Raw response:", json.dumps(resp.model_dump(), indent=2))
            except Exception:
                # fallback if resp isn't pydantic-serializable
                print("🔎 Raw response (fallback str):", str(resp))
            text = self._extract_output_text(resp)
            if text:
                return text
        except Exception as e:
            print("❌ Exception in _call_llm:", type(e).__name__, str(e))

        # Fallback: Chat Completions
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            chat = client.chat.completions.create(
                model=model,
                messages=messages,
                reasoning={"effort": "low"},
                text={"verbosity": "low"}
            )
            return (chat.choices[0].message.content or "").strip()
        except Exception:
            return ""

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
            resp = resp.model_dump()
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
