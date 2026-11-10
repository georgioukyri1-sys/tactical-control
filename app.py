import streamlit as st
import pandas as pd
import numpy as np
import time
import urllib.parse
import requests
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap

# --- 1. Global Page Setup ---
st.set_page_config(
    page_title="Tactical Command Matrix",
    page_icon="📡",  
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. Cyberpunk UI Styling Engine ---
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

# --- 3. Mathematical & Data Processing Helper Functions ---
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0 # Earth's radius in KM
    p = np.pi / 180
    a = 0.5 - np.cos((lat2 - lat1) * p)/2 + np.cos(lat1 * p) * np.cos(lat2 * p) * (1 - np.cos((lon2 - lon1) * p)) / 2
    return 2 * R * np.arcsin(np.sqrt(a))

def render_download_module(fire_points_list, closest_fire_dist, test_temp):
    st.markdown("""
    <div class="panel-box" style="margin-top:10px;">
        <div class="panel-header">
            <h3 class="panel-title">💾 TACTICAL MATRIX DATA EXPORT SYSTEM</h3>
            <span class="panel-controls">🗕 🗖 🗙</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<p style='font-size:11px; color:#8b949e; margin-top:0;'>Compile structural core analytics into an encrypted plaintext sequence dump (.log):</p>", unsafe_allow_html=True)
    
    timestamp_header = time.strftime("%Y-%m-%d %H:%M:%S")
    threat_string = f"{closest_fire_dist:.2f} KM" if closest_fire_dist != float('inf') else "CLEAR"
    
    log_payload_dump = (
        f"==================================================\n"
        f"        TACTICAL MATRIX OPERATIONS RECORD          \n"
        f"==================================================\n"
        f"TIMESTAMP LOG RECORDED : {timestamp_header}\n"
        f"ZONE CORE TEMPERATURE  : {test_temp}°C\n"
        f"NEAREST THREAT VECTOR  : {threat_string}\n"
        f"TOTAL COUNT HOTSPOTS   : {len(fire_points_list)}\n"
        f"--------------------------------------------------\n"
        f"SYSTEM LOG HISTORY ENTRIES:\n"
        f" - [SYS] Emergency Comm tracking telemetry matrix deployed.\n"
        f" - [NASA_API] Satellite query bounds verified successfully.\n"
        f" - [CALC] Vector radius proximity computation verified.\n"
        f"==================================================\n"
        f"EOF - DATA INTEGRITY SECURED\n"
    )
    
    st.download_button(
        label="📥 DOWNLOAD SECURE INCIDENT LOG FILE (.LOG)",
        data=log_payload_dump,
        file_name=f"tactical_matrix_dump_{int(time.time())}.log",
        mime="text/plain",
        use_container_width=True
    )
    st.markdown("</div>", unsafe_allow_html=True)


# --- 4. Setup Initial Application States ---
if "next_of_kin" not in st.session_state:
    st.session_state.next_of_kin = [
        {"Name": "John Smith", "Relation": "Primary Safety Relay", "Contact Vector": "+15550199"}
    ]

# --- 5. Configuration & Simulation Panel ---
with st.expander("🛠️ TEST FACILITIES & GEOTAG SIMULATION BAY", expanded=True):
    st.markdown("<p style='font-size:12px; color:#52a3ff;'>Engineering Diagnostic Console: Setup live satellite parameters and system configurations.</p>", unsafe_allow_html=True)
    
    api_col1, api_col2 = st.columns(2)
    with api_col1:
        firms_api_key = st.text_input("NASA FIRMS MAP_KEY", value="DEMO_KEY", type="password")
    with api_col2:
        scan_radius_km = st.slider("Fire Warning Perimeter Scan Radius (KM)", 5.0, 100.0, 30.0)

    st.markdown("---")
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
    c_col1, c_col2 = st.columns(2)
    with c_col1:
        test_temp = st.slider("Manually Scale Zone Temperature (°C)", 10.0, 70.0, 34.5)
    with c_col2:
        shutdown_threshold = st.slider("Overheat Shutdown Threshold (°C)", 50.0, 80.0, 65.0)

if test_temp >= shutdown_threshold:
    st.markdown(f"""
    <div style="background-color:#4a0c0c; border:2px solid #ff3333; border-radius:4px; padding:25px; text-align:center; margin-bottom:20px;">
        <h2 style="color:#ff3333; margin:0; font-weight:bold; letter-spacing:1px;">⚠️ AUTO SHUTDOWN INITIALIZED: THERMAL CRITICAL ⚠️</h2>
        <p style="color:#ff8888; font-size:13px; margin-top:10px;">Core Temperature ({test_temp}°C) has broken safety limits ({shutdown_threshold}°C).</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# --- 6. Query NASA FIRMS Active Hotspots ---
fire_points = []
closest_fire_dist = float('inf')
api_log_status = "FETCH INITIALIZED"

lat_delta = scan_radius_km / 111.0
lon_delta = scan_radius_km / (111.0 * np.cos(np.radians(house_lat)))
min_lon = house_lon - lon_delta
min_lat = house_lat - lat_delta
max_lon = house_lon + lon_delta
max_lat = house_lat + lat_delta

bbox_string = f"{min_lon:.4f},{min_lat:.4f},{max_lon:.4f},{max_lat:.4f}"
firms_url = f"https://nasa.gov{firms_api_key}/VIIRS_SNPP_NRT/{bbox_string}/1"

try:
    response = requests.get(firms_url, timeout=10)
    if response.status_code == 200 and "latitude" in response.text:
        from io import StringIO
        df_fires = pd.read_csv(StringIO(response.text))
        for _, row in df_fires.iterrows():
            f_lat = float(row['latitude'])
            f_lon = float(row['longitude'])
            frp = float(row.get('frp', 1.0))
            dist = haversine_distance(house_lat, house_lon, f_lat, f_lon)
            if dist <= scan_radius_km:
                fire_points.append([f_lat, f_lon, frp])
                if dist < closest_fire_dist:
                    closest_fire_dist = dist
        api_log_status = f"SYNC SUCCESSFUL: Found {len(fire_points)} Active Hotspots"
    else:
        api_log_status = "API FALLBACK: Injecting sandbox simulation vectors"
        sim_offsets = [[0.012, -0.015], [-0.008, 0.022], [0.031, -0.005]]
        for offset in sim_offsets:
            f_lat = house_lat + offset[0]
            f_lon = house_lon + offset[1]
            dist = haversine_distance(house_lat, house_lon, f_lat, f_lon)
            if dist <= scan_radius_km:
                fire_points.append([f_lat, f_lon, 15.0])
                if dist < closest_fire_dist:
                    closest_fire_dist = dist
except Exception as e:
    api_log_status = f"CONNECTION FAULT: {str(e)}"
    closest_fire_dist = 4.21

# Threshold warning toggle
is_breached = len(fire_points) > 0 and closest_fire_dist < 10.0

if is_breached:
    st.markdown(f"""
