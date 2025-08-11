import os
import re
import json
import requests

from ..chatbot.agents import load_prompt, clean_and_parse_json

tools_prompt_text = load_prompt("tools_prompt.txt")
steps_prompt_text = load_prompt("steps_prompt.txt")


class ToolsAgentJSON:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate(self, summary: str) -> list:
        system = f"""{tools_prompt_text}
Return a JSON array ONLY of tools with keys:
tool_name, description, dimensions (optional), risk_factor, safety_measure.
"""
        payload = {
            "model": "gpt-4.1-mini",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": f"Summary:\n{summary}\nReturn JSON only."},
            ],
            "max_tokens": 900,
        }
        r = requests.post(self.api_url, headers=self.headers, json=payload, timeout=25)
        raw = r.json()["choices"][0]["message"]["content"]
        return clean_and_parse_json(raw)


class StepsAgentJSON:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate(self, summary: str) -> dict:
        system = f"""{steps_prompt_text}
Return JSON with keys:
steps: [{{order, title, est_time_min, status, summary}}],
total_est_time_min, notes (optional).
"""
        payload = {
            "model": "gpt-4.1-mini",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": f"Summary:\n{summary}\nReturn JSON only."},
            ],
            "max_tokens": 900,
        }
        r = requests.post(self.api_url, headers=self.headers, json=payload, timeout=25)
        raw = r.json()["choices"][0]["message"]["content"]
        return clean_and_parse_json(raw)

