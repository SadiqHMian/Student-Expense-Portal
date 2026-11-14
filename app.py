import streamlit as st
import pandas as pd
import json
import csv
from datetime import datetime
from pathlib import Path
import plotly.express as px

# ==========================================
# 1. BACKEND LOGIC
# ==========================================
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

USERS_FILE   = DATA_DIR / "users.json"
EXPENSES_FILE = DATA_DIR / "expenses.csv"
BUDGETS_FILE  = DATA_DIR / "budgets.json"
EXPENSE_HEADERS = ["id", "username", "date", "category", "amount", "note"]
CATEGORIES = ["Food", "Transport", "University fees", "Shopping", "Other"]

def load_json(path, default):
    if not path.exists(): return default
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: return default

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f: json.dump(data, f, indent=4)
        return True
    except: return False

def load_expenses():
    if not EXPENSES_FILE.exists(): return []
    rows = []
    try:
        with open(EXPENSES_FILE, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                try:
                    r["amount"] = float(r["amount"])
                    rows.append(r)
                except: continue
    except: pass
    return rows

def write_expenses(expenses):
    try:
        with open(EXPENSES_FILE, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=EXPENSE_HEADERS)
            writer.writeheader()
            writer.writerows(expenses)
        return True
    except: return False

def user_login(username, password):
    users = load_json(USERS_FILE, {})
    return username in users and users[username]["password"] == password

def register_user(username, password):
    users = load_json(USERS_FILE, {})
    if username in users: return False
    users[username] = {"password": password}
    save_json(USERS_FILE, users)
    return True

def set_monthly_budget(username, amount):
    try:
        amount = float(amount)
        if amount <= 0: raise ValueError
    except: return False
    budgets = load_json(BUDGETS_FILE, {})
    budgets[username] = amount
    save_json(BUDGETS_FILE, budgets)
    return True

def add_record(username, category, amount, note=""):
    try:
        amount = float(amount)
        if amount <= 0: raise ValueError
    except: return False
    expenses = load_expenses()
    new_id = max([int(e["id"]) for e in expenses], default=0) + 1
    record = {"id": new_id, "username": username, "date": datetime.now().strftime("%Y-%m-%d"), "category": category, "amount": amount, "note": note}
    expenses.append(record)
    write_expenses(expenses)
    return True

def delete_record(username, record_id):
    expenses = load_expenses()
    new_expenses = [e for e in expenses if not (e["username"] == username and str(e["id"]) == str(record_id))]
    if len(new_expenses) == len(expenses): return False
    write_expenses(new_expenses)
    return True

def search_records(username, category=None, date=None):
    results = [e for e in load_expenses() if e["username"] == username]
    if category and category != "All": results = [e for e in results if e["category"] == category]
    if date: results = [e for e in results if e["date"] == date]
    return results

def generate_insights(df, budget):
    insights = []
    if df.empty:
        return ["Add some transactions to see your personalized insights!"]
    cat_totals = df.groupby("category")["amount"].sum()
    top_cat = cat_totals.idxmax()
    top_amt = cat_totals.max()
    insights.append(f"🏆 **Top Category:** You spent the most on **{top_cat}** (Rs. {top_amt:,.2f}).")
    
    date_totals = df.groupby("date")["amount"].sum()
    top_date = date_totals.idxmax()
    top_date_amt = date_totals.max()
    insights.append(f"📅 **Highest Spending Day:** You spent **Rs. {top_date_amt:,.2f}** on **{top_date}**.")
    
    if budget > 0:
        total_spent = df["amount"].sum()
        if total_spent > budget:
            insights.append(f"🚨 **Budget Alert:** You have exceeded your budget by **Rs. {total_spent - budget:,.2f}**!")
        elif total_spent == budget:
            insights.append(f"🛑 **Budget Finished:** You have used exactly your full budget of Rs. {budget:,.2f}.")
        elif total_spent > (budget * 0.8):
            insights.append(f"⚠️ **Budget Warning:** You have used {((total_spent/budget)*100):.1f}% of your budget. Slow down!")
        else:
            insights.append(f"✅ **On Track:** You have Rs. {budget - total_spent:,.2f} left for the month. Keep it up!")
    return insights


# ==========================================
# 2. FRONTEND LOGIC
# ==========================================
st.set_page_config(page_title="Student Cashly", page_icon="💰", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    [data-testid="stSidebar"] { background-color: #161A25; border-right: 1px solid #2E3345; }
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label { color: #FAFAFA !important; }

    [data-testid="stMetric"] {
        background-color: #161A25; border: 1px solid #2E3345; border-radius: 12px; padding: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    [data-testid="stMetricLabel"] { color: #A0AEC0 !important; font-size: 14px !important; }
    [data-testid="stMetricValue"] { color: #4ADE80 !important; font-size: 26px !important; }
    [data-testid="stMetricDelta"] { color: #4ADE80 !important; }

    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] { background-color: transparent; color: #A0AEC0; }
    .stTabs [aria-selected="true"] { color: #4ADE80 !important; border-bottom: 2px solid #4ADE80; }

    .insight-card {
        background-color: #161A25; border-left: 4px solid #4ADE80; padding: 15px; margin-bottom: 10px; border-radius: 5px; color: #FAFAFA;
    }
    label { color: #FAFAFA !important; }
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("<h1 style='color: #4ADE80;'>💰 Cashly</h1>", unsafe_allow_html=True)

if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.markdown("<h1 style='text-align: center;'>Welcome to Cashly</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        tab1, tab2 = st.tabs(["Login", "Register"])
        with tab1:
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("Login", use_container_width=True, type="primary"):
                if user_login(u, p):
                    st.session_state.user = u
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        with tab2:
            u = st.text_input("New Username")
            p = st.text_input("New Password", type="password")
            if st.button("Register", use_container_width=True, type="primary"):
                if register_user(u, p):
                    st.success("Registered! Please login.")
    st.stop()

user = st.session_state.user
if st.sidebar.button("Logout", use_container_width=True):
    st.session_state.user = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Monthly Budget Goal")
budgets = load_json(BUDGETS_FILE, {})
current_budget = budgets.get(user, 0)
new_budget = st.sidebar.number_input("Set Budget (Rs.)", value=float(current_budget), step=1000.0)
if st.sidebar.button("Update Budget", use_container_width=True):
    set_monthly_budget(user, new_budget)
    st.rerun()

current_month = datetime.now().strftime("%Y-%m")
user_expenses = [e for e in load_expenses() if e["username"] == user and e["date"].startswith(current_month)]
df = pd.DataFrame(user_expenses)

total_spent = df["amount"].sum() if not df.empty else 0
remaining = current_budget - total_spent if current_budget > 0 else 0

st.markdown(f"<h1>Welcome back, {user.capitalize()}! 💰</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #A0AEC0;'>Let's see how your money is behaving today...</p>", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Spent", f"Rs. {total_spent:,.0f}", "Across all categories")
col2.metric("Remaining", f"Rs. {remaining:,.0f}" if current_budget > 0 else "N/A", "This month")
col3.metric("Transactions", len(df) if not df.empty else 0, "Recent activity")
col4.metric("Top Category", df.groupby("category")["amount"].sum().idxmax() if not df.empty else "N/A", "Highest expense")

if current_budget > 0:
    percent_used = min((total_spent / current_budget), 1.0)
    st.markdown(f"**Monthly budget used: {percent_used*100:.0f}%**")
    st.progress(percent_used)
    
    if total_spent > current_budget:
        st.error(f"🚨 You have EXCEEDED your budget by Rs. {total_spent - current_budget:,.2f}!")
    elif total_spent == current_budget:
        st.warning("🛑 You have used exactly 100% of your budget.")
    elif percent_used >= 0.8:
        st.warning("⚠️ You have used over 80% of your budget.")

st.divider()

tab_over, tab_trends, tab_insights, tab_add, tab_history = st.tabs(
    ["📊 Overview", "📈 Trends", "💡 Insights", "➕ Add Transaction", "📋 History"]
)

# --- TAB 1: OVERVIEW ---
with tab_over:
    if not df.empty:
        col_chart1, col_chart2 = st.columns(2)
        df_grouped = df.groupby("category", as_index=False)["amount"].sum()
        
        with col_chart1:
            st.markdown("#### Spending by Category")
            fig1 = px.pie(df_grouped, values='amount', names='category', hole=0.6, 
                          color_discrete_sequence=['#4ADE80', '#3B82F6', '#EC4899', '#F59E0B', '#8B5CF6'])
            # FIXED: Force legend text to be white
            fig1.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white', 
                               legend=dict(font=dict(color="white")))
            st.plotly_chart(fig1, use_container_width=True)

        with col_chart2:
            st.markdown("#### Budget vs Spending")
            if current_budget > 0:
                balance_data = pd.DataFrame({"Type": ["Spent", "Remaining"], "amount": [total_spent, max(0, remaining)]})
                fig2 = px.pie(balance_data, values='amount', names='Type', hole=0.6, 
                              color="Type", color_discrete_map={"Spent": "#EC4899", "Remaining": "#4ADE80"})
                # FIXED: Force legend text to be white
                fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white', 
                                   legend=dict(font=dict(color="white")))
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Set a budget to see this chart.")
    else:
        st.info("No data yet.")

# --- TAB 2: TRENDS ---
with tab_trends:
    st.markdown("#### Spending Over Time")
    if not df.empty:
        df_dates = df.groupby("date", as_index=False)["amount"].sum().sort_values("date")
        fig_line = px.line(df_dates, x="date", y="amount", markers=True, 
                           labels={"date": "Date", "amount": "Amount (Rs.)"},
                           color_discrete_sequence=['#4ADE80'])
        fig_line.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                               font_color='white', xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#2E3345'))
        fig_line.update_traces(line=dict(width=4), marker=dict(size=10, color='#EC4899'))
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("Add transactions to see your daily spending trend.")

# --- TAB 3: INSIGHTS ---
with tab_insights:
    st.markdown("#### 💡 Smart Insights")
    insights = generate_insights(df, current_budget)
    for insight in insights:
        st.markdown(f"<div class='insight-card'>{insight}</div>", unsafe_allow_html=True)

# --- TAB 4: ADD TRANSACTION ---
with tab_add:
    with st.form("add_form"):
        cat = st.selectbox("Category", CATEGORIES)
        amt = st.number_input("Amount (Rs.)", min_value=1.0, step=100.0)
        note = st.text_input("Description / Note")
        submitted = st.form_submit_button("Add Expense", type="primary")
        if submitted:
            if add_record(user, cat, amt, note):
                st.success("Expense added successfully!")
                st.rerun()

# --- TAB 5: HISTORY ---
with tab_history:
    col_a, col_b = st.columns(2)
    search_cat = col_a.selectbox("Filter by Category", ["All"] + CATEGORIES)
    search_date = col_b.text_input("Filter by Date (YYYY-MM-DD)")
    
    results = search_records(user, search_cat, search_date)
    
    if results:
        df_hist = pd.DataFrame(results)[["id", "date", "category", "amount", "note"]]
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
        
        record_id = st.selectbox("Select Record ID to Delete", df_hist["id"].tolist())
        if st.button("Delete Record", type="primary"):
            if delete_record(user, record_id):
                st.success("Record deleted.")
                st.rerun()