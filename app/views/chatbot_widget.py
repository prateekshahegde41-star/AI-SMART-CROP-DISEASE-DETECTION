"""
VANYA Floating Chatbot Widget
Rendered fixed at the bottom-right after disease detection.
Uses quick-reply chips and session chat history.
"""
import sys
from pathlib import Path
import requests
import streamlit as st

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

try:
    from ..utils import API_URL
except (ImportError, ValueError):
    from utils import API_URL


def render_chatbot():
    rep = st.session_state.get("report")
    if not rep:
        return

    pred = rep.get("prediction", {})
    disease_label = pred.get("label", "")
    disease_readable = disease_label.replace("___", " - ").replace("_", " ")

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
        # Initial greeting
        st.session_state["chat_history"].append({
            "role": "assistant",
            "content": f"Hello! I am VANYA's Assistant. Ask me anything about **{disease_readable}**: causes, symptoms, prevention, treatment, or how it spreads."
        })

    # Fixed bottom-right container
    st.markdown("""
        <div class="floating-chat-container">
        </div>
    """, unsafe_allow_html=True)

    with st.popover("💬 Ask VANYA Assistant", use_container_width=False):
        st.markdown(f"#### 🌿 {disease_readable} Q&A")
        st.caption("Verified agronomic advisory assistant. Localized ICAR guidance.")

        # Quick-reply chips
        st.write("**Quick Questions:**")
        qc1, qc2, qc3 = st.columns(3)
        qc4, qc5, _ = st.columns(3)

        chip_clicked = None
        if qc1.button("Causes", use_container_width=True):
            chip_clicked = "What causes this disease?"
        if qc2.button("Symptoms", use_container_width=True):
            chip_clicked = "What are the symptoms?"
        if qc3.button("Prevention", use_container_width=True):
            chip_clicked = "How can I prevent this disease?"
        if qc4.button("Treatment", use_container_width=True):
            chip_clicked = "How do I treat this disease?"
        if qc5.button("How it Spreads", use_container_width=True):
            chip_clicked = "How does this disease spread?"

        # Display conversation history
        chat_container = st.container(height=320)
        with chat_container:
            for msg in st.session_state["chat_history"]:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

        # Chat input
        user_prompt = st.chat_input("Ask a question about this disease...", key="vanya_chat_input")
        prompt_to_send = chip_clicked or user_prompt

        if prompt_to_send:
            st.session_state["chat_history"].append({"role": "user", "content": prompt_to_send})
            try:
                res = requests.post(
                    f"{API_URL}/chat",
                    json={"disease_name": disease_label, "user_question": prompt_to_send},
                    timeout=15
                )
                if res.ok:
                    data = res.json()
                    bot_reply = data.get("reply", "No guidance found.")
                    st.session_state["chat_history"].append({"role": "assistant", "content": bot_reply})
                else:
                    st.session_state["chat_history"].append({
                        "role": "assistant",
                        "content": "Unable to contact the advisory server. Please check backend connection."
                    })
            except Exception as e:
                st.session_state["chat_history"].append({
                    "role": "assistant",
                    "content": f"Connection error: {e}"
                })
            st.rerun()

        st.caption("ℹ️ *General information only - not a substitute for advice from a local agricultural expert.*")
