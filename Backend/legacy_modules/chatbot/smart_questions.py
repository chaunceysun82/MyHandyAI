# smart_questions.py
import ast
import re
from typing import List, Dict, Any, Optional


class SmartQuestionManager:
    """Manages context-aware questions with local filtering and parsing for ANY DIY problem"""

    def __init__(self):
        # Generic normalization tables that work for any DIY scenario
        self.LOCATION_NORMALIZE = {
            "backyard": "garden", "yard": "garden", "wc": "bathroom",
            "lavatory": "bathroom", "kitchen sink": "kitchen", "bathroom sink": "bathroom",
            "living room": "living_room", "dining room": "dining_room", "bedroom": "bedroom",
            "attic": "attic", "crawlspace": "crawlspace", "roof": "roof", "deck": "deck",
            "patio": "patio", "driveway": "driveway", "sidewalk": "sidewalk"
        }

        self.THING_NORMALIZE = {
            "tap": "faucet", "garbage disposal": "disposal", "hose bib": "hose_bib",
            "hosebib": "hose_bib", "sink": "sink", "pipe": "pipe", "outlet": "outlet",
            "switch": "switch", "light": "light", "fixture": "fixture", "appliance": "appliance",
            "furniture": "furniture", "cabinet": "cabinet", "shelf": "shelf", "door": "door",
            "window": "window", "floor": "floor", "ceiling": "ceiling", "wall": "wall"
        }

        self.WALL_NORMALIZE = {
            "gypsum": "drywall", "sheetrock": "drywall", "cement board": "cement_board",
            "brick": "masonry", "block": "masonry", "concrete": "concrete", "wood": "wood",
            "metal": "metal", "plastic": "plastic", "vinyl": "vinyl", "stone": "stone"
        }

    def normalize_text(self, text: str, table: dict) -> str:
        """Normalize text using a lookup table"""
        if not isinstance(text, str):
            return text
        text_lower = text.strip().lower()
        for key, value in table.items():
            if key in text_lower:
                return value
        return text_lower

    def _find_terms(self, text: str, terms: List[str]) -> List[str]:
        """Find terms using word boundaries to avoid false positives"""
        hits = []
        for t in terms:
            # word-boundary for each token; supports multi-word like "no power", "stud finder"
            pattern = r"\b" + r"\s+".join(map(re.escape, t.split())) + r"\b"
            if re.search(pattern, text):
                hits.append(t)
        return hits

    def extract_context_from_answers(self, previous_answers: Dict[int, str]) -> Dict[str, Any]:
        """Extract meaningful context from previous answers - works for ANY DIY problem"""
        context = {}

        for idx, answer in previous_answers.items():
            answer_lower = answer.lower()

            # LOCATION - capture all matches and dedupe
            loc_hits = self._find_terms(answer_lower, [
                "bathroom", "kitchen", "basement", "garage", "garden", "outdoor", "indoor",
                "living room", "dining room", "bedroom", "attic", "crawlspace", "roof", "deck",
                "patio", "driveway", "sidewalk", "closet", "hallway", "staircase", "landing"
            ])
            for loc in loc_hits:
                if loc in ["bathroom", "kitchen", "basement", "garage", "bedroom", "attic", "closet", "hallway"]:
                    context["location"] = loc
                    context["room"] = loc
                    context["area_type"] = "indoor"
                elif loc in ["garden", "outdoor", "patio", "deck", "driveway", "sidewalk", "roof"]:
                    context["location"] = loc
                    context["area_type"] = "outdoor"
                elif loc in ["living room", "dining room"]:
                    context["location"] = loc.replace(" ", "_")
                    context["room"] = loc
                    context["area_type"] = "indoor"

            # SYMPTOMS / PROBLEMS - capture all matches
            problem_map = {
                "not working": "not_working", "broken": "broken", "damaged": "damaged",
                "leaking": "leaking", "dripping": "dripping", "clogged": "clogged",
                "slow drain": "slow_drain", "no power": "no_power", "flickering": "flickering",
                "loose": "loose", "wobbly": "wobbly", "cracked": "cracked", "rusty": "rusty",
                "stuck": "stuck", "noisy": "noisy", "smelly": "smelly", "hot": "hot", "cold": "cold"
            }
            hits = self._find_terms(answer_lower, list(problem_map.keys()))
            if hits:
                context.setdefault("symptoms", []).extend(problem_map[h] for h in hits)

            # MATERIALS - capture all matches
            mat_hits = self._find_terms(answer_lower, [
                "drywall", "plaster", "tile", "concrete", "pvc", "copper", "wood", "metal", "plastic",
                "vinyl", "stone", "brick", "glass", "ceramic", "aluminum", "steel", "iron", "brass", "bronze",
                "marble", "granite", "limestone"
            ])
            if mat_hits:
                context.setdefault("materials", []).extend(mat_hits)

            # TOOLS - capture all matches
            tool_hits = self._find_terms(answer_lower, [
                "drill", "hammer", "screwdriver", "wrench", "pliers", "saw", "level", "tape measure",
                "stud finder", "multimeter", "plunger", "snake", "caulk gun", "paint brush", "roller"
            ])
            if tool_hits:
                context.setdefault("tools_available", []).extend(tool_hits)

        # Dedupe lists at the end
        for k in ("symptoms", "materials", "tools_available"):
            if k in context:
                context[k] = sorted(set(context[k]))

        return context

    def safe_eval_bool(self, expr: str, ctx: dict) -> bool:
        """Safely evaluate boolean expressions for appliesIf"""
        if not expr:
            return True

        try:
            node = ast.parse(expr, mode="eval")
            allowed = (
                ast.Expression, ast.BoolOp, ast.UnaryOp, ast.And, ast.Or, ast.Not,
                ast.Compare, ast.Name, ast.Load, ast.Constant, ast.List, ast.Tuple,
                ast.In, ast.Eq, ast.NotEq, ast.Gt, ast.GtE, ast.Lt, ast.LtE
            )

            for sub in ast.walk(node):
                if not isinstance(sub, allowed):
                    raise ValueError("Disallowed expression in appliesIf")

            return bool(eval(compile(node, "<appliesIf>", "eval"), {}, ctx or {}))
        except Exception:
            # Be defensive: hide on rule error
            return False

    def filter_questions(self, questions: List[Dict[str, Any]], triage_state: Dict[str, Any], problem_type: str) -> \
    List[Dict[str, Any]]:
        """Filter questions based on context using appliesIf - works for ANY problem type"""
        ctx = {**(triage_state or {}), "problem_type": problem_type}
        filtered = []

        for q in questions:
            if not q.get("text"):
                continue
            try:
                if self.safe_eval_bool(q.get("appliesIf", ""), ctx):
                    filtered.append(q)
            except Exception:
                # Be defensive: hide on rule error
                pass

        return filtered

    def parse_dimensions(self, text: str) -> Optional[Dict[str, float]]:
        """Parse dimensions from text like '24 x 36 inches' or '2ft x 3ft'"""
        if not isinstance(text, str):
            return None

        text = text.lower().strip()

        # Common patterns for dimensions
        patterns = [
            # "24 x 36 inches" or "24x36 inches"
            r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*(?:in|inch|inches|'|ft|feet)",
            # "24 inches x 36 inches"
            r"(\d+(?:\.\d+)?)\s*(?:in|inch|inches|'|ft|feet)\s*[x×]\s*(\d+(?:\.\d+)?)\s*(?:in|inch|inches|'|ft|feet)",
            # "24 x 36" (assume inches)
            r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)",
            # "24cm x 36cm"
            r"(\d+(?:\.\d+)?)\s*cm\s*[x×]\s*(\d+(?:\.\d+)?)\s*cm",
            # "24mm x 36mm"
            r"(\d+(?:\.\d+)?)\s*mm\s*[x×]\s*(\d+(?:\.\d+)?)\s*mm"
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                width = float(match.group(1))
                height = float(match.group(2))

                # Convert to inches if needed
                if "cm" in text:
                    width = width / 2.54
                    height = height / 2.54
                elif "mm" in text:
                    width = width / 25.4
                    height = height / 25.4
                elif "ft" in text or "'" in text or "feet" in text:
                    width = width * 12
                    height = height * 12

                return {
                    "w_in": round(width, 1),
                    "h_in": round(height, 1)
                }

        return None

    def normalize_wall_type(self, text: str) -> str:
        """Normalize wall type text - works for any wall material"""
        if not isinstance(text, str):
            return text

        t = text.strip().lower()
        for key, value in self.WALL_NORMALIZE.items():
            if key in t:
                return value

        # Check for common wall types
        for wall_type in ["drywall", "plaster", "tile", "concrete", "masonry", "cement_board", "wood", "metal",
                          "plastic"]:
            if wall_type in t:
                return wall_type

        return t

    def apply_answer_to_state(self, question: Dict[str, Any], answer: str, triage_state: Dict[str, Any]) -> Dict[
        str, Any]:
        """Apply answer to triage state based on question metadata - works for ANY field"""
        collect = question.get("collect", {})
        field = collect.get("field")

        if not field:
            return triage_state

        # Parse field path (e.g., "dimensions.mirror" or "materials.wall_type")
        parts = field.split(".")

        if question.get("type") == "dimensions":
            dims = self.parse_dimensions(answer)
            if dims:
                target = parts[-1] if len(parts) >= 2 else "item"
                triage_state.setdefault("dimensions", {})[target] = dims

        elif question.get("type") in ("yes_no", "boolean"):
            s = (answer or "").strip().lower()

            def _has_word(s: str, w: str) -> bool:
                return re.search(rf"\b{re.escape(w)}\b", s) is not None

            truthy_terms = ["yes", "y", "true", "i do", "i have", "sure", "ok", "okay", "yep", "yeah"]
            falsey_terms = ["no", "n", "false", "nope", "nah", "i don't", "dont", "do not"]

            if any(_has_word(s, t) for t in truthy_terms):
                val = True
            elif any(_has_word(s, t) for t in falsey_terms):
                val = False
            else:
                # fallback: default to False unless you want tri-state
                val = False

            if parts[0] == "tools_available" and len(parts) == 2 and val:
                tools = set(triage_state.get("tools_available", []))
                tools.add(parts[1])
                triage_state["tools_available"] = list(tools)
            else:
                triage_state[parts[-1]] = val

        elif question.get("type") == "free_text":
            # Handle any field type generically
            if field == "materials.wall_type":
                wall_type = self.normalize_wall_type(answer)
                triage_state.setdefault("materials", []).append(wall_type)
            elif field == "location":
                location = self.normalize_text(answer, self.LOCATION_NORMALIZE)
                triage_state["location"] = location
                # Automatically determine if indoor/outdoor based on location
                if location in ["garden", "patio", "yard", "deck", "driveway", "sidewalk", "roof"]:
                    triage_state["area_type"] = "outdoor"
                elif location in ["bathroom", "kitchen", "basement", "garage", "bedroom", "attic", "closet", "hallway"]:
                    triage_state["area_type"] = "indoor"
            elif field == "thing":
                thing = self.normalize_text(answer, self.THING_NORMALIZE)
                triage_state["thing"] = thing
            elif field == "domain":
                triage_state["domain"] = answer.lower()
            elif field == "system":
                triage_state["system"] = answer.lower()
            elif field == "symptoms":
                # Handle multiple symptoms with deduplication
                items = [t.strip().lower() for t in answer.split(",") if t.strip()]
                triage_state.setdefault("symptoms", [])
                triage_state["symptoms"] = sorted(set(triage_state["symptoms"]) | set(items))
            elif field == "hazards":
                # Handle multiple hazards with deduplication
                items = [t.strip().lower() for t in answer.split(",") if t.strip()]
                triage_state.setdefault("hazards", [])
                triage_state["hazards"] = sorted(set(triage_state["hazards"]) | set(items))
            else:
                # Generic stash for any other field
                triage_state[parts[-1]] = answer

        return triage_state

    def normalize_questions(self, raw_questions: List[Any]) -> List[Dict[str, Any]]:
        """Normalize questions to standard format - works for ANY question type"""
        normalized = []

        for i, q in enumerate(raw_questions):
            if isinstance(q, str):
                text = q.strip()
                if not text:
                    continue
                normalized.append({
                    "id": f"q{i + 1}",
                    "text": text,
                    "type": "free_text",
                    "appliesIf": "",
                    "collect": {}
                })
            elif isinstance(q, dict):
                text = (q.get("text") or q.get("prompt") or "").strip()
                if not text:
                    continue
                normalized.append({
                    "id": q.get("id", f"q{i + 1}"),
                    "text": text,
                    "type": q.get("type", "free_text"),
                    "units": q.get("units", []),
                    "suggestions": q.get("suggestions", []),
                    "appliesIf": q.get("appliesIf", ""),
                    "collect": q.get("collect", {})
                })

        return normalized

    def prune_dimension_questions(self, questions: List[Dict[str, Any]], user_description: str,
                                  triage_state: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Remove dimension questions if measurements are already provided - works for any object"""
        if not user_description and not triage_state:
            return questions

        desc = (user_description or "").lower()
        has_measure = bool(re.search(r"\d+\s*(cm|mm|in|inch|inches|ft|')", desc))
        has_state_dims = bool(triage_state and triage_state.get("dimensions"))

        if has_measure or has_state_dims:
            return [q for q in questions if "dimension" not in q.get("text", "").lower()]

        return questions
