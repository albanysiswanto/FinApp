import streamlit as st
from supabase_client import supabase
import pandas as pd
from datetime import date

# ===== CONFIGURASI DASAR =====
st.set_page_config(page_title="Utang & Piutang", layout="wide")

# CSS custom
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
        padding: 1rem;
    }
    .form-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        margin-bottom: 20px;
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
</style>
""", unsafe_allow_html=True)

# ===== CEK LOGIN =====
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("⚠️ Silakan login terlebih dahulu.")
    st.switch_page("app.py")

user_id = st.session_state.user.id
st.markdown("## 💰 Kelola Utang & Piutang")

# ===== FORM TAMBAH DATA =====
with st.container():
    st.markdown("<div>", unsafe_allow_html=True)
    st.markdown("### ➕ Tambah Utang / Piutang")
    with st.form("add_debt_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Nama Pihak Terkait")
            debt_type = st.selectbox("Jenis", ["utang", "piutang"])
            amount = st.number_input("Jumlah", min_value=0.0, step=1000.0)
        with col2:
            due_date = st.date_input("Jatuh Tempo", value=date.today())
            description = st.text_area("Deskripsi")
        
        submitted = st.form_submit_button("Tambah Data")
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
                st.success("✅ Data berhasil ditambahkan!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Gagal menambahkan data: {e}")
    st.markdown("</div>", unsafe_allow_html=True)

# ===== AMBIL DATA =====
debts_res = supabase.table("debts").select("*").eq("user_id", user_id).order("due_date").execute()
debts_df = pd.DataFrame(debts_res.data or [])

if not debts_df.empty:
    debts_df["due_date"] = pd.to_datetime(debts_df["due_date"]).dt.date

    # ===== FILTER =====
    st.markdown("### 🔍 Filter Data")
    col_f0, col_f1, col_f2, col_f3 = st.columns(4)

    with col_f0:
        nama_filter = st.text_input("Cari Nama", "")

    with col_f1:
        tahun_tersedia = sorted(list({d.year for d in debts_df["due_date"]}), reverse=True)
        tahun_filter = st.selectbox("Tahun", ["Semua"] + tahun_tersedia)

    with col_f2:
        bulan_filter = st.selectbox(
            "Bulan",
            ["Semua"] + list(range(1, 13)),
            format_func=lambda x: x if x == "Semua" else date(2000, x, 1).strftime("%B")
        )

    with col_f3:
        status_filter = st.selectbox("Status", ["Semua", "lunas", "belum lunas"])

    # ===== PROSES FILTER =====
    filtered_df = debts_df.copy()

    # Filter nama (case-insensitive & partial match)
    if nama_filter:
        filtered_df = filtered_df[filtered_df["name"].str.contains(nama_filter, case=False, na=False)]

    if tahun_filter != "Semua":
        filtered_df = filtered_df[filtered_df["due_date"].apply(lambda d: d.year == tahun_filter)]
    if bulan_filter != "Semua":
        filtered_df = filtered_df[filtered_df["due_date"].apply(lambda d: d.month == bulan_filter)]
    if status_filter != "Semua":
        filtered_df = filtered_df[filtered_df["status"] == status_filter]

    # ===== TAMPILKAN DATA =====
    st.markdown("### 📋 Daftar Utang & Piutang")
    if filtered_df.empty:
        st.info("Tidak ada data sesuai filter.")
    else:
        df_display = filtered_df.copy()
        df_display["amount"] = df_display["amount"].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
        
        # Tabel interaktif
        st.dataframe(df_display[["name", "type", "amount", "due_date", "status", "description"]])

        # ===== UPDATE STATUS =====
        st.markdown("### ✏️ Update Status")
        for _, row in filtered_df.iterrows():
            status_check = st.checkbox(
                f"{row['name']} ({row['amount']})",
                value=(row["status"] == "lunas"),
                key=f"status_{row['id']}"
            )
            if status_check and row["status"] != "lunas":
                supabase.table("debts").update({"status": "lunas"}).eq("id", row["id"]).execute()
                st.rerun()
            elif not status_check and row["status"] != "belum lunas":
                supabase.table("debts").update({"status": "belum lunas"}).eq("id", row["id"]).execute()
                st.rerun()

        # ===== HAPUS DATA =====
        st.markdown("### 🗑 Hapus Data")
        selected_delete = st.selectbox(
            "Pilih data untuk dihapus",
            filtered_df["id"],
            format_func=lambda x: filtered_df.loc[filtered_df["id"] == x, "name"].values[0]
        )
        if st.button("Hapus Data"):
            supabase.table("debts").delete().eq("id", selected_delete).execute()
            st.success("✅ Data berhasil dihapus!")
            st.rerun()
else:
    st.info("💡 Belum ada data utang/piutang.")
