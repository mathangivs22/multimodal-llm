"""Prompts sent to the local model. Kept in one place so they are easy to tune."""

MINUTES_PROMPT = """You are an AI Meeting Assistant.

Analyze the meeting material below and return Minutes of Meeting as JSON only.

Use exactly this structure:

{{
    "meeting_overview": {{
        "title": "",
        "date": "",
        "participants": []
    }},
    "discussion_summary": [],
    "key_decisions": [
        {{
            "text": "",
            "status": "finalized or suggested",
            "source_seq": 0
        }}
    ],
    "action_items": [
        {{
            "task": "",
            "owner": "",
            "deadline": "",
            "source_seq": 0
        }}
    ],
    "pending_items": [],
    "next_meeting": ""
}}

Instructions:
- Only include information supported by the material.
- Each transcript line starts with a number in [brackets]. Put that number in source_seq for the decision or action item it supports. Use 0 if there is no clear source.
- Mark a decision "finalized" only if the team clearly agreed. Otherwise mark it "suggested".
- Keep deadlines exactly as written (for example "November 20"). Do not invent participants, dates or deadlines.
- Use an empty string or empty array when information is missing.
- Return valid JSON only.

SLIDES (text and speaker notes):
{slides}

SLIDE DIAGRAM ANALYSIS (from the vision model):
{visuals}

TRANSCRIPT (each line: [seq] mm:ss text):
{transcript}
"""

SLIDE_VISION_PROMPT = """Analyze this PowerPoint slide (slide {slide_number}).

Focus on its visual structure, not just the text.

Identify:
1. Components and their categories.
2. Connections between components.
3. Direction of arrows and data flow.
4. Workflow sequence, if present.
5. Any relationships that are unclear.

Return a JSON object with this structure:

{{
    "slide_number": {slide_number},
    "slide_title": "",
    "components": [{{"name": "", "category": ""}}],
    "relationships": [{{"source": "", "target": "", "description": "", "direction": ""}}],
    "workflow_steps": [],
    "uncertain_relationships": []
}}

Important:
- Only report relationships supported by the visual.
- Do not invent connections based on assumptions.
- If an arrow or connection is unclear, mention that.
- Preserve the names shown in the slide.
- Return valid JSON only.
"""
