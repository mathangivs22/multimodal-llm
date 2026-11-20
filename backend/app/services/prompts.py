"""Prompts sent to the local model. Kept in one place so they are easy to tune."""

MINUTES_PROMPT = """You are an AI Meeting Assistant writing Minutes of Meeting.

Return JSON only, with exactly this structure:

{{
    "meeting_overview": {{"title": "", "date": "", "participants": []}},
    "discussion_summary": [],
    "key_decisions": [{{"text": "", "status": "finalized or suggested", "source_seq": 0}}],
    "action_items": [{{"task": "", "owner": "", "deadline": "", "source_seq": 0}}],
    "pending_items": [],
    "next_meeting": ""
}}

Rules:
1. Use only facts stated in the transcript or slides. Do not add anything else.
2. Attribution: a suggestion, opinion or agreement belongs to a person only if that person's own words say it. "Carol recommended X" is valid only if Carol said it. Never swap speakers.
3. "finalized" only when someone clearly agrees or decides, for example "let's go with", "we agreed", "approved". Use "suggested" for "I suggest", "might be better", "proposal", or anything a team member has not confirmed.
4. Action items: the owner is the person who says "I'll ..." or accepts the task. The deadline is copied exactly as spoken, for example "November 20". If no owner or deadline is stated, use an empty string.
5. Each transcript line starts with a number in [brackets]. Put that number in source_seq for the decision or action item it comes from. Use 0 if there is no clear source.
6. Keep lists short. Use empty strings or empty arrays when information is missing.

Example. Transcript:
[1] 00:00:00 Alice. Let's go with PostgreSQL. Bob, can you set up the database?
[2] 00:00:08 Bob. Sure. I'll finish the database setup by November 20.
[3] 00:00:14 Carol. I suggest we add Redis later.

Correct output for the example:
{{"meeting_overview": {{"title": "", "date": "", "participants": ["Alice", "Bob", "Carol"]}},
  "discussion_summary": ["The team chose PostgreSQL.", "Carol suggested adding Redis later."],
  "key_decisions": [
    {{"text": "Use PostgreSQL", "status": "finalized", "source_seq": 1}},
    {{"text": "Add Redis later", "status": "suggested", "source_seq": 3}}],
  "action_items": [{{"task": "Set up the database", "owner": "Bob", "deadline": "November 20", "source_seq": 2}}],
  "pending_items": [], "next_meeting": ""}}

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
