# smart_email_agent/email_source.py

from typing import List, Dict, Protocol, runtime_checkable
import os


@runtime_checkable
class EmailSource(Protocol):
    """Interface for any email source (here: Gmail only)."""

    def get_emails(self) -> List[Dict[str, str]]:
        """
        Returns a list of raw email dicts with keys:
        - id: str
        - sender: str
        - subject: str
        - body: str
        """
        ...


# ============================================================
# Gmail email source (API-based)
# ============================================================

class GmailEmailSource:
    """
    Fetches emails from Gmail using the Gmail API.
    Requires:
    - credentials.json in project root
    - token.pickle created after first OAuth auth
    """

    def __init__(self, user_id: str = "me", max_results: int = 20):
        self.user_id = user_id
        self.max_results = max_results

    def _get_service(self):
        from googleapiclient.discovery import build
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        import os.path
        import pickle

        SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

        creds = None
        token_path = "token.pickle"
        cred_path = "credentials.json"

        if os.path.exists(token_path):
            with open(token_path, "rb") as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(cred_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, "wb") as token:
                pickle.dump(creds, token)

        service = build("gmail", "v1", credentials=creds)
        return service

    def get_emails(self) -> List[Dict[str, str]]:
        service = self._get_service()

        results = service.users().messages().list(
            userId=self.user_id,
            labelIds=["INBOX"],   # restrict to inbox
            q="is:unread",        # Gmail search query: only unread
            maxResults=self.max_results,
        ).execute()


        messages = results.get("messages", [])
        emails: List[Dict[str, str]] = []

        for m in messages:
            msg = service.users().messages().get(
                userId=self.user_id,
                id=m["id"],
                format="full"
            ).execute()

            headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
            sender = headers.get("from", "")
            subject = headers.get("subject", "")
            body = self._extract_body_text(msg)

            emails.append({
                "id": m["id"],
                "sender": sender,
                "subject": subject,
                "body": body,
            })

        return emails
    
    def mark_as_read(self, email_ids: list[str]) -> None:
        """
        Mark the given Gmail message IDs as read by removing the UNREAD label.
        """
        if not email_ids:
            return

        service = self._get_service()

        for msg_id in email_ids:
            try:
                service.users().messages().modify(
                    userId=self.user_id,
                    id=msg_id,
                    body={"removeLabelIds": ["UNREAD"]},
                ).execute()
            except Exception as e:
                print(f"[WARN] Failed to mark {msg_id} as read: {e}")

    def _extract_body_text(self, msg) -> str:
        import base64

        def _walk_parts(part) -> str:
            if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
                data = part["body"]["data"]
                decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                return decoded

            if "parts" in part:
                collected = []
                for p in part["parts"]:
                    txt = _walk_parts(p)
                    if txt:
                        collected.append(txt)
                return "\n".join(collected)

            return ""

        payload = msg.get("payload", {})
        return _walk_parts(payload)


# ============================================================
# Default source selector (Gmail only)
# ============================================================

def get_default_email_source() -> EmailSource:
    """
    Default email source for the whole app.
    Always returns GmailEmailSource.
    max_results default is 20 for CLI runs.
    """
    max_results = int(os.getenv("GMAIL_MAX_RESULTS", "20"))
    return GmailEmailSource(max_results=max_results)
