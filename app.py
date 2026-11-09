import streamlit as st
import pandas as pd
import numpy as np
import time
import urllib.parse
import folium
from streamlit_folium import st_folium

# --- 1. Global Page Setup ---
st.set_page_config(
    page_title="Tactical Command Matrix",
    page_icon="📡",  # Updated browser tab navigation indicator favicon
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. Advanced Cyberpunk UI Design System Styling ---
st.markdown("""
    <style>
    .stApp {
        background-color: #0b0f14;
        color: #7fa483;
        font-family: 'Consolas', 'Courier New', monospace;
    }
    .tactical-header-container {
        border-radius: 4px;
        padding: 10px;
        text-align: center;
        margin-bottom: 6px;
    }
    .header-alert {
        background-color: #210d0d;
        border: 2px solid #ff4757;
        box-shadow: 0 0 15px rgba(255, 71, 87, 0.25);
    }
    .header-nominal {
        background-color: #0c1c12;
        border: 2px solid #2ed573;
        box-shadow: 0 0 15px rgba(46, 213, 115, 0.25);
    }
    .tactical-title {
        font-size: 24px !important;
        font-weight: 800;
        letter-spacing: 3px;
        margin: 0 !important;
    }
    .sub-status-bar {
        display: flex;
        justify-content: space-between;
        border-radius: 4px;
        padding: 6px 15px;
        margin-bottom: 20px;
        font-size: 13px;
        font-weight: bold;
    }
    .panel-box {
        background-color: #0d121a;
        border: 1px solid #1f2d3d;
        border-radius: 3px;
        padding: 12px;
        margin-bottom: 15px;
    }
    .panel-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #1f2d3d;
        padding-bottom: 6px;
        margin-bottom: 12px;
    }
    .panel-title {
        color: #52a3ff !important;
        font-size: 11px !important;
        font-weight: bold;
        letter-spacing: 1px;
        margin: 0 !important;
    }
    .panel-controls { color: #4b6584; font-size: 11px; }
    .matrix-coordinates { font-size: 11px; color: #4e6172; margin-top: 8px; }
    
    .log-monitor {
        background-color: #05070a;
        border: 1px solid #16202c;
        border-radius: 3px;
        padding: 8px;
        height: 140px;
        overflow-y: auto;
        font-size: 11px;
        color: #648a68;
        line-height: 1.4;
    }
    .log-line { margin-bottom: 3px; }
    .log-ts { color: #3a7bd5; }
    .log-warn { color: #d27b11; }
    .log-crit { color: #ff4757; }
    
    .status-pill-container {
        display: flex;
        justify-content: space-between;
        margin-bottom: 10px;
    }
    .status-pill {
        background: #090d14;
        border: 1px solid #16202c;
        border-radius: 3px;
        padding: 8px;
        text-align: center;
        width: 31%;
    }
    .pill-val { font-size: 16px; font-weight: bold; }
    
    /* Strategic Emergency Broadcast Button styling */
    .btn-broadcast {
        display: block;
        background-color: #176565;
        color: white !important;
        font-weight: bold;
        text-align: center;
        padding: 14px;
        border: 1px solid #52a3ff;
        border-radius: 4px;
        text-decoration: none !important;
        font-size: 13px;
        text-transform: uppercase;
        box-shadow: 0 0 10px rgba(82, 163, 255, 0.1);
        margin-top: 15px;
    }
    .btn-broadcast:hover {
        background-color: #00cbcb;
        color: #0b0f14 !important;
        box-shadow: 0 0 15px rgba(82, 163, 255, 0.4);
    }
    </style>
""", unsafe_allow_html=True)

# Initialize runtime next of kin registry session vectors if empty
if "next_of_kin" not in st.session_state:
    st.session_state.next_of_kin = [
        {"Name": "John Smith", "Relation": "Primary Safety Relay", "Contact Vector": "+15550199"}
    ]

# --- 3. TEST FACILITIES & SIMULATION CONTROL BAY ---
with st.expander("🛠️ TEST FACILITIES & GEOTAG SIMULATION BAY", expanded=True):
    st.markdown("<p style='font-size:12px; color:#52a3ff;'>Engineering Diagnostic Console: Simulate sensor triggers, coordinates, and thresholds.</p>", unsafe_allow_html=True)
    
    geo_col1, geo_col2 = st.columns(2)
    with geo_col1:
        st.markdown("**🏡 HOUSE TARGET GEOTAG**")
        house_lat = st.number_input("House Latitude", value=34.0522, format="%.4f")
        house_lon = st.number_input("House Longitude", value=-118.2437, format="%.4f")
    with geo_col2:
        st.markdown("**🏃 USER/OPERATOR GEOTAG**")
        user_lat = st.number_input("User Latitude", value=34.0582, format="%.4f")
        user_lon = st.number_input("User Longitude", value=-118.2510, format="%.4f")
        
    st.markdown("---")
    c_col1, c_col2, c_col3 = st.columns(3)
    with c_col1:
        sim_alert = st.radio("Threat Assessment Simulation Mode", ["ACTIVE BREACH", "NOMINAL STABLE"], index=0)
    with c_col2:
        test_temp = st.slider("Manually Scale Zone Temperature (°C)", 10.0, 70.0, 34.5)
    with c_col3:
        st.markdown("**🛡️ AUTO SHUTDOWN PARAMS**")
        shutdown_threshold = st.slider("Overheat Shutdown Threshold (°C)", 50.0, 80.0, 65.0)

# --- 4. CONDITIONAL AUTO SHUTDOWN PROTECTION ROUTINE ---
if test_temp >= shutdown_threshold:
    st.markdown(f"""
    <div style="background-color:#4a0c0c; border:2px solid #ff3333; border-radius:4px; padding:25px; text-align:center; margin-bottom:20px;">
        <h2 style="color:#ff3333; margin:0; font-weight:bold; letter-spacing:1px;">⚠️ AUTO SHUTDOWN INITIALIZED: THERMAL CRITICAL ⚠️</h2>
        <p style="color:#ff8888; font-size:13px; margin-top:10px;">Core Temperature ({test_temp}°C) has broken safety limits ({shutdown_threshold}°C). Isolation routine active.</p>
    </div>
    """, unsafe_allow_html=True)
    st.toast("CRITICAL OVERHEAT: Halting core page elements...", icon="🛑")
    st.stop()

# --- 5. Threat Header Panel Rendering ---
if sim_alert == "ACTIVE BREACH":
    st.markdown("""
    <div class="tactical-header-container header-alert">
        <h1 class="tactical-title" style="color: #ff4757; text-shadow: 0 0 5px rgba(255, 71, 87, 0.4);">TACTICAL ALERT: PERIMETER BREACH DETECTED</h1>
    </div>
    <div class="sub-status-bar" style="background-color: #170a0a; border: 1px solid #7c1a1a;">
        <span style="color: #d27b11;">⚠️ SYSTEM ACTIVE SITUATION: ZONE 4</span>
        <span style="color: #ff4757;">CRISIS BROADCAST LAYERS READY ⏱️</span>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="tactical-header-container header-nominal">
        <h1 class="tactical-title" style="color: #2ed573; text-shadow: 0 0 5px rgba(46, 213, 115, 0.4);">TACTICAL SECURE: NO THREATS ACQUIRED</h1>
    </div>
    <div class="sub-status-bar" style="background-color: #0a170f; border: 1px solid #1a7c3e;">
        <span style="color: #2ed573;">🟢 SYSTEM STATUS: ONLINE NOMINAL</span>
        <span style="color: #2ed573;">ALL PERIMETERS SECURE 🔐</span>
    </div>
    """, unsafe_allow_html=True)

# --- 6. Main Dashboard Column Split ---
col_map, col_telemetry = st.columns(2)

with col_map:
    st.markdown("""
    <div class="panel-box">
        <div class="panel-header">
            <h3 class="panel-title">📡 3D HYBRID SATELLITE TRACKING ENGINE</h3>
            <span class="panel-controls">🗕 🗖 🗙</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Render license-free open satellite map layer using midpoint centering math
    m = folium.Map(
        location=[(house_lat + user_lat) / 2, (house_lon + user_lon) / 2], 
        zoom_start=14, 
        tiles="https://arcgisonline.com{z}/{y}/{x}", 
        attr="Esri"
    )
    folium.Marker([house_lat, house_lon], popup="🏡 TARGET HOUSE", icon=folium.Icon(color="red", icon="home")).add_to(m)
    folium.Marker([user_lat, user_lon], popup="🏃 USER OPS", icon=folium.Icon(color="blue", icon="user")).add_to(m)
    st_folium(m, use_container_width=True, height=350, key="satellite_radar_view")

    # --- 📋 ADD EMERGENCY CONTACT MODULE ---
    st.markdown("""
    <div class="panel-box" style="margin-top:15px;">
        <div class="panel-header">
            <h3 class="panel-title">🗃️ ADD EMERGENCY CONTACTS / NEXT OF KIN</h3>
            <span class="panel-controls">🗕 🗖 🗙</span>
        </div>
    """, unsafe_allow_html=True)
    
    with st.form("kin_entry_form", clear_on_submit=True):
        k_col1, k_col2, k_col3 = st.columns(3)
        with k_col1: new_name = st.text_input("Next of Kin Name")
        with k_col2: new_rel = st.text_input("Relationship")
        with k_col3: new_vec = st.text_input("Phone/Email Identifier")
        submit_kin = st.form_submit_button("➕ LOG CONTACT ENTRY")
        
        if submit_kin and new_name and new_vec:
            st.session_state.next_of_kin.append({"Name": new_name, "Relation": new_rel, "Contact Vector": new_vec})
            st.toast(f"Logged safety node for {new_name}.", icon="✅")
            
    st.dataframe(pd.DataFrame(st.session_state.next_of_kin), hide_index=True, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_telemetry:
    st.markdown("""
    <div class="panel-box">
        <div class="panel-header">
            <h3 class="panel-title">📊 SYSTEM TELEMETRY MATRIX</h3>
            <span class="panel-controls">🗕 🗖 🗙</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Mathematical separation calculus tracking
    delta_lat = house_lat - user_lat
    delta_lon = house_lon - user_lon
    distance_approx = np.sqrt(delta_lat**2 + delta_lon**2) * 111.0
    
    # Telemetry metrics interface row
    st.markdown(f"""
    <div class="status-pill-container">
        <div class="status-pill"><div style="font-size:10px; color:#8b949e;">TEMP</div><div class="pill-val" style="color:#ff4757;">{test_temp}°C</div></div>
