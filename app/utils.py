import os
import streamlit as st
import requests

def get_config(key: str, default: str = "") -> str:
    """Retrieve config from st.secrets first, falling back to os.environ."""
    try:
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.getenv(key, default)

API_URL = get_config("API_URL", "https://ai-smart-crop-disease-detection.onrender.com")
LEVEL_ICON = {"Low": "🟢", "Medium": "🟡", "High": "🔴", "None": "🟢", "Unknown": "⚪"}

def geocode(place: str):
    """Place name -> (lat, lon) via OpenStreetMap Nominatim."""
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": place, "format": "json", "limit": 1},
            headers={"User-Agent": "vanya-smart-agri-ai"},
            timeout=10
        )
        j = r.json()
        return (float(j[0]["lat"]), float(j[0]["lon"])) if j else None
    except Exception:
        return None
