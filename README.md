# 📬 Smart Email Triage Agent  
### AI-powered Gmail automation with GPT-5.1, Streamlit UI, and PostgreSQL storage

The **Smart Email Triage Agent** is an intelligent inbox assistant that automatically retrieves unread Gmail messages, summarizes them, detects urgency, extracts tasks, generates reply drafts, and stores everything in a persistent PostgreSQL database.  
It includes a modern Streamlit dashboard with dynamic filtering, metrics, and a technophilic UI theme.

---

## 🚀 Features

- **Gmail API integration** — fetch unread messages and mark them as read after processing  
- **GPT-5.1 AI Agent**:
  - Email summarization  
  - Priority classification  
  - Category prediction  
  - Task extraction  
  - Reply draft generation  
- **Streamlit Web Application**:
  - Newly processed email view  
  - Historical archive  
  - Category & urgency filters  
  - Task lists  
  - Neon/technophilic themed UI  
  - Database reset tools  
- **PostgreSQL storage** with deduplication  
- **Idempotent email processing** (same email is never processed twice)  

---

# 🛠️ Tech Stack

- **Python 3.12**  
- **Streamlit**  
- **OpenAI GPT-5.1 API**  
- **PostgreSQL (local or cloud)**  
- **psycopg2-binary**  
- **Gmail API (Google OAuth2)**  
- **dotenv for environment variables**

---

# Install Dependencies (preferably inside a virtual environment)

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib openai python-dotenv streamlit psycopg2-binary
```

# Create a PostgreSQL Database

```sql
CREATE DATABASE smart_email_agent;
CREATE USER smart_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE smart_email_agent TO smart_user;

\c smart_email_agent
GRANT USAGE, CREATE ON SCHEMA public TO smart_user;
ALTER SCHEMA public OWNER TO smart_user;
```

# Create your OPENAI_API_KEY and DATABASE_URL and put them in .env file

# Enable Gmail API + OAuth Credentials

Step-by-step:

Go to Google Cloud Console → https://console.cloud.google.com/

Create a project (or use existing)

Enable Gmail API

Go to APIs & Services → OAuth consent screen

App name: Smart Email Triage Agent

User type: External

Add your email as test user

Go to Credentials → Create Credentials → OAuth Client ID

Choose Desktop Application

Download the credentials.json

Place it in the project root

The first time the app runs, it opens a browser to authorize via Google OAuth.

# Run your app

```bash
streamlit run streamlit_app.py
```



