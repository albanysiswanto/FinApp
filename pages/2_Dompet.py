import streamlit as st
from supabase_client import supabase
import pandas as pd

st.set_page_config(page_title="Dompet", layout="wide")

# Pastikan user sudah login
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("Silakan login terlebih dahulu.")
    st.switch_page("app.py")

user_id = st.session_state.user.id

st.title("💰 Kelola Dompet")

# --- Tambah Dompet ---
with st.form("add_wallet_form"):
    name = st.text_input("Nama Dompet")
    balance = st.number_input("Saldo Awal", min_value=0.0, step=1000.0)
    submitted = st.form_submit_button("Tambah Dompet")

    if submitted:
        try:
            supabase.table("wallets").insert({
                "user_id": user_id,
                "name": name,
                "balance": balance
            }).execute()
            st.success("Dompet berhasil ditambahkan!")
            st.rerun()
        except Exception as e:
            st.error(f"Gagal menambahkan dompet: {e}")

# --- Ambil Data Dompet ---
wallets_data = supabase.table("wallets").select("*").eq("user_id", user_id).execute()
wallets_df = pd.DataFrame(wallets_data.data)

if not wallets_df.empty:
    st.subheader("Daftar Dompet")
    st.dataframe(wallets_df[["name", "balance", "created_at"]])

    # Buat mapping id → nama
    wallet_options = dict(zip(wallets_df["id"], wallets_df["name"]))

    # --- Hapus Dompet ---
    delete_id = st.selectbox(
        "Pilih Dompet untuk Dihapus",
        options=wallet_options.keys(),
        format_func=lambda x: wallet_options[x]
    )
    if st.button("Hapus Dompet"):
        supabase.table("wallets").delete().eq("id", delete_id).execute()
        st.success(f"Dompet '{wallet_options[delete_id]}' berhasil dihapus!")
        st.rerun()

    # --- Update Saldo ---
    st.subheader("Update Saldo Dompet")
    update_id = st.selectbox(
        "Pilih Dompet untuk Update",
        options=wallet_options.keys(),
        format_func=lambda x: wallet_options[x]
    )
    new_balance = st.number_input("Saldo Baru", min_value=0.0, step=1000.0)
    if st.button("Update Saldo"):
        supabase.table("wallets").update({"balance": new_balance}).eq("id", update_id).execute()
        st.success(f"Saldo dompet '{wallet_options[update_id]}' berhasil diupdate!")
        st.rerun()
else:
    st.info("Belum ada dompet. Silakan tambahkan dompet terlebih dahulu.")

