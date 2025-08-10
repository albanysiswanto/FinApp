import streamlit as st
import pandas as pd
from supabase_client import supabase
from datetime import datetime

# =========================
# CONFIGURASI DASAR
# =========================
st.set_page_config(page_title="Dashboard Keuangan", layout="wide")

# CSS Kustom
st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: 'Segoe UI', sans-serif;
    }
    .main {
        background-color: #f8f9fa;
        padding: 1rem;
    }
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        text-align: center;
        margin-bottom: 10px;
    }
    .metric-card h4 {
        color: #000000;
    }
    .stDataFrame table {
        border-radius: 8px;
        overflow: hidden;
    }
    div.stButton > button {
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
        font-weight: bold;
    }
    @media (max-width: 768px) {
        .metric-card {
            width: 100% !important;
            margin-bottom: 1rem;
        }
        .stDataFrame {
            overflow-x: auto !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# =========================
# FUNGSI
# =========================
def format_rupiah(x):
    return f"Rp {x:,.0f}".replace(",", ".")

# =========================
# CEK LOGIN
# =========================
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("⚠️ Silakan login terlebih dahulu.")
    st.stop()

user = st.session_state.user
user_id = user.id
st.success(f"✅ Login sebagai: **{user.email}**")
st.markdown("## 📊 Dashboard Keuangan")

# =========================
# AMBIL DATA
# =========================
transactions_df = pd.DataFrame(
    supabase.table("transactions").select("*").eq("user_id", user_id).execute().data or []
)
wallets_df = pd.DataFrame(
    supabase.table("wallets").select("*").eq("user_id", user_id).execute().data or []
)

# =========================
# RINGKASAN BULAN INI
# =========================
if not transactions_df.empty:
    transactions_df["date"] = pd.to_datetime(transactions_df["date"])
    now = datetime.now()
    bulan_ini_df = transactions_df[
        (transactions_df["date"].dt.month == now.month) &
        (transactions_df["date"].dt.year == now.year)
    ]

    total_pemasukan = bulan_ini_df.loc[bulan_ini_df["type"] == "pemasukan", "amount"].sum()
    total_pengeluaran = bulan_ini_df.loc[bulan_ini_df["type"] == "pengeluaran", "amount"].sum()
    saldo_total = wallets_df["balance"].sum()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='metric-card'><h4>Pemasukan Bulan Ini</h4><h2 style='color:green'>{format_rupiah(total_pemasukan)}</h2></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='metric-card'><h4>Pengeluaran Bulan Ini</h4><h2 style='color:red'>{format_rupiah(total_pengeluaran)}</h2></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='metric-card'><h4>Saldo Total</h4><h2 style='color:blue'>{format_rupiah(saldo_total)}</h2></div>", unsafe_allow_html=True)

    st.subheader("📈 Grafik Pemasukan vs Pengeluaran")
    chart_data = bulan_ini_df.groupby("type")["amount"].sum().reset_index()
    st.bar_chart(chart_data.set_index("type"))
else:
    st.info("💡 Belum ada transaksi untuk ditampilkan di dashboard.")

# =========================
# PILIH DATA KOLABORASI
# =========================
collabs = supabase.table("collaborations") \
    .select("*") \
    .or_(f"owner_id.eq.{user.id},collab_id.eq.{user.id}") \
    .eq("status", "accepted") \
    .execute()

options = [("me", "Data Saya")]
for c in collabs.data:
    if c["owner_id"] == user.id:
        options.append((c["collab_id"], f"Data {c['requester_email']}"))
    else:
        options.append((c["owner_id"], f"Data {c['owner_email']}"))

selected_user_id = st.selectbox(
    "🔄 Pilih data yang ingin dilihat",
    [o[0] for o in options],
    format_func=lambda x: dict(options)[x]
)
view_user_id = user.id if selected_user_id == "me" else selected_user_id

# =========================
# DOMPET
# =========================
wallets_data = supabase.table("wallets").select("name, balance").eq("user_id", view_user_id).execute().data
with st.expander("💼 Dompet", expanded=True):
    if wallets_data:
        st.dataframe(wallets_data)
    else:
        st.info("Tidak ada dompet ditemukan.")

# =========================
# TRANSAKSI
# =========================
transactions_data = supabase.table("transactions").select("user_id, wallet_id, category_id, amount, type, description, date").eq("user_id", view_user_id).execute().data
wallets_df = pd.DataFrame(supabase.table("wallets").select("id, name").eq("user_id", view_user_id).execute().data or [])
categories_df = pd.DataFrame(supabase.table("categories").select("id, name").eq("user_id", view_user_id).execute().data or [])

with st.expander("📜 Transaksi", expanded=True):
    if transactions_data:
        df_trans = pd.DataFrame(transactions_data)
        df_trans["date"] = pd.to_datetime(df_trans["date"]).dt.date

        df_trans = df_trans.merge(wallets_df[['id', 'name']], left_on='wallet_id', right_on='id', how='left') \
                           .rename(columns={'name': 'wallet_name'}).drop(columns=['id'])
        df_trans = df_trans.merge(categories_df[['id', 'name']], left_on='category_id', right_on='id', how='left') \
                           .rename(columns={'name': 'category_name'}).drop(columns=['id'])

        col1, col2 = st.columns(2)
        start_date = col1.date_input("📅 Dari tanggal", value=df_trans["date"].min())
        end_date = col2.date_input("📅 Sampai tanggal", value=df_trans["date"].max())

        type_filter = st.multiselect("🔍 Jenis Transaksi", options=df_trans["type"].unique().tolist())
        wallet_filter = st.multiselect("💼 Dompet", options=df_trans["wallet_name"].unique().tolist())

        filtered_df = df_trans[(df_trans["date"] >= start_date) & (df_trans["date"] <= end_date)]
        if type_filter:
            filtered_df = filtered_df[filtered_df["type"].isin(type_filter)]
        if wallet_filter:
            filtered_df = filtered_df[filtered_df["wallet_name"].isin(wallet_filter)]

        filtered_df["amount"] = filtered_df["amount"].apply(format_rupiah)
        st.dataframe(filtered_df[["date", "wallet_name", "category_name", "amount", "type", "description"]])
    else:
        st.info("Tidak ada transaksi ditemukan.")

# =========================
# UTANG / PIUTANG
# =========================
debts_data = supabase.table("debts").select("name, amount, type, description, due_date, created_at, status").eq("user_id", view_user_id).execute().data
with st.expander("💳 Utang / Piutang", expanded=True):
    if debts_data:
        df_debts = pd.DataFrame(debts_data)
        df_debts["created_at"] = pd.to_datetime(df_debts["created_at"], errors="coerce").dt.date
        df_debts["due_date"] = pd.to_datetime(df_debts["due_date"], errors="coerce").dt.date

        col1, col2 = st.columns(2)
        start_date = col1.date_input("📅 Dari tanggal", value=df_debts["created_at"].min(), key="debt_start_date")
        end_date = col2.date_input("📅 Sampai tanggal", value=df_debts["due_date"].max(), key="debt_end_date")

        status_filter = st.multiselect("🛠 Status", options=df_debts["status"].dropna().unique().tolist(), key="debt_status_filter")
        type_filter = st.multiselect("📌 Tipe", options=df_debts["type"].dropna().unique().tolist(), key="debt_type_filter")

        filtered_debts = df_debts[(df_debts["created_at"] >= start_date) & (df_debts["due_date"] <= end_date)]
        if status_filter:
            filtered_debts = filtered_debts[filtered_debts["status"].isin(status_filter)]
        if type_filter:
            filtered_debts = filtered_debts[filtered_debts["type"].isin(type_filter)]

        filtered_debts["amount"] = filtered_debts["amount"].apply(format_rupiah)
        st.dataframe(filtered_debts[["name", "amount", "type", "description", "status", "created_at", "due_date"]])
    else:
        st.info("Tidak ada data utang/piutang ditemukan.")

# =========================
# LOGOUT BUTTON
# =========================
st.markdown("---")
if st.button("🚪 Logout"):
    supabase.auth.sign_out()
    st.session_state.user = None
    st.switch_page("app.py")
