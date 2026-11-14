import streamlit as st

SHARED_CSS = """
<style>
/* ==================================================
   VANYA MOBILE-FIRST DESIGN SYSTEM
   ================================================== */

:root {
  --primary-color: #2e7d32;
  --primary-dark: #1b5e20;
  --primary-light: #e8f5e9;
  --bg-card: #ffffff;
  --text-main: #1f2937;
  --text-muted: #6b7280;
  --border-subtle: #e5e7eb;
  --radius-lg: 14px;
  --radius-md: 10px;
  --radius-full: 9999px;
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
  --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.08), 0 2px 4px -1px rgba(0,0,0,0.04);
}

/* Card container */
.vanya-card {
  background-color: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 18px 20px;
  margin-bottom: 16px;
  box-shadow: var(--shadow-sm);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.vanya-card:hover {
  box-shadow: var(--shadow-md);
}

.vanya-card-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--primary-dark);
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Status Badges */
.badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.badge-low {
  background-color: #e8f5e9;
  color: #2e7d32;
  border: 1px solid #c8e6c9;
}

.badge-medium {
  background-color: #fffde7;
  color: #f57f17;
  border: 1px solid #fff9c4;
}

.badge-high {
  background-color: #ffebee;
  color: #c62828;
  border: 1px solid #ffcdd2;
}

.badge-warning {
  background-color: #fff3e0;
  color: #e65100;
  border: 1px solid #ffe0b2;
}

/* Tap targets */
button[kind="primary"], button[kind="secondary"] {
  min-height: 44px !important;
  border-radius: var(--radius-md) !important;
  font-weight: 600 !important;
}

.stTextInput input, .stSelectbox select {
  min-height: 42px !important;
  border-radius: var(--radius-md) !important;
}

/* Floating Chat Action Button (Bottom-Right) */
section.main div[data-testid="stPopover"] {
  position: fixed !important;
  bottom: 24px !important;
  right: 24px !important;
  z-index: 99999 !important;
}

section.main div[data-testid="stPopover"] > button {
  border-radius: 9999px !important;
  padding: 12px 22px !important;
  background-color: var(--primary-color) !important;
  color: #ffffff !important;
  box-shadow: 0 4px 16px rgba(46, 125, 50, 0.45) !important;
  border: 2px solid #ffffff !important;
  font-weight: 700 !important;
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
  transition: transform 0.2s ease, background-color 0.2s ease;
}

section.main div[data-testid="stPopover"] > button:hover {
  background-color: var(--primary-dark) !important;
  color: #ffffff !important;
  transform: translateY(-2px);
}

/* Circular Avatar */
.user-avatar-circle {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background-color: #2e7d32;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1rem;
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  border: 2px solid #ffffff;
  object-fit: cover;
}

.sidebar-profile-box {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  background-color: #ffffff;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  margin-top: 10px;
}

/* Mobile responsive constraints (390px phone screens) */
@media (max-width: 640px) {
  .vanya-card {
    padding: 14px 14px;
  }
  .stHorizontalBlock {
    flex-direction: column !important;
  }
  section.main div[data-testid="stPopover"] {
    bottom: 16px !important;
    right: 16px !important;
  }
  div[data-testid="stPopoverBody"] {
    width: 92vw !important;
    max-width: 95vw !important;
  }
}
</style>
"""

def apply_styles():
    st.markdown(SHARED_CSS, unsafe_allow_html=True)
