from dataclasses import dataclass
from typing import List

@dataclass
class ProcessedEmail:
    id: str
    sender: str
    subject: str
    body: str
    urgency: str
    category: str
    tasks: List[str]
    summary: str = ""       # 👈 NEW
    reply_draft: str = ""

