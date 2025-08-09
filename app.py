import streamlit as st
from supabase_client import supabase

st.set_page_config(page_title="Finance Tracker", layout="wide")

# -------------------------
# Cek session Supabase saat pertama kali load
# -------------------------
if "user" not in st.session_state:
    # Coba ambil session dari Supabase
    session = supabase.auth.get_session()

    if session and session.user:
        st.session_state.user = session.user
    else:
        st.session_state.user = None


# -------------------------
# Fungsi Login
# -------------------------
def login():
    st.title("Login / Daftar")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            if res.user:
                st.session_state.user = res.user
                st.success(f"Selamat datang, {email}!")
                st.rerun()  # refresh biar langsung ke dashboard
            else:
                st.error("Login gagal. Periksa email dan password.")
        except Exception as e:
            st.error(f"Login gagal: {e}")

    if st.button("Daftar Akun"):
        try:
            res = supabase.auth.sign_up({"email": email, "password": password})
             # res biasanya object dengan .user dan .error tidak ada, 
            # jadi kita cek user hasil signup
            if res.user:
                st.success("Akun berhasil dibuat! Silakan verifikasi email dan login.")
            else:
                # Kalau user kosong, kemungkinan gagal signup karena email sudah ada atau error lain
                st.error("Registrasi gagal. Mungkin email sudah terdaftar atau password tidak valid.")
        except Exception as e:
            st.error(f"Registrasi gagal: {e}")


# -------------------------
# Routing
# -------------------------
if st.session_state.user:
    st.switch_page("pages/1_Dashboard.py")
else:
    login()
