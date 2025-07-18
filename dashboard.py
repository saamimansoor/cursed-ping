import os
os.system("playwright install chromium")

import json
import subprocess
import streamlit as st

# ─── PATHS & LOAD ────────────────────────────────────────────────
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

st.set_page_config(page_title="Notify Senpai")

# ─── CUSTOM CSS FOR TOGGLES ──────────────────────────────────────
st.markdown("""
    <style>
    @keyframes cursedGlow {
        0% { text-shadow: 0 0 5px #ff0000, 0 0 10px #ff0000; }
        50% { text-shadow: 0 0 20px #ff0000, 0 0 40px #ff5555; }
        100% { text-shadow: 0 0 5px #ff0000, 0 0 10px #ff0000; }
    }
    .cursed-title {
        font-family: 'Courier New', monospace;
        font-size: 42px;
        font-weight: 900;
        color: white;
        letter-spacing: 2px;
        animation: cursedGlow 1.8s infinite;
        margin-bottom: 2rem;
    }

    /* Toggle styling */
    .stCheckbox > div {
        display: flex;
        align-items: center;
    }
    .stCheckbox div[data-baseweb="checkbox"] {
        visibility: hidden;
        width: 0;
    }
    .stCheckbox label {
        display: flex;
        align-items: center;
        gap: 10px;
        background: #222;
        border-radius: 24px;
        padding: 2px 8px;
    }
    </style>
""", unsafe_allow_html=True)

# ─── HEADER ───────────────────────────────────────────────────────
st.markdown("<h1 class='cursed-title'>CURSED PING</h1>", unsafe_allow_html=True)
st.markdown("---")

# ─── MASTER SWITCH ───────────────────────────────────────────────
master = st.checkbox("Master Switch", value=config["master_switch"])
config["master_switch"] = master

st.markdown("---")
st.subheader("MIS Systems")

# ─── SYSTEM TOGGLES ────────────────────────────────────────────────
for name, sys in config["systems"].items():
    new_active = st.checkbox(f"{sys['icon']} {name}", value=sys["active"])
    config["systems"][name]["active"] = new_active

st.markdown("---")

# ─── ADD NEW MIS FORM ──────────────────────────────────────────────
with st.expander("➕ Add New MIS"):
    with st.form("add_mis"):
        name        = st.text_input("System Name")
        icon        = st.text_input("Icon (e.g. 🟦)")
        url         = st.text_input("URL")
        prop_col    = st.number_input("Proposal # Column Index", min_value=0, step=1)
        remarks_col = st.number_input("Remarks Column Index", min_value=0, step=1)
        filter_lbl  = st.text_input("Filter Label (e.g. Recall)")
        submitted   = st.form_submit_button("Add MIS")
    if submitted and name:
        config["systems"][name] = {
            "active":       True,
            "icon":         icon or "🔷",
            "url":          url,
            "prop_id_col":  prop_col,
            "remarks_col":  remarks_col,
            "filter_label": filter_lbl,
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        st.success(f"✅ Added **{name}**!")

# ─── SAVE BUTTON ────────────────────────────────────────────────────
if st.button("💾 Save All Changes"):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    st.success("Configuration saved!")

# ─── RUN BOT NOW BUTTON ─────────────────────────────────────────────
st.markdown("---")
if st.button("▶️ Run Bot Now"):
    with st.spinner("Running bot..."):
        result = subprocess.run(["python", "run_bot.py"], capture_output=True, text=True)
        st.code(result.stdout + "\n" + result.stderr)
    st.success("✅ Bot run complete!")

# ─── FOOTER ─────────────────────────────────────────────────────────
st.markdown("""
---
🙂 Made with broken backs, chainsaw blades, and ChatGPT.
""")