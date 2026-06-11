import streamlit as st
import database as db

# Initialize database
db.init_db()

# Set page configuration
st.set_page_config(
    page_title="Habit Tracker",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Global responsive styling for dark & light mode
st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] {
        padding-top: 1rem;
    }
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Define pages
pages = {
    "Dashboard": [st.Page("pages/dashboard.py", title="Dashboard", icon="📊")],
    "Habits": [st.Page("pages/habits.py", title="Habits", icon="✅")],
    "Analytics": [st.Page("pages/analytics.py", title="Analytics", icon="📈")],
}

# Set up navigation with sidebar
pg = st.navigation(pages, position="sidebar")

# Add a title in the sidebar
with st.sidebar:
    st.title("📋 Habit Tracker")
    st.caption("Build better habits, one day at a time.")
    st.divider()

# Run the selected page
pg.run()
