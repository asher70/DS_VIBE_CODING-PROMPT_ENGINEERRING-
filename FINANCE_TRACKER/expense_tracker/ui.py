import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime, timedelta

import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry

from expense_tracker.database import DEFAULT_CATEGORIES
from expense_tracker.nlp_parser import parse_nlp_input
from expense_tracker.analytics import (
    get_summary_stats,
    get_category_breakdown,
    generate_category_donut_chart,
    generate_monthly_trend_chart,
)
from expense_tracker.export import export_to_excel, export_to_pdf, import_from_csv
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ─── DATE UTILITIES ────────────────────────────────────────────────────────────
_DATE_FORMATS = [
    "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y",
    "%m/%d/%y", "%d-%m-%Y", "%Y/%m/%d",
]

def _parse_date(raw: str) -> str:
    raw = (raw or "").strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return datetime.now().strftime("%Y-%m-%d")

def _get_date(widget) -> str:
    for getter in [lambda w: w.entry.get(), lambda w: w.get()]:
        try:
            val = getter(widget).strip()
            if val:
                return val
        except Exception:
            continue
    return ""

def _set_date(widget, date_str: str):
    for setter in [
        lambda w, d: (w.entry.delete(0, "end"), w.entry.insert(0, d)),
        lambda w, d: (w.delete(0, "end"), w.insert(0, d)),
    ]:
        try:
            setter(widget, date_str)
            return
        except Exception:
            continue


# ─── TRANSACTION DIALOG ────────────────────────────────────────────────────────
class TransactionDialog(tb.Toplevel):
    def __init__(self, parent, title="Add Transaction", transaction=None):
        super().__init__(parent)
        self.title(title)
        self.trans_data = transaction
        self.result = None
        self.geometry("480x650")
        self.resizable(False, True)
        self.minsize(480, 560)
        self.grab_set()
        self._build_ui()
        if self.trans_data:
            self._load_data()
        # Focus first entry
        self.after(100, lambda: self.ent_title.focus_set())

    def _build_ui(self):
        # Gradient-style header band
        hdr_band = tb.Frame(self, bootstyle="primary", padding=(20, 12))
        hdr_band.pack(fill=X)
        tb.Label(hdr_band, text=self.title(),
                 font=("Segoe UI", 14, "bold"),
                 bootstyle="inverse-primary").pack(anchor=W)
        tb.Label(hdr_band, text="Fill in all required (*) fields and click Save.",
                 font=("Segoe UI", 9),
                 bootstyle="inverse-primary").pack(anchor=W)

        body = tb.Frame(self, padding=(20, 16))
        body.pack(fill=BOTH, expand=YES)

        # Title
        tb.Label(body, text="Title *", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky=W, pady=(0, 2))
        self.ent_title = tb.Entry(body, font=("Segoe UI", 10))
        self.ent_title.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        # Amount
        tb.Label(body, text="Amount ($) *", font=("Segoe UI", 10, "bold")).grid(
            row=2, column=0, columnspan=2, sticky=W, pady=(0, 2))
        self.ent_amount = tb.Entry(body, font=("Segoe UI", 10))
        self.ent_amount.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        # Type + Date side by side
        tb.Label(body, text="Type *", font=("Segoe UI", 10, "bold")).grid(
            row=4, column=0, sticky=W, pady=(0, 2), padx=(0, 8))
        tb.Label(body, text="Date *", font=("Segoe UI", 10, "bold")).grid(
            row=4, column=1, sticky=W, pady=(0, 2))

        self.cb_type = tb.Combobox(body, values=["Expense", "Income"],
                                   state="readonly", font=("Segoe UI", 10))
        self.cb_type.set("Expense")
        self.cb_type.grid(row=5, column=0, sticky="ew", padx=(0, 8), pady=(0, 10))

        self.ent_date = DateEntry(body, dateformat="%Y-%m-%d")
        self.ent_date.grid(row=5, column=1, sticky="ew", pady=(0, 10))

        # Category
        tb.Label(body, text="Category *", font=("Segoe UI", 10, "bold")).grid(
            row=6, column=0, columnspan=2, sticky=W, pady=(0, 2))
        self.cb_category = tb.Combobox(body, values=DEFAULT_CATEGORIES,
                                       state="readonly", font=("Segoe UI", 10))
        self.cb_category.set("Food & Dining")
        self.cb_category.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        # Notes
        tb.Label(body, text="Notes (optional)", font=("Segoe UI", 10, "bold")).grid(
            row=8, column=0, columnspan=2, sticky=W, pady=(0, 2))
        note_frame = tb.Frame(body)
        note_frame.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        self.txt_notes = tk.Text(note_frame, height=2, font=("Segoe UI", 9),
                                 relief="flat", bd=1, highlightthickness=1,
                                 highlightcolor="#0d6efd")
        self.txt_notes.pack(fill=X)

        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        # Buttons — always pinned to bottom
        sep = ttk.Separator(self)
        sep.pack(fill=X, side=BOTTOM)
        btn_row = tb.Frame(self, padding=(20, 12))
        btn_row.pack(fill=X, side=BOTTOM)
        tb.Button(btn_row, text="💾   Save Transaction", bootstyle="success",
                  command=self.on_save).pack(side=RIGHT, padx=(8, 0), ipadx=10, ipady=4)
        tb.Button(btn_row, text="Cancel", bootstyle="outline-secondary",
                  command=self.destroy).pack(side=RIGHT, ipadx=6, ipady=4)

        # Keyboard shortcut
        self.bind("<Return>", lambda e: self.on_save())
        self.bind("<Escape>", lambda e: self.destroy())

    def _load_data(self):
        d = self.trans_data
        self.ent_title.insert(0, d.get("title", ""))
        self.ent_amount.insert(0, str(d.get("amount", "")))
        self.cb_type.set(d.get("transaction_type", "Expense"))
        self.cb_category.set(d.get("category", "Food & Dining"))
        if d.get("notes"):
            self.txt_notes.insert("1.0", d["notes"])
        if d.get("date"):
            _set_date(self.ent_date, _parse_date(d["date"]))

    def on_save(self):
        title = self.ent_title.get().strip()
        amount_str = self.ent_amount.get().strip()
        tx_type = self.cb_type.get()
        category = self.cb_category.get()
        notes = self.txt_notes.get("1.0", "end").strip()
        date_str = _parse_date(_get_date(self.ent_date))

        if not title:
            messagebox.showerror("Required Field", "Please enter a title.", parent=self)
            self.ent_title.focus_set()
            return
        if not amount_str:
            messagebox.showerror("Required Field", "Please enter an amount.", parent=self)
            self.ent_amount.focus_set()
            return
        try:
            amount = float(amount_str.replace(",", ""))
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Amount",
                                 "Amount must be a positive number (e.g. 250 or 12.50).",
                                 parent=self)
            self.ent_amount.focus_set()
            return

        self.result = {
            "title": title, "amount": amount, "category": category,
            "transaction_type": tx_type, "date": date_str, "notes": notes,
        }
        self.destroy()


# ─── REMINDER DIALOG ───────────────────────────────────────────────────────────
class ReminderDialog(tb.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("New Recurring Bill")
        self.geometry("440x470")
        self.resizable(False, True)
        self.minsize(440, 430)
        self.grab_set()
        self.result = None
        self._build_ui()
        self.after(100, lambda: self.ent_title.focus_set())

    def _build_ui(self):
        hdr = tb.Frame(self, bootstyle="info", padding=(20, 12))
        hdr.pack(fill=X)
        tb.Label(hdr, text="New Recurring Bill",
                 font=("Segoe UI", 13, "bold"), bootstyle="inverse-info").pack(anchor=W)
        tb.Label(hdr, text="Set up automatic bill reminders.",
                 font=("Segoe UI", 9), bootstyle="inverse-info").pack(anchor=W)

        body = tb.Frame(self, padding=(20, 16))
        body.pack(fill=BOTH, expand=YES)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        tb.Label(body, text="Bill Title *", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky=W)
        self.ent_title = tb.Entry(body, font=("Segoe UI", 10))
        self.ent_title.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(2, 10))

        tb.Label(body, text="Amount ($) *", font=("Segoe UI", 10, "bold")).grid(
            row=2, column=0, columnspan=2, sticky=W)
        self.ent_amount = tb.Entry(body, font=("Segoe UI", 10))
        self.ent_amount.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(2, 10))

        tb.Label(body, text="Frequency *", font=("Segoe UI", 10, "bold")).grid(
            row=4, column=0, sticky=W, padx=(0, 6))
        tb.Label(body, text="Next Due Date *", font=("Segoe UI", 10, "bold")).grid(
            row=4, column=1, sticky=W)
        self.cb_freq = tb.Combobox(body, values=["Weekly", "Bi-weekly", "Monthly"],
                                   state="readonly")
        self.cb_freq.set("Monthly")
        self.cb_freq.grid(row=5, column=0, sticky="ew", padx=(0, 6), pady=(2, 10))
        self.ent_date = DateEntry(body, dateformat="%Y-%m-%d")
        self.ent_date.grid(row=5, column=1, sticky="ew", pady=(2, 10))

        tb.Label(body, text="Category *", font=("Segoe UI", 10, "bold")).grid(
            row=6, column=0, columnspan=2, sticky=W)
        self.cb_category = tb.Combobox(body, values=DEFAULT_CATEGORIES, state="readonly")
        self.cb_category.set("Rent & Housing")
        self.cb_category.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(2, 14))

        sep = ttk.Separator(self)
        sep.pack(fill=X, side=BOTTOM)
        brow = tb.Frame(self, padding=(20, 12))
        brow.pack(fill=X, side=BOTTOM)
        tb.Button(brow, text="➕   Add Bill", bootstyle="success",
                  command=self.on_save).pack(side=RIGHT, padx=(8, 0), ipadx=10, ipady=4)
        tb.Button(brow, text="Cancel", bootstyle="outline-secondary",
                  command=self.destroy).pack(side=RIGHT, ipadx=6, ipady=4)
        self.bind("<Return>", lambda e: self.on_save())
        self.bind("<Escape>", lambda e: self.destroy())

    def on_save(self):
        title = self.ent_title.get().strip()
        amount_str = self.ent_amount.get().strip()
        freq = self.cb_freq.get()
        category = self.cb_category.get()
        date_str = _parse_date(_get_date(self.ent_date))

        if not title:
            messagebox.showerror("Required", "Please enter a bill title.", parent=self)
            return
        try:
            amount = float(amount_str.replace(",", ""))
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Amount", "Amount must be a positive number.",
                                 parent=self)
            return

        self.result = {"title": title, "amount": amount, "category": category,
                       "frequency": freq, "next_due_date": date_str}
        self.destroy()


# ─── MAIN APPLICATION ──────────────────────────────────────────────────────────
class ExpenseTrackerApp(tb.Window):
    def __init__(self, db_manager):
        super().__init__(title="WealthSuite — Personal Finance Tracker", themename="cosmo")
        self.db = db_manager
        self.current_theme = "light"
        self.active_tab = "dashboard"
        self._sort_col = "date"
        self._sort_rev = True

        self.geometry("1300x840")
        self.minsize(1100, 720)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar_buttons: dict = {}
        self.tabs: dict = {}

        self._build_sidebar()
        self._build_main_container()
        self._build_statusbar()
        self.switch_tab("dashboard")
        self.current_month_str = datetime.now().strftime("%Y-%m")

        # Global keyboard shortcuts
        self.bind_all("<Delete>", self._on_delete_key)
        self.bind_all("<Control-n>", lambda e: self._add_tx())
        self.bind_all("<F5>", lambda e: self._refresh_current())

    # ── STATUS BAR ─────────────────────────────────────────────────────────────

    def _build_statusbar(self):
        bar = tb.Frame(self, bootstyle="secondary", padding=(10, 3))
        bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.status_var = tk.StringVar(value="Ready")
        tb.Label(bar, textvariable=self.status_var,
                 font=("Segoe UI", 8), bootstyle="inverse-secondary").pack(side=LEFT)
        tb.Label(bar,
                 text="Ctrl+N  Add  |  Del  Delete  |  F5  Refresh  |  Dbl-click  Edit",
                 font=("Segoe UI", 8), bootstyle="inverse-secondary").pack(side=RIGHT)

    def _set_status(self, msg: str):
        self.status_var.set(f"  {msg}")

    def _refresh_current(self):
        if self.active_tab == "dashboard":
            self._refresh_dashboard()
        elif self.active_tab == "analytics":
            self.refresh_analytics_tab()
        elif self.active_tab == "transactions":
            self._refresh_ledger()
        elif self.active_tab == "budgets":
            self._refresh_budgets()

    def _on_delete_key(self, event):
        if self.active_tab == "transactions":
            self._delete_tx()

    # ── THEME ──────────────────────────────────────────────────────────────────

    def _chart_colors(self):
        if self.current_theme == "dark":
            return "#1e2a3a", "#e0e0e0", "#304060"
        return "#ffffff", "#212529", "#dee2e6"

    def toggle_theme(self):
        if self.current_theme == "light":
            self.style.theme_use("superhero")
            self.current_theme = "dark"
            self.theme_btn.configure(text="☀  Light Mode")
        else:
            self.style.theme_use("cosmo")
            self.current_theme = "light"
            self.theme_btn.configure(text="🌙  Dark Mode")
        self._refresh_kpi_cards()
        if self.active_tab == "analytics":
            self.refresh_analytics_tab()

    # ── SIDEBAR ────────────────────────────────────────────────────────────────

    def _build_sidebar(self):
        sidebar = tb.Frame(self, bootstyle="dark", padding=(14, 16))
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.rowconfigure(8, weight=1)

        # Logo block
        logo_frame = tb.Frame(sidebar, bootstyle="dark")
        logo_frame.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        tb.Label(logo_frame, text="💳", font=("Segoe UI", 26),
                 bootstyle="inverse-dark").pack(side=LEFT)
        lbl_frame = tb.Frame(logo_frame, bootstyle="dark")
        lbl_frame.pack(side=LEFT, padx=8)
        tb.Label(lbl_frame, text="WealthSuite",
                 font=("Segoe UI", 16, "bold"), bootstyle="inverse-dark").pack(anchor=W)
        tb.Label(lbl_frame, text="Personal Finance",
                 font=("Segoe UI", 8), bootstyle="inverse-dark").pack(anchor=W)

        ttk.Separator(sidebar).grid(row=1, column=0, sticky="ew", pady=(8, 14))

        menu = [
            ("dashboard",    "📊", "Dashboard"),
            ("analytics",    "📈", "Analytics"),
            ("transactions", "📝", "Ledger"),
            ("budgets",      "📅", "Budgets & Bills"),
            ("tools",        "⚙", "Import / Export"),
        ]
        for idx, (tab_id, icon, label) in enumerate(menu, 2):
            btn = tb.Button(
                sidebar,
                text=f"  {icon}  {label}",
                bootstyle="outline-secondary",
                width=22,
                command=lambda tid=tab_id: self.switch_tab(tid),
            )
            btn.grid(row=idx, column=0, pady=4, sticky="ew")
            self.sidebar_buttons[tab_id] = btn

        ttk.Separator(sidebar).grid(row=8, column=0, sticky="ew", pady=(12, 8))

        self.theme_btn = tb.Button(
            sidebar, text="🌙  Dark Mode",
            bootstyle="outline-secondary",
            command=self.toggle_theme,
        )
        self.theme_btn.grid(row=9, column=0, pady=(0, 4), sticky="ew")

        # Version label
        tb.Label(sidebar, text="v1.0  •  SQLite  •  Pandas",
                 font=("Segoe UI", 7), bootstyle="inverse-dark").grid(
            row=10, column=0, sticky="s", pady=(8, 0))

    # ── MAIN CONTAINER ─────────────────────────────────────────────────────────

    def _build_main_container(self):
        self.main_frame = tb.Frame(self, padding=(18, 14))
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        for name in ("dashboard", "analytics", "transactions", "budgets", "tools"):
            f = tb.Frame(self.main_frame)
            f.grid(row=0, column=0, sticky="nsew")
            self.tabs[name] = f

        self._setup_dashboard()
        self._setup_analytics()
        self._setup_transactions()
        self._setup_budgets()
        self._setup_tools()

    def switch_tab(self, tab_id):
        for tid, frame in self.tabs.items():
            frame.grid_remove()
            self.sidebar_buttons[tid].configure(bootstyle="outline-secondary")
        self.tabs[tab_id].grid()
        self.sidebar_buttons[tab_id].configure(bootstyle="primary")
        self.active_tab = tab_id

        if tab_id == "dashboard":
            self._refresh_dashboard()
        elif tab_id == "analytics":
            self.refresh_analytics_tab()
        elif tab_id == "transactions":
            self._refresh_ledger()
        elif tab_id == "budgets":
            self._refresh_budgets()

    # ═══════════════════════════════════════════════════════════════════════════
    # DASHBOARD TAB
    # ═══════════════════════════════════════════════════════════════════════════

    def _setup_dashboard(self):
        tab = self.tabs["dashboard"]
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        # Page header
        hdr = tb.Frame(tab)
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        tb.Label(hdr, text="Financial Dashboard",
                 font=("Segoe UI", 22, "bold"), bootstyle="primary").pack(side=LEFT)
        self.lbl_date = tb.Label(hdr,
            text=datetime.now().strftime("  %A, %d %B %Y"),
            font=("Segoe UI", 10, "italic"))
        self.lbl_date.pack(side=LEFT, pady=(10, 0))
        tb.Button(hdr, text="↻  Refresh", bootstyle="outline-primary",
                  command=self._refresh_dashboard).pack(side=RIGHT)

        # KPI cards
        kpi = tb.Frame(tab)
        kpi.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        for i in range(3):
            kpi.columnconfigure(i, weight=1)

        def make_card(parent, col, bg, title_text, icon):
            f = tb.Frame(parent, padding=16, bootstyle=bg)
            f.grid(row=0, column=col,
                   padx=(0 if col == 0 else 6, 6 if col < 2 else 0),
                   sticky="nsew")
            tb.Label(f, text=f"{icon}  {title_text}",
                     font=("Segoe UI", 8, "bold"),
                     bootstyle=f"inverse-{bg}").pack(anchor=W)
            lbl = tb.Label(f, text="$0.00",
                           font=("Segoe UI", 22, "bold"),
                           bootstyle=f"inverse-{bg}")
            lbl.pack(anchor=W, pady=(6, 0))
            return f, lbl

        self.card_inc, self.val_income   = make_card(kpi, 0, "success", "MONTHLY INCOME",  "💰")
        self.card_exp, self.val_expense  = make_card(kpi, 1, "danger",  "MONTHLY EXPENSE", "💸")
        self.card_sav, self.val_savings  = make_card(kpi, 2, "info",    "NET SAVINGS",     "🏦")
        self.lbl_sav_title = self.card_sav.winfo_children()[0]

        # Split pane
        split = tb.Frame(tab)
        split.grid(row=2, column=0, sticky="nsew")
        split.columnconfigure(0, weight=1)
        split.rowconfigure(0, weight=1)

        # Recent transactions table
        tbl_lf = tb.LabelFrame(split, text=" 📋  Recent Transactions (last 10) ",
                               padx=8, pady=8)
        tbl_lf.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        tbl_lf.rowconfigure(0, weight=1)
        tbl_lf.columnconfigure(0, weight=1)

        cols = ("date", "title", "category", "type", "amount")
        self.dash_tree = ttk.Treeview(tbl_lf, columns=cols,
                                       show="headings", height=10,
                                       selectmode="browse")
        self.dash_tree.grid(row=0, column=0, sticky="nsew")
        for col, txt, w, anc in [
            ("date",     "Date",     85, CENTER),
            ("title",    "Title",   180, W),
            ("category", "Category",120, W),
            ("type",     "Type",     75, CENTER),
            ("amount",   "Amount",   95, E),
        ]:
            self.dash_tree.heading(col, text=txt)
            self.dash_tree.column(col, width=w, anchor=anc)

        dsb = tb.Scrollbar(tbl_lf, orient=VERTICAL, command=self.dash_tree.yview)
        self.dash_tree.configure(yscrollcommand=dsb.set)
        dsb.grid(row=0, column=1, sticky="ns")
        self.dash_tree.bind("<Double-1>", lambda e: self._edit_tx(self.dash_tree))

        # Right quick-add panel
        right = tb.Frame(split, width=320)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_propagate(False)

        nlp = tb.LabelFrame(right, text=" ⚡  Smart Quick-Add ", padx=10, pady=10)
        nlp.pack(fill=X, pady=(0, 10))
        tb.Label(nlp,
                 text='Type naturally:\n"Spent 200 on groceries" or "Salary 5000"',
                 font=("Segoe UI", 9, "italic"), bootstyle="secondary",
                 wraplength=280).pack(anchor=W, pady=(0, 6))
        self.ent_nlp = tb.Entry(nlp, font=("Segoe UI", 10))
        self.ent_nlp.pack(fill=X, pady=(0, 6))
        self.ent_nlp.bind("<Return>", lambda e: self._process_nlp())
        tb.Button(nlp, text="⚡  Parse & Add", bootstyle="primary",
                  command=self._process_nlp).pack(fill=X)

        gauge = tb.LabelFrame(right, text=" 📊  Monthly Savings Rate ", padx=10, pady=10)
        gauge.pack(fill=X, pady=(0, 10))
        self.savings_meter = tb.Meter(gauge, metersize=150, padding=4,
                                      amountused=0, amounttotal=100,
                                      subtext="Savings Rate", textright="%",
                                      stripethickness=12, bootstyle="info",
                                      interactive=False)
        self.savings_meter.pack(pady=6)

        quick = tb.LabelFrame(right, text=" 🚀  Quick Actions ", padx=10, pady=10)
        quick.pack(fill=X)
        tb.Button(quick, text="➕  Add Transaction", bootstyle="success",
                  command=self._add_tx).pack(fill=X, pady=2)
        tb.Button(quick, text="📈  View Analytics", bootstyle="info-outline",
                  command=lambda: self.switch_tab("analytics")).pack(fill=X, pady=2)
        tb.Button(quick, text="📝  Open Ledger", bootstyle="secondary-outline",
                  command=lambda: self.switch_tab("transactions")).pack(fill=X, pady=2)

    def _refresh_dashboard(self):
        today = datetime.now()
        som = today.replace(day=1).strftime("%Y-%m-%d")
        eom = ((today.replace(day=28) + timedelta(days=4)).replace(day=1)
               - timedelta(days=1)).strftime("%Y-%m-%d")
        try:
            all_tx   = self.db.get_transactions()
            month_tx = self.db.get_transactions(date_from=som, date_to=eom)
        except Exception as e:
            messagebox.showerror("DB Error", str(e))
            return

        stats = get_summary_stats(month_tx)
        self.val_income.configure(text=f"${stats['total_income']:,.2f}")
        self.val_expense.configure(text=f"${stats['total_expense']:,.2f}")
        self.val_savings.configure(text=f"${stats['net_savings']:,.2f}")

        if stats["net_savings"] < 0:
            self.card_sav.configure(bootstyle="warning")
        else:
            self.card_sav.configure(bootstyle="info")

        self.savings_meter.configure(
            amountused=max(0, min(100, int(stats["savings_rate"]))))

        self.dash_tree.delete(*self.dash_tree.get_children())
        for t in all_tx[:10]:
            pfx = "+" if t["transaction_type"] == "Income" else "-"
            tag = "inc" if t["transaction_type"] == "Income" else "exp"
            self.dash_tree.insert("", END,
                values=(t["date"], t["title"], t["category"],
                        t["transaction_type"], f"{pfx}${t['amount']:,.2f}"),
                tags=(tag,))
        self.dash_tree.tag_configure("inc",
            foreground="#2ecc71" if self.current_theme == "dark" else "#27ae60")
        self.dash_tree.tag_configure("exp",
            foreground="#e74c3c" if self.current_theme == "dark" else "#c0392b")

        n = len(all_tx)
        self._set_status(
            f"Dashboard refreshed — {n} total transactions | "
            f"This month: income ${stats['total_income']:,.2f} | "
            f"expense ${stats['total_expense']:,.2f}")

    def _refresh_kpi_cards(self):
        self._refresh_dashboard()

    def _process_nlp(self):
        text = self.ent_nlp.get().strip()
        if not text:
            return
        try:
            parsed = parse_nlp_input(text)
        except Exception as e:
            messagebox.showerror("Parser Error", str(e))
            return
        if not parsed or parsed.get("amount", 0) == 0:
            messagebox.showwarning("Could Not Parse",
                "No amount detected.\n"
                "Try: 'Spent 500 on food' or 'Received salary 4000'")
            return
        diag = TransactionDialog(self, title="Confirm Quick-Add", transaction=parsed)
        self.wait_window(diag)
        if diag.result:
            r = diag.result
            try:
                self.db.add_transaction(r["title"], r["amount"], r["category"],
                                        r["transaction_type"], r["date"], r["notes"])
            except Exception as e:
                messagebox.showerror("Save Error", str(e))
                return
            self.ent_nlp.delete(0, END)
            self._refresh_dashboard()
            self._set_status("Quick transaction added via NLP!")
            messagebox.showinfo("✅ Saved", "Transaction saved successfully!")

    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYTICS TAB
    # ═══════════════════════════════════════════════════════════════════════════

    def _setup_analytics(self):
        tab = self.tabs["analytics"]
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        ctrl = tb.Frame(tab)
        ctrl.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        tb.Label(ctrl, text="Analytics & Charts",
                 font=("Segoe UI", 20, "bold"), bootstyle="primary").pack(side=LEFT)
        tb.Button(ctrl, text="🔄  Redraw Charts", bootstyle="outline-primary",
                  command=self.refresh_analytics_tab).pack(side=RIGHT)

        self.chart_container = tb.Frame(tab)
        self.chart_container.grid(row=1, column=0, sticky="nsew")
        self.chart_container.columnconfigure(0, weight=1)
        self.chart_container.columnconfigure(1, weight=1)
        self.chart_container.rowconfigure(0, weight=1)

    def refresh_analytics_tab(self):
        for w in self.chart_container.winfo_children():
            w.destroy()
        try:
            tx = self.db.get_transactions()
        except Exception as e:
            messagebox.showerror("DB Error", str(e))
            return

        bg, fg, grid = self._chart_colors()
        is_dk = (self.current_theme == "dark")

        for col, gen_fn, err_col in [
            (0, lambda: generate_category_donut_chart(
                tx, bg_color=bg, fg_color=fg, grid_color=grid, is_dark=is_dk), 0),
            (1, lambda: generate_monthly_trend_chart(
                tx, bg_color=bg, fg_color=fg, grid_color=grid, is_dark=is_dk), 1),
        ]:
            try:
                fig = gen_fn()
                c = FigureCanvasTkAgg(fig, master=self.chart_container)
                c.draw()
                c.get_tk_widget().grid(row=0, column=col,
                                       sticky="nsew", padx=6, pady=6)
            except Exception as e:
                tb.Label(self.chart_container,
                         text=f"⚠ Chart error:\n{e}",
                         bootstyle="danger",
                         font=("Segoe UI", 10)).grid(row=0, column=col, padx=20)

        self._set_status(f"Charts rendered — {len(tx)} transactions loaded")

    # ═══════════════════════════════════════════════════════════════════════════
    # TRANSACTIONS / LEDGER TAB
    # ═══════════════════════════════════════════════════════════════════════════

    def _setup_transactions(self):
        tab = self.tabs["transactions"]
        tab.rowconfigure(2, weight=1)
        tab.columnconfigure(0, weight=1)

        # Page title
        hdr = tb.Frame(tab)
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tb.Label(hdr, text="Transaction Ledger",
                 font=("Segoe UI", 20, "bold"), bootstyle="primary").pack(side=LEFT)

        # Filters
        fbox = tb.LabelFrame(tab, text=" 🔍  Filters & Search ", padx=10, pady=8)
        fbox.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        tb.Label(fbox, text="Keyword:", font=("Segoe UI", 9)).grid(
            row=0, column=0, sticky=W, padx=(0, 4))
        self.ent_search = tb.Entry(fbox, width=20)
        self.ent_search.grid(row=0, column=1, padx=(0, 14), pady=4, sticky="ew")
        self.ent_search.bind("<KeyRelease>", lambda e: self._refresh_ledger())

        tb.Label(fbox, text="Category:", font=("Segoe UI", 9)).grid(
            row=0, column=2, sticky=W, padx=(0, 4))
        self.cb_filter_cat = tb.Combobox(fbox, values=["All"] + DEFAULT_CATEGORIES,
                                          state="readonly", width=16)
        self.cb_filter_cat.set("All")
        self.cb_filter_cat.grid(row=0, column=3, padx=(0, 14), pady=4)
        self.cb_filter_cat.bind("<<ComboboxSelected>>", lambda e: self._refresh_ledger())

        tb.Label(fbox, text="Type:", font=("Segoe UI", 9)).grid(
            row=0, column=4, sticky=W, padx=(0, 4))
        self.cb_filter_type = tb.Combobox(fbox, values=["All", "Income", "Expense"],
                                           state="readonly", width=10)
        self.cb_filter_type.set("All")
        self.cb_filter_type.grid(row=0, column=5, pady=4)
        self.cb_filter_type.bind("<<ComboboxSelected>>", lambda e: self._refresh_ledger())

        drow = tb.Frame(fbox)
        drow.grid(row=1, column=0, columnspan=6, sticky="w", pady=(0, 4))
        tb.Label(drow, text="Date From:", font=("Segoe UI", 9)).pack(side=LEFT, padx=(0, 4))
        self.dp_from = DateEntry(drow, dateformat="%Y-%m-%d", width=13)
        self.dp_from.pack(side=LEFT, padx=(0, 10))
        _set_date(self.dp_from, "")
        tb.Label(drow, text="To:", font=("Segoe UI", 9)).pack(side=LEFT, padx=(0, 4))
        self.dp_to = DateEntry(drow, dateformat="%Y-%m-%d", width=13)
        self.dp_to.pack(side=LEFT, padx=(0, 10))
        _set_date(self.dp_to, "")
        tb.Button(drow, text="Apply", bootstyle="info-outline",
                  command=self._refresh_ledger).pack(side=LEFT, padx=(0, 6))
        tb.Button(drow, text="Clear All", bootstyle="secondary-outline",
                  command=self._clear_filters).pack(side=LEFT)

        # Treeview — extended selectmode for multi-select
        gf = tb.Frame(tab)
        gf.grid(row=2, column=0, sticky="nsew")
        gf.rowconfigure(0, weight=1)
        gf.columnconfigure(0, weight=1)

        cols = ("id", "date", "title", "category", "type", "amount", "notes")
        self.ledger_tree = ttk.Treeview(
            gf, columns=cols, show="headings",
            selectmode="extended")           # ← MULTI-SELECT ENABLED
        self.ledger_tree.grid(row=0, column=0, sticky="nsew")

        col_cfg = [
            ("id",       "ID",       45,  CENTER),
            ("date",     "Date",     90,  CENTER),
            ("title",    "Title",   185,  W),
            ("category", "Category",130,  W),
            ("type",     "Type",     80,  CENTER),
            ("amount",   "Amount",   95,  E),
            ("notes",    "Notes",   240,  W),
        ]
        for col, txt, w, anc in col_cfg:
            self.ledger_tree.heading(col, text=txt,
                command=lambda c=col: self._sort_ledger(c))
            self.ledger_tree.column(col, width=w, anchor=anc)

        lsb = tb.Scrollbar(gf, orient=VERTICAL, command=self.ledger_tree.yview)
        self.ledger_tree.configure(yscrollcommand=lsb.set)
        lsb.grid(row=0, column=1, sticky="ns")
        self.ledger_tree.bind("<Double-1>", lambda e: self._edit_tx(self.ledger_tree))

        # Right-click context menu
        self._ledger_menu = tk.Menu(self, tearoff=0)
        self._ledger_menu.add_command(label="✏  Edit", command=lambda: self._edit_tx(self.ledger_tree))
        self._ledger_menu.add_command(label="🗑  Delete Selected", command=self._delete_tx)
        self._ledger_menu.add_separator()
        self._ledger_menu.add_command(label="➕  Add New", command=self._add_tx)
        self.ledger_tree.bind("<Button-3>", self._show_ledger_menu)

        # Bottom toolbar
        bot = tb.Frame(tab)
        bot.grid(row=3, column=0, sticky="ew", pady=(8, 0))

        tb.Button(bot, text="➕  Add Transaction", bootstyle="success",
                  command=self._add_tx).pack(side=LEFT, padx=(0, 6))
        tb.Button(bot, text="✏  Edit Selected", bootstyle="warning",
                  command=lambda: self._edit_tx(self.ledger_tree)).pack(side=LEFT, padx=(0, 6))
        tb.Button(bot, text="🗑  Delete Selected", bootstyle="danger",
                  command=self._delete_tx).pack(side=LEFT, padx=(0, 6))
        tb.Button(bot, text="🗑  Delete ALL Filtered", bootstyle="outline-danger",
                  command=self._delete_all_visible).pack(side=LEFT, padx=(0, 20))

        self.lbl_row_count = tb.Label(bot, text="",
                                       font=("Segoe UI", 9, "italic"),
                                       bootstyle="secondary")
        self.lbl_row_count.pack(side=RIGHT, padx=8)

    def _show_ledger_menu(self, event):
        row = self.ledger_tree.identify_row(event.y)
        if row:
            if row not in self.ledger_tree.selection():
                self.ledger_tree.selection_set(row)
            self._ledger_menu.post(event.x_root, event.y_root)

    def _sort_ledger(self, col):
        """Sort treeview by clicking a column header."""
        if self._sort_col == col:
            self._sort_rev = not self._sort_rev
        else:
            self._sort_col = col
            self._sort_rev = False

        items = [(self.ledger_tree.set(k, col), k)
                 for k in self.ledger_tree.get_children("")]
        try:
            items.sort(key=lambda t: float(
                t[0].replace("+", "").replace("-", "")
                    .replace("$", "").replace(",", "")),
                reverse=self._sort_rev)
        except ValueError:
            items.sort(key=lambda t: t[0].lower(), reverse=self._sort_rev)

        for idx, (_, k) in enumerate(items):
            self.ledger_tree.move(k, "", idx)

        # Show sort arrow in heading
        for c in ("id", "date", "title", "category", "type", "amount", "notes"):
            arrow = (" ▲" if not self._sort_rev else " ▼") if c == col else ""
            name = {"id":"ID","date":"Date","title":"Title","category":"Category",
                    "type":"Type","amount":"Amount","notes":"Notes"}[c]
            self.ledger_tree.heading(c, text=name + arrow)

    def _refresh_ledger(self):
        sq  = self.ent_search.get().strip() or None
        cat = self.cb_filter_cat.get()
        typ = self.cb_filter_type.get()

        df_val = _get_date(self.dp_from)
        dt_val = _get_date(self.dp_to)
        date_from = _parse_date(df_val) if df_val else None
        date_to   = _parse_date(dt_val) if dt_val else None

        try:
            records = self.db.get_transactions(
                search_query=sq,
                category=cat if cat != "All" else None,
                transaction_type=typ if typ != "All" else None,
                date_from=date_from,
                date_to=date_to,
            )
        except Exception as e:
            messagebox.showerror("DB Error", str(e))
            return

        self.ledger_tree.delete(*self.ledger_tree.get_children())
        for r in records:
            pfx = "+" if r["transaction_type"] == "Income" else "-"
            tag = "inc" if r["transaction_type"] == "Income" else "exp"
            self.ledger_tree.insert("", END,
                values=(r["id"], r["date"], r["title"], r["category"],
                        r["transaction_type"],
                        f"{pfx}${r['amount']:,.2f}",
                        r.get("notes") or ""),
                tags=(tag,))

        self.ledger_tree.tag_configure("inc",
            foreground="#2ecc71" if self.current_theme == "dark" else "#27ae60")
        self.ledger_tree.tag_configure("exp",
            foreground="#e74c3c" if self.current_theme == "dark" else "#c0392b")

        n = len(records)
        self.lbl_row_count.configure(text=f"{n} record{'s' if n != 1 else ''} shown")
        self._set_status(f"Ledger — {n} records  |  Hold Ctrl or Shift to select multiple rows  |  Press Del to delete")

    def _clear_filters(self):
        self.ent_search.delete(0, END)
        self.cb_filter_cat.set("All")
        self.cb_filter_type.set("All")
        _set_date(self.dp_from, "")
        _set_date(self.dp_to, "")
        self._refresh_ledger()

    def _add_tx(self):
        diag = TransactionDialog(self, title="Add New Transaction")
        self.wait_window(diag)
        if diag.result:
            r = diag.result
            try:
                self.db.add_transaction(r["title"], r["amount"], r["category"],
                                        r["transaction_type"], r["date"], r["notes"])
            except Exception as e:
                messagebox.showerror("Save Error", str(e))
                return
            self._refresh_ledger()
            self._set_status(f"Added: {r['title']}  ${r['amount']:,.2f}")
            messagebox.showinfo("✅ Added", "Transaction saved successfully!")

    def _edit_tx(self, tree):
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a row to edit.")
            return
        if len(sel) > 1:
            messagebox.showinfo("Tip",
                "Only one transaction can be edited at a time.\n"
                "The first selected row will be used.")
        vals = tree.item(sel[0], "values")
        if len(vals) == 5:
            messagebox.showinfo("Tip", "Switch to the Ledger tab to edit entries.")
            return
        tx_id = int(vals[0])
        amt_raw = (str(vals[5]).replace("+","").replace("-","")
                               .replace("$","").replace(",",""))
        tx_dict = {
            "id": tx_id, "date": vals[1], "title": vals[2],
            "category": vals[3], "transaction_type": vals[4],
            "amount": float(amt_raw), "notes": vals[6],
        }
        diag = TransactionDialog(self, title="Edit Transaction", transaction=tx_dict)
        self.wait_window(diag)
        if diag.result:
            r = diag.result
            try:
                self.db.update_transaction(tx_id, r["title"], r["amount"], r["category"],
                                           r["transaction_type"], r["date"], r["notes"])
            except Exception as e:
                messagebox.showerror("Update Error", str(e))
                return
            self._refresh_ledger()
            self._set_status(f"Updated transaction ID {tx_id}: {r['title']}")
            messagebox.showinfo("✅ Updated", "Transaction updated!")

    def _delete_tx(self):
        """Delete ALL selected rows (multi-select supported)."""
        sel = self.ledger_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection",
                "Select one or more rows to delete.\n"
                "(Hold Ctrl to select multiple, Shift for a range)")
            return

        count = len(sel)
        ids_titles = []
        for item in sel:
            vals = self.ledger_tree.item(item, "values")
            ids_titles.append((int(vals[0]), vals[2]))

        msg = (f"Delete {count} selected transaction{'s' if count > 1 else ''}?\n\n" +
               "\n".join(f"  • {t}  (ID {i})" for i, t in ids_titles[:8]) +
               (f"\n  … and {count-8} more" if count > 8 else "") +
               "\n\nThis cannot be undone.")
        if not messagebox.askyesno("Confirm Delete", msg):
            return

        errors = []
        for tx_id, title in ids_titles:
            try:
                self.db.delete_transaction(tx_id)
            except Exception as e:
                errors.append(f"ID {tx_id}: {e}")

        self._refresh_ledger()
        if errors:
            messagebox.showerror("Partial Error",
                f"Deleted {count-len(errors)} of {count}.\nErrors:\n" + "\n".join(errors))
        else:
            self._set_status(f"Deleted {count} transaction{'s' if count>1 else ''}")
            messagebox.showinfo("🗑 Deleted",
                f"{count} transaction{'s' if count > 1 else ''} deleted.")

    def _delete_all_visible(self):
        """Delete every row currently visible in the ledger (filtered or all)."""
        children = self.ledger_tree.get_children()
        if not children:
            messagebox.showinfo("Empty", "No transactions to delete.")
            return
        count = len(children)
        if not messagebox.askyesno("Delete ALL Visible",
                f"⚠ This will permanently delete ALL {count} visible records!\n\n"
                "Are you absolutely sure?"):
            return
        ids = [int(self.ledger_tree.item(c, "values")[0]) for c in children]
        ok = 0
        for tx_id in ids:
            try:
                self.db.delete_transaction(tx_id)
                ok += 1
            except Exception:
                pass
        self._refresh_ledger()
        self._set_status(f"Bulk-deleted {ok} transactions")
        messagebox.showinfo("Done", f"Deleted {ok} transactions.")

    # ═══════════════════════════════════════════════════════════════════════════
    # BUDGETS & BILLS TAB
    # ═══════════════════════════════════════════════════════════════════════════

    def _setup_budgets(self):
        tab = self.tabs["budgets"]
        tab.grid_columnconfigure(0, weight=3)
        tab.grid_columnconfigure(1, weight=2)
        tab.grid_rowconfigure(0, weight=1)

        blf = tb.LabelFrame(tab, text=" 📅  Category Monthly Budgets ", padx=12, pady=10)
        blf.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        blf.rowconfigure(1, weight=1)
        blf.columnconfigure(0, weight=1)

        tb.Label(blf,
            text="Green = on track  |  Orange = >50%  |  Red = >85%  |  Click 'Edit Limit' to set a cap",
            font=("Segoe UI", 9, "italic"),
            bootstyle="secondary").grid(row=0, column=0, columnspan=2, sticky=W, pady=(0, 8))

        # Scrollable budget area using Canvas
        host = tb.Frame(blf)
        host.grid(row=1, column=0, columnspan=2, sticky="nsew")
        host.rowconfigure(0, weight=1)
        host.columnconfigure(0, weight=1)

        self.budget_canvas = tk.Canvas(host, highlightthickness=0, bd=0)
        self.budget_canvas.grid(row=0, column=0, sticky="nsew")
        bsb = tb.Scrollbar(host, orient=VERTICAL, command=self.budget_canvas.yview)
        bsb.grid(row=0, column=1, sticky="ns")
        self.budget_canvas.configure(yscrollcommand=bsb.set)

        self.budget_inner = tb.Frame(self.budget_canvas)
        self._bwin = self.budget_canvas.create_window(
            (0, 0), window=self.budget_inner, anchor="nw")

        self.budget_inner.bind("<Configure>",
            lambda e: self.budget_canvas.configure(
                scrollregion=self.budget_canvas.bbox("all")))
        self.budget_canvas.bind("<Configure>",
            lambda e: self.budget_canvas.itemconfig(self._bwin, width=e.width))
        self.budget_canvas.bind("<MouseWheel>",
            lambda e: self.budget_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        # Right panel — reminders
        rlf = tb.LabelFrame(tab, text=" 🔔  Recurring Bill Reminders ", padx=12, pady=10)
        rlf.grid(row=0, column=1, sticky="nsew")
        rlf.rowconfigure(1, weight=1)
        rlf.columnconfigure(0, weight=1)

        rcols = ("id", "title", "amount", "due", "freq")
        self.reminders_tree = ttk.Treeview(rlf, columns=rcols, show="headings", height=14)
        self.reminders_tree.grid(row=1, column=0, sticky="nsew", columnspan=2)
        for col, txt, w, anc in [
            ("id","ID",32,CENTER),("title","Bill",120,W),("amount","Amount",72,E),
            ("due","Due Date",88,CENTER),("freq","Freq",60,CENTER)
        ]:
            self.reminders_tree.heading(col, text=txt)
            self.reminders_tree.column(col, width=w, anchor=anc)
        rsb = tb.Scrollbar(rlf, orient=VERTICAL, command=self.reminders_tree.yview)
        self.reminders_tree.configure(yscrollcommand=rsb.set)
        rsb.grid(row=1, column=2, sticky="ns")

        rb = tb.Frame(rlf)
        rb.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        tb.Button(rb, text="➕ Add",  bootstyle="success-outline", command=self._add_bill).pack(side=LEFT, padx=3)
        tb.Button(rb, text="✅ Paid", bootstyle="success",         command=self._pay_bill).pack(side=LEFT, padx=3)
        tb.Button(rb, text="🗑 Delete", bootstyle="danger-outline", command=self._delete_bill).pack(side=LEFT, padx=3)

    def _refresh_budgets(self):
        for w in self.budget_inner.winfo_children():
            w.destroy()

        try:
            budgets = self.db.get_budgets()
        except Exception:
            budgets = {}

        today = datetime.now()
        som = today.replace(day=1).strftime("%Y-%m-%d")
        eom = ((today.replace(day=28)+timedelta(days=4)).replace(day=1)-timedelta(days=1)).strftime("%Y-%m-%d")
        try:
            txs = self.db.get_transactions(date_from=som, date_to=eom)
        except Exception:
            txs = []

        cat_df = get_category_breakdown(txs)
        actual = {} if cat_df.empty else dict(zip(cat_df["category"], cat_df["amount"]))

        cats = [c for c in DEFAULT_CATEGORIES if c not in ("Salary & Income","Freelance")]

        for cat in cats:
            limit = budgets.get(cat, 0.0)
            spent = actual.get(cat, 0.0)

            row = tb.Frame(self.budget_inner, padding=(6, 4))
            row.pack(fill=X, pady=2)

            tb.Label(row, text=cat, font=("Segoe UI", 9, "bold"),
                     width=24, anchor=W).pack(side=LEFT)

            mid = tb.Frame(row)
            mid.pack(side=LEFT, fill=X, expand=YES, padx=8)

            limit_txt = (f"${spent:,.2f}  /  ${limit:,.2f}"
                         if limit > 0 else f"${spent:,.2f}  (no limit)")
            tb.Label(mid, text=limit_txt, font=("Segoe UI", 9),
                     anchor=E).pack(anchor=E, pady=(0,2))

            pct = int(spent / limit * 100) if limit > 0 else 0
            style = "info" if limit == 0 else (
                "success" if pct <= 50 else "warning" if pct <= 85 else "danger")
            tb.Progressbar(mid, value=min(100, pct),
                           bootstyle=style).pack(fill=X)

            tb.Button(row, text="Set Limit", bootstyle="outline-secondary",
                      command=lambda c=cat, l=limit: self._set_budget(c, l)
                      ).pack(side=RIGHT, padx=(4,0))

        # Reminders
        self.reminders_tree.delete(*self.reminders_tree.get_children())
        try:
            for r in self.db.get_reminders():
                tag = ""
                try:
                    due = datetime.strptime(r["next_due_date"], "%Y-%m-%d")
                    if due.date() <= datetime.now().date():
                        tag = "overdue"
                except Exception:
                    pass
                self.reminders_tree.insert("", END,
                    values=(r["id"], r["title"], f"${r['amount']:,.2f}",
                            r["next_due_date"], r["frequency"]),
                    tags=(tag,))
            self.reminders_tree.tag_configure("overdue", foreground="#e74c3c")
        except Exception:
            pass

    def _set_budget(self, category, current):
        new_val = simpledialog.askfloat("Budget Limit",
            f"Monthly limit ($) for:\n'{category}'\n(Enter 0 to remove limit)",
            initialvalue=current, minvalue=0.0, parent=self)
        if new_val is not None:
            try:
                self.db.set_budget(category, new_val)
            except Exception as e:
                messagebox.showerror("Error", str(e))
                return
            self._refresh_budgets()
            self._set_status(f"Budget updated: {category} → ${new_val:,.2f}/month")

    def _add_bill(self):
        diag = ReminderDialog(self)
        self.wait_window(diag)
        if diag.result:
            r = diag.result
            try:
                self.db.add_reminder(r["title"], r["amount"], r["category"],
                                     r["frequency"], r["next_due_date"])
            except Exception as e:
                messagebox.showerror("Error", str(e))
                return
            self._refresh_budgets()
            messagebox.showinfo("✅ Added", "Bill reminder added!")

    def _pay_bill(self):
        sel = self.reminders_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select a bill to mark as paid.")
            return
        vals = self.reminders_tree.item(sel[0], "values")
        bill_id = int(vals[0])
        title   = vals[1]
        amt     = float(vals[2].replace("$","").replace(",",""))
        due     = vals[3]
        freq    = vals[4]

        if not messagebox.askyesno("Pay Bill",
                f"Mark '{title}'  (${amt:,.2f}) as paid?\n\n"
                "• An expense entry will be auto-logged.\n"
                "• The next due date will roll over."):
            return

        try:
            reminders = self.db.get_reminders()
            item = next((x for x in reminders if x["id"] == bill_id), None)
            cat = item["category"] if item else "Utilities & Bills"
            self.db.add_transaction(f"Bill: {title}", amt, cat, "Expense", due,
                                    f"Auto-paid recurring bill (ID {bill_id})")
            dt = datetime.strptime(due, "%Y-%m-%d")
            if freq == "Weekly":
                nxt = dt + timedelta(weeks=1)
            elif freq == "Bi-weekly":
                nxt = dt + timedelta(weeks=2)
            else:
                m, y = dt.month+1, dt.year
                if m > 12: m, y = 1, y+1
                try:
                    nxt = datetime(y, m, dt.day)
                except ValueError:
                    nxt = datetime(y, m, 28)
            self.db.update_reminder_due_date(bill_id, nxt.strftime("%Y-%m-%d"))
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        self._refresh_budgets()
        self._set_status(f"Bill paid: {title} — next due {nxt.strftime('%Y-%m-%d')}")
        messagebox.showinfo("✅ Paid", "Bill logged and due date rolled over!")

    def _delete_bill(self):
        sel = self.reminders_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select a bill to delete.")
            return
        vals = self.reminders_tree.item(sel[0], "values")
        bill_id, title = int(vals[0]), vals[1]
        if messagebox.askyesno("Confirm Delete", f"Remove recurring bill '{title}'?"):
            try:
                self.db.delete_reminder(bill_id)
            except Exception as e:
                messagebox.showerror("Error", str(e))
                return
            self._refresh_budgets()
            messagebox.showinfo("Deleted", "Bill removed.")

    # ═══════════════════════════════════════════════════════════════════════════
    # TOOLS TAB
    # ═══════════════════════════════════════════════════════════════════════════

    def _setup_tools(self):
        tab = self.tabs["tools"]
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        # CSV Import
        ic = tb.LabelFrame(tab, text=" 📥  Bulk CSV Importer ", padx=16, pady=14)
        ic.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=8)
        ic.rowconfigure(4, weight=1)
        ic.columnconfigure(0, weight=1)

        tb.Label(ic, text="Import transactions from a CSV file",
                 font=("Segoe UI", 11, "bold"), bootstyle="primary").grid(
            row=0, column=0, sticky=W, pady=(0, 8))

        inst = (
            "Required CSV columns (exact names):\n"
            "   title             —  description text\n"
            "   amount            —  positive number\n"
            "   category          —  e.g. Food & Dining\n"
            "   transaction_type  —  Income  or  Expense\n"
            "   date              —  YYYY-MM-DD format\n"
            "   notes             —  optional\n\n"
            "Headers with spaces (e.g. 'transaction type') are\n"
            "also accepted — they are normalised automatically."
        )
        tb.Label(ic, text=inst, font=("Consolas", 9),
                 bootstyle="secondary", justify=LEFT).grid(
            row=1, column=0, sticky=W, pady=(0, 10))

        tb.Button(ic, text="📁  Browse & Import CSV…", bootstyle="info",
                  command=self._import_csv).grid(row=2, column=0, sticky="ew", pady=(0, 10))

        ttk.Separator(ic).grid(row=3, column=0, sticky="ew", pady=(0, 6))
        tb.Label(ic, text="Import Log:", font=("Segoe UI", 9, "bold")).grid(
            row=3, column=0, sticky=W)
        lf2 = tb.Frame(ic)
        lf2.grid(row=4, column=0, sticky="nsew")
        lf2.rowconfigure(0, weight=1)
        lf2.columnconfigure(0, weight=1)
        self.lst_logs = tk.Listbox(lf2, font=("Consolas", 8), height=10,
                                   selectmode="browse")
        self.lst_logs.grid(row=0, column=0, sticky="nsew")
        lsb2 = tb.Scrollbar(lf2, orient=VERTICAL, command=self.lst_logs.yview)
        self.lst_logs.configure(yscrollcommand=lsb2.set)
        lsb2.grid(row=0, column=1, sticky="ns")

        # Export
        ec = tb.LabelFrame(tab, text=" 📤  Export Reports ", padx=16, pady=14)
        ec.grid(row=0, column=1, sticky="nsew", pady=8)

        tb.Label(ec, text="Generate professional reports",
                 font=("Segoe UI", 11, "bold"), bootstyle="primary").pack(anchor=W, pady=(0, 12))

        # Excel card
        ttk.Separator(ec).pack(fill=X, pady=(0, 10))
        tb.Label(ec, text="📊  Excel Workbook (.xlsx)",
                 font=("Segoe UI", 10, "bold")).pack(anchor=W)
        tb.Label(ec,
                 text="Zebra-striped ledger + Executive Summary sheet with SUMIF formulas.",
                 font=("Segoe UI", 9), bootstyle="secondary",
                 wraplength=320, justify=LEFT).pack(anchor=W, pady=(4, 8))
        tb.Button(ec, text="⬇  Export Excel (.xlsx)", bootstyle="success",
                  command=self._export_excel).pack(fill=X, pady=(0, 16))

        # PDF card
        ttk.Separator(ec).pack(fill=X, pady=(0, 10))
        tb.Label(ec, text="📄  PDF Report (.pdf)",
                 font=("Segoe UI", 10, "bold")).pack(anchor=W)
        tb.Label(ec,
                 text="KPI summary, full ledger table, category breakdown, and page numbers.",
                 font=("Segoe UI", 9), bootstyle="secondary",
                 wraplength=320, justify=LEFT).pack(anchor=W, pady=(4, 8))
        tb.Button(ec, text="⬇  Export PDF (.pdf)", bootstyle="danger",
                  command=self._export_pdf).pack(fill=X)

    def _import_csv(self):
        fp = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV Files","*.csv"),("All Files","*.*")])
        if not fp:
            return
        self.lst_logs.delete(0, END)
        self.lst_logs.insert(END, f"📂  Opening: {os.path.basename(fp)}")
        try:
            rows = import_from_csv(fp)
            self.lst_logs.insert(END, f"✓  Parsed {len(rows)} rows — saving…")
            for i, r in enumerate(rows, 1):
                self.db.add_transaction(r["title"], r["amount"], r["category"],
                                        r["transaction_type"], r["date"], r["notes"])
                self.lst_logs.insert(END,
                    f"  [{i:03}]  {r['title'][:30]}  ${r['amount']:.2f}")
                self.lst_logs.see(END)
            self.lst_logs.insert(END, "─" * 44)
            self.lst_logs.insert(END,
                f"✅  Imported {len(rows)} transactions successfully!")
            self._set_status(f"CSV import complete — {len(rows)} records added")
            messagebox.showinfo("✅ Import Complete",
                                f"Successfully imported {len(rows)} transactions.")
        except Exception as e:
            self.lst_logs.insert(END, f"✗  ERROR: {e}")
            self._set_status("CSV import failed — see log for details")
            messagebox.showerror("Import Failed", str(e))

    def _export_excel(self):
        try:
            tx = self.db.get_transactions()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        if not tx:
            messagebox.showwarning("No Data", "Add some transactions before exporting.")
            return
        fp = filedialog.asksaveasfilename(
            title="Save Excel File", defaultextension=".xlsx",
            filetypes=[("Excel Workbook","*.xlsx")],
            initialfile=f"WealthSuite_{datetime.now().strftime('%Y-%m-%d')}.xlsx")
        if not fp:
            return
        try:
            export_to_excel(fp, tx)
            self._set_status(f"Excel exported → {os.path.basename(fp)}")
            messagebox.showinfo("✅ Exported", f"Excel file saved:\n{fp}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    def _export_pdf(self):
        try:
            tx = self.db.get_transactions()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        if not tx:
            messagebox.showwarning("No Data", "Add some transactions before exporting.")
            return
        fp = filedialog.asksaveasfilename(
            title="Save PDF Report", defaultextension=".pdf",
            filetypes=[("PDF Document","*.pdf")],
            initialfile=f"WealthSuite_Report_{datetime.now().strftime('%Y-%m-%d')}.pdf")
        if not fp:
            return
        try:
            export_to_pdf(fp, tx, get_summary_stats(tx))
            self._set_status(f"PDF exported → {os.path.basename(fp)}")
            messagebox.showinfo("✅ Exported", f"PDF report saved:\n{fp}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))
