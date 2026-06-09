import streamlit as st
from datetime import datetime

from utils.database import (
    create_table,
    insert_transaction,
    get_transactions,
    delete_transaction,
    update_transaction,
    get_categories,
    get_months,
    get_transaction_by_id,
)
from utils.analytics import total_income, total_expenses, balance, pie_chart, monthly_graph, category_graph
from utils.export import to_csv_bytes, to_excel_bytes

st.set_page_config(page_title="Expense Tracker", layout="wide")
st.title("💰 Expense Tracker")

# ── Session State ──
if "edit_id" not in st.session_state:
    st.session_state.edit_id = None

# Ensure table exists
create_table()

# ═══════════════════════════════════════════
#  FILTERS
# ═══════════════════════════════════════════
st.header("🔍 Filters")

categories = get_categories()
available_months = get_months()

c1, c2, c3 = st.columns(3)
with c1:
    filter_type = st.selectbox("Transaction Type", options=["All", "income", "expense"], index=0)
with c2:
    filter_category = st.selectbox("Category", options=["All"] + categories, index=0)
with c3:
    filter_month = st.selectbox("Month", options=["All"] + available_months, index=0)

c4, c5 = st.columns(2)
with c4:
    filter_start = st.date_input("Start Date", value=None)
with c5:
    filter_end = st.date_input("End Date", value=None)

filter_description = st.text_input("Search description", placeholder="Type to search descriptions...")

filters = {}
if filter_type != "All":
    filters["transaction_type"] = filter_type
if filter_category != "All":
    filters["category"] = filter_category
if filter_month != "All":
    filters["month"] = filter_month
if filter_start is not None:
    filters["start_date"] = filter_start.strftime("%Y-%m-%d")
if filter_end is not None:
    filters["end_date"] = filter_end.strftime("%Y-%m-%d")
if filter_description.strip():
    filters["description_search"] = filter_description.strip()

records = get_transactions(**filters)

# ═══════════════════════════════════════════
#  DASHBOARD — Dynamic Analytics
# ═══════════════════════════════════════════
st.header("📊 Dashboard")

inc = total_income(**filters)
exp = total_expenses(**filters)
bal = balance(**filters)

m1, m2, m3 = st.columns(3)
m1.metric("Total Income", f"${inc:,.2f}", delta=None)
m2.metric("Total Expenses", f"${exp:,.2f}", delta=None)
m3.metric("Net Balance", f"${bal:,.2f}", delta=f"{((inc - exp) / exp * 100):.1f}%" if exp > 0 else "0%")

st.divider()

if records:
    c1, c2 = st.columns(2)

    pfig = pie_chart(**filters)
    if pfig:
        c1.plotly_chart(pfig, use_container_width=True)
    else:
        c1.info("No income or expense data to display pie chart.")

    cfig = category_graph(**filters)
    if cfig:
        c2.plotly_chart(cfig, use_container_width=True)
    else:
        c2.info("No expense data to display category chart.")

    mfig = monthly_graph(**filters)
    if mfig:
        st.plotly_chart(mfig, use_container_width=True)
    else:
        st.info("No monthly data to display bar chart.")
else:
    st.info("No transactions match the current filters. Adjust filters to see analytics.")

st.divider()

# ── Add Transaction Form ──
st.header("Add Transaction")
with st.form("transaction_form"):
    col1, col2 = st.columns(2)

    with col1:
        transaction_type = st.selectbox(
            "Transaction Type",
            options=["income", "expense"],
            index=1,
        )
        amount = st.number_input(
            "Amount",
            min_value=0.0,
            format="%.2f",
            step=0.01,
        )

    with col2:
        category = st.text_input("Category", placeholder="e.g. Food, Rent, Salary")
        date = st.date_input("Date", value=datetime.now())

    description = st.text_area("Description", placeholder="Optional details...")
    submitted = st.form_submit_button("Submit", type="primary")

    if submitted:
        if amount <= 0:
            st.error("Amount must be greater than 0.")
        elif not category.strip():
            st.error("Category is required.")
        else:
            tid = insert_transaction(
                type=transaction_type,
                amount=amount,
                category=category.strip(),
                description=description.strip() if description else None,
                date=date.strftime("%Y-%m-%d"),
            )
            st.success(f"Transaction saved with ID: {tid}")
            st.rerun()

st.divider()

# ── Edit Transaction Form ──
if st.session_state.edit_id is not None:
    tx = get_transaction_by_id(st.session_state.edit_id)
    if tx:
        st.header(f"✏️ Edit Transaction #{tx['id']}")
        with st.form("edit_form"):
            col1, col2 = st.columns(2)
            with col1:
                edit_type = st.selectbox(
                    "Type",
                    options=["income", "expense"],
                    index=0 if tx["type"] == "income" else 1,
                    key="edit_type",
                )
                edit_amount = st.number_input(
                    "Amount",
                    min_value=0.0,
                    format="%.2f",
                    step=0.01,
                    value=float(tx["amount"]),
                    key="edit_amount",
                )
            with col2:
                edit_category = st.text_input(
                    "Category",
                    value=tx["category"],
                    key="edit_category",
                )
                edit_date = st.date_input(
                    "Date",
                    value=datetime.strptime(tx["date"], "%Y-%m-%d").date(),
                    key="edit_date",
                )
            edit_description = st.text_area(
                "Description",
                value=tx["description"] or "",
                key="edit_description",
            )

            c1, c2 = st.columns(2)
            update_submitted = c1.form_submit_button("Update", type="primary")
            cancel = c2.form_submit_button("Cancel")

            if update_submitted:
                if edit_amount <= 0:
                    st.error("Amount must be greater than 0.")
                elif not edit_category.strip():
                    st.error("Category is required.")
                else:
                    update_transaction(
                        transaction_id=tx["id"],
                        type=edit_type,
                        amount=edit_amount,
                        category=edit_category.strip(),
                        description=edit_description.strip() or None,
                        date=edit_date.strftime("%Y-%m-%d"),
                    )
                    st.session_state.edit_id = None
                    st.success("Transaction updated!")
                    st.rerun()
            if cancel:
                st.session_state.edit_id = None
                st.rerun()
    else:
        st.session_state.edit_id = None

    st.divider()

# ── Transactions Table ──
st.header("Transactions")

if records:
    dl1, dl2 = st.columns(2)
    dl1.download_button(
        label="📥 Download CSV",
        data=to_csv_bytes(records),
        file_name="transactions.csv",
        mime="text/csv",
    )
    dl2.download_button(
        label="📥 Download Excel",
        data=to_excel_bytes(records),
        file_name="transactions.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

if not records:
    st.info("No transactions found matching the current filters.")
else:
    # Table header
    header = st.columns([0.8, 1.2, 1.5, 2, 2.5, 1.5, 1, 1])
    header[0].markdown("**ID**")
    header[1].markdown("**Type**")
    header[2].markdown("**Amount**")
    header[3].markdown("**Category**")
    header[4].markdown("**Description**")
    header[5].markdown("**Date**")
    header[6].markdown("**Edit**")
    header[7].markdown("**Delete**")
    st.divider()

    for tx in records:
        cols = st.columns([0.8, 1.2, 1.5, 2, 2.5, 1.5, 1, 1])
        cols[0].write(tx["id"])
        cols[1].write(tx["type"])
        cols[2].write(f"{tx['amount']:,.2f}")
        cols[3].write(tx["category"])
        cols[4].write(tx["description"] or "—")
        cols[5].write(tx["date"])

        if cols[6].button("✏️", key=f"edit_{tx['id']}"):
            st.session_state.edit_id = tx["id"]
            st.rerun()
        if cols[7].button("🗑️", key=f"del_{tx['id']}"):
            delete_transaction(tx["id"])
            st.success(f"Deleted #{tx['id']}")
            st.rerun()
