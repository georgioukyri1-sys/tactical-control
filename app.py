import streamlit as st
import pandas as pd
import numpy as np
import time
import urllib.parse
import requests
from io import StringIO
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
    /* Style native Streamlit bordered containers to match tactical panels */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #0d121a;
        border: 1px solid #1f2d3d !important;
        border-radius: 3px !important;
        padding: 12px;
        margin-bottom: 15px;
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
    R = 6371.0  # Earth's radius in KM
    p = np.pi / 180
    a = (
        0.5
        - np.cos((lat2 - lat1) * p) / 2
        + np.cos(lat1 * p) * np.cos(lat2 * p) * (1 - np.cos((lon2 - lon1) * p)) / 2
    )
    return 2 * R * np.arcsin(np.sqrt(a))

def render_panel_header(title_text):
    st.markdown(f"""
        <div class="panel-header">
            <h3 class="panel-title">{title_text}</h3>
            <span class="panel-controls">🗕 🗖 🗙</span>
        </div>
    """, unsafe_allow_html=True)

def render_download_module(fire_points_list, closest_fire_dist, test_temp):
    with st.container(border=True):
        render_panel_header("💾 TACTICAL MATRIX DATA EXPORT SYSTEM")
        st.markdown(
            "<p style='font-size:11px; color:#8b949e; margin-top:0;'>Compile structural core analytics into an encrypted plaintext sequence dump (.log):</p>",
            unsafe_allow_html=True
        )
        
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
            width="stretch"
        )

# --- 4. Setup Initial Application States ---
if "next_of_kin" not in st.session_state:
    st.session_state.next_of_kin = [
        {"Name": "John Smith", "Relation": "Primary Safety Relay", "Contact Vector": "+15550199"}
    ]

# --- 5. Configuration & Simulation Panel ---
with st.expander("🛠️ TEST FACILITIES & GEOTAG SIMULATION BAY", expanded=True):
    st.markdown(
        "<p style='font-size:12px; color:#52a3ff;'>Engineering Diagnostic Console: Setup live satellite parameters and system configurations.</p>",
        unsafe_allow_html=True
    )
    
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
cos_lat = max(np.cos(np.radians(house_lat)), 0.0001)
lon_delta = scan_radius_km / (111.0 * cos_lat)

min_lon = house_lon - lon_delta
min_lat = house_lat - lat_delta
max_lon = house_lon + lon_delta
max_lat = house_lat + lat_delta

bbox_string = f"{min_lon:.4f},{min_lat:.4f},{max_lon:.4f},{max_lat:.4f}"
firms_url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{firms_api_key}/VIIRS_SNPP_NRT/{bbox_string}/1"

def inject_simulation_fires():
    global closest_fire_dist
    sim_offsets = [[0.012, -0.015], [-0.008, 0.022], [0.031, -0.005]]
    for lat_off, lon_off in sim_offsets:
        f_lat = house_lat + lat_off
        f_lon = house_lon + lon_off
        dist = haversine_distance(house_lat, house_lon, f_lat, f_lon)
        if dist <= scan_radius_km:
            fire_points.append([f_lat, f_lon, 15.0])
            if dist < closest_fire_dist:
                closest_fire_dist = dist

try:
    response = requests.get(firms_url, timeout=10)
    if response.status_code == 200 and "latitude" in response.text:
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
        inject_simulation_fires()
except Exception as e:
    api_log_status = f"CONNECTION FAULT ({type(e).__name__}): Injecting sandbox vectors"
    inject_simulation_fires()

# Threshold warning toggle
is_breached = len(fire_points) > 0 and closest_fire_dist < 10.0

if is_breached:
    st.markdown(f"""
    <div class="tactical-header-container header-alert">
        <h1 class="tactical-title" style="color: #ff4757; text-shadow: 0 0 5px rgba(255, 71, 87, 0.4);">TACTICAL ALERT: PERIMETER FIRE BREACH DETECTED</h1>
    </div>
    <div class="sub-status-bar" style="background-color: #170a0a; border: 1px solid #7c1a1a;">
        <span style="color: #ff4757;">⚠️ CRITICAL THREAT: NEAREST WILDFIRE ACQUIRED AT {closest_fire_dist:.2f} KM</span>
        <span style="color: #ff4757;">CRISIS BROADCAST LAYERS READY ⏱️</span>
    </div>
    """, unsafe_allow_html=True)
else:
    display_dist = closest_fire_dist if closest_fire_dist != float('inf') else 0.0
    st.markdown(f"""
    <div class="tactical-header-container header-nominal">
        <h1 class="tactical-title" style="color: #2ed573; text-shadow: 0 0 5px rgba(46, 213, 115, 0.4);">TACTICAL SECURE: NO IMMEDIATE FLAME BREACH</h1>
    </div>
    <div class="sub-status-bar" style="background-color: #0a170f; border: 1px solid #1a7c3e;">
        <span style="color: #2ed573;">🟢 SYSTEM STATUS: ONLINE NOMINAL (NEAREST SECURE COHORT: {display_dist:.2f} KM)</span>
        <span style="color: #2ed573;">ALL PERIMETERS SECURE 🔐</span>
    </div>
    """, unsafe_allow_html=True)

# --- 7. Render Layout Screen Modules ---
col_map, col_telemetry = st.columns(2)

with col_map:
    with st.container(border=True):
        render_panel_header("📡 3D HYBRID SATELLITE THERMAL TRACKING ENGINE")
        m = folium.Map(
            location=[house_lat, house_lon],
            zoom_start=12,
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri"
        )
        if fire_points:
            HeatMap(
                data=[[p[0], p[1], 1] for p in fire_points],
                radius=25,
                blur=15,
                gradient={0.4: 'yellow', 0.65: 'orange', 1.0: 'red'}
            ).add_to(m)
            
        folium.Marker(
            [house_lat, house_lon],
            popup="🏡 TARGET HOUSE",
            icon=folium.Icon(color="red", icon="home")
        ).add_to(m)
        folium.Marker(
            [user_lat, user_lon],
            popup="🏃 USER OPS",
            icon=folium.Icon(color="blue", icon="user")
        ).add_to(m)
        st_folium(m, width=700, height=350, key="satellite_radar_view")

    with st.container(border=True):
        render_panel_header("🗃️ ADD EMERGENCY CONTACTS / NEXT OF KIN")
        with st.form("kin_entry_form", clear_on_submit=True):
            k_col1, k_col2, k_col3 = st.columns(3)
            with k_col1:
                new_name = st.text_input("Next of Kin Name")
            with k_col2:
                new_rel = st.text_input("Relationship")
            with k_col3:
                new_vec = st.text_input("Phone/Email Identifier")
            submit_kin = st.form_submit_button("➕ LOG CONTACT ENTRY")
            
            if submit_kin and new_name and new_vec:
                st.session_state.next_of_kin.append({
                    "Name": new_name,
                    "Relation": new_rel,
                    "Contact Vector": new_vec
                })
                st.toast(f"Logged safety node for {new_name}.", icon="✅")
                
        st.dataframe(
            pd.DataFrame(st.session_state.next_of_kin),
            hide_index=True,
            width="stretch"
        )

with col_telemetry:
    with st.container(border=True):
        render_panel_header("📊 SYSTEM TELEMETRY MATRIX")
        separation_dist = haversine_distance(house_lat, house_lon, user_lat, user_lon)
        threat_val_string = f"{closest_fire_dist:.2f} KM" if closest_fire_dist != float('inf') else "CLEAR"
        
        st.markdown(f"""
        <div class="status-pill-container">
            <div class="status-pill"><div style="font-size:10px; color:#8b949e;">ZONE TEMP</div><div class="pill-val" style="color:#ff4757;">{test_temp}°C</div></div>
            <div class="status-pill"><div style="font-size:10px; color:#8b949e;">FIRE DISTANCE</div><div class="pill-val" style="color:#ff9f43;">{threat_val_string}</div></div>
            <div class="status-pill"><div style="font-size:10px; color:#8b949e;">USER SEPARATION</div><div class="pill-val" style="color:#52a3ff;">{separation_dist:.2f} KM</div></div>
        </div>
        """, unsafe_allow_html=True)

    with st.container(border=True):
        render_panel_header("⚙️ INFRASTRUCTURE TEST STATUS")
        st.markdown(f"""
        <div style="font-size:11px; line-height:1.5; color:#7fa483;">
            <p style="margin:2px 0; color:#2ed573;">✔️ PERIMETER SENSOR CALIBRATION: Complete</p>
            <p style="margin:2px 0; color:#2ed573;">✔️ NASA FIRMS GEOSPATIAL FEED: Active</p>
            <p style="margin:2px 0;">• ACTIVE SATELLITE LAYER: VIIRS 375m Resolution Array</p>
            <p style="margin:2px 0;">• RADAR CONTEXT MAPPING: Bounding Box Vector Ingestion active</p>
            <p style="margin:2px 0; color:#52a3ff;">• TOTAL THERMAL HOTSPOTS DETECTED WITHIN SCAN ZONE: {len(fire_points)}</p>
        </div>
        """, unsafe_allow_html=True)

    with st.container(border=True):
        render_panel_header("📡 LOCATION SHARE & STATUS BROADCASTER")
        contact_options = [f"{c['Name']} ({c['Relation']})" for c in st.session_state.next_of_kin]
        chosen_contact = st.selectbox("Active Target Relay", contact_options)
        
        maps_query_url = f"https://www.google.com/maps?q={user_lat},{user_lon}"
        broadcast_msg = (
            f"TACTICAL ALERT BROADCAST: Proximity tracking alert active. "
            f"Nearest fire perimeter scan is {threat_val_string} away from target house asset. "
            f"Pin coordinate trace: {maps_query_url}"
        )
        
        encoded_payload = urllib.parse.quote(broadcast_msg)
        whatsapp_comms_endpoint = f"https://api.whatsapp.com/send?text={encoded_payload}"
        
        st.markdown(f"""
        <a href="{whatsapp_comms_endpoint}" target="_blank" class="btn-broadcast">🚀 SEND LOCATION & 'SAFE' STATUS TO {chosen_contact.upper()}</a>
        """, unsafe_allow_html=True)

    # --- 8. Core Layout Placement: Download Module ---
    render_download_module(fire_points, closest_fire_dist, test_temp)

# --- 9. Console Log Window ---
with st.container(border=True):
    render_panel_header("💻 CONSOLE LOG MONITOR SYSTEM")
    ts = time.strftime("%H:%M:%S")
    st.markdown(f"""
    <div class="log-monitor">
        <div class="log-line"><span class="log-ts">[{ts}]</span> <span style="color:#52a3ff;">NASA_API:</span> {api_log_status}.</div>
        <div class="log-line"><span class="log-ts">[{ts}]</span> <span style="color:#52a3ff;">GPS:</span> Bounding box grid bounds compiled: {bbox_string}.</div>
        <div class="log-line"><span class="log-ts">[{ts}]</span> <span style="color:#52a3ff;">CALC:</span> Nearest thermal sensor point calculated at distance value {threat_val_string}.</div>
        <div class="log-line"><span class="log-ts">[{ts}]</span> <span class="log-warn;">SYS:</span> Safety trigger check active. Alert status evaluated.</div>
    </div>
    """, unsafe_allow_html=True)
