# pages/2_Transaksi.py
import streamlit as st
from supabase_client import supabase
import pandas as pd
from datetime import date

st.set_page_config(page_title="Transaksi", layout="wide")

# --- Fungsi format Rupiah ---
def format_rupiah(x):
    return f"Rp {x:,.0f}".replace(",", ".")

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

# --- Helper ---
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

# --- Input Tambah Transaksi ---
st.subheader("Tambah Transaksi")

wallet_id = st.selectbox(
    "Pilih Dompet",
    options=list(wallet_options.keys()),
    format_func=lambda x: wallet_options[x],
    key="wallet_id"
)

trans_type = st.selectbox(
    "Jenis Transaksi",
    options=["", "pemasukan", "pengeluaran"],
    format_func=lambda x: "Pilih..." if x == "" else x.capitalize(),
    key="trans_type"
)

if trans_type:
    filtered_categories = categories_df[categories_df["type"] == trans_type]
    category_options_filtered = dict(zip(filtered_categories["id"], filtered_categories["name"]))
    category_id = st.selectbox(
        "Pilih Kategori",
        options=list(category_options_filtered.keys()),
        format_func=lambda x: category_options_filtered[x],
        key="category_id"
    )
else:
    category_id = None
    st.info("Silakan pilih jenis transaksi terlebih dahulu.")

amount = st.number_input("Jumlah", min_value=0.0, step=1000.0, key="amount")
description = st.text_area("Deskripsi", key="description")
trans_date = st.date_input("Tanggal", value=date.today(), key="trans_date")

if st.button("Tambah Transaksi"):
    if not trans_type or not category_id:
        st.error("Jenis transaksi dan kategori harus dipilih.")
    else:
        try:
            payload = {
                "user_id": user_id,
                "wallet_id": wallet_id,
                "category_id": category_id,
                "amount": float(amount),
                "type": trans_type,
                "description": description,
                "date": trans_date.isoformat()
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

if type_filter == "Semua":
    category_filter_df = categories_df
else:
    category_filter_df = categories_df[categories_df["type"] == type_filter]

category_filter_options = dict(zip(category_filter_df["id"], category_filter_df["name"]))

wallet_filter = st.selectbox(
    "Pilih Dompet",
    options=["Semua"] + list(wallet_options.keys()),
    format_func=lambda x: wallet_options[x] if x != "Semua" else "Semua"
)
category_filter = st.selectbox(
    "Pilih Kategori",
    options=["Semua"] + list(category_filter_options.keys()),
    format_func=lambda x: category_filter_options[x] if x != "Semua" else "Semua"
)

# --- Ambil data transaksi ---
query = supabase.table("transactions").select("*").eq("user_id", user_id)
if type_filter != "Semua":
    query = query.eq("type", type_filter)
if wallet_filter != "Semua":
    query = query.eq("wallet_id", wallet_filter)
if category_filter != "Semua":
    query = query.eq("category_id", category_filter)

transactions_res = query.order("date", desc=True).execute()
transactions_df = pd.DataFrame(transactions_res.data or [])

if not transactions_df.empty:
    transactions_df["date"] = pd.to_datetime(transactions_df["date"])
    transactions_df = transactions_df[
        (transactions_df["date"].dt.month == month_filter) &
        (transactions_df["date"].dt.year == year_filter)
    ]

# --- Tampilkan Transaksi ---
if not transactions_df.empty:
    transactions_df["wallet_name"] = transactions_df["wallet_id"].map(wallet_options)
    transactions_df["category_name"] = transactions_df["category_id"].map(category_options)
    transactions_df = transactions_df.sort_values(by=["date", "created_at"], ascending=[False, False])

    st.subheader("📋 Daftar Transaksi")

    for _, row in transactions_df.iterrows():
        with st.container():
            st.markdown(
                f"""
                <div style="border:1px solid #ddd; border-radius:8px; padding:10px; margin-bottom:10px;">
                    <b>{row['description'] or '-'}</b> - {row['wallet_name']}<br>
                    <b>{format_rupiah(row['amount'])}</b><br>
                    <span style="color:{'green' if row['type']=='pemasukan' else 'red'};">
                        {row['category_name']} ({row['type']})
                    </span><br>
                    <small>{row['date'].strftime('%Y-%m-%d')}</small>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Tombol hapus langsung
            if st.button("🗑️ Hapus", key=f"hapus_{row['id']}"):
                try:
                    trans = get_transaction_from_db(row["id"])
                    if trans:
                        wallet_balance = get_wallet_balance_from_db(trans["wallet_id"])
                        amt = float(trans["amount"] or 0)

                        # Kembalikan saldo
                        if trans["type"] == "pemasukan":
                            new_balance = wallet_balance - amt
                        else:
                            new_balance = wallet_balance + amt

                        # Update saldo
                        supabase.table("wallets").update(
                            {"balance": new_balance}
                        ).eq("id", trans["wallet_id"]).execute()

                        # Hapus transaksi
                        supabase.table("transactions").delete().eq("id", row["id"]).execute()

                        st.success("Transaksi berhasil dihapus dan saldo dikembalikan.")
                        st.rerun()

                except Exception as e:
                    st.error(f"Gagal menghapus transaksi: {e}")
else:
    st.info("Belum ada transaksi.")
