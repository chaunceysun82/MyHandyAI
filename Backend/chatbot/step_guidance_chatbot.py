# chatbot/step_guidance_chatbot.py
from __future__ import annotations

import os
import re
import json
import math
from typing import Dict, Any, List, Optional

DEFAULT_MODEL = os.getenv("STEP_GUIDANCE_MODEL", "gpt-5-nano") 
CLASSIFIER_MODEL = os.getenv("STEP_GUIDANCE_CLASSIFIER_MODEL", "gpt-5-nano")
MAX_TURNS_IN_CONTEXT = int(os.getenv("STEP_GUIDANCE_MAX_TURNS", "10"))
MIN_RELEVANCE_TO_ANSWER = float(os.getenv("STEP_GUIDANCE_MIN_REL", "0.35"))  # 0..1

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

    def chat(self, user_message: str, step: int) -> str:
        """
        Free-form chat with the LLM using the guide + current step context.
        Before answering, verify relevance; if off-topic, nudge the user.
        """
        self.current_step=step
        user_message = (user_message or "").strip()
        self._remember("user", user_message)

        # 1) Relevance gate (heuristic + micro-classifier)
        rel_score, rel_label = self._relevance_check(user_message)
        if rel_label == "not_relevant" or rel_score < MIN_RELEVANCE_TO_ANSWER:
            step_title = self._step_title(self.current_step)
            msg = (
                f"That question doesn’t appear related to the project "
                "Ask me about this project, the tools/materials involved, safety, or troubleshooting. "
            )
            self._remember("assistant", msg)
            return msg

        # 2) Build messages for the main model
        system = self._build_system_prompt()
        guide_context = self._build_guide_context_block(self.current_step)
        step_context = self._build_step_context_block(self.current_step)
        
        print("step_context: ", step_context)

        messages = [
            {"role": "system", "content": system},
            {"role": "system", "content": guide_context},
            {"role": "system", "content": step_context},
        ]
        for turn in self.history[-MAX_TURNS_IN_CONTEXT:]:
            messages.append({"role": turn["role"], "content": turn["content"]})
        messages.append({"role": "user", "content": user_message})
        
        print("messages: ", messages)

        reply = self._call_llm(messages, model=DEFAULT_MODEL)
        if not reply:
            reply = (
                "I couldn’t reach the model just now. Here’s a quick overview of the current step:\n\n"
                + self._render_step(self.current_step)
            )
        self._remember("assistant", reply)
        return reply

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
                tools_brief += "\n- "+t.get("name","")
                if step==0:
                    tools_brief +="\ndescription: "+ t.get("description","")
                    tools_brief +="\nprice: "+ t.get("price","")
                    tools_brief +="\nrisk_factors: "+ t.get("risk_factors","")
                    tools_brief +="\nsafety_measures: "+ t.get("safety_measures","")
                    
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
        if step_idx <0:
            steps_brief = ""
            try:
                for step_num, step in self.steps_data.items():
                    steps_brief += (step or {}).get("title") or ""
            except Exception:
                pass
        
        if step_idx == 0:  
            pass  
        
        if (step_idx>0):
            step_idx=step_idx-1
            
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
        ctx = self._build_guide_context_block(self.current_step) + "\n" + self._build_step_context_block(self.current_step)
        messages = [
            {"role": "system", "content": system},
            {"role": "system", "content": ctx},
            {"role": "user", "content": f"Is this question relevant to the current step?\nQ: {user_message}\nAnswer with one word."},
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
        
        print ("reach call_llm")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return ""
        print ("api_key: ", api_key)
        # Try Responses API
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            resp = client.responses.create(
                model=model,
                input=messages,
                reasoning={ "effort": "low" },
                text={ "verbosity": "low" }
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
                reasoning={ "effort": "low" },
                text={ "verbosity": "low" }
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
