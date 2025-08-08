import streamlit as st
from supabase_client import supabase
import pandas as pd
from datetime import date

st.set_page_config(page_title="Utang & Piutang", layout="wide")

# Cek login
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("Silakan login terlebih dahulu.")
    st.switch_page("app.py")

user_id = st.session_state.user.id
st.title("💰 Kelola Utang & Piutang")

# --- Form tambah utang/piutang ---
with st.form("add_debt_form"):
    name = st.text_input("Nama Pihak Terkait")
    amount = st.number_input("Jumlah", min_value=0.0, step=1000.0)
    debt_type = st.selectbox("Jenis", ["utang", "piutang"])
    description = st.text_area("Deskripsi")
    due_date = st.date_input("Jatuh Tempo", value=date.today())
    
    submitted = st.form_submit_button("Tambah")
    if submitted:
        try:
            payload = {
                "user_id": user_id,
                "name": name,
                "amount": float(amount),
                "type": debt_type,
                "description": description,
                "due_date": due_date.isoformat(),
                "status": "belum lunas"
            }
            supabase.table("debts").insert(payload).execute()
            st.success("Data berhasil ditambahkan!")
            st.rerun()
        except Exception as e:
            st.error(f"Gagal menambahkan data: {e}")

# --- Ambil data utang/piutang ---
debts_res = supabase.table("debts").select("*").eq("user_id", user_id).order("due_date").execute()
debts_df = pd.DataFrame(debts_res.data or [])

if not debts_df.empty:
    debts_df["due_date"] = pd.to_datetime(debts_df["due_date"]).dt.date

    # --- Filter ---
    st.subheader("🔍 Filter")
    col_f1, col_f2 = st.columns(2)

    # Filter bulan & tahun
    with col_f1:
        tahun_tersedia = sorted(list({d.year for d in debts_df["due_date"]}), reverse=True)
        tahun_filter = st.selectbox("Tahun", ["Semua"] + tahun_tersedia)

    with col_f2:
        bulan_filter = st.selectbox("Bulan", ["Semua"] + list(range(1, 13)),
                                    format_func=lambda x: x if x == "Semua" else date(2000, x, 1).strftime("%B"))

    # Filter status
    status_filter = st.selectbox("Status", ["Semua", "lunas", "belum lunas"])

    # Terapkan filter
    filtered_df = debts_df.copy()
    if tahun_filter != "Semua":
        filtered_df = filtered_df[filtered_df["due_date"].apply(lambda d: d.year == tahun_filter)]
    if bulan_filter != "Semua":
        filtered_df = filtered_df[filtered_df["due_date"].apply(lambda d: d.month == bulan_filter)]
    if status_filter != "Semua":
        filtered_df = filtered_df[filtered_df["status"] == status_filter]

    # --- Tampilkan data ---
    st.subheader("Daftar Utang & Piutang")
    if filtered_df.empty:
        st.info("Tidak ada data sesuai filter.")
    else:
        for _, row in filtered_df.iterrows():
            col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 1, 1, 2, 2, 1, 1])
            with col1:
                st.write(row["name"])
            with col2:
                st.write(row["type"])
            with col3:
                st.write(f"Rp. {row['amount']:,}")
            with col4:
                st.write(row["due_date"])
            with col5:
                st.write(row["status"])
            with col6:
                st.write(row["description"] or "-")
            with col7:
                status_check = st.checkbox("✔", value=(row["status"] == "lunas"), key=row["id"])
                if status_check and row["status"] != "lunas":
                    supabase.table("debts").update({"status": "lunas"}).eq("id", row["id"]).execute()
                    st.rerun()
                elif not status_check and row["status"] != "belum lunas":
                    supabase.table("debts").update({"status": "belum lunas"}).eq("id", row["id"]).execute()
                    st.rerun()

        # --- Hapus data ---
        selected_delete = st.selectbox(
            "Pilih data untuk dihapus", 
            filtered_df["id"], 
            format_func=lambda x: filtered_df.loc[filtered_df["id"]==x, "name"].values[0]
        )
        if st.button("Hapus Data"):
            supabase.table("debts").delete().eq("id", selected_delete).execute()
            st.success("Data berhasil dihapus!")
            st.rerun()
else:
    st.info("Belum ada data utang/piutang.")
