# smart_email_agent/triage.py

from typing import List, Optional

from .ai_classifier import classify_with_ai
from .models import ProcessedEmail
from .email_source import get_default_email_source, EmailSource, GmailEmailSource
from .storage import Storage


def process_emails(
    source: Optional[EmailSource] = None,
    storage: Optional[Storage] = None,
) -> List[ProcessedEmail]:
    """
    - Fetch raw emails from the source
    - Skip ones already stored in DB
    - Process only NEW ones
    - Use GPT-based classification ONLY (no rule-based fallback)
    - Save results (and their tasks) to SQLite
    - Return the list of newly processed emails
    """
    if source is None:
        source = get_default_email_source()
    if storage is None:
        storage = Storage()

    # 1) Fetch emails from source
    raw_emails = source.get_emails()

    # 2) Get already-seen IDs from DB
    seen_ids = storage.get_seen_email_ids()

    # 3) Filter down to only new ones
    new_raw_emails = [e for e in raw_emails if e["id"] not in seen_ids]

    processed: List[ProcessedEmail] = []

    for e in new_raw_emails:
        subject = e["subject"]
        body = e["body"]
        sender = e["sender"]

        # ---------- AI-based classification ONLY ----------
        # Let any errors (quota, network, JSON, etc.) raise so you see them.
        ai_result = classify_with_ai(
            subject=subject,
            body=body,
            sender=sender,
        )

        summary = ai_result.get("summary", "")
        urgency = ai_result.get("urgency", "normal")
        category = ai_result.get("category", "personal")
        tasks = ai_result.get("tasks", []) or []
        reply_draft = ai_result.get("reply_draft", "")

        # ---------- Build ProcessedEmail ----------
        pe = ProcessedEmail(
            id=e["id"],
            sender=sender,
            subject=subject,
            body=body,
            urgency=urgency,
            category=category,
            tasks=tasks,
            summary=summary,
        )
        pe.reply_draft = reply_draft

        processed.append(pe)

        # Save to DB
        storage.save_processed_email(pe)

        # If we processed any Gmail emails, mark them as read in Gmail
        if processed and isinstance(source, GmailEmailSource):
            source.mark_as_read([e.id for e in processed])

    return processed


def print_summary(emails: List[ProcessedEmail]) -> None:
    urgency_order = {"urgent": 0, "normal": 1, "low": 2}
    emails_sorted = sorted(emails, key=lambda x: urgency_order.get(x.urgency, 3))

    print("=" * 60)
    print("SMART EMAIL TRIAGE SUMMARY (AI-only)")
    print("=" * 60)

    if not emails_sorted:
        print("\nNo new emails to process. You're all caught up! 🎉")
        return

    for e in emails_sorted:
        print("\n----------------------------------------")
        print(f"ID       : {e.id}")
        print(f"From     : {e.sender}")
        print(f"Subject  : {e.subject}")
        print(f"Urgency  : {e.urgency.upper()}")
        print(f"Category : {e.category}")
        if e.tasks:
            print("Tasks:")
            for t in e.tasks:
                print(f"  - {t}")
        else:
            print("Tasks: None detected")

        print("\nAI Suggested Reply Draft:")
        print(e.reply_draft)
        print("----------------------------------------")


def run_triage() -> None:
    storage = Storage()
    try:
        emails = process_emails(storage=storage)
        print_summary(emails)
    finally:
        storage.close()
