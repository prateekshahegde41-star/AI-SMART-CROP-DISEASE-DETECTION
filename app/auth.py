"""
Authentication and Profile management for VANYA Streamlit frontend.
Persists session across page refresh via streamlit-cookies-controller.
Supports Supabase Auth + Storage and offline demo fallback.
"""
import os
import sys
from pathlib import Path
import requests
import streamlit as st
try:
    from .utils import API_URL, get_config
except (ImportError, ValueError):
    try:
        from utils import API_URL, get_config
    except Exception:
        def get_config(key: str, default: str = "") -> str:
            try:
                if key in st.secrets:
                    return str(st.secrets[key])
            except Exception:
                pass
            return os.getenv(key, default)
        API_URL = get_config(
    "API_URL",
    "https://ai-smart-crop-disease-detection.onrender.com"
)

try:
    from streamlit_cookies_controller import CookieController
    controller = CookieController()
except Exception:
    class _MockCookieController:
        def get(self, key):
            return st.session_state.get(f"_cookie_{key}")
        def set(self, key, value):
            st.session_state[f"_cookie_{key}"] = value
        def remove(self, key):
            st.session_state.pop(f"_cookie_{key}", None)
    controller = _MockCookieController()


def get_supabase():
    url = get_config("SUPABASE_URL")
    key = get_config("SUPABASE_PUBLISHABLE_KEY") or get_config("SUPABASE_ANON_KEY")
    if not url or not key:
        return None
    try:
        from supabase import create_client
        return create_client(url, key)
    except Exception as e:
        print("[auth] Supabase client init failed:", e)
        return None


def fetch_and_set_profile(user_id: str, email: str, access_token: str | None = None):
    """Fetch user profile from backend or Supabase and store in session_state."""
    headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}
    try:
        r = requests.get(f"{API_URL}/profile", headers=headers, timeout=5)
        if r.ok and r.json():
            st.session_state["profile"] = r.json()
            return
    except Exception:
        pass

    # Direct query to Supabase profiles table
    supabase = get_supabase()
    if supabase:
        try:
            res = supabase.table("profiles").select("*").eq("id", user_id).execute()
            if res.data:
                st.session_state["profile"] = res.data[0]
                return
            # Also try matching by email if ID differed
            res_email = supabase.table("profiles").select("*").eq("email", email).execute()
            if res_email.data:
                st.session_state["profile"] = res_email.data[0]
                return
        except Exception as e:
            print("[auth] Direct Supabase profile lookup:", e)

    # Fallback to local default profile
    existing = st.session_state.get("profile") or {}
    role = "admin" if email.lower() in ("prateekshahegde41@gmail.com", "admin@demo.local") else existing.get("role", "farmer")
    st.session_state["profile"] = {
        "id": user_id,
        "email": email,
        "full_name": existing.get("full_name") or email.split("@")[0].capitalize(),
        "phone": existing.get("phone", ""),
        "avatar_url": existing.get("avatar_url", None),
        "role": role
    }


def restore_session_from_cookie():
    """Restores authentication from cookie refresh token across page refreshes."""
    if st.session_state.get("authenticated", False):
        return True

    try:
        refresh_token = controller.get("vanya_refresh_token")
    except Exception:
        refresh_token = None

    if not refresh_token:
        return False

    supabase = get_supabase()
    if not supabase:
        # Check for demo tokens
        if refresh_token in ("demo-farmer-refresh", "demo-admin-refresh"):
            is_admin = refresh_token == "demo-admin-refresh"
            st.session_state["authenticated"] = True
            st.session_state["user"] = {
                "id": "demo-admin" if is_admin else "demo-farmer",
                "email": "admin@demo.local" if is_admin else "farmer@demo.local"
            }
            st.session_state["access_token"] = "demo-admin" if is_admin else "demo-farmer"
            st.session_state["profile"] = {
                "id": st.session_state["user"]["id"],
                "email": st.session_state["user"]["email"],
                "full_name": "Demo Admin" if is_admin else "Demo Farmer",
                "phone": "+91 9876543210",
                "avatar_url": None,
                "role": "admin" if is_admin else "farmer"
            }
            return True
        return False

    try:
        res = supabase.auth.refresh_session(refresh_token)
        if res and res.session:
            st.session_state["authenticated"] = True
            st.session_state["user"] = {
                "id": str(res.user.id),
                "email": res.user.email
            }
            st.session_state["access_token"] = res.session.access_token
            if res.session.refresh_token:
                controller.set("vanya_refresh_token", res.session.refresh_token)
            fetch_and_set_profile(str(res.user.id), res.user.email, res.session.access_token)
            return True
    except Exception as e:
        print("[auth] Session restore failed:", e)
        try:
            controller.remove("vanya_refresh_token")
        except Exception:
            pass

    return False


def login_page():
    st.markdown("""
        <div style="text-align: center; margin-bottom: 24px;">
            <h1 style="color: #2e7d32; font-size: 2.2rem; margin-bottom: 4px;">🌿 VANYA</h1>
            <p style="color: #4b5563; font-size: 1rem; margin: 0;">Smart AI Plant Disease Detection & Farmer Advisory</p>
        </div>
    """, unsafe_allow_html=True)

    supabase = get_supabase()

    tab_login, tab_signup = st.tabs(["🔑 Login", "📝 Create Account"])

    with tab_login:
        st.subheader("Welcome Back")
        email = st.text_input("Email Address", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Log In", type="primary", use_container_width=True):
                if not email or not password:
                    st.warning("Please provide both email and password.")
                elif not supabase:
                    # Seamless offline demo login
                    is_admin = "admin" in email.lower() or email.lower() == "prateekshahegde41@gmail.com"
                    uid = f"user-{abs(hash(email)) % 1000000}"
                    name = email.split("@")[0].replace(".", " ").title()
                    st.session_state["authenticated"] = True
                    st.session_state["user"] = {"id": uid, "email": email}
                    st.session_state["access_token"] = "demo-admin" if is_admin else "demo-farmer"
                    st.session_state["profile"] = {
                        "id": uid,
                        "email": email,
                        "full_name": name,
                        "phone": "",
                        "avatar_url": None,
                        "role": "admin" if is_admin else "farmer"
                    }
                    try:
                        controller.set("vanya_refresh_token", "demo-admin-refresh" if is_admin else "demo-farmer-refresh")
                    except Exception:
                        pass
                    st.success(f"Logged in as {name}!")
                    st.rerun()
                else:
                    try:
                        with st.spinner("Signing in..."):
                            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        st.session_state["authenticated"] = True
                        st.session_state["user"] = {"id": str(res.user.id), "email": res.user.email}
                        st.session_state["access_token"] = res.session.access_token
                        if res.session.refresh_token:
                            controller.set("vanya_refresh_token", res.session.refresh_token)
                        fetch_and_set_profile(str(res.user.id), res.user.email, res.session.access_token)
                        st.success("Login successful!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Login failed: {e}")

        # Quick Demo Login Option for testing & grading
        st.divider()
        st.caption("Quick Test Login (No Supabase required)")
        dcol1, dcol2 = st.columns(2)
        with dcol1:
            if st.button("🌱 Demo Farmer", use_container_width=True):
                st.session_state["authenticated"] = True
                st.session_state["user"] = {"id": "demo-farmer", "email": "farmer@demo.local"}
                st.session_state["access_token"] = "demo-farmer"
                st.session_state["profile"] = {
                    "id": "demo-farmer",
                    "email": "farmer@demo.local",
                    "full_name": "Ramesh Kumar",
                    "phone": "+91 9876543210",
                    "avatar_url": None,
                    "role": "farmer"
                }
                try:
                    controller.set("vanya_refresh_token", "demo-farmer-refresh")
                except Exception:
                    pass
                st.rerun()
        with dcol2:
            if st.button("🛠️ Demo Admin", use_container_width=True):
                st.session_state["authenticated"] = True
                st.session_state["user"] = {"id": "demo-admin", "email": "admin@demo.local"}
                st.session_state["access_token"] = "demo-admin"
                st.session_state["profile"] = {
                    "id": "demo-admin",
                    "email": "admin@demo.local",
                    "full_name": "Dr. Shravani (Expert)",
                    "phone": "+91 9845012345",
                    "avatar_url": None,
                    "role": "admin"
                }
                try:
                    controller.set("vanya_refresh_token", "demo-admin-refresh")
                except Exception:
                    pass
                st.rerun()

    with tab_signup:
        st.subheader("Join VANYA")
        s_name = st.text_input("Full Name", key="signup_name")
        s_email = st.text_input("Email Address", key="signup_email")
        s_pass = st.text_input("Create Password", type="password", key="signup_pass")
        s_confirm = st.text_input("Confirm Password", type="password", key="signup_confirm")

        if st.button("Create Account", type="primary", use_container_width=True):
            if not s_name or not s_email or not s_pass:
                st.warning("Please fill in all required fields.")
            elif s_pass != s_confirm:
                st.error("Passwords do not match.")
            elif len(s_pass) < 6:
                st.error("Password must be at least 6 characters.")
            elif not supabase:
                # Seamless offline account creation
                uid = f"user-{abs(hash(s_email)) % 1000000}"
                st.session_state["authenticated"] = True
                st.session_state["user"] = {"id": uid, "email": s_email}
                st.session_state["access_token"] = "demo-farmer"
                st.session_state["profile"] = {
                    "id": uid,
                    "email": s_email,
                    "full_name": s_name,
                    "phone": "",
                    "avatar_url": None,
                    "role": "farmer"
                }
                try:
                    controller.set("vanya_refresh_token", "demo-farmer-refresh")
                except Exception:
                    pass
                st.success(f"Welcome, {s_name}! Account created.")
                st.rerun()
            else:
                try:
                    with st.spinner("Creating your account..."):
                        res = supabase.auth.sign_up({
                            "email": s_email,
                            "password": s_pass,
                            "options": {"data": {"full_name": s_name}}
                        })
                    if res.session:
                        st.session_state["authenticated"] = True
                        st.session_state["user"] = {"id": str(res.user.id), "email": res.user.email}
                        st.session_state["access_token"] = res.session.access_token
                        if res.session.refresh_token:
                            controller.set("vanya_refresh_token", res.session.refresh_token)
                        fetch_and_set_profile(str(res.user.id), res.user.email, res.session.access_token)
                        st.success("Account created successfully!")
                        st.rerun()
                    else:
                        st.success("Account created! Please check your email to confirm or log in above.")
                except Exception as e:
                    st.error(f"Sign up error: {e}")


def check_auth() -> bool:
    """Verifies authentication. Restores session if cookie is present, else shows login."""
    if st.session_state.get("authenticated", False):
        return True

    if restore_session_from_cookie():
        return True

    login_page()
    st.stop()
    return False


def logout():
    """Logs the user out, cleans Supabase session, clears cookie, clears session_state."""
    supabase = get_supabase()
    if supabase:
        try:
            supabase.auth.sign_out()
        except Exception:
            pass

    try:
        controller.remove("vanya_refresh_token")
    except Exception:
        pass

    for key in [
        "authenticated", "user", "access_token", "profile",
        "report", "chat_history", "selected_plant_id"
    ]:
        st.session_state.pop(key, None)

    st.rerun()


def render_sidebar_profile():
    """
    Renders sidebar bottom-left circular avatar + email with Edit Profile popover and Logout.
    Only Logout ends the session.
    """
    user = st.session_state.get("user")
    if not user:
        return

    profile = st.session_state.get("profile") or {}
    full_name = profile.get("full_name") or user.get("email", "").split("@")[0].capitalize()
    email = user.get("email", "")
    role = profile.get("role", "farmer")
    avatar_url = profile.get("avatar_url")

    # Generate initials fallback
    parts = full_name.strip().split()
    initials = "".join([p[0].upper() for p in parts[:2]]) if parts else "V"

    st.sidebar.divider()

    # Circular avatar + name in sidebar
    avatar_html = (
        f'<img src="{avatar_url}" class="user-avatar-circle">'
        if avatar_url
        else f'<div class="user-avatar-circle">{initials}</div>'
    )

    role_badge = f'<span class="badge badge-{"high" if role == "admin" else "low"}">{role.upper()}</span>'

    st.sidebar.markdown(
        f"""
        <div class="sidebar-profile-box">
            {avatar_html}
            <div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                <div style="font-weight: 700; color: #1f2937; font-size: 0.92rem;">{full_name}</div>
                <div style="font-size: 0.78rem; color: #6b7280; overflow: hidden; text-overflow: ellipsis;">{email}</div>
                <div style="margin-top: 3px;">{role_badge}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Popover with Edit Profile and Logout
    with st.sidebar.popover("⚙️ Profile & Settings", use_container_width=True):
        st.subheader("Farmer Profile")
        st.write(f"**Email:** {email}")
        st.write(f"**Role:** {role.capitalize()}")

        with st.expander("✏️ Edit Profile Details", expanded=False):
            new_name = st.text_input("Full Name", value=full_name, key="edit_prof_name")
            new_phone = st.text_input("Phone Number", value=profile.get("phone", ""), key="edit_prof_phone")
            photo_file = st.file_uploader("Upload Profile Photo", type=["jpg", "png", "webp"], key="edit_prof_avatar")

            if st.button("Save Profile Changes", type="primary", use_container_width=True):
                updated_avatar = avatar_url
                # Upload avatar if provided
                if photo_file:
                    supabase = get_supabase()
                    if supabase:
                        try:
                            file_bytes = photo_file.getvalue()
                            path_on_bucket = f"{user['id']}/avatar.jpg"
                            supabase.storage.from_("avatars").upload(
                                path_on_bucket,
                                file_bytes,
                                file_options={"content-type": photo_file.type, "upsert": "true"}
                            )
                            updated_avatar = supabase.storage.from_("avatars").get_public_url(path_on_bucket)
                        except Exception as e:
                            print("[avatar] Upload failed:", e)

                # Send update to backend
                token = st.session_state.get("access_token", "")
                headers = {"Authorization": f"Bearer {token}"} if token else {}
                try:
                    r = requests.post(
                        f"{API_URL}/profile",
                        json={"full_name": new_name, "phone": new_phone, "avatar_url": updated_avatar},
                        headers=headers,
                        timeout=10
                    )
                    if r.ok:
                        st.session_state["profile"].update({
                            "full_name": new_name,
                            "phone": new_phone,
                            "avatar_url": updated_avatar
                        })
                        st.success("Profile updated successfully!")
                        st.rerun()
                except Exception as e:
                    # Update local state fallback
                    st.session_state["profile"].update({
                        "full_name": new_name,
                        "phone": new_phone,
                        "avatar_url": updated_avatar
                    })
                    st.success("Profile saved locally!")
                    st.rerun()

        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            logout()
