# run_triage.py

from smart_email_agent.storage import Storage
from smart_email_agent.triage import run_triage

import sys

if __name__ == "__main__":
    storage = Storage()

    if len(sys.argv) > 1 and sys.argv[1] == "--clear-db":
        storage.clear_all()
        print("Database cleared.")
        storage.close()
        sys.exit(0)

    run_triage()

