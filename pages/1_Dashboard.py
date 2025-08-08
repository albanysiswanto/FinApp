import streamlit as st
import pandas as pd
from supabase_client import supabase
from datetime import datetime

st.set_page_config(page_title="Dashboard", layout="wide")

# --- Cek login ---
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("Silakan login terlebih dahulu.")
    st.switch_page("app.py")

user = st.session_state.user
user_id = user.id

st.success(f"Login sebagai: {st.session_state.user.email}")
st.title("📊 Dashboard Keuangan")

# --- Ambil data awal ---
transactions_res = supabase.table("transactions").select("*").eq("user_id", user_id).execute()
transactions_df = pd.DataFrame(transactions_res.data or [])

wallets_res = supabase.table("wallets").select("*").eq("user_id", user_id).execute()
wallets_df = pd.DataFrame(wallets_res.data or [])

# --- Ringkasan Bulan Ini ---
if not transactions_df.empty:
    transactions_df["date"] = pd.to_datetime(transactions_df["date"])
    bulan_ini = datetime.now().month
    tahun_ini = datetime.now().year

    bulan_ini_df = transactions_df[
        (transactions_df["date"].dt.month == bulan_ini) &
        (transactions_df["date"].dt.year == tahun_ini)
    ]

    total_pemasukan = bulan_ini_df[bulan_ini_df["type"] == "pemasukan"]["amount"].sum()
    total_pengeluaran = bulan_ini_df[bulan_ini_df["type"] == "pengeluaran"]["amount"].sum()
    saldo_total = wallets_df["balance"].sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Pemasukan Bulan Ini", f"Rp {total_pemasukan:,.0f}")
    col2.metric("Pengeluaran Bulan Ini", f"Rp {total_pengeluaran:,.0f}")
    col3.metric("Saldo Total", f"Rp {saldo_total:,.0f}")

    chart_data = bulan_ini_df.groupby("type")["amount"].sum().reset_index()
    st.subheader("Grafik Pemasukan vs Pengeluaran")
    st.bar_chart(chart_data.set_index("type"))
else:
    st.info("Belum ada transaksi untuk ditampilkan di dashboard.")

# --- Ambil daftar kolaborasi ---
collabs = supabase.table("collaborations") \
    .select("*") \
    .or_(f"owner_id.eq.{user.id},collab_id.eq.{user.id}") \
    .eq("status", "accepted") \
    .execute()

options = [("me", "Data Saya")]
for c in collabs.data:
    if c["owner_id"] == user.id:
        options.append((c["collab_id"], f"Data {c['collab_email']}"))
    else:
        options.append((c["owner_id"], f"Data {c['owner_email']}"))

selected_user_id = st.selectbox(
    "Pilih data yang ingin dilihat",
    [o[0] for o in options],
    format_func=lambda x: dict(options)[x]
)

view_user_id = user.id if selected_user_id == "me" else selected_user_id

# =========================
# DOMPET
# =========================
wallets = supabase.table("wallets").select("*").eq("user_id", view_user_id).execute()
st.subheader("💼 Dompet")
if wallets.data:
    st.dataframe(wallets.data)
else:
    st.info("Tidak ada dompet ditemukan.")

# =========================
# TRANSAKSI (dengan filter)
# =========================
transactions = supabase.table("transactions").select("*").eq("user_id", view_user_id).execute()
st.subheader("📜 Transaksi")
if transactions.data:
    df_trans = pd.DataFrame(transactions.data)
    df_trans["date"] = pd.to_datetime(df_trans["date"])

    with st.expander("🔍 Filter Transaksi"):
        col1, col2 = st.columns(2)
        start_date = col1.date_input("Dari tanggal", value=df_trans["date"].min())
        end_date = col2.date_input("Sampai tanggal", value=df_trans["date"].max())

        type_filter = st.multiselect("Jenis Transaksi", options=df_trans["type"].unique().tolist())
        wallet_filter = st.multiselect("Dompet", options=df_trans["wallet_id"].unique().tolist())

    filtered_df = df_trans[
        (df_trans["date"].dt.date >= start_date) &
        (df_trans["date"].dt.date <= end_date)
    ]

    if type_filter:
        filtered_df = filtered_df[filtered_df["type"].isin(type_filter)]
    if wallet_filter:
        filtered_df = filtered_df[filtered_df["wallet_id"].isin(wallet_filter)]

    st.dataframe(filtered_df)
else:
    st.info("Tidak ada transaksi ditemukan.")

# =========================
# UTANG / PIUTANG (dengan filter)
# =========================
debts = supabase.table("debts").select("*").eq("user_id", view_user_id).execute()
st.subheader("💳 Utang / Piutang")
if debts.data:
    df_debts = pd.DataFrame(debts.data)

    # Pastikan kolom tanggal menjadi datetime
    df_debts["created_at"] = pd.to_datetime(df_debts["created_at"], errors="coerce")
    df_debts["due_date"] = pd.to_datetime(df_debts["due_date"], errors="coerce")

    with st.expander("🔍 Filter Utang/Piutang"):
        col1, col2 = st.columns(2)
        start_date = col1.date_input(
            "Dari tanggal",
            value=df_debts["created_at"].min().date() if not df_debts.empty else None,
            key="debt_start_date"
        )
        end_date = col2.date_input(
            "Sampai tanggal",
            value=df_debts["due_date"].max().date() if not df_debts.empty else None,
            key="debt_end_date"
        )

        status_filter = st.multiselect(
            "Status",
            options=df_debts["status"].dropna().unique().tolist(),
            key="debt_status_filter"
        )

        type_filter = st.multiselect(
            "Tipe",
            options=df_debts["type"].dropna().unique().tolist(),
            key="debt_type_filter"
        )

    # Filtering data
    filtered_debts = df_debts[
        (df_debts["created_at"].dt.date >= start_date) &
        (df_debts["due_date"].dt.date <= end_date)
    ]

    if status_filter:
        filtered_debts = filtered_debts[filtered_debts["status"].isin(status_filter)]
    if type_filter:
        filtered_debts = filtered_debts[filtered_debts["type"].isin(type_filter)]

    st.dataframe(filtered_debts)
else:
    st.info("Tidak ada data utang/piutang ditemukan.")

# =========================
# Logout
# =========================
if st.button("Logout"):
    supabase.auth.sign_out()
    st.session_state.user = None
    st.switch_page("app.py")
