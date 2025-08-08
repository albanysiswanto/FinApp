# pages/2_Transaksi.py
import streamlit as st
from supabase_client import supabase
import pandas as pd
from datetime import date

st.set_page_config(page_title="Transaksi", layout="wide")

# Pastikan user login
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("Silakan login terlebih dahulu.")
    st.switch_page("app.py")

user_id = st.session_state.user.id

st.title("📜 Kelola Transaksi")

# Ambil data dompet & kategori
wallets_res = supabase.table("wallets").select("*").eq("user_id", user_id).execute()
categories_res = supabase.table("categories").select("*").eq("user_id", user_id).execute()

wallets_df = pd.DataFrame(wallets_res.data or [])
categories_df = pd.DataFrame(categories_res.data or [])

if wallets_df.empty:
    st.error("⚠️ Kamu belum punya dompet. Buat dompet dulu di halaman Dompet.")
    st.stop()

if categories_df.empty:
    st.error("⚠️ Kamu belum punya kategori. Buat kategori dulu di halaman Kategori.")
    st.stop()

# Mapping untuk selectbox
wallet_options = dict(zip(wallets_df["id"], wallets_df["name"]))
category_options = dict(zip(categories_df["id"], categories_df["name"]))

def get_wallet_balance_from_db(wid):
    res = supabase.table("wallets").select("balance").eq("id", wid).single().execute()
    data = res.data
    if data and "balance" in data:
        try:
            return float(data["balance"])
        except:
            return 0.0
    return 0.0

def get_transaction_from_db(tid):
    res = supabase.table("transactions").select("*").eq("id", tid).single().execute()
    return res.data

# --- Form Tambah Transaksi ---
with st.form("add_transaction_form"):
    wallet_id = st.selectbox("Pilih Dompet", options=list(wallet_options.keys()),
                              format_func=lambda x: wallet_options[x])
    category_id = st.selectbox("Pilih Kategori", options=list(category_options.keys()),
                                format_func=lambda x: category_options[x])
    trans_type = st.selectbox("Jenis Transaksi", options=["pemasukan", "pengeluaran"])
    amount = st.number_input("Jumlah", min_value=0.0, step=1000.0)
    description = st.text_area("Deskripsi")
    trans_date = st.date_input("Tanggal", value=date.today())

    submitted = st.form_submit_button("Tambah Transaksi")
    if submitted:
        try:
            date_iso = trans_date.isoformat()
            payload = {
                "user_id": user_id,
                "wallet_id": wallet_id,
                "category_id": category_id,
                "amount": float(amount),
                "type": trans_type,
                "description": description,
                "date": date_iso
            }

            supabase.table("transactions").insert(payload).execute()

            wallet_balance = get_wallet_balance_from_db(wallet_id)
            if trans_type == "pemasukan":
                new_balance = wallet_balance + float(amount)
            else:
                new_balance = wallet_balance - float(amount)

            supabase.table("wallets").update({"balance": new_balance}).eq("id", wallet_id).execute()

            st.success("Transaksi berhasil ditambahkan!")
            st.rerun()
        except Exception as e:
            st.error(f"Gagal menambahkan transaksi: {e}")

# --- Filter Transaksi ---
st.subheader("Filter Transaksi")

month_filter = st.selectbox(
    "Pilih Bulan",
    options=list(range(1, 13)),
    format_func=lambda x: date(1900, x, 1).strftime("%B"),
    index=date.today().month - 1
)
year_filter = st.number_input(
    "Pilih Tahun",
    min_value=2000,
    max_value=date.today().year,
    value=date.today().year
)

type_filter = st.selectbox("Jenis Transaksi", options=["Semua", "pemasukan", "pengeluaran"])

wallet_filter = st.selectbox(
    "Pilih Dompet",
    options=["Semua"] + list(wallet_options.keys()),
    format_func=lambda x: wallet_options[x] if x != "Semua" else "Semua"
)

category_filter = st.selectbox(
    "Pilih Kategori",
    options=["Semua"] + list(category_options.keys()),
    format_func=lambda x: category_options[x] if x != "Semua" else "Semua"
)

# --- Ambil data transaksi dari database ---
query = supabase.table("transactions").select("*").eq("user_id", user_id)

if type_filter != "Semua":
    query = query.eq("type", type_filter)
if wallet_filter != "Semua":
    query = query.eq("wallet_id", wallet_filter)
if category_filter != "Semua":
    query = query.eq("category_id", category_filter)

transactions_res = query.order("date", desc=True).execute()
transactions_df = pd.DataFrame(transactions_res.data or [])

# Filter bulan & tahun di sisi Python
if not transactions_df.empty:
    transactions_df["date"] = pd.to_datetime(transactions_df["date"])
    transactions_df = transactions_df[
        (transactions_df["date"].dt.month == month_filter) &
        (transactions_df["date"].dt.year == year_filter)
    ]

if not transactions_df.empty:
    transactions_df["wallet_name"] = transactions_df["wallet_id"].map(wallet_options)
    transactions_df["category_name"] = transactions_df["category_id"].map(category_options)

    st.subheader("Daftar Transaksi")
    st.dataframe(transactions_df[["date", "wallet_name", "category_name", "type", "amount", "description"]])

    label_map = {}
    for _, row in transactions_df.iterrows():
        label_map[row["id"]] = f"{row['date'].strftime('%Y-%m-%d')} | {row['wallet_name']} | {row['category_name']} | {row['type']} | {row['amount']}"

    delete_id = st.selectbox(
        "Pilih Transaksi untuk Dihapus",
        options=list(label_map.keys()),
        format_func=lambda x: label_map[x]
    )

    if st.button("Hapus Transaksi"):
        try:
            trans = get_transaction_from_db(delete_id)
            if not trans:
                st.error("Transaksi tidak ditemukan.")
            else:
                wallet_balance = get_wallet_balance_from_db(trans["wallet_id"])
                amt = float(trans["amount"])
                if trans["type"] == "pemasukan":
                    new_balance = wallet_balance - amt
                else:
                    new_balance = wallet_balance + amt

                supabase.table("wallets").update({"balance": new_balance}).eq("id", trans["wallet_id"]).execute()
                supabase.table("transactions").delete().eq("id", delete_id).execute()

                st.success("Transaksi berhasil dihapus dan saldo dikembalikan.")
                st.rerun()
        except Exception as e:
            st.error(f"Gagal menghapus transaksi: {e}")
else:
    st.info("Belum ada transaksi.")
