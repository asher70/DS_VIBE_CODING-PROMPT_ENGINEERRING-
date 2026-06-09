"""Analytics functions for expense tracker.

Provides summary metrics and Plotly visualisations.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.database import get_transactions


def _to_dataframe(**filters) -> pd.DataFrame:
    """Fetch transactions as a pandas DataFrame, optionally filtered."""
    records = get_transactions(**filters)
    if not records:
        return pd.DataFrame(
            columns=["id", "type", "amount", "category", "description", "date", "created_at"]
        )
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = df["amount"].astype(float)
    return df


# ── Summary Metrics ──

def total_income(**filters) -> float:
    """Sum of all income transactions."""
    df = _to_dataframe(**filters)
    if df.empty:
        return 0.0
    return df.loc[df["type"] == "income", "amount"].sum()


def total_expenses(**filters) -> float:
    """Sum of all expense transactions."""
    df = _to_dataframe(**filters)
    if df.empty:
        return 0.0
    return df.loc[df["type"] == "expense", "amount"].sum()


def balance(**filters) -> float:
    """Net balance: income minus expenses."""
    return total_income(**filters) - total_expenses(**filters)


# ── Plotly Charts ──

def pie_chart(**filters) -> go.Figure | None:
    """Pie chart comparing total income vs total expenses."""
    inc = total_income(**filters)
    exp = total_expenses(**filters)
    if inc == 0 and exp == 0:
        return None
    fig = go.Figure(
        data=[
            go.Pie(
                labels=["Income", "Expenses"],
                values=[inc, exp],
                hole=0.35,
                marker_colors=["#2ecc71", "#e74c3c"],
            )
        ]
    )
    fig.update_layout(title_text="Income vs Expenses", showlegend=True)
    return fig


def monthly_graph(**filters) -> go.Figure | None:
    """Bar chart of income and expenses grouped by month."""
    df = _to_dataframe(**filters)
    if df.empty:
        return None
    df["month"] = df["date"].dt.strftime("%Y-%m")
    monthly = (
        df.groupby(["month", "type"])["amount"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )
    if "income" not in monthly.columns:
        monthly["income"] = 0.0
    if "expense" not in monthly.columns:
        monthly["expense"] = 0.0

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=monthly["month"],
            y=monthly["income"],
            name="Income",
            marker_color="#2ecc71",
        )
    )
    fig.add_trace(
        go.Bar(
            x=monthly["month"],
            y=monthly["expense"],
            name="Expenses",
            marker_color="#e74c3c",
        )
    )
    fig.update_layout(
        title="Monthly Income vs Expenses",
        xaxis_title="Month",
        yaxis_title="Amount",
        barmode="group",
        template="plotly_white",
    )
    return fig


def category_graph(**filters) -> go.Figure | None:
    """Bar chart of expenses grouped by category."""
    df = _to_dataframe(**filters)
    if df.empty:
        return None
    cat = df[df["type"] == "expense"].groupby("category")["amount"].sum().reset_index()
    if cat.empty:
        return None
    cat = cat.sort_values("amount", ascending=True)
    fig = px.bar(
        cat,
        x="amount",
        y="category",
        orientation="h",
        color="amount",
        color_continuous_scale="Reds",
        title="Expenses by Category",
        labels={"amount": "Amount", "category": "Category"},
        template="plotly_white",
    )
    fig.update_layout(coloraxis_showscale=False)
    return fig
