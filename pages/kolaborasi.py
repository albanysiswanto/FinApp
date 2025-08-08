# pages/kolaborasi.py
import streamlit as st
from supabase_client import supabase
from datetime import datetime

st.set_page_config(page_title="Kolaborasi", layout="wide")

# --- Cek login ---
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("Silakan login terlebih dahulu.")
    st.switch_page("app.py")

user = st.session_state.user
user_id = user.id
user_email = user.email.strip().lower()

st.title("🤝 Kolaborasi (Akses Baca Antar Pengguna)")

# ---------------------------
# Form: Minta akses ke akun lain (kirim permintaan)
# ---------------------------
st.subheader("Minta akses untuk melihat akun pasangan")
invite_email = st.text_input("Masukkan email pasangan (pemilik data)")

if st.button("Kirim Permintaan Akses"):
    invite_email_norm = (invite_email or "").strip().lower()
    if not invite_email_norm:
        st.error("Masukkan email tujuan.")
    elif invite_email_norm == user_email:
        st.error("Tidak bisa meminta akses ke akun sendiri.")
    else:
        # Cek apakah sudah ada permintaan yang sama (berdasarkan owner_email & collab_id)
        check = supabase.table("collaborations") \
            .select("*") \
            .eq("owner_email", invite_email_norm) \
            .eq("collab_id", user_id) \
            .execute()

        if check.data and len(check.data) > 0:
            st.info("Permintaan akses sudah pernah dikirim.")
        else:
            supabase.table("collaborations").insert({
                # owner_id intentionally not set here; owner will set when they accept
                "collab_id": user_id,                  # requester id
                "requester_email": user_email,         # requester email (untuk tampilan)
                "owner_email": invite_email_norm,      # target email (pemilik akun)
                "status": "pending",
                "created_at": datetime.utcnow().isoformat()
            }).execute()
            st.success("Permintaan akses terkirim. Tunggu pasangan menerima.")

st.divider()

# ---------------------------
# Bagian: Permintaan yang dikirim (outgoing)
# ---------------------------
st.subheader("Permintaan yang Anda Kirim")
outgoing = supabase.table("collaborations") \
    .select("*") \
    .eq("collab_id", user_id) \
    .order("created_at", desc=True) \
    .execute()

if outgoing.data:
    for row in outgoing.data:
        st.markdown(f"- **Ke:** {row.get('owner_email')}  — **Status:** {row.get('status')}")
        if row.get('status') == 'pending':
            if st.button(f"Batalkan {row['id']}", key=f"cancel-{row['id']}"):
                supabase.table("collaborations").delete().eq("id", row['id']).execute()
                st.success("Permintaan dibatalkan.")
                st.rerun()
else:
    st.info("Belum ada permintaan yang Anda kirim.")

st.divider()

# ---------------------------
# Bagian: Permintaan masuk untuk Anda (owner melihat siapa minta akses)
# ---------------------------
st.subheader("Permintaan Masuk untuk Anda")
# Cari berdasarkan owner_email karena owner_id mungkin kosong sebelum owner terima
incoming = supabase.table("collaborations") \
    .select("*") \
    .eq("owner_email", user_email) \
    .eq("status", "pending") \
    .order("created_at", desc=True) \
    .execute()

if incoming.data:
    for row in incoming.data:
        st.markdown(f"**Dari:** {row.get('requester_email')}  — Dikirim: {row.get('created_at')}")
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"Terima-{row['id']}", key=f"accept-{row['id']}"):
                # Saat owner menerima, isi owner_id supaya hubungan tertaut ke user id
                supabase.table("collaborations").update({
                    "status": "accepted",
                    "owner_id": user_id,   # now owner_id terisi
                    "owner_email": user_email  # normalize owner_email
                }).eq("id", row['id']).execute()
                st.success("Permintaan diterima. Pengirim sekarang punya akses baca ke akun Anda.")
                st.experimental_rerun()
        with col2:
            if st.button(f"Tolak-{row['id']}", key=f"reject-{row['id']}"):
                supabase.table("collaborations").update({
                    "status": "rejected"
                }).eq("id", row['id']).execute()
                st.success("Permintaan ditolak.")
                st.experimental_rerun()
else:
    st.info("Tidak ada permintaan masuk.")
