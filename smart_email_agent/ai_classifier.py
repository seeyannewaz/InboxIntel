import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
You are an intelligent email triage assistant.

You MUST respond ONLY with a single valid JSON object with this exact schema:
{
  "summary": "1-3 sentence plain-English summary of the email",
  "urgency": "urgent | normal | low",
  "category": "work | school | personal | promo | automated",
  "tasks": ["task1", "task2"],
  "reply_draft": "suggested reply text"
}

Rules:
- No extra commentary, no explanations, no markdown, no code fences.
- "summary" should focus on the main point and key actions/dates, not every detail.
- "tasks" should be a list of concrete, actionable items from the email body.
- If there are no tasks, use an empty list [].
- If the email is clearly automated or promotional, set category to "promo" or "automated"
  and you may set reply_draft to an empty string.
""".strip()

def _clean_json_text(raw: str) -> str:
    """
    Clean up common patterns like ```json ... ``` wrappers before json.loads.
    """
    text = raw.strip()

    # Strip markdown fences like ```json ... ```
    if text.startswith("```"):
        # remove starting ```
        text = text.strip("`").strip()
        # remove leading 'json' if present
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
    return text


def classify_with_ai(subject: str, body: str, sender: str) -> dict:
    """
    Uses GPT-5.1 via Chat Completions.
    Returns a Python dict with keys: urgency, category, tasks, reply_draft.
    Raises an exception if JSON cannot be parsed (caught in triage.py).
    """

    user_prompt = f"""
EMAIL SENDER: {sender}
SUBJECT: {subject}

BODY:
{body}
""".strip()

    response = client.chat.completions.create(
        model="gpt-5.1",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        # optional: you *can* try enabling JSON mode if your model+SDK support it:
        # response_format={"type": "json_object"},
        temperature=0,  # more deterministic JSON
    )

    content = response.choices[0].message.content
    text = _clean_json_text(content)

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"AI returned invalid JSON: {content}") from e
