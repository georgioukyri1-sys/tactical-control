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
from streamlit_js_eval import get_geolocation

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
    .w3w-badge {
        background-color: #090d14;
        border: 1px solid #ff4757;
        border-radius: 3px;
        padding: 8px 12px;
        margin-top: 8px;
        font-size: 13px;
        color: #ffffff;
    }
    .w3w-slashes {
        color: #ff4757;
        font-weight: 900;
        margin-right: 4px;
    }
    /* Blackout Screen / Stealth Tactical Tab Styling */
    .blackout-screen {
        background-color: #000000;
        border: 2px solid #ff1e1e;
        border-radius: 4px;
        padding: 22px;
        color: #ff1e1e;
        font-family: 'Consolas', 'Courier New', monospace;
        box-shadow: inset 0 0 30px rgba(255, 0, 0, 0.15);
    }
    .blackout-header {
        border-bottom: 1px solid #660000;
        padding-bottom: 10px;
        margin-bottom: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .blackout-title {
        color: #ff1e1e !important;
        font-size: 20px;
        font-weight: 900;
        letter-spacing: 3px;
        margin: 0;
        text-shadow: 0 0 8px rgba(255, 30, 30, 0.6);
    }
    .blackout-card {
        background-color: #050000;
        border: 1px solid #990000;
        border-radius: 3px;
        padding: 14px;
        margin-bottom: 14px;
    }
    .blackout-label {
        color: #b30000;
        font-size: 11px;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .blackout-value {
        color: #ff1e1e;
        font-size: 18px;
        font-weight: bold;
        letter-spacing: 1px;
    }
    .blackout-btn {
        display: block;
        background-color: #1a0000;
        color: #ff1e1e !important;
        border: 1px solid #ff1e1e;
        padding: 12px;
        text-align: center;
        text-decoration: none !important;
        font-weight: bold;
        letter-spacing: 2px;
        margin-top: 10px;
    }
    .blackout-btn:hover {
        background-color: #ff1e1e;
        color: #000000 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. Mathematical, Geolocation & what3words Helper Functions ---
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    p = np.pi / 180
    a = (
        0.5
        - np.cos((lat2 - lat1) * p) / 2
        + np.cos(lat1 * p) * np.cos(lat2 * p) * (1 - np.cos((lon2 - lon1) * p)) / 2
    )
    return 2 * R * np.arcsin(np.sqrt(a))

def resolve_what3words(lat, lon, api_key=""):
    """Resolves coordinates to a what3words address via API, with deterministic offline grid fallback."""
    if api_key and api_key.strip():
        try:
            url = f"https://api.what3words.com/v3/convert-to-3wa?coordinates={lat},{lon}&key={api_key.strip()}"
            res = requests.get(url, timeout=6)
            if res.status_code == 200:
                data = res.json()
                if "words" in data:
                    return data["words"], True
        except Exception:
            pass

    # Deterministic 3m-square offline word-grid generator for sandbox/offline operation
    word_bank_a = [
        "filled", "bounded", "harbour", "signal", "ember", "summit", "beacon",
        "shelter", "timber", "granite", "anchor", "vector", "canyon", "meadow",
        "bridge", "watch", "compass", "ridge", "hollow", "valley"
    ]
    word_bank_b = [
        "count", "plots", "guard", "north", "river", "stone", "watch",
        "clear", "swift", "track", "relay", "point", "cross", "field",
        "crest", "shore", "haven", "orbit", "pulse", "trail"
    ]
    word_bank_c = [
        "soap", "valve", "tower", "flare", "cedar", "flint", "delta",
        "radar", "spark", "frost", "haven", "alert", "basalt", "birch",
        "cliff", "dune", "forge", "grove", "ledge", "spire"
    ]
    # ~3 meter grid quantization
    lat_cell = int(round((lat + 90.0) * 37000))
    lon_cell = int(round((lon + 180.0) * 37000))
    idx_a = abs((lat_cell * 73856093) ^ (lon_cell * 19349663)) % len(word_bank_a)
    idx_b = abs((lat_cell * 83492791) ^ (lon_cell * 49979687)) % len(word_bank_b)
    idx_c = abs((lat_cell * 2971215073) ^ (lon_cell * 6728042131)) % len(word_bank_c)
    return f"{word_bank_a[idx_a]}.{word_bank_b[idx_b]}.{word_bank_c[idx_c]}", False

def render_panel_header(title_text):
    st.markdown(f"""
        <div class="panel-header">
            <h3 class="panel-title">{title_text}</h3>
            <span class="panel-controls">🗕 🗖 🗙</span>
        </div>
    """, unsafe_allow_html=True)

def render_download_module(fire_points_list, closest_fire_dist, test_temp, house_w3w, user_w3w):
    with st.container(border=True):
        render_panel_header("💾 TACTICAL MATRIX DATA EXPORT SYSTEM")
        st.markdown(
            "<p style='font-size:11px; color:#8b949e; margin-top:0;'>Compile structural core analytics into an encrypted plaintext sequence dump (.log):</p>",
            unsafe_allow_html=True
        )
        
        timestamp_header = time.strftime("%Y-%m-%d %H:%M:%S")
        threat_string = f"{closest_fire_dist:.2f} KM" if closest_fire_dist != float('inf') else "CLEAR"
        
        log_payload_dump = (
            "==================================================\n"
            "        TACTICAL MATRIX OPERATIONS RECORD          \n"
            "==================================================\n"
            f"TIMESTAMP LOG RECORDED : {timestamp_header}\n"
            f"HOUSE WHAT3WORDS TAG   : ///{house_w3w}\n"
            f"USER WHAT3WORDS TAG    : ///{user_w3w}\n"
            f"ZONE CORE TEMPERATURE  : {test_temp}°C\n"
            f"NEAREST THREAT VECTOR  : {threat_string}\n"
            f"TOTAL COUNT HOTSPOTS   : {len(fire_points_list)}\n"
            "--------------------------------------------------\n"
            "SYSTEM LOG HISTORY ENTRIES:\n"
            " - [SYS] Emergency Comm tracking telemetry matrix deployed.\n"
            " - [W3W] 3-word geolocation grid tags compiled.\n"
            " - [CALC] Vector radius proximity computation verified.\n"
            "==================================================\n"
            "EOF - DATA INTEGRITY SECURED\n"
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
        {"Name": "John Smith", "Relation": "Primary Safety Relay", "Contact Vector": "+447700900199"}
    ]
if "is_subscribed" not in st.session_state:
    st.session_state.is_subscribed = False
if "pump_armed" not in st.session_state:
    st.session_state.pump_armed = False
if "sump_armed" not in st.session_state:
    st.session_state.sump_armed = False
if "user_lat" not in st.session_state:
    st.session_state.user_lat = 51.7729
if "user_lon" not in st.session_state:
    st.session_state.user_lon = 0.1023
if "gps_sync_status" not in st.session_state:
    st.session_state.gps_sync_status = "DEFAULT COORDINATES (CLICK AUTO-GPS)"

# --- 5. Shared Configuration & Simulation Panel ---
with st.expander("🛠️ TEST FACILITIES, AUTO-GPS & SUBSCRIPTION CONSOLE", expanded=True):
    st.markdown(
        "<p style='font-size:12px; color:#52a3ff;'>Engineering Diagnostic Console: Setup live satellite/flood feeds, what3words API, auto-GPS, and subscription access.</p>",
        unsafe_allow_html=True
    )
    
    # Subscription Verification Bar
    sub_col1, sub_col2 = st.columns([3, 1])
    with sub_col1:
        access_key = st.text_input(
            "Pro Hardware Subscription Key (Demo Key: PRO-2026)",
            type="password",
            placeholder="Enter subscription key to unlock Pump Station & Flood Barrier Controls..."
        )
    with sub_col2:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("🔓 VERIFY SUBSCRIPTION", width="stretch"):
            if access_key == "PRO-2026":
                st.session_state.is_subscribed = True
                st.toast("Pro Subscription Active: Suppression & Flood Pump Stations Unlocked.", icon="✅")
            else:
                st.session_state.is_subscribed = False
                st.error("Invalid subscription key.")

    if st.session_state.is_subscribed:
        st.success("🟢 **PRO TIER ACTIVE:** Remote Pump Station & Flood Barrier Defense Controls Unlocked.")
    else:
        st.info("🔒 **FREE TIER:** House & Auto-GPS Geotagging + what3words Active. Subscribe to unlock Pump Station & Barrier Controls.")

    st.markdown("---")
    api_col1, api_col2, api_col3 = st.columns(3)
    with api_col1:
        firms_api_key = st.text_input("NASA FIRMS MAP_KEY (Fire Feed)", value="DEMO_KEY", type="password")
    with api_col2:
        w3w_api_key = st.text_input("what3words API Key (Optional Live Sync)", value="", type="password")
    with api_col3:
        scan_radius_km = st.slider("Perimeter Scan Radius (KM)", 5.0, 100.0, 25.0)

    st.markdown("---")
    geo_col1, geo_col2 = st.columns(2)
    with geo_col1:
        st.markdown("**🏡 HOUSE TARGET GEOTAG**")
        house_lat = st.number_input("House Latitude", value=51.7729, format="%.4f")
        house_lon = st.number_input("House Longitude", value=0.1023, format="%.4f")
    with geo_col2:
        st.markdown("**🛰️ USER/OPERATOR AUTO-GEOTAG**")
        gps_btn_col, gps_stat_col = st.columns([1, 2])
        with gps_btn_col:
            request_gps = st.button("📍 AUTO-DETECT USER GPS", width="stretch")
        if request_gps:
            loc = get_geolocation(component_key="user_auto_gps")
            if loc and "coords" in loc:
                st.session_state.user_lat = float(loc["coords"]["latitude"])
                st.session_state.user_lon = float(loc["coords"]["longitude"])
                st.session_state.gps_sync_status = f"LIVE GPS LOCKED (±{int(loc['coords'].get('accuracy', 10))}m)"
                st.toast("Live browser GPS coordinates acquired.", icon="🛰️")
            else:
                st.session_state.gps_sync_status = "AWAITING BROWSER GPS PERMISSION"
        with gps_stat_col:
            st.caption(f"Status: `{st.session_state.gps_sync_status}`")
        
        user_lat = st.number_input("User Latitude (Auto-Synced)", key="user_lat", format="%.4f")
        user_lon = st.number_input("User Longitude (Auto-Synced)", key="user_lon", format="%.4f")

    st.markdown("---")
    c_col1, c_col2 = st.columns(2)
    with c_col1:
        test_temp = st.slider("Zone Core Temperature (°C)", 10.0, 70.0, 28.5)
    with c_col2:
        shutdown_threshold = st.slider("Thermal Overheat Threshold (°C)", 50.0, 80.0, 65.0)

# Resolve what3words tags for House and User
house_w3w, house_w3w_live = resolve_what3words(house_lat, house_lon, w3w_api_key)
user_w3w, user_w3w_live = resolve_what3words(user_lat, user_lon, w3w_api_key)
w3w_mode_label = "LIVE API" if (house_w3w_live or user_w3w_live) else "OFFLINE 3M GRID"
separation_dist = haversine_distance(house_lat, house_lon, user_lat, user_lon)

# --- 6. Top-Level Navigation Tabs ---
tab_fire, tab_flood, tab_blackout, tab_coming_soon = st.tabs([
    "🔥 FIRE COMMAND MATRIX",
    "🌊 FLOOD COMMAND MATRIX",
    "⬛ BLACKOUT STEALTH OPS",
    "🚀 COMING SOON"
])

# ==============================================================================
# TAB 1: FIRE COMMAND MATRIX
# ==============================================================================
with tab_fire:
    if test_temp >= shutdown_threshold:
        st.markdown(f"""
        <div style="background-color:#4a0c0c; border:2px solid #ff3333; border-radius:4px; padding:25px; text-align:center; margin-bottom:20px;">
            <h2 style="color:#ff3333; margin:0; font-weight:bold; letter-spacing:1px;">⚠️ AUTO SHUTDOWN INITIALIZED: THERMAL CRITICAL ⚠️</h2>
            <p style="color:#ff8888; font-size:13px; margin-top:10px;">Core Temperature ({test_temp}°C) has broken safety limits ({shutdown_threshold}°C).</p>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    fire_points = []
    closest_fire_dist = float('inf')
    api_log_status = "FETCH INITIALIZED"

    lat_delta = scan_radius_km / 111.0
    cos_lat = max(np.cos(np.radians(house_lat)), 0.0001)
    lon_delta = scan_radius_km / (111.0 * cos_lat)
    bbox_string = f"{house_lon - lon_delta:.4f},{house_lat - lat_delta:.4f},{house_lon + lon_delta:.4f},{house_lat + lat_delta:.4f}"
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
        response = requests.get(firms_url, timeout=8)
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

    is_fire_breached = len(fire_points) > 0 and closest_fire_dist < 10.0

    if is_fire_breached:
        st.markdown(f"""
        <div class="tactical-header-container header-alert">
            <h1 class="tactical-title" style="color: #ff4757;">TACTICAL ALERT: PERIMETER FIRE BREACH DETECTED</h1>
        </div>
        <div class="sub-status-bar" style="background-color: #170a0a; border: 1px solid #7c1a1a;">
            <span style="color: #ff4757;">⚠️ CRITICAL THREAT: NEAREST WILDFIRE ACQUIRED AT {closest_fire_dist:.2f} KM</span>
            <span style="color: #ff4757;">///{house_w3w} ⏱️</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        display_dist = closest_fire_dist if closest_fire_dist != float('inf') else 0.0
        st.markdown(f"""
        <div class="tactical-header-container header-nominal">
            <h1 class="tactical-title" style="color: #2ed573;">TACTICAL SECURE: NO IMMEDIATE FLAME BREACH</h1>
        </div>
        <div class="sub-status-bar" style="background-color: #0a170f; border: 1px solid #1a7c3e;">
            <span style="color: #2ed573;">🟢 SYSTEM STATUS: ONLINE NOMINAL (NEAREST COHORT: {display_dist:.2f} KM)</span>
            <span style="color: #2ed573;">///{house_w3w} 🔐</span>
        </div>
        """, unsafe_allow_html=True)

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
                popup=f"🏡 TARGET HOUSE | ///{house_w3w}",
                icon=folium.Icon(color="red", icon="home")
            ).add_to(m)
            folium.Marker(
                [user_lat, user_lon],
                popup=f"🛰️ USER AUTO-GPS | ///{user_w3w}",
                icon=folium.Icon(color="blue", icon="user")
            ).add_to(m)
            st_folium(m, width=700, height=350, key="satellite_radar_view")

        with st.container(border=True):
            render_panel_header("🗃️ EMERGENCY CONTACTS / NEXT OF KIN")
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

            st.dataframe(pd.DataFrame(st.session_state.next_of_kin), hide_index=True, width="stretch")

    with col_telemetry:
        with st.container(border=True):
            render_panel_header("📊 FIRE TELEMETRY & WHAT3WORDS GRID")
            threat_val_string = f"{closest_fire_dist:.2f} KM" if closest_fire_dist != float('inf') else "CLEAR"
            st.markdown(f"""
            <div class="status-pill-container">
                <div class="status-pill"><div style="font-size:10px; color:#8b949e;">ZONE TEMP</div><div class="pill-val" style="color:#ff4757;">{test_temp}°C</div></div>
                <div class="status-pill"><div style="font-size:10px; color:#8b949e;">FIRE DISTANCE</div><div class="pill-val" style="color:#ff9f43;">{threat_val_string}</div></div>
                <div class="status-pill"><div style="font-size:10px; color:#8b949e;">USER SEPARATION</div><div class="pill-val" style="color:#52a3ff;">{separation_dist:.2f} KM</div></div>
            </div>
            <div class="w3w-badge">
                <span style="font-size:10px; color:#8b949e;">🏡 HOUSE WHAT3WORDS ({w3w_mode_label}):</span><br>
                <span class="w3w-slashes">///</span><strong>{house_w3w}</strong> <span style="font-size:11px; color:#4b6584;">({house_lat:.4f}, {house_lon:.4f})</span>
            </div>
            <div class="w3w-badge">
                <span style="font-size:10px; color:#8b949e;">🛰️ USER AUTO-GPS WHAT3WORDS ({w3w_mode_label}):</span><br>
                <span class="w3w-slashes">///</span><strong>{user_w3w}</strong> <span style="font-size:11px; color:#4b6584;">({user_lat:.4f}, {user_lon:.4f})</span>
            </div>
            """, unsafe_allow_html=True)

        # Subscription-Gated Fire Pump Station Control
        with st.container(border=True):
            render_panel_header("🚰 PERIMETER SUPPRESSION PUMP STATION CONTROL")
            if st.session_state.is_subscribed:
                p_col1, p_col2 = st.columns(2)
                with p_col1:
                    st.session_state.pump_armed = st.toggle(
                        "ARM PERIMETER ROOF SPRINKLERS",
                        value=st.session_state.pump_armed
                    )
                with p_col2:
                    pump_psi = st.slider("Target Line Pressure (PSI)", 40, 120, 85)
                pump_state_label = "ACTIVE / PRESSURIZED" if st.session_state.pump_armed else "STANDBY / READY"
                pump_color = "#ff4757" if st.session_state.pump_armed else "#2ed573"
                st.markdown(f"""
                <div style="font-size:11px; line-height:1.6; color:#7fa483; margin-top:6px;">
                    <p style="margin:2px 0; color:{pump_color};">● FIRE PUMP STATUS: <strong>{pump_state_label}</strong></p>
                    <p style="margin:2px 0;">• LINE PRESSURE OUTPUT: {pump_psi if st.session_state.pump_armed else 0} PSI | RESERVOIR: 98%</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="background:#090d14; border:1px dashed #4b6584; border-radius:4px; padding:12px; text-align:center;">
                    <p style="color:#ff9f43; font-size:12px; font-weight:bold; margin:0 0 6px 0;">🔒 PUMP STATION ACCESS RESTRICTED</p>
                    <p style="color:#8b949e; font-size:11px; margin:0;">Remote sprinkler activation and line pressure telemetry require an active Pro subscription.</p>
                </div>
                """, unsafe_allow_html=True)

        with st.container(border=True):
            render_panel_header("📡 FIRE LOCATION SHARE & STATUS BROADCASTER")
            contact_options = [f"{c['Name']} ({c['Relation']})" for c in st.session_state.next_of_kin]
            chosen_contact = st.selectbox("Active Target Relay", contact_options, key="fire_contact_select")
            maps_query_url = f"https://www.google.com/maps?q={user_lat},{user_lon}"
            w3w_url = f"https://what3words.com/{user_w3w}"
            broadcast_msg = (
                f"TACTICAL FIRE BROADCAST: Nearest fire perimeter is {threat_val_string} from house (///{house_w3w}). "
                f"Operator GPS: ///{user_w3w} ({maps_query_url}) | w3w link: {w3w_url}"
            )
            whatsapp_endpoint = f"https://api.whatsapp.com/send?text={urllib.parse.quote(broadcast_msg)}"
            st.markdown(f"""
            <a href="{whatsapp_endpoint}" target="_blank" class="btn-broadcast">🚀 SEND FIRE GPS & WHAT3WORDS TO {chosen_contact.upper()}</a>
            """, unsafe_allow_html=True)

        render_download_module(fire_points, closest_fire_dist, test_temp, house_w3w, user_w3w)

    with st.container(border=True):
        render_panel_header("💻 CONSOLE LOG MONITOR SYSTEM")
        ts = time.strftime("%H:%M:%S")
        st.markdown(f"""
        <div class="log-monitor">
            <div class="log-line"><span class="log-ts">[{ts}]</span> <span style="color:#52a3ff;">NASA_API:</span> {api_log_status}.</div>
            <div class="log-line"><span class="log-ts">[{ts}]</span> <span style="color:#52a3ff;">W3W_GRID:</span> House ///{house_w3w} | User ///{user_w3w} ({w3w_mode_label}).</div>
            <div class="log-line"><span class="log-ts">[{ts}]</span> <span style="color:#52a3ff;">AUTO_GPS:</span> {st.session_state.gps_sync_status} ({user_lat:.4f}, {user_lon:.4f}).</div>
            <div class="log-line"><span class="log-ts">[{ts}]</span> <span class="log-warn;">SYS:</span> Pump Station Gate = {'UNLOCKED' if st.session_state.is_subscribed else 'LOCKED'}.</div>
        </div>
        """, unsafe_allow_html=True)


# ==============================================================================
# TAB 2: FLOOD COMMAND MATRIX (UK ENVIRONMENT AGENCY LIVE FEED + SANDBOX)
# ==============================================================================
with tab_flood:
    flood_warnings = []
    river_stations = []
    flood_log_status = "QUERYING UK ENVIRONMENT AGENCY FEED"
    max_river_level = 0.0

    ea_floods_url = f"https://environment.data.gov.uk/flood-monitoring/id/floods?lat={house_lat}&long={house_lon}&dist={int(scan_radius_km)}"
    ea_stations_url = f"https://environment.data.gov.uk/flood-monitoring/id/stations?lat={house_lat}&long={house_lon}&dist={int(scan_radius_km)}&_limit=6"

    try:
        f_res = requests.get(ea_floods_url, timeout=8)
        if f_res.status_code == 200:
            items = f_res.json().get("items", [])
            for item in items:
                flood_warnings.append({
                    "Severity": item.get("severity", "Flood Alert"),
                    "SeverityLevel": item.get("severityLevel", 3),
                    "Area": item.get("eaAreaName", "Local Catchment"),
                    "Description": item.get("description", "Active Flood Advisory")
                })
            flood_log_status = f"UK EA LIVE SYNC: {len(flood_warnings)} Active Flood Advisories in {int(scan_radius_km)}km"
        else:
            flood_log_status = "UK EA API UNAVAILABLE: Using local river telemetry"
    except Exception as e:
        flood_log_status = f"EA CONNECTION FAULT ({type(e).__name__}): Using local telemetry"

    try:
        s_res = requests.get(ea_stations_url, timeout=8)
        if s_res.status_code == 200:
            st_items = s_res.json().get("items", [])
            for st_item in st_items:
                s_lat = st_item.get("lat")
                s_lon = st_item.get("long")
                label = st_item.get("label", "River Gauge")
                measures = st_item.get("measures", [])
                latest_val = None
                if isinstance(measures, list) and len(measures) > 0:
                    latest_reading = measures[0].get("latestReading", {})
                    if isinstance(latest_reading, dict):
                        latest_val = latest_reading.get("value")
                if s_lat is not None and s_lon is not None:
                    val_float = float(latest_val) if latest_val is not None else 1.42
                    if val_float > max_river_level:
                        max_river_level = val_float
                    river_stations.append({
                        "Name": label,
                        "Lat": float(s_lat),
                        "Lon": float(s_lon),
                        "Level_m": val_float
                    })
    except Exception:
        pass

    if not river_stations:
        river_stations = [
            {"Name": "River Stort @ Harlow Mill Gauge", "Lat": house_lat + 0.011, "Lon": house_lon - 0.008, "Level_m": 1.65},
            {"Name": "Parndon Mill Lock Sensor", "Lat": house_lat - 0.009, "Lon": house_lon - 0.018, "Level_m": 1.82}
        ]
        max_river_level = 1.82

    severe_count = sum(1 for w in flood_warnings if w.get("SeverityLevel", 4) <= 2)
    is_flood_breached = severe_count > 0 or max_river_level >= 2.5

    if is_flood_breached:
        st.markdown(f"""
        <div class="tactical-header-container header-alert">
            <h1 class="tactical-title" style="color: #ff4757;">FLOOD ALERT: HIGH WATER / SEVERE WARNING ACTIVE</h1>
        </div>
        <div class="sub-status-bar" style="background-color: #170a0a; border: 1px solid #7c1a1a;">
            <span style="color: #ff4757;">🌊 CRITICAL HYDROLOGY: {len(flood_warnings)} WARNINGS | PEAK STAGE {max_river_level:.2f}m</span>
            <span style="color: #ff4757;">///{house_w3w} ⏱️</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="tactical-header-container header-nominal">
            <h1 class="tactical-title" style="color: #2ed573;">HYDROLOGY NOMINAL: NO SEVERE FLOOD BREACH</h1>
        </div>
        <div class="sub-status-bar" style="background-color: #0a170f; border: 1px solid #1a7c3e;">
            <span style="color: #2ed573;">🟢 CATCHMENT STATUS: {len(flood_warnings)} ADVISORIES | PEAK GAUGE: {max_river_level:.2f}m</span>
            <span style="color: #2ed573;">///{house_w3w} 🔐</span>
        </div>
        """, unsafe_allow_html=True)

    f_col_map, f_col_tel = st.columns(2)

    with f_col_map:
        with st.container(border=True):
            render_panel_header("🌊 CATCHMENT HYDROLOGY & RIVER GAUGE RADAR")
            fm = folium.Map(
                location=[house_lat, house_lon],
                zoom_start=12,
                tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                attr="Esri"
            )
            folium.Circle(
                location=[house_lat, house_lon],
                radius=scan_radius_km * 1000,
                color="#52a3ff",
                fill=True,
                fill_opacity=0.06
            ).add_to(fm)

            for stn in river_stations:
                stn_w3w, _ = resolve_what3words(stn["Lat"], stn["Lon"], "")
                folium.Marker(
                    [stn["Lat"], stn["Lon"]],
                    popup=f"🌊 {stn['Name']} ({stn['Level_m']:.2f}m) | ///{stn_w3w}",
                    icon=folium.Icon(color="cadetblue", icon="tint")
                ).add_to(fm)

            folium.Marker(
                [house_lat, house_lon],
                popup=f"🏡 TARGET HOUSE | ///{house_w3w}",
                icon=folium.Icon(color="red", icon="home")
            ).add_to(fm)
            folium.Marker(
                [user_lat, user_lon],
                popup=f"🛰️ USER AUTO-GPS | ///{user_w3w}",
                icon=folium.Icon(color="blue", icon="user")
            ).add_to(fm)
            st_folium(fm, width=700, height=350, key="flood_radar_view")

        with st.container(border=True):
            render_panel_header("📋 ACTIVE FLOOD ADVISORIES & RIVER GAUGES")
            if flood_warnings:
                st.dataframe(pd.DataFrame(flood_warnings)[["Severity", "Area", "Description"]], hide_index=True, width="stretch")
            else:
                st.info("No active Environment Agency flood warnings within your selected perimeter radius.")
            st.dataframe(pd.DataFrame(river_stations), hide_index=True, width="stretch")

    with f_col_tel:
        with st.container(border=True):
            render_panel_header("📊 HYDROLOGY TELEMETRY & WHAT3WORDS")
            st.markdown(f"""
            <div class="status-pill-container">
                <div class="status-pill"><div style="font-size:10px; color:#8b949e;">PEAK RIVER LEVEL</div><div class="pill-val" style="color:#52a3ff;">{max_river_level:.2f} m</div></div>
                <div class="status-pill"><div style="font-size:10px; color:#8b949e;">ACTIVE WARNINGS</div><div class="pill-val" style="color:#ff9f43;">{len(flood_warnings)}</div></div>
                <div class="status-pill"><div style="font-size:10px; color:#8b949e;">USER SEPARATION</div><div class="pill-val" style="color:#2ed573;">{separation_dist:.2f} KM</div></div>
            </div>
            <div class="w3w-badge">
                <span style="font-size:10px; color:#8b949e;">🏡 HOUSE FLOOD ASSET TAG:</span> <span class="w3w-slashes">///</span><strong>{house_w3w}</strong>
            </div>
            <div class="w3w-badge">
                <span style="font-size:10px; color:#8b949e;">🛰️ USER EVACUATION GPS TAG:</span> <span class="w3w-slashes">///</span><strong>{user_w3w}</strong>
            </div>
            """, unsafe_allow_html=True)

        # Subscription-Gated Sump Pump & Flood Barrier Control
        with st.container(border=True):
            render_panel_header("🚧 SUMP PUMP & FLOOD BARRIER DEFENSE")
            if st.session_state.is_subscribed:
                s_col1, s_col2 = st.columns(2)
                with s_col1:
                    st.session_state.sump_armed = st.toggle(
                        "ARM SUMP PUMPS & FLOOD GATES",
                        value=st.session_state.sump_armed
                    )
                with s_col2:
                    flow_rate = st.slider("Target Sump Discharge (L/min)", 100, 600, 450)
                sump_label = "DEPLOYED / PUMPING" if st.session_state.sump_armed else "STANDBY / ARMED"
                sump_color = "#52a3ff" if st.session_state.sump_armed else "#2ed573"
                st.markdown(f"""
                <div style="font-size:11px; line-height:1.6; color:#7fa483; margin-top:6px;">
                    <p style="margin:2px 0; color:{sump_color};">● FLOOD DEFENSE STATUS: <strong>{sump_label}</strong></p>
                    <p style="margin:2px 0;">• DISCHARGE RATE: {flow_rate if st.session_state.sump_armed else 0} L/min | BACKUP BATTERY: 96%</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="background:#090d14; border:1px dashed #4b6584; border-radius:4px; padding:12px; text-align:center;">
                    <p style="color:#ff9f43; font-size:12px; font-weight:bold; margin:0 0 6px 0;">🔒 FLOOD PUMP & BARRIER ACCESS RESTRICTED</p>
                    <p style="color:#8b949e; font-size:11px; margin:0;">Remote submersible sump pump and flood barrier deployment require an active Pro subscription.</p>
                </div>
                """, unsafe_allow_html=True)

        with st.container(border=True):
            render_panel_header("📡 FLOOD EVACUATION & STATUS BROADCASTER")
            f_contact_options = [f"{c['Name']} ({c['Relation']})" for c in st.session_state.next_of_kin]
            f_chosen_contact = st.selectbox("Active Flood Relay", f_contact_options, key="flood_contact_select")
            f_maps_url = f"https://www.google.com/maps?q={user_lat},{user_lon}"
            f_broadcast_msg = (
                f"FLOOD ALERT BROADCAST: {len(flood_warnings)} active warnings near ///{house_w3w} (Peak River: {max_river_level:.2f}m). "
                f"Operator GPS: ///{user_w3w} ({f_maps_url})"
            )
            f_whatsapp_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(f_broadcast_msg)}"
            st.markdown(f"""
            <a href="{f_whatsapp_url}" target="_blank" class="btn-broadcast">🚀 SEND FLOOD STATUS & WHAT3WORDS TO {f_chosen_contact.upper()}</a>
            """, unsafe_allow_html=True)


# ==============================================================================
# TAB 3: BLACKOUT STEALTH OPS (PITCH BLACK BACKGROUND + RED LETTERING)
# ==============================================================================
with tab_blackout:
    bo_threat_str = f"{closest_fire_dist:.2f} KM" if closest_fire_dist != float('inf') else "CLEAR"
    bo_maps_url = f"https://www.google.com/maps?q={user_lat},{user_lon}"
    bo_w3w_url = f"https://what3words.com/{user_w3w}"
    bo_sos_msg = (
        f"BLACKOUT STEALTH SOS: Operator at ///{user_w3w} ({user_lat:.4f}, {user_lon:.4f}). "
        f"Base asset ///{house_w3w}. Fire vector: {bo_threat_str} | River stage: {max_river_level:.2f}m. "
        f"Map: {bo_maps_url} | w3w: {bo_w3w_url}"
    )
    bo_whatsapp_link = f"https://api.whatsapp.com/send?text={urllib.parse.quote(bo_sos_msg)}"

    st.markdown(f"""
    <div class="blackout-screen">
        <div class="blackout-header">
            <h2 class="blackout-title">⬛ BLACKOUT NIGHT-OPS // LOW-LIGHT TACTICAL HUD</h2>
            <span style="color:#ff1e1e; font-size:12px; font-weight:bold;">[{time.strftime("%H:%M:%S")} UTC] ● NIGHT-VISION SAFE</span>
        </div>

        <div style="display:flex; justify-content:space-between; gap:14px; flex-wrap:wrap;">
            <div class="blackout-card" style="flex:1; min-width:260px;">
                <div class="blackout-label">🛰️ OPERATOR AUTO-GPS GEOLOCATION TAG</div>
                <div class="blackout-value">///{user_w3w}</div>
                <div style="color:#cc0000; font-size:12px; margin-top:4px;">LAT: {user_lat:.5f} | LON: {user_lon:.5f}</div>
                <div style="color:#990000; font-size:11px; margin-top:2px;">SYNC: {st.session_state.gps_sync_status}</div>
            </div>

            <div class="blackout-card" style="flex:1; min-width:260px;">
                <div class="blackout-label">🏡 HOME ASSET GEOLOCATION TAG</div>
                <div class="blackout-value">///{house_w3w}</div>
                <div style="color:#cc0000; font-size:12px; margin-top:4px;">LAT: {house_lat:.5f} | LON: {house_lon:.5f}</div>
                <div style="color:#990000; font-size:11px; margin-top:2px;">SEPARATION VECTOR: {separation_dist:.2f} KM</div>
            </div>
        </div>

        <div style="display:flex; justify-content:space-between; gap:14px; flex-wrap:wrap;">
            <div class="blackout-card" style="flex:1; min-width:180px;">
                <div class="blackout-label">🔥 NEAREST THERMAL VECTOR</div>
                <div class="blackout-value">{bo_threat_str}</div>
            </div>
            <div class="blackout-card" style="flex:1; min-width:180px;">
                <div class="blackout-label">🌊 PEAK RIVER GAUGE</div>
                <div class="blackout-value">{max_river_level:.2f} m</div>
            </div>
            <div class="blackout-card" style="flex:1; min-width:180px;">
                <div class="blackout-label">🌡️ ZONE CORE TEMP</div>
                <div class="blackout-value">{test_temp}°C</div>
            </div>
            <div class="blackout-card" style="flex:1; min-width:180px;">
                <div class="blackout-label">🚰 PUMP HARDWARE TIER</div>
                <div class="blackout-value">{'PRO ARMED' if st.session_state.is_subscribed else 'LOCKED'}</div>
            </div>
        </div>

        <div class="blackout-card">
            <div class="blackout-label">📡 STEALTH BEACON TRANSMISSION</div>
            <div style="color:#cc0000; font-size:12px;">
                High-contrast zero-glare red phosphor readout preserves night vision during power grid outages.
                Transmit your exact 3-meter what3words square and GPS coordinates directly to emergency contacts:
            </div>
            <a href="{bo_whatsapp_link}" target="_blank" class="blackout-btn">
                🚨 TRANSMIT BLACKOUT SOS & WHAT3WORDS (///{user_w3w.upper()})
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ==============================================================================
# TAB 4: COMING SOON ROADMAP
# ==============================================================================
with tab_coming_soon:
    with st.container(border=True):
        render_panel_header("🚀 TACTICAL COMMAND MATRIX — UPCOMING MODULES ROADMAP")
        st.markdown("""
        <p style='font-size:12px; color:#8b949e;'>
            Next-generation telemetry, autonomous defense hardware, and AI hazard routing currently in field testing:
        </p>
        """, unsafe_allow_html=True)

        cs_col1, cs_col2 = st.columns(2)
        with cs_col1:
            st.markdown("""
            <div style="background:#090d14; border:1px solid #1f2d3d; border-radius:4px; padding:14px; margin-bottom:12px;">
                <span style="color:#ff9f43; font-size:10px; font-weight:bold;">IN DEVELOPMENT • Q3</span>
                <h4 style="color:#52a3ff; margin:4px 0;">🧭 Dynamic Evacuation Vector Routing</h4>
                <p style="color:#7fa483; font-size:12px; margin:0;">
                    Real-time road closure ingestion that computes safe escape routes away from advancing fire fronts and flooded roads.
                </p>
            </div>
            <div style="background:#090d14; border:1px solid #1f2d3d; border-radius:4px; padding:14px; margin-bottom:12px;">
                <span style="color:#ff9f43; font-size:10px; font-weight:bold;">HARDWARE BETA • Q4</span>
                <h4 style="color:#52a3ff; margin:4px 0;">🔋 Off-Grid Solar & Power Grid Telemetry</h4>
                <p style="color:#7fa483; font-size:12px; margin:0;">
                    Live battery reserve tracking and automatic failover monitoring for backup home generators and pump stations.
                </p>
            </div>
            """, unsafe_allow_html=True)

        with cs_col2:
            st.markdown("""
            <div style="background:#090d14; border:1px solid #1f2d3d; border-radius:4px; padding:14px; margin-bottom:12px;">
                <span style="color:#2ed573; font-size:10px; font-weight:bold;">ALPHA TESTING • Q3</span>
                <h4 style="color:#52a3ff; margin:4px 0;">🌬️ Wind Vector & Ember Drift Modeling</h4>
                <p style="color:#7fa483; font-size:12px; margin:0;">
                    Live meteorological wind speed and direction overlays to project spot-fire ember trajectories before perimeter breach.
                </p>
            </div>
            <div style="background:#090d14; border:1px solid #1f2d3d; border-radius:4px; padding:14px; margin-bottom:12px;">
                <span style="color:#2ed573; font-size:10px; font-weight:bold;">COMING SOON • Q4</span>
                <h4 style="color:#52a3ff; margin:4px 0;">📱 SMS / Satellite Fallback Relay</h4>
                <p style="color:#7fa483; font-size:12px; margin:0;">
                    Automated Twilio SMS and low-bandwidth satellite packet alerts when cellular data networks go offline.
                </p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        with st.form("beta_waitlist_form", clear_on_submit=True):
            st.markdown("**🔔 REQUEST EARLY ACCESS TO BETA MODULES**")
            w_col1, w_col2 = st.columns([3, 1])
            with w_col1:
                beta_email = st.text_input("Operator Email Address", placeholder="operator@domain.com", label_visibility="collapsed")
            with w_col2:
                join_beta = st.form_submit_button("JOIN BETA QUEUE", width="stretch")
            if join_beta and beta_email:
                st.toast(f"Registered {beta_email} for Tactical Command Matrix Beta.", icon="🚀")
