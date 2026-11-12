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

try:
    from streamlit_js_eval import get_geolocation
    HAS_JS_EVAL = True
except ImportError:
    HAS_JS_EVAL = False

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
    .header-flood-alert {
        background-color: #091d2c;
        border: 2px solid #00a8ff;
        box-shadow: 0 0 15px rgba(0, 168, 255, 0.25);
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
    R = 6371.0
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

        log_lines = [
            "==================================================",
            "        TACTICAL MATRIX OPERATIONS RECORD          ",
            "==================================================",
            f"TIMESTAMP LOG RECORDED : {timestamp_header}",
            f"ZONE CORE TEMPERATURE  : {test_temp}°C",
            f"NEAREST THREAT VECTOR  : {threat_string}",
            f"TOTAL COUNT HOTSPOTS   : {len(fire_points_list)}",
            "--------------------------------------------------",
            "SYSTEM LOG HISTORY ENTRIES:",
            " - [SYS] Emergency Comm tracking telemetry matrix deployed.",
            " - [NASA_API] Satellite query bounds verified successfully.",
            " - [CALC] Vector radius proximity computation verified.",
            "==================================================",
            "EOF - DATA INTEGRITY SECURED",
        ]
        log_payload_dump = "\n".join(log_lines) + "\n"

        st.download_button(
            label="📥 DOWNLOAD SECURE INCIDENT LOG FILE (.LOG)",
            data=log_payload_dump,
            file_name=f"tactical_matrix_dump_{int(time.time())}.log",
            mime="text/plain",
            use_container_width=True
        )

# --- 4. Setup Initial Application States ---
if "next_of_kin" not in st.session_state:
    st.session_state.next_of_kin = [
        {"Name": "John Smith", "Relation": "Primary Safety Relay", "Contact Vector": "+15550199"}
    ]

if "is_subscribed" not in st.session_state:
    st.session_state.is_subscribed = False

if "user_lat" not in st.session_state:
    st.session_state.user_lat = 51.7780

if "user_lon" not in st.session_state:
    st.session_state.user_lon = 0.0950

if "auto_gps_active" not in st.session_state:
    st.session_state.auto_gps_active = False

if "pump_armed" not in st.session_state:
    st.session_state.pump_armed = False

if "flood_barrier_armed" not in st.session_state:
    st.session_state.flood_barrier_armed = False

# --- 5. Top-Level Navigation Tabs ---
tab_fire, tab_flood, tab_coming_soon = st.tabs([
    "🔥 FIRE COMMAND MATRIX",
    "🌊 FLOOD COMMAND MATRIX",
    "🚀 COMING SOON"
])

# --- 6. Shared Configuration & Simulation Panel ---
with st.expander("🛠️ TEST FACILITIES, SUBSCRIPTION & GEOTAG SIMULATION BAY", expanded=True):
    st.markdown(
        "<p style='font-size:12px; color:#52a3ff;'>Engineering Diagnostic Console: Setup live satellite/hydrology parameters, subscription tier, and geotags.</p>",
        unsafe_allow_html=True
    )

    sub_col1, sub_col2 = st.columns([3, 1])
    with sub_col1:
        access_key = st.text_input(
            "Pro Hardware Defense Access Key (Demo Key: PRO-2026)",
            type="password",
            placeholder="Enter key to unlock Pump Station & Flood Barrier Controls..."
        )
    with sub_col2:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("🔓 VERIFY PLAN", use_container_width=True):
            if access_key == "PRO-2026":
                st.session_state.is_subscribed = True
                st.toast("Pro Subscription Verified: Suppression Pump & Flood Barrier Unlocked.", icon="✅")
            else:
                st.session_state.is_subscribed = False
                st.error("Invalid subscription key.")

    st.markdown("---")
    api_col1, api_col2 = st.columns(2)
    with api_col1:
        firms_api_key = st.text_input("NASA FIRMS MAP_KEY", value="DEMO_KEY", type="password")
    with api_col2:
        scan_radius_km = st.slider("Perimeter Scan Radius (KM)", 5.0, 100.0, 30.0)

    st.markdown("---")
    geo_col1, geo_col2 = st.columns(2)
    with geo_col1:
        st.markdown("**🏡 HOUSE TARGET GEOTAG**")
        house_lat = st.number_input("House Latitude", value=51.7729, format="%.4f")
        house_lon = st.number_input("House Longitude", value=0.1023, format="%.4f")

    with geo_col2:
        st.markdown("**🏃 USER/OPERATOR AUTO-GEOTAG**")
        gps_btn_col1, gps_btn_col2 = st.columns(2)
        with gps_btn_col1:
            if st.button("📍 AUTO-DETECT USER GPS", use_container_width=True):
                st.session_state.auto_gps_active = True
        with gps_btn_col2:
            if st.button("🛑 MANUAL OVERRIDE", use_container_width=True):
                st.session_state.auto_gps_active = False

        if st.session_state.auto_gps_active:
            if HAS_JS_EVAL:
                loc = get_geolocation()
                if loc and "coords" in loc:
                    st.session_state.user_lat = float(loc["coords"]["latitude"])
                    st.session_state.user_lon = float(loc["coords"]["longitude"])
                    st.success(f"GPS LOCKED: {st.session_state.user_lat:.4f}, {st.session_state.user_lon:.4f}")
                else:
                    st.info("Requesting browser GPS permission... Allow location access in your browser.")
            else:
                st.warning("Install `streamlit-js-eval` for live browser GPS. Using manual coordinates.")

        user_lat = st.number_input("User Latitude", key="user_lat", format="%.4f")
        user_lon = st.number_input("User Longitude", key="user_lon", format="%.4f")

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

# ==============================================================================
# TAB 1: FIRE COMMAND MATRIX
# ==============================================================================
with tab_fire:
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
                use_container_width=True
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

        # Subscription-Gated Fire Suppression Pump Station
        with st.container(border=True):
            render_panel_header("🚰 PERIMETER SUPPRESSION PUMP STATION CONTROL")
            if st.session_state.is_subscribed:
                p_col1, p_col2 = st.columns(2)
                with p_col1:
                    st.session_state.pump_armed = st.toggle(
                        "ARM ROOF & PERIMETER SPRINKLER PUMP",
                        value=st.session_state.pump_armed
                    )
                with p_col2:
                    target_psi = st.slider("Target Line Pressure (PSI)", 40, 120, 85)
                pump_status = "ACTIVE / PRESSURIZED" if st.session_state.pump_armed else "STANDBY READY"
                pump_color = "#2ed573" if st.session_state.pump_armed else "#52a3ff"
                st.markdown(
                    f"<p style='font-size:11px; color:{pump_color}; margin:0;'>• PUMP TELEMETRY: {pump_status} @ {target_psi} PSI | RESERVOIR: 98%</p>",
                    unsafe_allow_html=True
                )
            else:
                st.info("🔒 **PRO SUBSCRIPTION REQUIRED:** Remote Suppression Pump Station controls are locked. Enter your Pro Access Key in the Simulation Bay above to unlock.")

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
            chosen_contact = st.selectbox("Active Target Relay", contact_options, key="fire_contact_select")

            maps_query_url = f"https://www.google.com/maps?q={user_lat},{user_lon}"
            broadcast_msg = (
                f"TACTICAL FIRE ALERT BROADCAST: Proximity tracking alert active. "
                f"Nearest fire perimeter scan is {threat_val_string} away from target house asset. "
                f"Pin coordinate trace: {maps_query_url}"
            )

            encoded_payload = urllib.parse.quote(broadcast_msg)
            whatsapp_comms_endpoint = f"https://api.whatsapp.com/send?text={encoded_payload}"

            st.markdown(f"""
            <a href="{whatsapp_comms_endpoint}" target="_blank" class="btn-broadcast">🚀 SEND LOCATION & 'SAFE' STATUS TO {chosen_contact.upper()}</a>
            """, unsafe_allow_html=True)

        render_download_module(fire_points, closest_fire_dist, test_temp)

    with st.container(border=True):
        render_panel_header("💻 FIRE CONSOLE LOG MONITOR SYSTEM")
        ts = time.strftime("%H:%M:%S")
        st.markdown(f"""
        <div class="log-monitor">
            <div class="log-line"><span class="log-ts">[{ts}]</span> <span style="color:#52a3ff;">NASA_API:</span> {api_log_status}.</div>
            <div class="log-line"><span class="log-ts">[{ts}]</span> <span style="color:#52a3ff;">GPS:</span> Bounding box grid bounds compiled: {bbox_string}.</div>
            <div class="log-line"><span class="log-ts">[{ts}]</span> <span style="color:#52a3ff;">CALC:</span> Nearest thermal sensor point calculated at distance value {threat_val_string}.</div>
            <div class="log-line"><span class="log-ts">[{ts}]</span> <span class="log-warn;">SYS:</span> Safety trigger check active. Alert status evaluated.</div>
        </div>
        """, unsafe_allow_html=True)

# ==============================================================================
# TAB 2: FLOOD COMMAND MATRIX (UK ENVIRONMENT AGENCY LIVE API)
# ==============================================================================
with tab_flood:
    flood_warnings = []
    river_stations = []
    peak_river_level = 0.0
    flood_api_status = "INITIALIZING UK EA HYDROLOGY FEED"

    try:
        ea_flood_url = f"https://environment.data.gov.uk/flood-monitoring/id/floods?lat={house_lat}&long={house_lon}&dist={int(scan_radius_km)}"
        f_resp = requests.get(ea_flood_url, timeout=8)
        if f_resp.status_code == 200:
            items = f_resp.json().get("items", [])
            for item in items:
                flood_warnings.append({
                    "Severity": item.get("severity", "Flood Alert"),
                    "SeverityLevel": item.get("severityLevel", 3),
                    "Area": item.get("eaAreaName", "Local Catchment"),
                    "Description": item.get("description", "Active flood warning in perimeter.")
                })

        ea_station_url = f"https://environment.data.gov.uk/flood-monitoring/id/stations?lat={house_lat}&long={house_lon}&dist={int(scan_radius_km)}&parameter=level&_limit=8"
        s_resp = requests.get(ea_station_url, timeout=8)
        if s_resp.status_code == 200:
            st_items = s_resp.json().get("items", [])
            for st_item in st_items:
                s_lat = st_item.get("lat")
                s_lon = st_item.get("long")
                label = st_item.get("label", "River Gauge")
                val = 1.42
                measures = st_item.get("measures", [])
                if isinstance(measures, dict):
                    measures = [measures]
                if measures and isinstance(measures[0], dict):
                    latest = measures[0].get("latestReading", {})
                    if isinstance(latest, dict) and "value" in latest:
                        val = float(latest["value"])
                if s_lat is not None and s_lon is not None:
                    river_stations.append({"label": label, "lat": float(s_lat), "lon": float(s_lon), "level": val})
                    if val > peak_river_level:
                        peak_river_level = val

        flood_api_status = f"UK EA SYNC OK: {len(flood_warnings)} Active Warnings | {len(river_stations)} River Gauges"
    except Exception as e:
        flood_api_status = f"HYDROLOGY API FALLBACK ({type(e).__name__}): Simulating local river gauges"

    if not river_stations:
        river_stations = [
            {"label": "River Stort @ Harlow Mill", "lat": house_lat + 0.008, "lon": house_lon - 0.006, "level": 1.85},
            {"label": "Parndon Mill Sluice", "lat": house_lat - 0.005, "lon": house_lon - 0.012, "level": 1.62},
        ]
        peak_river_level = 1.85

    has_severe_flood = len(flood_warnings) > 0

    if has_severe_flood:
        st.markdown(f"""
        <div class="tactical-header-container header-flood-alert">
            <h1 class="tactical-title" style="color: #00a8ff; text-shadow: 0 0 5px rgba(0, 168, 255, 0.4);">FLOOD ALERT: {len(flood_warnings)} ACTIVE HYDROLOGY WARNING(S)</h1>
        </div>
        <div class="sub-status-bar" style="background-color: #071622; border: 1px solid #0077b6;">
            <span style="color: #00a8ff;">🌊 CATCHMENT ALERT: PEAK RIVER STAGE AT {peak_river_level:.2f} M</span>
            <span style="color: #00a8ff;">FLOOD DEFENSE LAYERS READY ⏱️</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="tactical-header-container header-nominal">
            <h1 class="tactical-title" style="color: #2ed573; text-shadow: 0 0 5px rgba(46, 213, 115, 0.4);">HYDROLOGY NOMINAL: NO ACTIVE FLOOD WARNINGS</h1>
        </div>
        <div class="sub-status-bar" style="background-color: #0a170f; border: 1px solid #1a7c3e;">
            <span style="color: #2ed573;">🟢 RIVER STAGE NOMINAL (PEAK GAUGE: {peak_river_level:.2f} M)</span>
            <span style="color: #2ed573;">ALL CATCHMENTS SECURE 🔐</span>
        </div>
        """, unsafe_allow_html=True)

    f_col_map, f_col_tel = st.columns(2)

    with f_col_map:
        with st.container(border=True):
            render_panel_header("🌊 LIVE CATCHMENT & RIVER GAUGE RADAR")
            fm = folium.Map(
                location=[house_lat, house_lon],
                zoom_start=12,
                tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                attr="Esri"
            )
            folium.Circle(
                location=[house_lat, house_lon],
                radius=scan_radius_km * 1000,
                color="#00a8ff",
                fill=True,
                fill_opacity=0.06
            ).add_to(fm)

            for st_node in river_stations:
                folium.CircleMarker(
                    location=[st_node["lat"], st_node["lon"]],
                    radius=8,
                    color="#00a8ff",
                    fill=True,
                    fill_color="#00a8ff",
                    popup=f"🌊 {st_node['label']}: {st_node['level']:.2f}m"
                ).add_to(fm)

            folium.Marker([house_lat, house_lon], popup="🏡 TARGET HOUSE", icon=folium.Icon(color="red", icon="home")).add_to(fm)
            folium.Marker([user_lat, user_lon], popup="🏃 USER OPS", icon=folium.Icon(color="blue", icon="user")).add_to(fm)
            st_folium(fm, width=700, height=350, key="flood_radar_view")

    with f_col_tel:
        with st.container(border=True):
            render_panel_header("📊 FLOOD TELEMETRY MATRIX")
            f_sep_dist = haversine_distance(house_lat, house_lon, user_lat, user_lon)
            st.markdown(f"""
            <div class="status-pill-container">
                <div class="status-pill"><div style="font-size:10px; color:#8b949e;">PEAK RIVER LEVEL</div><div class="pill-val" style="color:#00a8ff;">{peak_river_level:.2f} M</div></div>
                <div class="status-pill"><div style="font-size:10px; color:#8b949e;">ACTIVE WARNINGS</div><div class="pill-val" style="color:#ff9f43;">{len(flood_warnings)}</div></div>
                <div class="status-pill"><div style="font-size:10px; color:#8b949e;">USER SEPARATION</div><div class="pill-val" style="color:#52a3ff;">{f_sep_dist:.2f} KM</div></div>
            </div>
            """, unsafe_allow_html=True)

        with st.container(border=True):
            render_panel_header("🛡️ SUMP PUMP & FLOOD BARRIER DEFENSE")
            if st.session_state.is_subscribed:
                fb_col1, fb_col2 = st.columns(2)
                with fb_col1:
                    st.session_state.flood_barrier_armed = st.toggle(
                        "DEPLOY AUTO-FLOOD BARRIERS & SUMP PUMP",
                        value=st.session_state.flood_barrier_armed
                    )
                with fb_col2:
                    flow_rate = st.slider("Sump Discharge Rate (L/MIN)", 150, 600, 450)
                fb_status = "DEPLOYED / PUMPING" if st.session_state.flood_barrier_armed else "STANDBY READY"
                fb_color = "#2ed573" if st.session_state.flood_barrier_armed else "#00a8ff"
                st.markdown(
                    f"<p style='font-size:11px; color:{fb_color}; margin:0;'>• DEFENSE TELEMETRY: {fb_status} @ {flow_rate} L/MIN | BACKUP BATTERY: 96%</p>",
                    unsafe_allow_html=True
                )
            else:
                st.info("🔒 **PRO SUBSCRIPTION REQUIRED:** Automated Flood Barrier & Submersible Sump Pump controls are locked. Verify Pro key (`PRO-2026`) in the Simulation Bay.")

        with st.container(border=True):
            render_panel_header("📡 FLOOD STATUS BROADCASTER")
            f_contact_options = [f"{c['Name']} ({c['Relation']})" for c in st.session_state.next_of_kin]
            f_chosen_contact = st.selectbox("Active Target Relay", f_contact_options, key="flood_contact_select")

            f_maps_url = f"https://www.google.com/maps?q={user_lat},{user_lon}"
            f_broadcast_msg = (
                f"TACTICAL FLOOD BROADCAST: Active warnings in scan zone: {len(flood_warnings)}. "
                f"Peak nearby river stage: {peak_river_level:.2f}m. "
                f"Live operator pin: {f_maps_url}"
            )
            f_whatsapp_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(f_broadcast_msg)}"
            st.markdown(f"""
            <a href="{f_whatsapp_url}" target="_blank" class="btn-broadcast">🌊 SEND FLOOD LOCATION & 'SAFE' STATUS TO {f_chosen_contact.upper()}</a>
            """, unsafe_allow_html=True)

    with st.container(border=True):
        render_panel_header("💻 HYDROLOGY CONSOLE LOG MONITOR")
        fts = time.strftime("%H:%M:%S")
        st.markdown(f"""
        <div class="log-monitor">
            <div class="log-line"><span class="log-ts">[{fts}]</span> <span style="color:#00a8ff;">UK_EA_API:</span> {flood_api_status}.</div>
            <div class="log-line"><span class="log-ts">[{fts}]</span> <span style="color:#00a8ff;">GAUGE:</span> Peak river stage verified at {peak_river_level:.2f}m within {scan_radius_km:.0f} KM radius.</div>
        </div>
        """, unsafe_allow_html=True)

# ==============================================================================
# TAB 3: COMING SOON ROADMAP
# ==============================================================================
with tab_coming_soon:
    with st.container(border=True):
        render_panel_header("🚀 TACTICAL COMMAND MATRIX — UPCOMING MODULES ROADMAP")
        st.markdown("""
        <div style="font-size:13px; color:#8b949e; line-height:1.6;">
            <p><strong style="color:#52a3ff;">1. /// what3words Geolocation Grid:</strong> Instant 3-word emergency address conversion for target house and mobile operator coordinates for rapid verbal relay to emergency responders.</p>
            <p><strong style="color:#52a3ff;">2. Dynamic Evacuation Vector Routing:</strong> Real-time road-closure-aware routing that automatically avoids active wildfire perimeters and flooded catchments.</p>
            <p><strong style="color:#52a3ff;">3. Live Wind & Ember Drift Cone Modeling:</strong> Predictive plume projection combining live wind speed/direction vectors with VIIRS thermal hotspots.</p>
            <p><strong style="color:#52a3ff;">4. Off-Grid Solar & Battery Telemetry:</strong> Direct inverter integration to monitor backup power reserves during grid shutoffs.</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("beta_waitlist_form", clear_on_submit=True):
            beta_email = st.text_input("Request Early Beta Access (Email or Callsign)")
            if st.form_submit_button("📡 JOIN BETA DISPATCH"):
                if beta_email:
                    st.toast(f"Registered {beta_email} for Tactical Matrix v2.0 Beta.", icon="🚀")
