import streamlit as st
from groq_client import generate_questions

st.set_page_config(page_title="AI Quiz Generator", page_icon="🧠", layout="centered")

is_dark = (st.context.theme.get("type") or "light") == "dark"

dark_css = """
    .main-title { color: #f3f4f6 !important; }
    .subtitle { color: #9ca3af !important; }
    .card { background-color: #111827 !important; border-color: #374151 !important; }
    .question-text { color: #f9fafb !important; }
    .feedback-correct { background-color: #064e3b !important; color: #d1fae5 !important; border-color: #059669 !important; }
    .feedback-wrong { background-color: #450a0a !important; color: #fecaca !important; border-color: #dc2626 !important; }
    .score-badge { background-color: #374151 !important; color: #f9fafb !important; }
    .review-card { background-color: #1f2937 !important; border-color: #374151 !important; }
    .stat-box { background-color: #1f2937 !important; border-color: #374151 !important; }
    .stat-number { color: #f3f4f6 !important; }
    .stat-label { color: #9ca3af !important; }
    .results-label { color: #9ca3af !important; }
    span[style*="color:#15803d"] { color: #4ade80 !important; }
    span[style*="color:#b91c1c"] { color: #f87171 !important; }
"""

st.markdown(
    f"""
    <style>
    .main-title {{
        text-align: center;
        font-size: 2.8rem;
        font-weight: 800;
        color: #1f2937;
        margin-bottom: 0.2rem;
    }}
    .subtitle {{
        text-align: center;
        font-size: 1.1rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }}
    .card {{
        background-color: #ffffff;
        border-radius: 16px;
        padding: 2rem;
        box-shadow: 0 4px 24px rgba(0,0,0,0.06);
        border: 1px solid #e5e7eb;
        margin-bottom: 1.5rem;
    }}
    .question-number {{
        font-size: 0.85rem;
        font-weight: 600;
        color: #6366f1;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.5rem;
    }}
    .question-text {{
        font-size: 1.25rem;
        font-weight: 600;
        color: #111827;
        margin-bottom: 1.5rem;
        line-height: 1.4;
    }}
    .feedback-box {{
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin-top: 1rem;
        margin-bottom: 1rem;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }}
    .feedback-correct {{
        background-color: #d1fae5;
        color: #065f46;
        border: 1px solid #a7f3d0;
    }}
    .feedback-wrong {{
        background-color: #fee2e2;
        color: #991b1b;
        border: 1px solid #fecaca;
    }}
    .score-badge {{
        display: inline-block;
        background-color: #f3f4f6;
        border-radius: 8px;
        padding: 0.4rem 0.9rem;
        font-weight: 700;
        color: #374151;
        font-size: 0.95rem;
    }}
    .btn-primary {{
        background-color: #6366f1;
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.6rem 1.4rem;
        font-weight: 600;
        cursor: pointer;
    }}
    .review-card {{
        background-color: #ffffff;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.04);
        border: 1px solid #e5e7eb;
        margin-bottom: 1rem;
    }}
    .review-correct {{
        border-left: 4px solid #22c55e;
    }}
    .review-wrong {{
        border-left: 4px solid #ef4444;
    }}
    .hero-icon {{
        font-size: 3rem;
        text-align: center;
        margin-bottom: 0.5rem;
    }}
    .results-score {{
        text-align: center;
        font-size: 3.5rem;
        font-weight: 800;
        color: #6366f1;
        margin: 0.5rem 0;
    }}
    .results-label {{
        text-align: center;
        color: #6b7280;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }}
    .stat-box {{
        background-color: #f9fafb;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        border: 1px solid #e5e7eb;
    }}
    .stat-number {{
        font-size: 1.5rem;
        font-weight: 700;
        color: #1f2937;
    }}
    .stat-label {{
        font-size: 0.8rem;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    {dark_css if is_dark else ""}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="hero-icon">🧠</div>', unsafe_allow_html=True)
st.markdown('<div class="main-title">AI Quiz Generator</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Enter any topic and test your knowledge with AI-generated questions</div>', unsafe_allow_html=True)

quiz_topic = st.text_input("Enter Quiz Topic", placeholder="e.g. Space, History, Python Programming")

col_gen = st.columns([1, 3, 1])[1]
with col_gen:
    generate_clicked = st.button("🚀 Generate Quiz", use_container_width=True)

if generate_clicked:
    if quiz_topic.strip():
        with st.spinner("Generating your quiz..."):
            try:
                questions = generate_questions(quiz_topic.strip())
                st.session_state["questions"] = questions
                st.session_state["current_question"] = 0
                st.session_state["score"] = 0
                st.session_state["submitted"] = False
                st.session_state["result"] = None
            except Exception as e:
                st.error(f"Failed to generate quiz: {e}")
    else:
        st.warning("Please enter a quiz topic.")

if "questions" in st.session_state:
    total = len(st.session_state["questions"])
    idx = st.session_state["current_question"]

    if idx < total:
        progress = (idx + (1 if st.session_state.get("submitted") else 0)) / total
        st.progress(progress, text=f"Progress {int(progress * 100)}%")

        q = st.session_state["questions"][idx]

        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f'<div class="question-number">Question {idx + 1} of {total}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="question-text">{q["question"]}</div>', unsafe_allow_html=True)

            if not st.session_state.get("submitted"):
                selected = st.radio("Select your answer:", q["options"], key=f"answer_{idx}", label_visibility="collapsed")

                col_btn = st.columns([1, 3, 1])[1]
                with col_btn:
                    if st.button("Submit Answer", key=f"submit_{idx}", use_container_width=True, type="primary"):
                        st.session_state[f"selected_{idx}"] = selected
                        correct = q["answer"]
                        if selected == correct:
                            st.session_state["score"] += 1
                            st.session_state["result"] = "Correct"
                        else:
                            st.session_state["result"] = "Wrong"
                        st.session_state["submitted"] = True
                        st.rerun()
            else:
                selected = st.session_state.get(f"selected_{idx}")
                user_opt = q["options"].index(selected) if selected in q["options"] else -1
                correct_opt = q["options"].index(q["answer"]) if q["answer"] in q["options"] else -1

                for i, opt in enumerate(q["options"]):
                    if opt == selected and opt == q["answer"]:
                        st.markdown(f"✅ **{opt}**  —  Your answer (Correct)")
                    elif opt == selected and opt != q["answer"]:
                        st.markdown(f"❌ **{opt}**  —  Your answer")
                    elif opt == q["answer"] and opt != selected:
                        st.markdown(f"✅ **{opt}**  —  Correct answer")
                    else:
                        st.markdown(f"{opt}")

                if st.session_state["result"] == "Correct":
                    st.markdown('<div class="feedback-box feedback-correct">🎉 Correct! Well done.</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="feedback-box feedback-wrong">😕 That\'s not quite right.</div>', unsafe_allow_html=True)

                st.markdown(f'<div class="score-badge">🏆 Score: {st.session_state["score"]} / {total}</div>', unsafe_allow_html=True)

                st.markdown("</div>", unsafe_allow_html=True)

                if idx < total - 1:
                    col_next = st.columns([1, 3, 1])[1]
                    with col_next:
                        if st.button("Next Question →", key=f"next_{idx}", use_container_width=True, type="primary"):
                            st.session_state["current_question"] += 1
                            st.session_state["submitted"] = False
                            st.session_state["result"] = None
                            st.rerun()
                else:
                    col_result = st.columns([1, 3, 1])[1]
                    with col_result:
                        if st.button("📊 Show Results", key=f"results_{idx}", use_container_width=True, type="primary"):
                            st.session_state["current_question"] += 1
                            st.session_state["submitted"] = False
                            st.session_state["result"] = None
                            st.rerun()

    else:
        score = st.session_state["score"]
        correct_count = score
        wrong_count = total - score
        percentage = round((correct_count / total) * 100, 2) if total else 0

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="hero-icon">🏁</div>', unsafe_allow_html=True)
        st.markdown('<div class="main-title" style="font-size:2rem;">Quiz Complete!</div>', unsafe_allow_html=True)

        st.markdown(f'<div class="results-score">{percentage}%</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="results-label">You scored {score} out of {total}</div>', unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(
                '<div class="stat-box"><div class="stat-number">{}</div><div class="stat-label">Correct</div></div>'.format(correct_count),
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                '<div class="stat-box"><div class="stat-number">{}</div><div class="stat-label">Wrong</div></div>'.format(wrong_count),
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                '<div class="stat-box"><div class="stat-number">{}</div><div class="stat-label">Total</div></div>'.format(total),
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("## 📋 Review Your Answers")

        for i, q in enumerate(st.session_state["questions"]):
            selected = st.session_state.get(f"selected_{i}")
            is_correct = selected == q["answer"]
            card_class = "review-correct" if is_correct else "review-wrong"

            st.markdown(f'<div class="review-card {card_class}">', unsafe_allow_html=True)
            st.markdown(f"**Q{i + 1}.** {q['question']}")

            if is_correct:
                st.markdown(f"<span style='color:#15803d'>✅ Your Answer: {selected} — Correct</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span style='color:#b91c1c'>❌ Your Answer: {selected}</span>", unsafe_allow_html=True)
                st.markdown(f"<span style='color:#15803d'>✅ Correct Answer: {q['answer']}</span>", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

        col_restart = st.columns([1, 3, 1])[1]
        with col_restart:
            if st.button("🔄 Start New Quiz", use_container_width=True, type="primary"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
