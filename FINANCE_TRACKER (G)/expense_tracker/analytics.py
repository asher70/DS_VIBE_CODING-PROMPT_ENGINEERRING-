import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("TkAgg")  # Ensure Tkinter backend is used
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from datetime import datetime

# Curated premium color palettes for charts
LIGHT_PALETTE = ["#3f51b5", "#00bcd4", "#4caf50", "#ffeb3b", "#ff9800", "#e91e63", "#9c27b0", "#795548", "#607d8b", "#9e9e9e"]
DARK_PALETTE = ["#5c6bc0", "#26c6da", "#66bb6a", "#ffee58", "#ffa726", "#ec407a", "#ab47bc", "#8d6e63", "#78909c", "#bdbdbd"]

def get_summary_stats(transactions):
    """
    Computes summary metrics from a list of transactions using Pandas.
    Returns:
      dict: {total_income, total_expense, net_savings, savings_rate}
    """
    if not transactions:
        return {
            "total_income": 0.0,
            "total_expense": 0.0,
            "net_savings": 0.0,
            "savings_rate": 0.0
        }
        
    df = pd.DataFrame(transactions)
    
    # Calculate totals
    income_mask = df["transaction_type"] == "Income"
    expense_mask = df["transaction_type"] == "Expense"
    
    total_income = df.loc[income_mask, "amount"].sum()
    total_expense = df.loc[expense_mask, "amount"].sum()
    
    net_savings = total_income - total_expense
    savings_rate = (net_savings / total_income * 100) if total_income > 0 else 0.0
    # Prevent negative infinite savings rate visualization
    if total_income == 0 and total_expense > 0:
        savings_rate = -100.0
        
    return {
        "total_income": float(total_income),
        "total_expense": float(total_expense),
        "net_savings": float(net_savings),
        "savings_rate": float(savings_rate)
    }

def get_category_breakdown(transactions):
    """
    Returns expense totals grouped by category.
    """
    if not transactions:
        return pd.DataFrame(columns=["category", "amount", "percentage"])
        
    df = pd.DataFrame(transactions)
    expense_df = df[df["transaction_type"] == "Expense"]
    
    if expense_df.empty:
        return pd.DataFrame(columns=["category", "amount", "percentage"])
        
    category_totals = expense_df.groupby("category")["amount"].sum().reset_index()
    total_expense = category_totals["amount"].sum()
    
    category_totals["percentage"] = (category_totals["amount"] / total_expense * 100).round(1)
    category_totals = category_totals.sort_values(by="amount", ascending=False).reset_index(drop=True)
    
    return category_totals

def get_monthly_trends(transactions, limit=6):
    """
    Groups income and expenses by month (YYYY-MM).
    Returns a DataFrame with columns: month, Income, Expense.
    """
    if not transactions:
        return pd.DataFrame(columns=["month", "Income", "Expense"])

    df = pd.DataFrame(transactions)
    df["month"] = df["date"].apply(
        lambda d: d[:7] if isinstance(d, str) and len(d) >= 7
        else datetime.now().strftime("%Y-%m")
    )

    income_by_month = (
        df[df["transaction_type"] == "Income"]
        .groupby("month")["amount"].sum()
    )
    expense_by_month = (
        df[df["transaction_type"] == "Expense"]
        .groupby("month")["amount"].sum()
    )

    all_months = sorted(df["month"].unique())
    result = pd.DataFrame({
        "month":   all_months,
        "Income":  [float(income_by_month.get(m, 0.0)) for m in all_months],
        "Expense": [float(expense_by_month.get(m, 0.0)) for m in all_months],
    })
    return result.tail(limit).reset_index(drop=True)

def apply_matplotlib_theme(fig, ax, bg_color, fg_color, grid_color):
    """Applies a custom dark/light theme style to a matplotlib figure."""
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)
    
    # Set text colors
    ax.title.set_color(fg_color)
    ax.xaxis.label.set_color(fg_color)
    ax.yaxis.label.set_color(fg_color)
    
    # Set axis lines and ticks colors
    ax.spines['bottom'].set_color(grid_color)
    ax.spines['top'].set_color(grid_color)
    ax.spines['left'].set_color(grid_color)
    ax.spines['right'].set_color(grid_color)
    ax.tick_params(colors=fg_color, which='both')
    
    # Setup grid
    ax.grid(True, linestyle="--", alpha=0.3, color=grid_color)

def generate_category_donut_chart(transactions, bg_color="#ffffff", fg_color="#212529", grid_color="#dee2e6", is_dark=False):
    """
    Generates a premium Matplotlib donut (pie) chart of expenses.
    Returns:
      Figure: Matplotlib figure object.
    """
    fig = Figure(figsize=(5, 4.2), dpi=100)
    ax = fig.add_subplot(111)
    
    # Base styling
    apply_matplotlib_theme(fig, ax, bg_color, fg_color, grid_color)
    
    category_df = get_category_breakdown(transactions)
    palette = DARK_PALETTE if is_dark else LIGHT_PALETTE
    
    if category_df.empty:
        # Show empty placeholder chart
        ax.text(0.5, 0.5, "No Expense Data Available\nAdd some expenses first!", 
                ha='center', va='center', fontsize=12, color=fg_color)
        ax.axis('off')
        return fig
        
    labels = category_df["category"].tolist()
    sizes = category_df["amount"].tolist()
    
    # Create donut chart
    wedges, texts, autotexts = ax.pie(
        sizes, 
        labels=labels, 
        autopct='%1.1f%%',
        startangle=140, 
        pctdistance=0.75,
        colors=palette[:len(labels)],
        wedgeprops=dict(width=0.4, edgecolor=bg_color, linewidth=2)  # width creates the donut hole
    )
    
    # Style text inside slices
    for text in texts:
        text.set_color(fg_color)
        text.set_fontsize(9)
        
    for autotext in autotexts:
        autotext.set_color('#ffffff')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(9)
        
    ax.set_title("Expenses by Category", fontsize=14, fontweight='bold', pad=15)
    
    # Equal aspect ratio ensures pie is circular
    ax.axis('equal')  
    fig.tight_layout()
    return fig

def generate_monthly_trend_chart(transactions, bg_color="#ffffff", fg_color="#212529", grid_color="#dee2e6", is_dark=False):
    """
    Generates a grouped bar chart comparing Income and Expenses.
    Returns:
      Figure: Matplotlib figure object.
    """
    fig = Figure(figsize=(6, 4.2), dpi=100)
    ax = fig.add_subplot(111)
    
    # Base styling
    apply_matplotlib_theme(fig, ax, bg_color, fg_color, grid_color)
    
    trends = get_monthly_trends(transactions, limit=6)
    
    if trends.empty:
        ax.text(0.5, 0.5, "No Historical Data Available\nSeed/add transactions first!", 
                ha='center', va='center', fontsize=12, color=fg_color)
        ax.axis('off')
        return fig
        
    months = trends["month"].tolist()
    # Format month strings to be readable, e.g. "2026-05" -> "May '26"
    readable_months = []
    for m in months:
        try:
            dt = datetime.strptime(m, "%Y-%m")
            readable_months.append(dt.strftime("%b '%y"))
        except ValueError:
            readable_months.append(m)
            
    income = trends["Income"].tolist()
    expense = trends["Expense"].tolist()
    
    x = np.arange(len(readable_months))
    width = 0.35
    
    # Neon blue for Income, Neon Red for Expense in dark mode; deep corporate colors for light mode
    income_color = "#2ecc71" if is_dark else "#27ae60"  # Greenish
    expense_color = "#e74c3c" if is_dark else "#c0392b"  # Reddish
    
    rects1 = ax.bar(x - width/2, income, width, label='Income', color=income_color)
    rects2 = ax.bar(x + width/2, expense, width, label='Expense', color=expense_color)
    
    ax.set_title("Income vs Expense Trend", fontsize=14, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(readable_months)
    
    # Legend custom styling
    legend = ax.legend(facecolor=bg_color, edgecolor=grid_color)
    for text in legend.get_texts():
        text.set_color(fg_color)
        
    # Labeling
    ax.set_ylabel("Amount ($)", fontsize=10)
    
    fig.tight_layout()
    return fig
