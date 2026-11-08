import streamlit as st
import pandas as pd
import numpy as np
import time

# --- 1. Global Page Setup ---
st.set_page_config(
    page_title="Tactical Command Matrix",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. Advanced Cyberpunk UI Design System Styling ---
st.markdown("""
    <style>
    /* Global Background and Terminal Typography Styling */
    .stApp {
        background-color: #0b0f14;
        color: #7fa483;
        font-family: 'Consolas', 'Courier New', monospace;
    }
    
    /* Top Integrated Threat Header System */
    .tactical-header-container {
        background-color: #1c140a;
        border: 2px solid #d27b11;
        border-radius: 4px;
        padding: 10px;
        text-align: center;
        margin-bottom: 6px;
        box-shadow: 0 0 15px rgba(210, 123, 17, 0.15);
    }
    .tactical-title {
        color: #e58713 !important;
        font-size: 24px !important;
        font-weight: 800;
        letter-spacing: 3px;
        margin: 0 !important;
        text-shadow: 0 0 5px rgba(229, 135, 19, 0.4);
    }
    .sub-status-bar {
        display: flex;
        justify-content: space-between;
        background-color: #170a0a;
        border: 1px solid #7c1a1a;
        border-radius: 4px;
        padding: 6px 15px;
        margin-bottom: 20px;
        font-size: 13px;
        font-weight: bold;
    }
    
    /* Window Pane Container Grid Mockups */
    .panel-box {
        background-color: #0d121a;
        border: 1px solid #1f2d3d;
        border-radius: 3px;
        padding: 12px;
        margin-bottom: 15px;
        position: relative;
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
    .panel-controls {
        color: #4b6584;
        font-size: 11px;
    }
    
    /* Matrix Grid Readout Styling */
    .matrix-coordinates {
        font-size: 11px;
        color: #4e6172;
        margin-top: 8px;
    }
    
    /* Live Log Monitor Sandbox Window */
    .log-monitor {
        background-color: #05070a;
        border: 1px solid #16202c;
        border-radius: 3px;
        padding: 8px;
        height: 120px;
        overflow-y: auto;
        font-size: 11px;
        color: #648a68;
        line-height: 1.4;
    }
    .log-line { margin-bottom: 3px; }
    .log-ts { color: #3a7bd5; }
    .log-warn { color: #d27b11; }
    .log-crit { color: #ff4757; }
    
    /* Metric Indicators block */
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
    .pill-val {
        font-size: 16px;
        font-weight: bold;
        color: #2ed573;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. Top Master Status Displays ---
st.markdown("""
<div class="tactical-header-container">
    <h1 class="tactical-title">TACTICAL ALERT: PERIMETER BREACH DETECTED</h1>
</div>
<div class="sub-status-bar">
    <span style="color: #e58713;">⚠️ SYSTEM STATUS: ACTIVE INCIDENT</span>
    <span style="color: #ff4757;">ZONE L-4 SECURING: 00:04:12 ⏱️</span>
</div>
""", unsafe_allow_html=True)

# --- 4. Main Two-Column Layout Grid Split ---
col_map, col_telemetry = st.columns(2)

with col_map:
    st.markdown("""
    <div class="panel-box">
        <div class="panel-header">
            <h3 class="panel-title">📡 3D TOPOGRAPHIC MAPPING MATRIX SYSTEM</h3>
            <span class="panel-controls">🗕 🗖 🗙</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    center_lat, center_lon = 34.0522, -118.2437
    map_dataframe = pd.DataFrame({
        'lat': [center_lat, center_lat + 0.008, center_lat - 0.005, center_lat + 0.003],
        'lon': [center_lon, center_lon - 0.007, center_lon + 0.009, center_lon - 0.003],
        'status': ['CORE HUB', 'HOSTILE ACT. (9)', 'UNIT ALPHA (READY)', 'UNITY UNIT 3']
    })
    
    st.map(map_dataframe, latitude='lat', longitude='lon', zoom=13)
    st.markdown('<div class="matrix-coordinates">LAT 34.052, LON -118.243 | GRID ZONE REFERENCE: L-4</div>', unsafe_allow_html=True)

with col_telemetry:
    st.markdown("""
    <div class="panel-box">
        <div class="panel-header">
            <h3 class="panel-title">📊 SCI-FI SENSOR TELEMETRY GRID</h3>
            <span class="panel-controls">🗕 🗖 🗙</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    sub_tel_left, sub_tel_right = st.columns(2)
    
    with sub_tel_left:
        st.write("### ENVIRONMENTAL READS")
        chart_data_1 = pd.DataFrame(
            np.sin(np.linspace(0, 10, 20)) * 5 + 34.5,
            columns=['TEMP INDEX (°C)']
        )
        st.line_chart(chart_data_1, height=130, use_container_width=True)
        st.markdown("<p style='font-size:11px; text-align:center;'>TEMP: 34.5°C | HUMIDITY: 62%</p>", unsafe_allow_html=True)
        
    with sub_tel_right:
        st.write("### POWER GRID DRAW")
        chart_data_2 = pd.DataFrame(
            np.random.randint(70, 98, size=(10, 1)),
            columns=['MAIN HUB DRAW (%)']
        )
        st.bar_chart(chart_data_2, height=130, use_container_width=True)
        st.markdown("<p style='font-size:11px; text-align:center;'>POWER INTEGRITY: 94% NOMINAL</p>", unsafe_allow_html=True)

    st.markdown("""
    <div class="status-pill-container">
        <div class="status-pill"><div style="font-size:10px; color:#8b949e;">UNIT HEALTH</div><div class="pill-val">98%</div></div>
        <div class="status-pill"><div style="font-size:10px; color:#8b949e;">COMMS</div><div class="pill-val" style="color:#e58713;">62%</div></div>
        <div class="status-pill"><div style="font-size:10px; color:#8b949e;">COMMS STATUS</div><div class="pill-val">SECURE</div></div>
    </div>
    """, unsafe_allow_html=True)

# --- 5. Terminal Console Window Logging Modules ---
st.markdown("""
<div class="panel-box">
    <div class="panel-header">
        <h3 class="panel-title">💻 CONSOLE LOG MONITOR SYSTEM</h3>
        <span class="panel-controls">🗕 🗖 🗙</span>
    </div>
</div>
""", unsafe_allow_html=True)

ts = time.strftime("%H:%M:%S")
st.markdown(f"""
<div class="log-monitor">
    <div class="log-line"><span class="log-ts">[{ts}:01]</span> <span class="log-crit">SYS: Perimeter sensor fence L-4 reporting breach. Target acquired.</span></div>
    <div class="log-line"><span class="log-ts">[{ts}:04]</span> CMD: Initializing Zone L-4 defensive lockdown protocols...</div>
    <div class="log-line"><span class="log-ts">[{ts}:09]</span> LOG: Dispatching Tactical Unit Alpha to coordinate arrays.</div>
    <div class="log-line"><span class="log-ts">[{ts}:15]</span> <span class="log-warn">ALERT: Secondary sub-system validation latency detected in comms mesh network.</span></div>
    <div class="log-line"><span class="log-ts">[{ts}:21]</span> CMD: Escalation to CRITICAL matrix operational parameters confirmed.</div>
</div>
""", unsafe_allow_html=True)

# --- 6. Tactical Navigation Action Buttons ---
st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)

with btn_col1:
    if st.button("🚨 ACKNOWLEDGE ALERT", use_container_width=True, type="primary"):
        st.toast("Threat matrix acknowledged by Master Operator.", icon="🚨")
with btn_col2:
    if st.button("🚀 DEPLOY SQUAD VECTOR", use_container_width=True):
        st.toast("Dispatched Unit Alpha backup support assets.", icon="🚀")
with btn_col3:
    if st.button("🔓 COMMAND TERMINAL LOGOUT", use_container_width=True):
        st.toast("Terminating current matrix operational terminal state.", icon="🔒")
with btn_col4:
    if st.button("⚙️ CHECK SYSTEM STATUS", use_container_width=True):
        st.toast("Running core status evaluation diagnostics...", icon="⚙️")
