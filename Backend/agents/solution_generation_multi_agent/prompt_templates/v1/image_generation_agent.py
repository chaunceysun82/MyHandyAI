# ─── DOMAIN PHYSICS LIBRARY ───────────────────────────────────────────────────
# Injected into every prompt based on detected domain.
# Each entry covers: impossible states, hand constraints, object orientation,
# camera recommendations, and common AI hallucination failures.

DOMAIN_PHYSICS_LIBRARY = {
    "plumbing": {
        "physics": [
            "Water and liquids flow DOWNWARD only — never sideways or upward",
            "P-trap curves DOWN then UP then horizontal to wall — never reversed",
            "Drain basket sits at BOTTOM of sink basin — never above basin level",
            "Supply lines (braided steel) run from wall/floor UPWARD to faucet valves",
            "Shutoff valves are on supply lines BELOW the basin",
            "A pipe being cleaned or inspected must be DETACHED from the fixture first — you cannot clean inside a pipe that is still connected and sealed",
            "Bucket is placed BELOW the leak/drain to catch water — never above",
            "Plumber's tape wraps clockwise on male threads only",
        ],
        "hand_rules": [
            "Under-sink work: both hands reach INTO the cabinet from the front opening",
            "Over-sink work: hands reach DOWN toward the drain from above",
            "Never show hands emerging from inside a sealed pipe",
            "Wrench grips a fitting — not air beside it",
        ],
        "camera": [
            "Under-sink steps: medium shot from front of open cabinet, eye-level, showing full cabinet interior",
            "Drain cleaning steps: close-up top-down into sink basin",
            "Pipe connection steps: medium shot slightly from below cabinet floor level",
            "Always show enough context to see pipe orientation (up/down)",
        ],
        "alignment": [
            "Sink basin is ABOVE all drain components — always",
            "Drain pipe exits through cabinet floor or wall — always downward",
        ],
        "impossible_states": [
            "P-trap attached AND hands cleaning inside it simultaneously",
            "Water flowing upward into drain",
            "Drain above sink basin",
            "Three or more hands visible",
        ],
    },

    "electrical": {
        "physics": [
            "Wires run along wall studs or inside conduit — never floating in air",
            "Junction boxes are flush-mounted to wall or ceiling",
            "Breaker switches flip vertically — up=on, down=off",
            "Ground wire is always green or bare copper",
            "Neutral wire is always white",
            "Hot wire is black (or red for 240V)",
            "Panel breakers are in correct vertical orientation with labels",
        ],
        "hand_rules": [
            "Electrical panel work: one or both hands at panel height, person standing facing panel",
            "Outlet work: person crouching or kneeling at outlet height",
            "Never show bare hands touching exposed live wires",
            "Insulated screwdriver tip touches screw — not the wire directly",
        ],
        "camera": [
            "Panel work: medium wide shot showing full panel and person from waist up",
            "Outlet/switch work: close-up at outlet height, eye-level to outlet",
            "Wire routing: wide shot showing wall section and wire path",
            "Always show enough wall context to understand wire routing direction",
        ],
        "alignment": [
            "Outlets are vertical rectangles mounted vertically on wall",
            "Switch plates are vertical, rocker switches flip up/down",
            "Panel box is mounted vertically, breakers in rows",
            "TV mounted with screen FACING into the room — never screen to wall",
        ],
        "impossible_states": [
            "Screen of wall-mounted TV facing the wall",
            "Wires floating without conduit or stud attachment",
            "Three or more hands visible",
            "Panel upside down",
        ],
    },

    "carpentry": {
    "physics": [
        "Wood grain runs consistently in one direction per piece",
        "Joints must be flush — gaps indicate incomplete work",
        "Fasteners (screws/nails) go INTO the wood at 90 degrees unless angled for toe-nailing",
        "Clamps apply pressure FROM both sides toward the joint",
        "Saw blade cuts downward through material resting on a stable surface",
        "Level bubble must be centered for a level surface",
        "All tools must appear TRUE TO SCALE relative to the room and person — ",
        "a measuring tape is hand-sized, not wall-height; a drill is forearm-length",
        "Hands and arms must appear in natural proportion to the person's body — ",
        "never enlarged or zoomed beyond what a medium/wide shot would show",
    ],
    "hand_rules": [
        "Drill held with dominant hand on grip, other hand steadying workpiece or drill body",
        "Saw operation: both hands on saw, material clamped or held by helper",
        "Measuring tape: one hand holds tape body, other pulls and reads — ",
        "tape is MAX 1 meter visible, not floor-to-ceiling length",
        "Never show three hands",
        "Hands must be in natural proportion — if hands appear larger than a person's ",
        "head in the frame, the camera is too close; pull back to medium or wide shot",
        "For wall work, person stands at arm's length from wall — ",
        "hands are NOT filling the foreground of the frame",
    ],
    "camera": [
        "Joint/connection work: close-up at joint level — but person still visible",
        "Full assembly/installation: wide shot showing complete piece AND full person in frame",
        "Measuring: medium shot — person visible from waist up, tape visible but hand-sized",
        "Drilling: medium shot — person's full upper body visible, drill in natural proportion",
        "Stud finding / wall marking: medium-wide shot showing the CORRECT wall ",
        "(the wall where the mirror/object will hang) — person standing facing that wall, ",
        "full body or waist-up visible, tool hand-sized not foreground-filling",
        "NEVER use extreme close-up (hands filling frame) for carpentry — ",
        "always show enough of the person to establish body proportions",
        "Camera should be 2-3 meters from the person for most carpentry steps",
    ],
    "alignment": [
        "Mirror hung with reflective face INTO the room — never backward",
        "Picture frame shows front face to viewer",
        "Cabinet doors open toward the room — hinges on wall side",
        "Shelves are horizontal, level, supported at both ends",
        "ALL wall work (drilling, stud-finding, marking, mounting) happens on ",
        "the PRIMARY FEATURE WALL — the main flat wall where the object will be installed, ",
        "NOT the side walls, NOT the ceiling, NOT adjacent walls",
        "The feature wall is the largest unobstructed wall visible straight ahead ",
        "when entering the room — the sofa/furniture faces it",
    ],
    "impossible_states": [
        "Mirror showing its back face as the hung result",
        "Floating shelves with no visible mounting",
        "Three or more hands",
        "Drill bit entering at impossible angle",
        "Hands/tools appearing larger than the person's torso in the frame",
        "Measuring tape appearing taller than a person",
        "Stud finder / drill / tools used on the wrong wall (side wall instead of feature wall)",
        "Person invisible or only hands visible in a wide installation step",
    ],
},

    "painting": {
        "physics": [
            "Paint drips DOWNWARD only — never sideways or upward",
            "Roller applies paint in W or M pattern from top to bottom",
            "Painter's tape is applied to the EDGE of the surface NOT being painted",
            "Paint tray sits on a flat stable surface — never tilted",
            "Brush bristles bend in direction of stroke — downward on vertical surfaces",
        ],
        "hand_rules": [
            "Roller: dominant hand on handle, other on extension pole or steadying",
            "Brush: pencil grip on ferrule area",
            "Tape application: both hands, one pressing tape, one holding roll",
        ],
        "camera": [
            "Wall painting: wide shot showing wall section, person, and roller stroke area",
            "Detail/edge work: close-up at brush contact point",
            "Full room: wide establishing shot showing tarps, ladder, painted progress",
            "Avoid too-close shots that lose the wall context and painted area",
        ],
        "alignment": [
            "Painter's tape follows straight lines along trim/ceiling edges",
            "Drop cloths cover entire floor area under work zone",
        ],
        "impossible_states": [
            "Paint dripping upward",
            "Roller applying paint at ceiling while person stands on floor (too far)",
            "Three or more hands",
        ],
    },

    "roofing": {
        "physics": [
            "Shingles overlap DOWNSLOPE — upper shingle covers top edge of lower",
            "Water flows DOWN the roof slope — away from ridge toward gutter",
            "Flashing tucks UNDER upper shingles and OVER lower shingles",
            "Nails go through shingle into decking at correct nail line",
            "Gutter slopes slightly toward downspout for drainage",
        ],
        "hand_rules": [
            "Roof work: person kneeling or crouching on roof surface",
            "Both hands visible — one steadying, one working",
            "Safety harness visible on steep roofs",
        ],
        "camera": [
            "Wide shot showing roof slope, ridge, and work area in context",
            "Medium shot for shingle placement showing overlap",
            "Close-up for nail/fastener detail",
            "Always show enough slope context to confirm water flow direction",
        ],
        "alignment": [
            "Ridge is at TOP, eave at BOTTOM",
            "Shingles laid bottom-to-top (eave to ridge)",
            "Downspout at bottom of gutter, gutter slopes toward it",
        ],
        "impossible_states": [
            "Shingles overlapping upslope (reversed)",
            "Water shown flowing up the roof",
            "Three or more hands",
            "Person standing vertically on steep roof without support",
        ],
    },

    "hvac": {
        "physics": [
            "Hot air rises — supply vents near ceiling, return vents near floor",
            "Refrigerant lines are insulated with foam sleeve",
            "Filter slides INTO the air handler with airflow arrow pointing toward unit",
            "Condensate drain line slopes DOWNWARD away from unit",
            "Duct connections are sealed with mastic or foil tape — not plastic tape",
        ],
        "hand_rules": [
            "Filter replacement: both hands on filter edges, person facing unit",
            "Vent work: one hand holding vent cover, other with screwdriver",
        ],
        "camera": [
            "Filter replacement: medium shot showing unit opening and filter",
            "Duct work: wide shot showing duct run and connection point",
            "Thermostat work: close-up eye-level to thermostat",
        ],
        "alignment": [
            "Filter has airflow direction arrow — arrow points INTO unit (toward blower)",
            "Thermostat mounted vertically on wall at eye level",
            "Condenser unit sits on pad OUTSIDE, level",
        ],
        "impossible_states": [
            "Filter installed backward (arrow pointing out)",
            "Condensate draining uphill",
            "Three or more hands",
        ],
    },

    "flooring": {
        "physics": [
            "Planks/tiles laid from one wall outward — expansion gap at all walls",
            "Underlayment goes UNDER flooring, ON TOP of subfloor",
            "Tile spacers maintain consistent grout lines",
            "Grout fills joints AFTER tiles are fully set and adhesive cured",
            "Flooring nailer drives nails at 45-degree angle through tongue",
        ],
        "hand_rules": [
            "Tile setting: both hands on tile, pressing down and sliding into adhesive",
            "Plank installation: one hand tapping with mallet through pull bar, other steadying",
        ],
        "camera": [
            "Wide shot showing installed floor section and work-in-progress edge",
            "Close-up for grout application and spacer placement",
            "Medium shot for plank/tile placement showing alignment with previous row",
        ],
        "alignment": [
            "Tiles are level with each other — no lippage",
            "Grout lines are consistent width throughout",
            "Expansion gap visible at walls (will be covered by baseboard)",
        ],
        "impossible_states": [
            "Tiles floating above subfloor",
            "Grout applied before tiles are set",
            "Three or more hands",
        ],
    },

    "appliance": {
        "physics": [
            "Appliances rest on floor or countertop — never floating",
            "Power cord routes to nearest outlet — not stretched across room",
            "Water supply line connects to inlet valve at BOTTOM or BACK of appliance",
            "Gas line has shutoff valve accessible near appliance",
            "Dryer vent hose connects to back of dryer and exits through wall",
        ],
        "hand_rules": [
            "Moving appliance: both hands on sides, person leaning into it",
            "Connection work: one hand holding connector, other tightening",
        ],
        "camera": [
            "Installation: wide shot showing appliance in its space with connections visible",
            "Connection detail: close-up at connection point",
            "Level check: medium shot showing appliance front and level tool on top",
        ],
        "alignment": [
            "Refrigerator door opens toward accessible side — not into wall",
            "Washer/dryer front faces into laundry room",
            "Dishwasher front panel faces into kitchen",
            "TV screen ALWAYS faces INTO the room — never toward wall",
        ],
        "impossible_states": [
            "TV screen facing wall after mounting",
            "Appliance floating above floor",
            "Three or more hands",
            "Water line connected upside down",
        ],
    },

    "drywall": {
        "physics": [
            "Drywall screws dimple surface slightly — never break paper face",
            "Joint compound feathers out 8-12 inches from seam each coat",
            "Tape embeds INTO first coat of compound — not on top of dry compound",
            "Sanding creates dust that falls DOWNWARD",
            "Sheets hang VERTICALLY for walls, perpendicular to joists for ceilings",
        ],
        "hand_rules": [
            "Mudding: dominant hand on knife, other holding mud pan",
            "Sanding: both hands on sanding block or pole sander",
            "Sheet hanging: both hands supporting sheet against wall",
        ],
        "camera": [
            "Mudding: medium shot showing wall section and feathered compound area",
            "Sanding: wide shot showing dust and sanded area",
            "Taping: close-up showing tape embedding into wet compound",
            "Wide shots preferred to show feathering extent",
        ],
        "alignment": [
            "Drywall sheets are plumb and level",
            "Seams fall on stud centers",
            "Corner bead is straight and plumb on outside corners",
        ],
        "impossible_states": [
            "Tape applied to dry compound",
            "Three or more hands",
            "Compound applied in thick ridges (not feathered)",
        ],
    },

    "doors_windows": {
        "physics": [
            "Door swings on hinges — hinge side is fixed, latch side moves",
            "Weather stripping compresses when door closes — visible as slight bulge",
            "Window sash slides in tracks — up/down for single/double hung",
            "Shims are tapered — thin end toward opening, thick end toward frame",
            "Door must be plumb for latch to engage correctly",
        ],
        "hand_rules": [
            "Hinge installation: one hand holding hinge, other driving screw",
            "Shimming: one hand holding door, other tapping shim with hammer",
        ],
        "camera": [
            "Wide shot showing full door/window in frame and surrounding wall",
            "Medium shot for hardware installation",
            "Close-up for shim placement and gap assessment",
            "Show from room interior perspective — door/window facing viewer",
        ],
        "alignment": [
            "Door face (panel side) faces into the room it opens toward",
            "Window glass faces outward — interior trim faces room",
            "Handle/knob on latch side, hinges on opposite side",
        ],
        "impossible_states": [
            "Door hinges on both sides simultaneously",
            "Three or more hands",
            "Door floating without frame",
        ],
    },

    "landscaping": {
        "physics": [
            "Water flows DOWNHILL — grade slopes away from house foundation",
            "Roots grow DOWNWARD and outward from trunk base",
            "Mulch layers 2-3 inches deep — not mounded against plant stems",
            "Sod rolls out flat on prepared soil — seams staggered like bricks",
            "Shovel blade enters soil at downward angle with foot pressure",
        ],
        "hand_rules": [
            "Digging: both hands on shovel handle at different heights",
            "Planting: both hands in soil, person kneeling",
            "Pruning: one hand on pruner, other steadying branch",
        ],
        "camera": [
            "Wide shot for grading and drainage showing slope direction",
            "Medium shot for planting showing hole depth and root ball",
            "Close-up for detail pruning cuts",
            "Always show enough context for scale reference",
        ],
        "alignment": [
            "Plants upright with root ball below soil surface",
            "Mulch ring around plant — not touching stem",
            "Edging creates clean line between lawn and bed",
        ],
        "impossible_states": [
            "Water flowing uphill toward house",
            "Plant root ball above soil surface",
            "Three or more hands",
        ],
    },

    "pest_control": {
        "physics": [
            "Sealant/caulk flows from nozzle and fills gap — never floats above surface",
            "Bait stations placed flat on surfaces — floor, wall base, or shelf",
            "Spray applies as fine mist settling DOWNWARD onto surfaces",
            "Traps set on surfaces pests travel — floors, wall edges",
        ],
        "hand_rules": [
            "Caulk gun: dominant hand squeezing trigger, other guiding nozzle at gap",
            "Trap placement: both hands positioning trap on surface",
        ],
        "camera": [
            "Wide shot showing entry point / problem area context",
            "Close-up for sealant application at gap",
            "Medium shot for trap/bait placement showing location context",
        ],
        "alignment": [
            "Caulk bead fills gap flush with surrounding surfaces",
            "Traps flat on travel surfaces — not tilted",
        ],
        "impossible_states": [
            "Caulk floating above gap",
            "Three or more hands",
            "Spray going upward",
        ],
    },

    "insulation": {
        "physics": [
            "Batt insulation fits snugly between studs — no gaps at edges",
            "Vapor barrier faces WARM side of wall (interior in cold climates)",
            "Blown insulation settles DOWNWARD — fills from bottom up",
            "Weatherstripping compresses against door/window when closed",
            "Foam sealant expands as it cures — fills gaps and excess trims away",
        ],
        "hand_rules": [
            "Batt installation: both hands pressing insulation into stud bay",
            "Foam application: one hand on can, directing nozzle into gap",
        ],
        "camera": [
            "Wide shot showing stud bay and full batt placement",
            "Close-up for gap sealing and foam application",
            "Medium shot for vapor barrier installation showing coverage",
        ],
        "alignment": [
            "Insulation fills full depth of stud bay",
            "Vapor barrier overlaps at seams minimum 6 inches",
            "No compression of batt insulation — reduces R-value",
        ],
        "impossible_states": [
            "Vapor barrier on wrong side",
            "Three or more hands",
            "Insulation floating between studs without support",
        ],
    },

    "general": {
        "physics": [
            "All objects obey gravity — rest on surfaces unless explicitly supported",
            "Liquids flow downward only",
            "Tools contact the work surface they are acting on",
            "Heavy objects require two hands or mechanical assistance",
        ],
        "hand_rules": [
            "Maximum TWO hands visible in any image",
            "Hands connect to visible arms which connect to a body",
            "Arms enter frame from a direction consistent with a standing/kneeling person",
        ],
        "camera": [
            "Show enough context to understand what is being done and where",
            "Medium shots preferred — not too close to lose context",
            "Wide shots for assembly and installation steps",
            "Close-ups only for detail work (fasteners, connections, markings)",
        ],
        "alignment": [
            "Mounted objects face INTO the room toward the viewer",
            "Screens and reflective surfaces face the user",
            "Labels and controls face the user",
        ],
        "impossible_states": [
            "Three or more hands",
            "Floating objects",
            "Liquids defying gravity",
            "Objects facing wrong direction after installation",
        ],
    },
}

# ─── CAMERA ANGLE GUIDE ───────────────────────────────────────────────────────
CAMERA_ANGLE_GUIDE = """
CAMERA SELECTION RULES — defined by what is VISIBLE IN FRAME:

- WIDE SHOT: Full person head-to-toe visible, plus 30-50% of surrounding room.
  Room furniture, floor, ceiling partially visible. Person occupies 40-60% of
  frame height. Use for: mounting, hanging, installing large objects, any step
  where the object being installed is > 30cm.
  Example: person standing at wall hanging a mirror — full body visible,
  sofa and room visible behind them, mirror on wall visible in full.

- MEDIUM SHOT (most common): Person visible from waist to top of head.
  Both hands and the work surface clearly visible. Room context visible
  behind/beside person (wall, floor, some furniture). Person occupies
  50-70% of frame height. Tool appears ARM-SIZED in frame, not frame-filling.
  Use for: drilling, stud-finding, measuring, screwing in hardware.
  Example: person standing at wall drilling — upper body, both arms, drill,
  and wall section all visible. Room visible behind them.

- CLOSE-UP: Hands + tool + work surface ONLY. No face. Arms visible to elbow.
  Use ONLY for fine detail: marking a pencil dot, tightening one screw,
  reading a measurement. The subject (screw/mark/joint) is 10cm or smaller.
  FORBIDDEN for: drilling, stud-finding, hanging objects, any step where
  room context or object position matters.

- TOP-DOWN: Camera directly above, person crouching or kneeling visible from above.
  Use for: floor layout, tile arrangement, measuring floor area.

- FROM BELOW: Camera below subject looking upward.
  Use for: under-sink, under-cabinet, ceiling work.

PROPORTION RULE — ENFORCED IN EVERY SHOT:
  Hands must appear SMALLER than the person's torso in the frame.
  Tools must appear SMALLER than the person's arm.
  If hands are filling more than 25% of the frame width — the shot is too close.
  Pull back to the next wider shot type.

PERSON VISIBILITY RULE:
  For WIDE and MEDIUM shots: the person's torso must be visible.
  Floating hands with no body = FORBIDDEN in wide and medium shots.
  The person's arms must connect visibly to their body in the frame.

ROOM CONTEXT RULE:
  For installation steps (drilling, mounting, hanging): at least one piece of
  room furniture (sofa, table, chair) must be visible in the background to
  establish scale and confirm the correct wall is being worked on.
"""

# ─── OBJECT ALIGNMENT RULES ───────────────────────────────────────────────────
OBJECT_ALIGNMENT_RULES = """
OBJECT ORIENTATION — ABSOLUTE RULES:
These override any other interpretation of the step description.

SCREENS & DISPLAYS:
- Wall-mounted TV: screen ALWAYS faces INTO the room. Viewer sees the screen front.
  If step involves cable routing "behind the TV", show hands at the SIDE EDGE of
  a forward-facing TV reaching around — never show screen facing wall.
- Monitor: screen faces user at desk. Always.
- Projector screen: fabric face faces audience/seating area.

MIRRORS & REFLECTIVE SURFACES:
- Hung mirror: reflective face ALWAYS faces INTO the room. Viewer sees reflection.
  Back of mirror (with hanging hardware) is against/near wall — NOT visible as
  the primary subject after hanging.
- Exception: pre-hanging steps (attaching D-rings, checking wire) may show back.
  Caption these clearly as "back of mirror — before hanging".

DOORS & WINDOWS:
- Interior door: panel/face side faces the room it opens INTO.
- Window: glass faces outside, interior trim/sill faces room.

APPLIANCES:
- Refrigerator, dishwasher, washer, dryer, oven: controls and door face INTO room.
- Wall oven: door opens downward toward user.

PLUMBING FIXTURES:
- Sink: basin faces up, drain at bottom of basin.
- Toilet: seat and bowl face up, tank at back/top.
- Faucet: handles and spout face up toward user.

ELECTRICAL:
- Outlet: slots face INTO room (vertical rectangle on wall).
- Switch: rocker/toggle faces INTO room, accessible to user.
- Panel: breakers face INTO room, door opens toward user.
"""

# ─── HAND RULES — UNIVERSAL ───────────────────────────────────────────────────
HAND_RULES = """
HAND RULES — NON-NEGOTIABLE:
1. MAXIMUM TWO HANDS in any image. Never three. Never four.
2. Both hands must belong to the SAME person — consistent skin tone and sleeve.
3. Hands connect to wrists, wrists to forearms, forearms to arms, arms to a body.
4. Arms must enter frame from a direction physically possible for a standing/kneeling person.
5. If one hand holds an object and one operates a tool, both are shown in natural positions.
6. Gloves: if shown, BOTH hands wear the same glove type and color.
7. Hands do NOT: emerge from walls, ceilings, or pipes; phase through solid objects;
   grip tools at impossible angles; appear disconnected from any arm.
"""


# ─── PROMPT 1: VISUAL DNA ─────────────────────────────────────────────────────
VISUAL_DNA_PROMPT = """You are a visual consistency engineer for a DIY step image generation pipeline.

Given a project summary, generate a complete Visual DNA object that will govern
ALL image generation for this project. This is generated ONCE and must be
detailed enough to keep every step image visually consistent.

Return ONLY valid JSON:
{
  "domain": "<plumbing|electrical|carpentry|painting|roofing|hvac|flooring|appliance|drywall|doors_windows|landscaping|pest_control|insulation|general>",

  "scene_prefix": "<20-35 word description: work location, wall/floor material+colour, background style, lighting direction+tone. No actions or tools. BE SPECIFIC about colors — e.g. 'sage green painted drywall wall' not just 'wall'>",

  "glove_color": "<appropriate glove type+color for domain>",

  "safety_equipment": {
    "always_required": ["<item always worn: e.g. 'brown leather work gloves', 'safety glasses'>"],
    "step_specific": {
      "drilling": ["safety glasses", "dust mask", "work gloves"],
      "cutting": ["safety glasses", "cut-resistant gloves"],
      "electrical": ["insulated gloves", "safety glasses"],
      "heavy_lifting": ["work gloves", "back support belt"]
    },
    "enforcement": "EVERY step involving tools, drilling, cutting, or heavy objects MUST show appropriate safety equipment. Bare hands on power tools is FORBIDDEN."
  },

  "body_anchors": {
    "primary": "<body anchor sentence including {glove_color}>",
    "elevated": "<elevated body anchor including {glove_color}>",
    "ground_level": "<ground level body anchor including {glove_color}>",
    "standing": "<standing body anchor including {glove_color}>"
  },

  "action_location_keywords": {
    "primary": ["<kw1>", "<kw2>"],
    "elevated": ["ladder", "ceiling", "roof"],
    "ground_level": ["floor", "ground", "base"],
    "standing": ["workbench", "counter", "table"]
  },

  "object_colors": {
    "<main_object_name>": "<exact color+material — copy EXACTLY from user description if provided. E.g. 'sage green smooth painted drywall' not 'green wall'>",
    "<secondary_object>": "<exact color+material>"
  },

  "color_lock": {
    "wall": "<EXACT wall color — e.g. 'sage green', 'warm white', 'beige' — extracted from user description or summary>",
    "floor": "<exact floor color and material>",
    "primary_object": "<exact color of main object being worked on>",
    "enforcement": "These colors are LOCKED and must appear in EVERY step image. If reference images show a different color, reference images are WRONG — use these locked colors."
  },

  "face_rule": "NEVER show a person's face clearly in any step image. Person is always shown from behind, side profile with face turned away, or with face outside the frame. This prevents identity concerns and keeps focus on the task.",

  "step_shooting_plan": {
    "description": "<1-2 sentence overview of the visual narrative across all steps>",
    "establishing_shot": "<describe the ideal wide shot that establishes the scene — room, wall color, main object, scale>",
    "progression_notes": "<how the scene should evolve visually step by step — e.g. 'wall starts bare, pencil marks appear in step 2, holes drilled in step 3, hardware visible in step 4, mirror hung in final steps'>",
    "consistent_elements": ["<element that must appear in every step: e.g. 'sage green wall always visible in background'>", "<element 2>"],
    "camera_progression": "<how camera angle should change across steps — e.g. 'wide for setup steps, medium for drilling, wide again for final hang'>",
    "safety_note": "<when safety gear must appear — e.g. 'gloves and glasses mandatory for steps involving drill, hammer, or heavy lifting'>"
  },

  "simplification_rules": ["<one rule for this domain>"]
}

CRITICAL:
- object_colors and color_lock must reflect user-provided colors if any are mentioned
- color_lock.enforcement overrides everything — these colors cannot change between steps
- face_rule is absolute — no faces in any step image
- step_shooting_plan is a narrative guide for the entire project's visual sequence
- Return ONLY the JSON. No markdown. No explanation."""


# ─── PROMPT 2: CONTEXT IMAGE PLANNER ─────────────────────────────────────────
CONTEXT_IMAGE_PLANNER_PROMPT = """You are a visual planning expert for a DIY instructional image pipeline.

Given a DIY project summary and its domain, plan 2-3 establishing "context images"
that will be generated ONCE and used as visual reference for ALL step images.

These images show the main objects from different angles so the AI image model
can maintain visual consistency across all steps.

Return ONLY valid JSON:
{
  "context_images": [
    {
      "name": "<short_name e.g. 'front_view', 'back_view', 'wide_room_view'>",
      "angle": "<wide|medium|close-up|top-down|from-below>",
      "purpose": "<what this image establishes for future steps>",
      "prompt": "<detailed 50-80 word photorealistic Imagen prompt. Include: camera angle, all main objects visible, their colors/materials, lighting, NO people, NO hands, NO text, NO labels. Show the static scene before work begins.>"
    }
  ]
}

RULES:
- Always include a WIDE shot showing full scene context and scale
- Include angle showing the back/mechanism of the main object if relevant
  (e.g. back of mirror showing D-rings, back of TV showing ports)
- NO people or hands in context images — objects only
- Describe objects with maximum specificity: exact shape, color, material, finish
- These images establish the visual "ground truth" — be as specific as possible
- 2 images minimum, 3 maximum

Return ONLY the JSON. No markdown. No explanation."""


# ─── PROMPT 3: STEP PLANNER ───────────────────────────────────────────────────
STEP_PLANNER_PROMPT = """You are a visual planning expert for a DIY step image generation pipeline.

Before generating an image for a step, you must CREATE A PLAN for what the image
should show. This plan becomes the structured Imagen prompt.

You receive:
- The step description
- The project domain and its physics rules
- Previous step state summaries (memory)
- Object color registry (must be maintained)
- Color lock (colors that CANNOT change between steps)
- Safety equipment requirements
- Step shooting plan from Visual DNA

Return ONLY valid JSON:
{
  "camera_angle": "<wide|medium|close-up|top-down|from-below>",
  "camera_reason": "<1 sentence: why this angle best shows this step>",
  "camera_distance": "<specific: '3-4 meters from person' | '2-3 meters' | 'arm length from subject'>",
  "body_visibility": "<'full body head-to-toe' | 'waist-to-head' | 'hands and forearms only (close-up only)'>",
  "face_rule": "Person's face must NOT be visible — show from behind, side with face turned away, or face outside frame",
  "which_wall": "<'primary feature wall facing viewer' | 'floor' | 'ceiling' | 'not applicable'>",
  "person_position": "<where person stands relative to camera and wall>",
  "primary_action": "<single most visual action, verb+direction+object, max 15 words>",
  "safety_equipment_this_step": ["<list all safety items required: e.g. 'brown leather work gloves', 'safety glasses', 'dust mask'>"],
  "safety_reason": "<why this safety equipment is needed for this specific step>",
  "objects_visible": ["<object1 with LOCKED color from color_lock registry>", "<object2>"],
  "locked_colors_used": {
    "wall": "<repeat exact locked wall color — must match color_lock>",
    "floor": "<repeat exact locked floor color>",
    "primary_object": "<repeat exact locked primary object color>"
  },
  "object_scale_check": "<each tool's size relative to person>",
  "hand_description": "<exactly what hands are doing — max 2 hands, wearing safety gloves if step requires>",
  "room_context_visible": "<what room elements visible to establish scale>",
  "cumulative_state": "<what scene looks like based on ALL prior steps>",
  "physics_checks": ["<physics rule and how satisfied>"],
  "impossible_states_avoided": ["<impossible state avoided>"],
  "orientation_note": "<object orientation if any>",
  "imagen_prompt": "<final 70-110 word structured prompt. MUST include: [SHOT TYPE + CAMERA DISTANCE] [PERSON POSITION — FACE NOT VISIBLE] [SAFETY EQUIPMENT WORN] [ROOM CONTEXT WITH LOCKED WALL COLOR] [ACTION] [TOOL SIZE IN PROPORTION] [LOCKED COLORS FOR ALL OBJECTS]>",
  "state_summary": "<10-20 word plain English: what physically changed>"
}

CRITICAL RULES:

COLOR LOCK (highest priority):
- The color_lock in your input is ABSOLUTE — these colors cannot change
- If color_lock says wall is 'sage green', EVERY imagen_prompt must say 'sage green wall'
- Copy the locked color strings VERBATIM into imagen_prompt — do not paraphrase
- Example: NOT 'green wall' — ALWAYS 'sage green smooth painted drywall wall'
- locked_colors_used field must repeat these exactly — use as a self-check

FACE RULE (absolute):
- Person's face must NEVER be visible in any step image
- Show person from behind facing the wall, OR side profile with face turned away,
  OR with face cropped out of top of frame
- Add 'face not visible, person shown from behind facing the wall' to every imagen_prompt
- This is non-negotiable regardless of camera angle

SAFETY EQUIPMENT (mandatory for tool/drill/lift steps):
- Identify safety_equipment_this_step from the domain's safety_equipment rules
- Any step involving: drill, hammer, saw, heavy object, cutting → gloves + glasses mandatory
- Add gloves and glasses explicitly to imagen_prompt:
  'wearing [color] work gloves and safety glasses'
- Do NOT leave safety equipment implicit — state it explicitly in the prompt

SHOT SELECTION:
- Drilling, stud-finding, measuring → ALWAYS medium or wide. NEVER close-up.
- Hanging/mounting large object → ALWAYS wide. Person full body visible.
- Fine detail only → close-up

BODY VISIBILITY:
- wide: full body head-to-toe, person 40-60% of frame height
- medium: waist-to-head, torso visible, person 50-70% of frame height
- floating hands without body = FORBIDDEN in wide/medium shots

PROPORTION:
- hands smaller than person's torso
- tools smaller than person's arm
- measuring tape: max 60-80cm visible, never floor-to-ceiling
- drill: forearm-length, never larger than person's torso

WALL IDENTIFICATION:
- ALL wall work → primary feature wall only
- room furniture must be visible in background to confirm scale and correct wall

IMAGEN PROMPT MANDATORY STRUCTURE:
'[SHOT TYPE] shot, camera [X] meters from person.
Person [full body / waist-up], standing [distance] from [EXACT LOCKED WALL COLOR] wall,
face not visible — shown from behind facing wall.
Wearing [safety equipment explicitly listed].
[Room furniture] visible in background.
Person is [action]. [Tool name], [arm/hand-sized], in natural proportion.
[Primary object with EXACT LOCKED COLOR on wall].'

Return ONLY the JSON. No markdown. No explanation."""



# ─── PROMPT 4: IMAGE GENERATION (passed to Gemini with reference images) ──────
IMAGE_GENERATION_PROMPT = """You are generating a photorealistic DIY instructional image using Gemini.

Reference images are provided:
1. Context images — establish scene colors, object shapes, room style
2. Prior step images — show cumulative work state

CRITICAL: If reference images show a wall color that differs from the color
specified in the text prompt, FOLLOW THE TEXT PROMPT COLOR. The text prompt
color is the locked ground truth.

Generate ONE photorealistic image matching the structured prompt exactly.

ABSOLUTE RULES:

1. WALL COLOR IS LOCKED — use the exact wall color stated in the prompt.
   If prompt says 'sage green wall', every pixel of that wall is sage green.
   Do NOT substitute white, beige, or any other color. Reference images showing
   different wall colors are contextual only — the text prompt color overrides.

2. FACE RULE — person's face must NOT be visible. Show person from behind
   facing the wall, side profile with face turned away, or face outside frame.
   This is non-negotiable in every step image.

3. SAFETY EQUIPMENT — if prompt says 'wearing brown leather work gloves and
   safety glasses', both items must be clearly visible on the person.
   Bare hands on power tools = FORBIDDEN when gloves are specified.

4. MAXIMUM TWO HANDS — never three, never four.

5. PERSON MUST BE VISIBLE — for wide and medium shots, person's torso must
   be in frame. Floating hands with no body = FORBIDDEN.

6. BODY PROPORTIONS — hands smaller than torso, tools smaller than arms.
   Measuring tape max 60-80cm visible. Drill forearm-length only.

7. CORRECT WALL — drilling/mounting on PRIMARY FEATURE WALL only.
   Room furniture visible in background to confirm scale.

8. SHOT DISTANCE — follow camera distance in prompt exactly.
   'Wide shot 3-4 meters' = full body figure, NOT a close-up of hands.

9. TOOL SCALE — no tool appears larger than the person's torso.

10. MOUNTED OBJECTS — show FRONT face toward viewer (mirror reflective side,
    TV screen, picture front).

11. PHYSICS — all physics rules in prompt must be satisfied.

12. NO TEXT — no labels, watermarks, brand names, numbers on walls.

13. MATCH REFERENCE IMAGES for everything EXCEPT wall color and safety equipment
    (those follow text prompt as ground truth).

14. Photorealistic, 4K HDR, sharp focus, professional photography quality."""
