import calendar
from datetime import date

import streamlit as st

import database as db

st.title("✅ Habits")
st.write("Track, manage, and build your daily habits.")

with st.container(border=True):
    with st.form("add_habit_form", clear_on_submit=True):
        st.markdown("##### ➕ Add New Habit")
        cols = st.columns([4, 1])
        with cols[0]:
            habit_name = st.text_input("Habit name", placeholder="e.g. Morning run", label_visibility="collapsed")
        with cols[1]:
            submitted = st.form_submit_button("Add", use_container_width=True)

        if submitted:
            if habit_name.strip():
                db.create_habit(habit_name.strip())
                st.success(f"Added **{habit_name.strip()}**!")
                st.rerun()
            else:
                st.warning("Please enter a habit name.")

st.divider()
st.markdown("##### 📋 Your Habits")

habits = db.get_habits()

if not habits:
    st.info("No habits yet. Add one above!", icon="💡")
else:
    total_days = calendar.monthrange(date.today().year, date.today().month)[1]

    for habit in habits:
        with st.container(border=True):
            name_col, streak_col, action_col, delete_col = st.columns([3, 2, 2, 1])

            with name_col:
                st.markdown(f"**{habit['habit_name']}**")

            with streak_col:
                streak = db.get_streak(habit["id"])
                st.markdown(f"🔥 **{streak}** streak")

            with action_col:
                done_today = db.is_habit_done_today(habit["id"])
                if done_today:
                    st.button("✓ Done", key=f"done_{habit['id']}", disabled=True, use_container_width=True)
                else:
                    if st.button("Done Today", key=f"done_{habit['id']}", use_container_width=True):
                        db.log_habit(habit["id"])
                        st.success("Logged for today!")
                        st.rerun()

            with delete_col:
                if st.button("🗑️", key=f"delete_{habit['id']}", help="Delete habit"):
                    db.delete_habit(habit["id"])
                    st.success(f"Deleted **{habit['habit_name']}**")
                    st.rerun()

            completed = db.get_monthly_completions(habit["id"])
            progress = completed / total_days if total_days else 0
            pct = progress * 100
            st.progress(progress, text=f"{pct:.1f}% — {completed}/{total_days} days this month")
            st.caption(f"Created on {habit['created_date']}")
            st.write("")
