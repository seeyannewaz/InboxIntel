# streamlit_app.py

import streamlit as st

from smart_email_agent.triage import process_emails
from smart_email_agent.storage import Storage
from smart_email_agent.email_source import GmailEmailSource
from smart_email_agent.models import ProcessedEmail

# ---------------------------
# Storage (per run)
# ---------------------------
storage = Storage()

# ---------------------------
# Global styles (technophilic vibes)
# ---------------------------
st.set_page_config(
    page_title="InboxIntel",
    page_icon="🤖",
    layout="wide",
)

# Custom CSS for neon/tech look
st.markdown(
    """
    <style>
    /* Base background */
    .stApp {
        background: radial-gradient(circle at top left, #0f172a 0, #020617 45%, #000000 100%);
        color: #e5e7eb;
        font-family: "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Make cards cleaner */
    .email-card {
        border-radius: 16px;
        padding: 16px 18px;
        margin-bottom: 12px;
        background: linear-gradient(135deg, rgba(15,23,42,0.9), rgba(30,64,175,0.45));
        border: 1px solid rgba(148,163,184,0.35);
        box-shadow: 0 18px 45px rgba(15,23,42,0.8);
    }

    .email-header-text {
        font-weight: 600;
        font-size: 0.9rem;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        color: #9ca3af;
    }

    .metric-card {
        border-radius: 16px;
        padding: 12px 16px;
        background: radial-gradient(circle at top, rgba(56,189,248,0.25), rgba(15,23,42,0.95));
        border: 1px solid rgba(59,130,246,0.5);
        box-shadow: 0 14px 35px rgba(15,23,42,0.8);
    }

    /* Sidebar tweak */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #020617 0%, #020617 50%, #111827 100%);
        border-right: 1px solid rgba(55,65,81,0.8);
    }

    /* Titles */
    .app-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #38bdf8, #a855f7, #22c55e);
        -webkit-background-clip: text;
        color: transparent;
        letter-spacing: 0.05em;
    }

    .app-subtitle {
        font-size: 0.95rem;
        color: #9ca3af;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------
# Helper functions
# ---------------------------

def urgency_badge(urgency: str) -> str:
    u = (urgency or "").lower()
    if u == "urgent":
        color = "#ef4444"  # red
    elif u == "low":
        color = "#22c55e"  # green
    else:
        color = "#eab308"  # amber for normal

    return f"""
    <span style="
        background-color:{color};
        color:#020617;
        padding:3px 10px;
        border-radius:999px;
        font-size:0.75rem;
        font-weight:600;
        margin-left:6px;
        ">
        {u.upper() or "UNKNOWN"}
    </span>
    """


def category_badge(category: str) -> str:
    c = (category or "").lower()
    colors = {
        "work": "#3b82f6",
        "school": "#a855f7",
        "personal": "#0ea5e9",
        "promo": "#ec4899",
        "automated": "#64748b",
    }
    color = colors.get(c, "#6b7280")

    return f"""
    <span style="
        background-color:{color};
        color:#020617;
        padding:3px 10px;
        border-radius:999px;
        font-size:0.75rem;
        font-weight:600;
        margin-left:6px;
        ">
        {c or "unknown"}
    </span>
    """


def render_email_card(email: ProcessedEmail):
    with st.expander(f"📧 {email.subject}", expanded=False):
        st.markdown('<div class="email-card">', unsafe_allow_html=True)

        # Priority + Category labels with badges
        st.markdown(
            f"""
            <div style="display:flex; gap:16px; align-items:center; flex-wrap:wrap; margin-bottom:8px;">
                <span class="email-header-text">Priority {urgency_badge(email.urgency)}</span>
                <span class="email-header-text">Category {category_badge(email.category)}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write(f"**From:** `{email.sender}`")

        st.write("---")
        st.write("**Summary:**")
        if email.summary:
            st.write(email.summary)
        else:
            st.write("_No summary available._")

        with st.expander("🔍 Raw email body"):
            st.text(email.body or "(no body)")

        st.write("---")
        st.write("**Tasks detected:**")
        if email.tasks:
            for t in email.tasks:
                st.write(f"- {t}")
        else:
            st.write("_No tasks detected._")

        st.write("---")
        st.write("**AI Suggested Reply Draft:**")
        if email.reply_draft:
            st.code(email.reply_draft, language="text")
        else:
            st.caption("No reply suggested (promo/automated or empty).")

        st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------
# Header
# ---------------------------

st.markdown('<div class="app-title">InboxIntel</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-subtitle">🤖 AI-powered Gmail triage • live summaries • task extraction • reply drafts</div>',
    unsafe_allow_html=True,
)
st.write("")

# ---------------------------
# Sidebar controls
# ---------------------------

st.sidebar.header("⚙️ Control Center")

max_results = st.sidebar.slider(
    "Max unread emails to fetch",
    min_value=1,
    max_value=50,
    value=10,
    step=1,
    help=(
        "Controls how many recent unread Gmail messages are fetched. "
        "Only *new* ones are processed; already-seen emails are skipped using SQLite."
    ),
)

process_button = st.sidebar.button("🚀 Run InboxIntel Now", use_container_width=True)

st.sidebar.markdown("---")

# CLEAR PROCESSED EMAILS BUTTON
st.sidebar.subheader("🗑 Data Maintenance")
confirm_delete = st.sidebar.checkbox("I understand this clears all stored emails/tasks")

if st.sidebar.button("🔥 Clear Processed Emails Database", use_container_width=True):
    if confirm_delete:
        storage.clear_all()
        st.sidebar.success("Database cleared! Future runs will treat everything as new.")
    else:
        st.sidebar.warning("Please confirm the checkbox before deletion.")

st.sidebar.markdown("---")
st.sidebar.caption("Connected to Gmail • All email content stays local to you.")


# ---------------------------
# Main logic
# ---------------------------

source = GmailEmailSource(max_results=max_results)

new_emails: list[ProcessedEmail] = []

if process_button:
    with st.spinner("Fetching and processing unread emails... 🧠⚡"):
        try:
            new_emails = process_emails(source=source, storage=storage)
        except Exception as ex:
            st.error(f"Error while processing emails: {ex}")


# Fetch all stored emails for history view
all_emails = storage.fetch_all_emails()

# ---------------------------
# Top metrics / status
# ---------------------------

total = len(all_emails)
urgent_count = len([e for e in all_emails if (e.urgency or "").lower() == "urgent"])
normal_count = len([e for e in all_emails if (e.urgency or "").lower() == "normal"])
low_count = len([e for e in all_emails if (e.urgency or "").lower() == "low"])

col_a, col_b, col_c, col_d = st.columns(4)
with col_a:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("Total triaged", total)
    st.markdown("</div>", unsafe_allow_html=True)
with col_b:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("Urgent", urgent_count)
    st.markdown("</div>", unsafe_allow_html=True)
with col_c:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("Normal", normal_count)
    st.markdown("</div>", unsafe_allow_html=True)
with col_d:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("Low", low_count)
    st.markdown("</div>", unsafe_allow_html=True)

st.write("")

# ---------------------------
# Tabs: Newly processed vs history
# ---------------------------

tab_new, tab_history = st.tabs(["✨ This Run", "📚 Triaged Archive"])

with tab_new:
    st.subheader("✨ Newly processed emails in this run")

    if process_button:
        if not new_emails:
            st.info("No new unread emails were found or everything was already processed.")
        else:
            st.success(f"Processed {len(new_emails)} new email(s) in this run.")
            for e in new_emails:
                render_email_card(e)
    else:
        st.info("Click **'🚀 Run InboxIntel Now'** in the sidebar to triage new Gmail emails.")


with tab_history:
    st.subheader("📚 All stored triaged emails")

    if not all_emails:
        st.info("No emails in the database yet. Process some emails first.")
    else:
        st.caption(f"Total stored emails: {len(all_emails)}")

        # Filter by urgency/category
        col1, col2 = st.columns(2)
        with col1:
            urgency_filter = st.multiselect(
                "Filter by urgency",
                options=["urgent", "normal", "low"],
                default=["urgent", "normal", "low"],
            )
        with col2:
            category_filter = st.multiselect(
                "Filter by category",
                options=["work", "school", "personal", "promo", "automated"],
                default=["work", "school", "personal", "promo", "automated"],
            )

        # Flexible filtering: if filters empty, show everything
        if not urgency_filter and not category_filter:
            filtered = all_emails
        else:
            def matches(email: ProcessedEmail) -> bool:
                u_ok = (not urgency_filter) or (email.urgency in urgency_filter)
                c_ok = (not category_filter) or (email.category in category_filter)
                return u_ok and c_ok

            filtered = [e for e in all_emails if matches(e)]

        if not filtered:
            st.warning("No emails match the selected filters.")
        else:
            for e in filtered:
                render_email_card(e)

# After all UI + loops at the bottom of the file
storage.close()

