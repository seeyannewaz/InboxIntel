# # smart_email_agent/storage.py

# import sqlite3
# from datetime import datetime
# from typing import Iterable, Set, List

# from .models import ProcessedEmail


# class Storage:
#     """
#     Lightweight SQLite wrapper to:
#     - Remember processed email IDs
#     - Store emails & tasks
#     """

#     def __init__(self, db_path: str = "smart_email_agent.db"):
#         self.db_path = db_path
#         self.conn = sqlite3.connect(self.db_path)
#         self.conn.row_factory = sqlite3.Row
#         self._create_tables()

#     def _create_tables(self) -> None:
#         cur = self.conn.cursor()

#         # Emails table with summary column
#         cur.execute(
#             """
#             CREATE TABLE IF NOT EXISTS emails (
#                 email_id     TEXT PRIMARY KEY,
#                 sender       TEXT,
#                 subject      TEXT,
#                 body         TEXT,
#                 urgency      TEXT,
#                 category     TEXT,
#                 summary      TEXT,
#                 processed_at TEXT
#             )
#             """
#         )

#         # Backwards-compat: if 'summary' column doesn't exist yet in an old DB, add it
#         cur.execute("PRAGMA table_info(emails)")
#         columns = [row["name"] for row in cur.fetchall()]
#         if "summary" not in columns:
#             cur.execute("ALTER TABLE emails ADD COLUMN summary TEXT")

#         # Tasks table unchanged
#         cur.execute(
#             """
#             CREATE TABLE IF NOT EXISTS tasks (
#                 id          INTEGER PRIMARY KEY AUTOINCREMENT,
#                 email_id    TEXT,
#                 description TEXT,
#                 due_date    TEXT,
#                 created_at  TEXT,
#                 FOREIGN KEY (email_id) REFERENCES emails(email_id)
#             )
#             """
#         )

#         self.conn.commit()

#     # ---------- Email ID tracking ----------

#     def get_seen_email_ids(self) -> Set[str]:
#         """Return a set of email_ids already stored."""
#         cur = self.conn.cursor()
#         cur.execute("SELECT email_id FROM emails")
#         rows = cur.fetchall()
#         return {row["email_id"] for row in rows}

#     # ---------- Saving processed emails & tasks ----------

#     def save_processed_email(self, email: ProcessedEmail) -> None:
#         """
#         Save a processed email and its tasks.
#         If the email already exists, it will be ignored.
#         """
#         cur = self.conn.cursor()
#         processed_at = datetime.utcnow().isoformat(timespec="seconds")

#         cur.execute(
#             """
#             INSERT OR IGNORE INTO emails (
#                 email_id, sender, subject, body, urgency, category, summary, processed_at
#             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
#             """,
#             (
#                 email.id,
#                 email.sender,
#                 email.subject,
#                 email.body,
#                 email.urgency,
#                 email.category,
#                 email.summary,
#                 processed_at,
#             ),
#         )

#         # Insert tasks (if any)
#         for task in email.tasks:
#             cur.execute(
#                 """
#                 INSERT INTO tasks (email_id, description, due_date, created_at)
#                 VALUES (?, ?, ?, ?)
#                 """,
#                 (
#                     email.id,
#                     task,
#                     None,
#                     processed_at,
#                 ),
#             )

#         self.conn.commit()

#     # ---------- Optional helpers (for future UI, debugging, etc.) ----------

#     def fetch_all_emails(self) -> List[ProcessedEmail]:
#         """Load all stored emails (without querying the source)."""
#         cur = self.conn.cursor()
#         cur.execute(
#             """
#             SELECT email_id, sender, subject, body, urgency, category, summary
#             FROM emails
#             ORDER BY processed_at DESC
#             """
#         )
#         rows = cur.fetchall()
#         return [
#             ProcessedEmail(
#                 id=row["email_id"],
#                 sender=row["sender"],
#                 subject=row["subject"],
#                 body=row["body"],
#                 urgency=row["urgency"],
#                 category=row["category"],
#                 tasks=self.fetch_tasks_for_email(row["email_id"]),
#                 summary=row["summary"] or "",
#             )
#             for row in rows
#         ]

#     def fetch_tasks_for_email(self, email_id: str) -> List[str]:
#         cur = self.conn.cursor()
#         cur.execute(
#             "SELECT description FROM tasks WHERE email_id = ? ORDER BY id ASC",
#             (email_id,),
#         )
#         return [row["description"] for row in cur.fetchall()]

#     def clear_all(self) -> None:
#         """Delete all processed emails and tasks from the database."""
#         cur = self.conn.cursor()
#         cur.execute("DELETE FROM tasks")
#         cur.execute("DELETE FROM emails")
#         self.conn.commit()

#     def close(self) -> None:
#         self.conn.close()


# smart_email_agent/storage.py

# smart_email_agent/storage.py

import os
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

import psycopg2
import psycopg2.extras

from .models import ProcessedEmail


@dataclass
class StorageConfig:
    database_url: str


class Storage:
    """
    PostgreSQL-backed storage for processed emails and tasks.

    Expects DATABASE_URL in the environment, e.g.:
    postgresql://user:password@host:5432/smart_email_agent
    """

    def __init__(self, config: Optional[StorageConfig] = None) -> None:
        if config is None:
            db_url = os.getenv("DATABASE_URL")
            if not db_url:
                raise RuntimeError(
                    "DATABASE_URL is not set. Example: "
                    "postgresql://user:password@localhost:5432/smart_email_agent"
                )
            config = StorageConfig(database_url=db_url)

        self.config = config
        # Create a fresh connection per Storage instance (safe for Streamlit threads)
        self.conn = psycopg2.connect(self.config.database_url)
        # DictCursor so we can use row["column_name"]
        self.conn.autocommit = False
        self._create_tables()

    # ---------------------------
    # Schema / Setup
    # ---------------------------

    def _create_tables(self) -> None:
        cur = self.conn.cursor()
        # Emails table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS emails (
                email_id     TEXT PRIMARY KEY,
                sender       TEXT,
                subject      TEXT,
                body         TEXT,
                urgency      TEXT,
                category     TEXT,
                summary      TEXT,
                processed_at TIMESTAMPTZ
            );
            """
        )

        # Tasks table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id          SERIAL PRIMARY KEY,
                email_id    TEXT REFERENCES emails(email_id) ON DELETE CASCADE,
                description TEXT,
                due_date    TIMESTAMPTZ,
                created_at  TIMESTAMPTZ
            );
            """
        )

        self.conn.commit()

    # ---------------------------
    # Core helpers
    # ---------------------------

    def get_seen_email_ids(self) -> List[str]:
        """Return a list of email IDs that have already been processed."""
        cur = self.conn.cursor()
        cur.execute("SELECT email_id FROM emails;")
        rows = cur.fetchall()
        return [row[0] for row in rows]

    def save_processed_email(self, email: ProcessedEmail) -> None:
        """
        Save a processed email and its tasks.
        If the email already exists, ignore the insert.
        """
        cur = self.conn.cursor()
        processed_at = datetime.utcnow()

        # Insert email if not exists
        cur.execute(
            """
            INSERT INTO emails (
                email_id, sender, subject, body, urgency, category, summary, processed_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (email_id) DO NOTHING;
            """,
            (
                email.id,
                email.sender,
                email.subject,
                email.body,
                email.urgency,
                email.category,
                email.summary,
                processed_at,
            ),
        )

        # Insert tasks (if any)
        if email.tasks:
            for task in email.tasks:
                cur.execute(
                    """
                    INSERT INTO tasks (email_id, description, due_date, created_at)
                    VALUES (%s, %s, %s, %s);
                    """,
                    (
                        email.id,
                        task,
                        None,  # due_date parsing can be added later
                        processed_at,
                    ),
                )

        self.conn.commit()

    def fetch_tasks_for_email(self, email_id: str) -> List[str]:
        """Return list of task descriptions for a given email."""
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT description
            FROM tasks
            WHERE email_id = %s
            ORDER BY created_at ASC;
            """,
            (email_id,),
        )
        rows = cur.fetchall()
        return [row[0] for row in rows]

    def fetch_all_emails(self) -> List[ProcessedEmail]:
        """Load all stored emails (without querying Gmail)."""
        # Use DictCursor so we can refer by column name
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(
            """
            SELECT email_id, sender, subject, body, urgency, category, summary
            FROM emails
            ORDER BY processed_at DESC;
            """
        )
        rows = cur.fetchall()

        emails: List[ProcessedEmail] = []
        for row in rows:
            email_id = row["email_id"]
            tasks = self.fetch_tasks_for_email(email_id)
            emails.append(
                ProcessedEmail(
                    id=email_id,
                    sender=row["sender"],
                    subject=row["subject"],
                    body=row["body"],
                    urgency=row["urgency"],
                    category=row["category"],
                    tasks=tasks,
                    summary=row["summary"] or "",
                )
            )
        return emails

    def clear_all(self) -> None:
        """Delete all emails and tasks."""
        cur = self.conn.cursor()
        cur.execute("DELETE FROM tasks;")
        cur.execute("DELETE FROM emails;")
        self.conn.commit()

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

