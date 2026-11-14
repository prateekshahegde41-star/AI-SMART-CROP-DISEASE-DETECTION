"""
VANYA - Smart Agricultural AI Assistant
Main Application Entrypoint
Run: streamlit run app/Home.py
"""
import sys
from pathlib import Path
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

st.set_page_config(
    page_title="VANYA - Smart Crop Disease Detection",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

from styles import apply_styles
from auth import check_auth, render_sidebar_profile
from views import detect, history, suitability, outbreak, admin

# 1. Apply unified shared CSS
apply_styles()

# 2. Enforce Authentication & session persistence
check_auth()

# 3. Render sidebar bottom circular avatar + profile popup
render_sidebar_profile()

# 4. Dynamically construct navigation page list based on verified role
profile = st.session_state.get("profile") or {}
user_role = profile.get("role", "farmer")

pages = [
    st.Page(detect.render, title="Detect", icon="🌿", url_path="detect", default=True),
    st.Page(history.render, title="History", icon="📜", url_path="history"),
    st.Page(suitability.render, title="Crop Suitability", icon="🌾", url_path="suitability"),
    st.Page(outbreak.render, title="Outbreak Map", icon="🗺️", url_path="outbreak"),
]

# Admin page is strictly appended ONLY if verified profile role == 'admin'
if user_role == "admin":
    pages.append(
        st.Page(admin.render, title="Admin Dashboard", icon="🛠️", url_path="admin")
    )

nav = st.navigation(pages)
nav.run()
