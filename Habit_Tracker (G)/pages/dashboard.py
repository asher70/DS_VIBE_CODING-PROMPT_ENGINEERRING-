import calendar
from datetime import date

import streamlit as st

import database as db

st.title("📅 Dashboard")
st.write("Calendar view of habit completions for the current month.")

habits = db.get_habits()

if not habits:
    st.info("No habits yet. Go to the **Habits** page to add one!")
else:
    habit_options = {h["habit_name"]: h["id"] for h in habits}
    selected_name = st.selectbox("🔍 Select a habit", list(habit_options.keys()))
    selected_id = habit_options[selected_name]

    completed_dates = set(db.get_habit_dates(selected_id))

    today = date.today()
    year, month = today.year, today.month
    month_name = calendar.month_name[month]
    month_calendar = calendar.Calendar().monthdayscalendar(year, month)

    with st.container(border=True):
        st.markdown(f"#### {selected_name}")
        st.caption("🟢  Completed  ·  ⚪  Incomplete")

        # Calendar styling — theme-aware for light & dark mode
        st.markdown(
            """
            <style>
            .cal-container {
                max-width: 480px;
                margin: 0 auto;
            }
            .cal-title {
                text-align: center;
                font-size: 1.4rem;
                font-weight: 600;
                margin-bottom: 1rem;
            }
            .cal-grid {
                display: grid;
                grid-template-columns: repeat(7, 1fr);
                gap: 8px;
                text-align: center;
            }
            .cal-day-header {
                font-weight: 700;
                padding: 8px 0;
                background-color: rgba(128,128,128,0.12);
                border-radius: 8px;
                font-size: 0.85rem;
                letter-spacing: 0.5px;
            }
            .cal-day {
                padding: 12px 0;
                border-radius: 8px;
                font-size: 1rem;
                min-height: 44px;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: transform 0.1s ease;
            }
            .cal-empty {
                background: transparent;
            }
            .cal-completed {
                background-color: #4CAF50;
                color: #fff;
                font-weight: 700;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }
            .cal-incomplete {
                background: rgba(128,128,128,0.06);
                color: inherit;
                font-weight: 400;
            }
            .cal-today {
                border: 2px solid rgba(128,128,128,0.4);
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        html = f'<div class="cal-container">'
        html += f'<div class="cal-title">{month_name} {year}</div>'
        html += '<div class="cal-grid">'

        for wd in ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]:
            html += f'<div class="cal-day-header">{wd}</div>'

        for week in month_calendar:
            for day in week:
                if day == 0:
                    html += '<div class="cal-day cal-empty"></div>'
                else:
                    day_iso = date(year, month, day).isoformat()
                    cls = "cal-day cal-completed" if day_iso in completed_dates else "cal-day cal-incomplete"
                    if day_iso == today.isoformat():
                        cls += " cal-today"
                    html += f'<div class="{cls}">{day}</div>'

        html += "</div></div>"
        st.markdown(html, unsafe_allow_html=True)
