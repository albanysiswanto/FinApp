import streamlit as st
import pandas as pd
from supabase_client import supabase
from datetime import datetime

st.set_page_config(page_title="Dashboard", layout="wide")

# --- Fungsi format Rupiah ---
def format_rupiah(x):
    return f"Rp {x:,.0f}".replace(",", ".")

# --- Cek login ---
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("Silakan login terlebih dahulu.")
    st.stop()  # hentikan eksekusi sampai login berhasil

user = st.session_state.user
user_id = user.id

st.success(f"Login sebagai: {user.email}")
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
    col1.metric("Pemasukan Bulan Ini", format_rupiah(total_pemasukan))
    col2.metric("Pengeluaran Bulan Ini", format_rupiah(total_pengeluaran))
    col3.metric("Saldo Total", format_rupiah(saldo_total))

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
        options.append((c["collab_id"], f"Data {c['requester_email']}"))
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
wallets = supabase.table("wallets").select("name, balance").eq("user_id", view_user_id).execute()
st.subheader("💼 Dompet")
if wallets.data:
    st.dataframe(wallets.data)
else:
    st.info("Tidak ada dompet ditemukan.")

## =========================
# TRANSAKSI (dengan filter)
# =========================
transactions = supabase.table("transactions").select("user_id, wallet_id, category_id, amount, type, description, date").eq("user_id", view_user_id).execute()
st.subheader("📜 Transaksi")
wallets_res = supabase.table("wallets").select("id, name").eq("user_id", view_user_id).execute()
wallets_df = pd.DataFrame(wallets_res.data or [])

categories_res = supabase.table("categories").select("id, name").eq("user_id", view_user_id).execute()
categories_df = pd.DataFrame(categories_res.data or [])

if transactions.data:
    df_trans = pd.DataFrame(transactions.data)
    df_trans["date"] = pd.to_datetime(df_trans["date"]).dt.date

    # Merge dengan wallet names
    df_trans = df_trans.merge(wallets_df[['id', 'name']], left_on='wallet_id', right_on='id', how='left')
    df_trans = df_trans.rename(columns={'name': 'wallet_name'}).drop(columns=['id'])

    # Merge dengan category names
    df_trans = df_trans.merge(categories_df[['id', 'name']], left_on='category_id', right_on='id', how='left')
    df_trans = df_trans.rename(columns={'name': 'category_name'}).drop(columns=['id'])

    with st.expander("🔍 Filter Transaksi"):
        col1, col2 = st.columns(2)
        start_date = col1.date_input("Dari tanggal", value=df_trans["date"].min())
        end_date = col2.date_input("Sampai tanggal", value=df_trans["date"].max())

        type_filter = st.multiselect("Jenis Transaksi", options=df_trans["type"].unique().tolist())
        wallet_filter = st.multiselect("Dompet", options=df_trans["wallet_name"].unique().tolist())

    filtered_df = df_trans[
        (df_trans["date"] >= start_date) &
        (df_trans["date"] <= end_date)
    ]

    if type_filter:
        filtered_df = filtered_df[filtered_df["type"].isin(type_filter)]
    if wallet_filter:
        filtered_df = filtered_df[filtered_df["wallet_name"].isin(wallet_filter)]

    # Format kolom amount jadi Rupiah langsung di filtered_df
    filtered_df["amount"] = filtered_df["amount"].apply(format_rupiah)

    # Tampilkan dengan kolom nama, bisa pilih kolom mana saja
    st.dataframe(filtered_df[[
        "date", "wallet_name", "category_name", "amount", "type", "description"
    ]])
else:
    st.info("Tidak ada transaksi ditemukan.")

# =========================
# UTANG / PIUTANG (dengan filter)
# =========================
debts = supabase.table("debts").select("name, amount, type, description, due_date, created_at, status").eq("user_id", view_user_id).execute()
st.subheader("💳 Utang / Piutang")
if debts.data:
    df_debts = pd.DataFrame(debts.data)

    # Pastikan kolom tanggal menjadi datetime
    df_debts["created_at"] = pd.to_datetime(df_debts["created_at"], errors="coerce").dt.date
    df_debts["due_date"] = pd.to_datetime(df_debts["due_date"], errors="coerce").dt.date

    with st.expander("🔍 Filter Utang/Piutang"):
        col1, col2 = st.columns(2)
        start_date = col1.date_input(
            "Dari tanggal",
            value=df_debts["created_at"].min() if not df_debts.empty else None,
            key="debt_start_date"
        )
        end_date = col2.date_input(
            "Sampai tanggal",
            value=df_debts["due_date"].max() if not df_debts.empty else None,
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
        (df_debts["created_at"] >= start_date) &
        (df_debts["due_date"] <= end_date)
    ]

    if status_filter:
        filtered_debts = filtered_debts[filtered_debts["status"].isin(status_filter)]
    if type_filter:
        filtered_debts = filtered_debts[filtered_debts["type"].isin(type_filter)]
        
    # Format kolom amount jadi Rupiah langsung di filtered_df
    filtered_debts["amount"] = filtered_debts["amount"].apply(format_rupiah)

    st.dataframe(filtered_debts[["name", "amount", "type", "description", "status", "created_at","due_date", ]])
else:
    st.info("Tidak ada data utang/piutang ditemukan.")

# =========================
# Logout
# =========================
if st.button("Logout"):
    supabase.auth.sign_out()
    st.session_state.user = None
    st.switch_page("app.py")
