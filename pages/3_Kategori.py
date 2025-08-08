import streamlit as st
from supabase_client import supabase
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Kategori", layout="wide")

# Pastikan user login
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("Silakan login terlebih dahulu.")
    st.switch_page("app.py")


user_id = st.session_state.user.id

st.title("🏷️ Kelola Kategori")

# --- Ambil data kategori ---
categories_data = supabase.table("categories").select("*").eq("user_id", user_id).execute()
categories_df = pd.DataFrame(categories_data.data)

# --- Form Tambah Kategori ---
with st.form("add_category_form"):
    name = st.text_input("Nama Kategori")
    cat_type = st.selectbox("Jenis Kategori", options=["pemasukan", "pengeluaran"])
    submitted = st.form_submit_button("Tambah Kategori")

    if submitted:
        if not name.strip():
            st.error("Nama kategori tidak boleh kosong.")
        else:
            try:
                supabase.table("categories").insert({
                    "user_id": user_id,
                    "name": name.strip(),
                    "type": cat_type,
                    "created_at": datetime.utcnow().isoformat()
                }).execute()
                st.success("Kategori berhasil ditambahkan!")
                st.rerun()
            except Exception as e:
                st.error(f"Gagal menambahkan kategori: {e}")

# --- Tampilkan daftar kategori ---
if not categories_df.empty:
    st.subheader("Daftar Kategori")
    st.dataframe(categories_df[["name", "type", "created_at"]])

    # --- Hapus Kategori ---
    delete_id = st.selectbox("Pilih Kategori untuk Dihapus", categories_df["id"], format_func=lambda x: categories_df.loc[categories_df["id"] == x, "name"].iloc[0])
    if st.button("Hapus Kategori"):
        try:
            supabase.table("categories").delete().eq("id", delete_id).execute()
            st.success("Kategori berhasil dihapus!")
            st.rerun()
        except Exception as e:
            st.error(f"Gagal menghapus kategori: {e}")
else:
    st.info("Belum ada kategori. Silakan tambah kategori terlebih dahulu.")
