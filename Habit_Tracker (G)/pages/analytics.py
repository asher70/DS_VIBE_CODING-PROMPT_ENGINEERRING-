import streamlit as st
import plotly.express as px

import database as db

st.title("📈 Analytics")
st.write("Deep-dive statistics and trends for your habits.")

habits = db.get_habits()

if not habits:
    st.info("No habits yet. Go to the **Habits** page to add one!", icon="💡")
else:
    habit_options = {h["habit_name"]: h["id"] for h in habits}
    selected_name = st.selectbox("🔍 Select a habit", list(habit_options.keys()))
    selected_id = habit_options[selected_name]

    current_streak = db.get_streak(selected_id)
    longest_streak = db.get_longest_streak(selected_id)
    completed, possible, percentage = db.get_overall_stats(selected_id)

    # Metrics cards
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                label="🔥 Current Streak",
                value=f"{current_streak} days",
            )
        with col2:
            st.metric(
                label="🏆 Longest Streak",
                value=f"{longest_streak} days",
            )
        with col3:
            st.metric(
                label="📊 Completion Rate",
                value=f"{percentage}%",
                delta=f"{completed}/{possible} days",
            )

    st.markdown("##### 📅 Monthly Activity Trend")
    with st.container(border=True):
        monthly = db.get_monthly_stats(selected_id)
        if monthly:
            months = [m["month"] for m in monthly]
            completions = [m["completions"] for m in monthly]

            fig = px.bar(
                x=months,
                y=completions,
                labels={"x": "Month", "y": "Completed Days"},
                title=f"Monthly Completions — {selected_name}",
                color_discrete_sequence=["#4CAF50"],
            )
            fig.update_layout(
                xaxis_tickangle=0,
                bargap=0.3,
                margin=dict(l=20, r=20, t=60, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No completion data yet.")
