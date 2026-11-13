import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import time
import json
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
    .header-warn {
        background-color: #241a08;
        border: 2px solid #ffa502;
        box-shadow: 0 0 15px rgba(255, 165, 2, 0.25);
    }
    .header-nominal {
        background-color: #0c1c12;
        border: 2px solid #2ed573;
        box-shadow: 0 0 15px rgba(46, 213, 115, 0.25);
    }
    .header-vip {
        background-color: #1c1507;
        border: 2px solid #ffa502;
        box-shadow: 0 0 15px rgba(255, 165, 2, 0.25);
    }
    .tactical-title {
        font-size: 20px !important;
        font-weight: 800;
        letter-spacing: 2px;
        margin: 0 !important;
    }
    .sub-status-bar {
        display: flex;
        justify-content: space-between;
        border-radius: 4px;
        padding: 6px 15px;
        margin-bottom: 16px;
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
    .pill-val { font-size: 15px; font-weight: bold; }
    .w3w-badge {
        background-color: #090d14;
        border: 1px solid #2f3542;
        border-left: 3px solid #ff4757;
        padding: 6px 10px;
        font-size: 12px;
        color: #f1f2f6;
        margin-bottom: 8px;
        border-radius: 2px;
    }
    .btn-broadcast {
        display: block;
        background-color: #176565;
        color: white !important;
        font-weight: bold;
        text-align: center;
        padding: 12px;
        border: 1px solid #52a3ff;
        border-radius: 4px;
        text-decoration: none !important;
        font-size: 13px;
        text-transform: uppercase;
        margin-top: 12px;
    }
    .btn-broadcast:hover {
        background-color: #00cbcb;
        color: #0b0f14 !important;
    }
    .blackout-box {
        background-color: #000000;
        border: 1px solid #ff1e1e;
        color: #ff1e1e;
        padding: 16px;
        border-radius: 3px;
        margin-bottom: 14px;
    }
    .blackout-title {
        color: #ff1e1e;
        font-size: 13px;
        font-weight: bold;
        letter-spacing: 2px;
        border-bottom: 1px solid #660000;
        padding-bottom: 6px;
        margin-bottom: 10px;
    }
    .blackout-val {
        color: #ff1e1e;
        font-size: 20px;
        font-weight: bold;
    }
    .btn-blackout-sos {
        display: block;
        background-color: #000000;
        color: #ff1e1e !important;
        border: 2px solid #ff1e1e;
        font-weight: bold;
        text-align: center;
        padding: 14px;
        text-decoration: none !important;
        letter-spacing: 2px;
        margin-top: 10px;
    }
    .btn-blackout-sos:hover {
        background-color: #330000;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. Helper Functions & Safe Secret Loader ---
def get_secret_safe(key_name, default_val):
    try:
        return st.secrets[key_name]
    except Exception:
        return default_val

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    p = np.pi / 180
    a = (
        0.5
        - np.cos((lat2 - lat1) * p) / 2
        + np.cos(lat1 * p) * np.cos(lat2 * p) * (1 - np.cos((lon2 - lon1) * p)) / 2
    )
    return 2 * R * np.arcsin(np.sqrt(a))

def get_what3words(lat, lon, api_key=""):
    if api_key.strip():
        try:
            url = f"https://api.what3words.com/v3/convert-to-3wa?coordinates={lat},{lon}&key={api_key.strip()}"
            res = requests.get(url, timeout=5)
            if res.status_code == 200 and "words" in res.json():
                return f"///{res.json()['words']}"
        except Exception:
            pass
    words_a = ["beacon", "harlow", "shield", "vector", "radar", "summit", "cedar", "granite"]
    words_b = ["watch", "ember", "river", "guard", "sector", "signal", "anchor", "pulse"]
    words_c = ["north", "matrix", "relay", "safe", "point", "haven", "orbit", "crest"]
    idx1 = abs(int(round(lat * 37000))) % len(words_a)
    idx2 = abs(int(round(lon * 37000))) % len(words_b)
    idx3 = abs(int(round((lat + lon) * 37000))) % len(words_c)
    return f"///{words_a[idx1]}.{words_b[idx2]}.{words_c[idx3]}"

def render_panel_header(title_text):
    st.markdown(f"""
        <div class="panel-header">
            <h3 class="panel-title">{title_text}</h3>
            <span class="panel-controls">🗕 🗖 🗙</span>
        </div>
    """, unsafe_allow_html=True)

def default_property_hardware():
    return {
        "sprinkler_armed": False,
        "target_psi": 85,
        "flood_barrier_deployed": False,
        "sump_pump_active": True,
        "flow_rate": 450,
        "deadbolts_locked": True,
        "perimeter_sensors": True,
        "cctv_active": True,
        "shutters_locked": False
    }

@st.cache_data(ttl=300, show_spinner=False)
def scan_location_hazards(lat, lon, scan_radius_km, firms_api_key):
    # 1. Fire scan (NASA FIRMS Global VIIRS)
    fires = []
    nearest_fire = float('inf')
    lat_delta = scan_radius_km / 111.0
    cos_lat = max(np.cos(np.radians(lat)), 0.0001)
    lon_delta = scan_radius_km / (111.0 * cos_lat)
    bbox = f"{lon - lon_delta:.4f},{lat - lat_delta:.4f},{lon + lon_delta:.4f},{lat + lat_delta:.4f}"
    firms_url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{firms_api_key}/VIIRS_SNPP_NRT/{bbox}/1"

    try:
        res = requests.get(firms_url, timeout=6)
        if res.status_code == 200 and "latitude" in res.text:
            df_fires = pd.read_csv(StringIO(res.text))
            for _, row in df_fires.iterrows():
                f_lat, f_lon = float(row['latitude']), float(row['longitude'])
                dist = haversine_distance(lat, lon, f_lat, f_lon)
                if dist <= scan_radius_km:
                    fires.append([f_lat, f_lon, float(row.get('frp', 1.0))])
                    nearest_fire = min(nearest_fire, dist)
        else:
            raise ValueError("Fallback")
    except Exception:
        for lat_off, lon_off in [[0.018, -0.020], [-0.015, 0.025]]:
            f_lat, f_lon = lat + lat_off, lon + lon_off
            dist = haversine_distance(lat, lon, f_lat, f_lon)
            if dist <= scan_radius_km:
                fires.append([f_lat, f_lon, 15.0])
                nearest_fire = min(nearest_fire, dist)

    # 2. Flood scan (UK Environment Agency Severity 1-3 + Open-Meteo Copernicus GloFAS)
    ea_items = []
    source_label = "Copernicus GloFAS (Europe / Global)"
    is_england = (49.8 <= lat <= 55.9) and (-6.5 <= lon <= 2.1)
    if is_england:
        try:
            ea_url = f"https://environment.data.gov.uk/flood-monitoring/id/floods?lat={lat}&long={lon}&dist={int(scan_radius_km)}"
            ea_res = requests.get(ea_url, timeout=6)
            if ea_res.status_code == 200:
                raw_items = ea_res.json().get("items", [])
                for item in raw_items:
                    sev_raw = item.get("severityLevel", 3)
                    try:
                        sev_int = int(sev_raw)
                    except (ValueError, TypeError):
                        sev_int = 3
                    if sev_int in (1, 2, 3):
                        item["parsed_severity"] = sev_int
                        ea_items.append(item)
                source_label = "UK Environment Agency + Copernicus GloFAS"
        except Exception:
            pass

    peak_discharge = None
    mean_discharge = None
    surge_ratio = None
    try:
        om_url = (
            f"https://flood-api.open-meteo.com/v1/flood?"
            f"latitude={lat}&longitude={lon}&daily=river_discharge,river_discharge_mean&forecast_days=3"
        )
        om_res = requests.get(om_url, timeout=6)
        if om_res.status_code == 200:
            daily = om_res.json().get("daily", {})
            d_vals = [float(x) for x in daily.get("river_discharge", []) if x is not None]
            m_vals = [float(x) for x in daily.get("river_discharge_mean", []) if x is not None]
            if d_vals:
                peak_discharge = max(d_vals)
            if m_vals and max(m_vals) > 0:
                mean_discharge = max(m_vals)
            if peak_discharge is not None and mean_discharge is not None and mean_discharge > 0:
                surge_ratio = peak_discharge / mean_discharge
    except Exception:
        pass

    return {
        "fires": fires,
        "nearest_fire": nearest_fire,
        "ea_items": ea_items,
        "peak_discharge": peak_discharge,
        "mean_discharge": mean_discharge,
        "surge_ratio": surge_ratio,
        "source_label": source_label
    }

# --- 4. Initialize Session States ---
MAX_LOCATIONS = 5

if "properties" not in st.session_state:
    st.session_state.properties = {
        "Primary Residence (Harlow, UK)": {"lat": 51.7729, "lon": 0.1023},
        "European Villa (Athens, GR)": {"lat": 37.9838, "lon": 23.7275}
    }
if "active_property" not in st.session_state:
    st.session_state.active_property = "Primary Residence (Harlow, UK)"
if "property_hardware" not in st.session_state:
    st.session_state.property_hardware = {
        name: default_property_hardware() for name in st.session_state.properties
    }
if "auth_tier" not in st.session_state:
    st.session_state.auth_tier = "FREE"
if "failed_attempts" not in st.session_state:
    st.session_state.failed_attempts = 0
if "lockout_until" not in st.session_state:
    st.session_state.lockout_until = 0.0
if "security_logs" not in st.session_state:
    st.session_state.security_logs = ["[SYS] Multi-property security matrix initialized."]
if "user_lat" not in st.session_state:
    st.session_state.user_lat = 51.7729
if "user_lon" not in st.session_state:
    st.session_state.user_lon = 0.1023
if "next_of_kin" not in st.session_state:
    st.session_state.next_of_kin = [
        {"Name": "John Smith", "Relation": "Primary Safety Relay", "Contact": "+447700900077"}
    ]
if "fire_alert_km" not in st.session_state:
    st.session_state.fire_alert_km = 10.0
if "discharge_ratio_threshold" not in st.session_state:
    st.session_state.discharge_ratio_threshold = 2.5
if "ping_level_3" not in st.session_state:
    st.session_state.ping_level_3 = False
if "enable_browser_ping" not in st.session_state:
    st.session_state.enable_browser_ping = True
if "last_alert_signature" not in st.session_state:
    st.session_state.last_alert_signature = ""

# --- 5. Command Console: Multi-Property & Alert Settings ---
with st.expander("🛠️ COMMAND CONSOLE: SAVED LOCATIONS (MAX 5), GEOTAG & ALERT THRESHOLDS", expanded=True):
    prop_names = list(st.session_state.properties.keys())
    if st.session_state.active_property not in prop_names:
        st.session_state.active_property = prop_names[0]

    prop_col1, prop_col2 = st.columns([3, 1])
    with prop_col1:
        selected_prop = st.selectbox(
            f"🏠 ACTIVE PROPERTY / FAVORITE LOCATION ({len(prop_names)}/{MAX_LOCATIONS} SLOTS USED)",
            prop_names,
            index=prop_names.index(st.session_state.active_property)
        )
        st.session_state.active_property = selected_prop

    with prop_col2:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if len(prop_names) > 1:
            if st.button("🗑️ REMOVE SELECTED", width="stretch"):
                del st.session_state.properties[selected_prop]
                st.session_state.property_hardware.pop(selected_prop, None)
                st.session_state.active_property = list(st.session_state.properties.keys())[0]
                st.rerun()

    if len(prop_names) < MAX_LOCATIONS:
        with st.form("add_property_form", clear_on_submit=True):
            st.markdown(f"**➕ ADD HOME OR FAVORITE LOCATION ({MAX_LOCATIONS - len(prop_names)} SLOTS REMAINING)**")
            ap_c1, ap_c2, ap_c3, ap_c4 = st.columns([2, 1, 1, 1])
            with ap_c1:
                new_prop_name = st.text_input("Location Label (e.g., Holiday Home Paris)")
            with ap_c2:
                new_prop_lat = st.number_input("Latitude", value=48.8566, format="%.4f")
            with ap_c3:
                new_prop_lon = st.number_input("Longitude", value=2.3522, format="%.4f")
            with ap_c4:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                add_prop_btn = st.form_submit_button("SAVE LOCATION", width="stretch")

            if add_prop_btn and new_prop_name.strip():
                clean_name = new_prop_name.strip()
                if clean_name in st.session_state.properties:
                    st.warning("A location with that name already exists.")
                else:
                    st.session_state.properties[clean_name] = {
                        "lat": float(new_prop_lat),
                        "lon": float(new_prop_lon)
                    }
                    st.session_state.property_hardware[clean_name] = default_property_hardware()
                    st.session_state.active_property = clean_name
                    st.toast(f"Saved location: {clean_name}", icon="📍")
                    st.rerun()
    else:
        st.info(f"Maximum of {MAX_LOCATIONS} saved locations reached. Remove a slot above to add a new location.")

    st.markdown("---")
    al_c1, al_c2, al_c3 = st.columns(3)
    with al_c1:
        st.session_state.fire_alert_km = st.slider(
            "🔥 Fire Proximity Alert Radius (KM)", 2.0, 50.0, float(st.session_state.fire_alert_km)
        )
    with al_c2:
        st.session_state.discharge_ratio_threshold = st.slider(
            "🌊 GloFAS River Surge Alert Ratio (× Mean)", 1.5, 5.0, float(st.session_state.discharge_ratio_threshold), 0.1
        )
    with al_c3:
        st.session_state.enable_browser_ping = st.toggle(
            "🔔 Browser Sound & Desktop Push Ping",
            value=st.session_state.enable_browser_ping
        )
        st.session_state.ping_level_3 = st.checkbox(
            "Also ping for early UK Level 3 Flood Alerts",
            value=st.session_state.ping_level_3
        )

    st.markdown("---")
    api_col1, api_col2, api_col3 = st.columns(3)
    with api_col1:
        firms_api_key = st.text_input("NASA FIRMS MAP_KEY (Global)", value="DEMO_KEY", type="password")
    with api_col2:
        w3w_api_key = st.text_input("what3words API Key (Optional)", value="", type="password")
    with api_col3:
        scan_radius_km = st.slider("Radar Scan Radius (KM)", 5.0, 100.0, 30.0)

    st.markdown("---")
    geo_col1, geo_col2 = st.columns(2)
    current_prop_data = st.session_state.properties[selected_prop]
    with geo_col1:
        st.markdown(f"**🏡 {selected_prop.upper()} GEOTAG**")
        house_lat = st.number_input("Location Latitude", value=float(current_prop_data["lat"]), format="%.4f", key=f"lat_{selected_prop}")
        house_lon = st.number_input("Location Longitude", value=float(current_prop_data["lon"]), format="%.4f", key=f"lon_{selected_prop}")
        st.session_state.properties[selected_prop]["lat"] = house_lat
        st.session_state.properties[selected_prop]["lon"] = house_lon

    with geo_col2:
        st.markdown("**🏃 USER / OPERATOR AUTO-GEOTAG**")
        if HAS_JS_EVAL:
            loc = get_geolocation()
            if loc and "coords" in loc:
                st.session_state.user_lat = round(float(loc["coords"]["latitude"]), 5)
                st.session_state.user_lon = round(float(loc["coords"]["longitude"]), 5)
        user_lat = st.number_input("User Latitude (Auto/Override)", key="user_lat", format="%.5f")
        user_lon = st.number_input("User Longitude (Auto/Override)", key="user_lon", format="%.5f")

house_w3w = get_what3words(house_lat, house_lon, w3w_api_key)
user_w3w = get_what3words(user_lat, user_lon, w3w_api_key)
separation_dist = haversine_distance(house_lat, house_lon, user_lat, user_lon)
hw_state = st.session_state.property_hardware[selected_prop]

# --- 6. Multi-Location & User Proximity Threat Evaluation ---
active_hazards = scan_location_hazards(house_lat, house_lon, scan_radius_km, firms_api_key)
user_hazards = scan_location_hazards(user_lat, user_lon, scan_radius_km, firms_api_key)

active_alerts = []
passive_advisories = []
threat_matrix_rows = []

locations_to_audit = [("Current User (Operator GPS)", user_lat, user_lon, user_hazards)]
for p_name, p_info in st.session_state.properties.items():
    if p_name == selected_prop:
        loc_haz = active_hazards
    else:
        loc_haz = scan_location_hazards(p_info["lat"], p_info["lon"], scan_radius_km, firms_api_key)
    locations_to_audit.append((p_name, p_info["lat"], p_info["lon"], loc_haz))

for label, lat_v, lon_v, haz in locations_to_audit:
    reasons = []
    advisory_notes = []

    if haz["nearest_fire"] <= st.session_state.fire_alert_km:
        reasons.append(f"🔥 Fire {haz['nearest_fire']:.2f} KM away")

    for item in haz["ea_items"]:
        sev = item.get("parsed_severity", 3)
        desc = item.get("description", "Flood Zone")
        if sev == 1:
            reasons.append(f"🚨 SEVERE FLOOD WARNING (Level 1 - Life Threat): {desc}")
        elif sev == 2:
            reasons.append(f"🌊 FLOOD WARNING (Level 2 - Action Required): {desc}")
        elif sev == 3:
            if st.session_state.ping_level_3:
                reasons.append(f"⚠️ Flood Alert (Level 3): {desc}")
            else:
                advisory_notes.append(f"Level 3 Flood Alert: {desc}")

    if haz["surge_ratio"] is not None and haz["surge_ratio"] >= st.session_state.discharge_ratio_threshold:
        reasons.append(f"🌊 River Surge {haz['surge_ratio']:.1f}× normal ({haz['peak_discharge']:.1f} m³/s)")

    if reasons:
        active_alerts.append(f"{label}: " + " | ".join(reasons))
    if advisory_notes:
        passive_advisories.append(f"{label}: " + " | ".join(advisory_notes))

    f_col_txt = f"{haz['nearest_fire']:.2f} KM" if haz["nearest_fire"] != float('inf') else "Clear"
    if haz["surge_ratio"] is not None:
        r_col_txt = f"{haz['peak_discharge']:.1f} m³/s ({haz['surge_ratio']:.1f}×)"
    elif haz["peak_discharge"] is not None:
        r_col_txt = f"{haz['peak_discharge']:.1f} m³/s"
    else:
        r_col_txt = "N/A"

    if reasons:
        status_badge = "🚨 DANGER"
    elif advisory_notes:
        status_badge = "⚠️ LEVEL 3 WATCH"
    else:
        status_badge = "🟢 CLEAR"

    threat_matrix_rows.append({
        "Monitored Target": label,
        "Status": status_badge,
        "Nearest Fire": f_col_txt,
        "GloFAS River Flow": r_col_txt,
        "UK EA Warnings": len(haz["ea_items"])
    })

# Global Top-Level Danger Notification Banner & Browser Ping
if active_alerts:
    joined_alerts = " • ".join(active_alerts)
    st.markdown(f"""
    <div class="tactical-header-container header-alert" style="margin-bottom: 14px;">
        <h2 class="tactical-title" style="color: #ff4757;">🚨 PROXIMITY DANGER ALERT: THREAT DETECTED NEAR MONITORED TARGET</h2>
        <p style="color: #ffcccc; font-size: 13px; margin: 6px 0 0 0; font-weight: bold;">{joined_alerts}</p>
    </div>
    """, unsafe_allow_html=True)

    alert_sig = "|".join(active_alerts)
    if alert_sig != st.session_state.last_alert_signature:
        st.session_state.last_alert_signature = alert_sig
        st.toast(f"🚨 DANGER ALERT: {active_alerts[0]}", icon="🚨")
        if st.session_state.enable_browser_ping:
            safe_ping_msg = json.dumps(active_alerts[0])
            components.html(f"""
                <script>
                (function() {{
                    try {{
                        const ctx = new (window.AudioContext || window.webkitAudioContext)();
                        const osc = ctx.createOscillator();
                        const gain = ctx.createGain();
                        osc.type = 'sawtooth';
                        osc.frequency.setValueAtTime(880, ctx.currentTime);
                        gain.gain.setValueAtTime(0.15, ctx.currentTime);
                        osc.connect(gain);
                        gain.connect(ctx.destination);
                        osc.start();
                        osc.stop(ctx.currentTime + 0.35);
                    }} catch(e) {{}}
                    if ("Notification" in window) {{
                        if (Notification.permission === "granted") {{
                            new Notification("🚨 TACTICAL DANGER ALERT", {{ body: {safe_ping_msg} }});
                        }} else if (Notification.permission !== "denied") {{
                            Notification.requestPermission().then(function(perm) {{
                                if (perm === "granted") {{
                                    new Notification("🚨 TACTICAL DANGER ALERT", {{ body: {safe_ping_msg} }});
                                }}
                            }});
                        }}
                    }}
                }})();
                </script>
            """, height=0)
elif passive_advisories:
    joined_adv = " • ".join(passive_advisories)
    st.markdown(f"""
    <div class="tactical-header-container header-warn" style="margin-bottom: 14px;">
        <h2 class="tactical-title" style="color: #ffa502;">⚠️ FLOOD ALERT ADVISORY (SEVERITY LEVEL 3 — BE PREPARED)</h2>
        <p style="color: #ffeaa7; font-size: 12px; margin: 6px 0 0 0;">{joined_adv}</p>
    </div>
    """, unsafe_allow_html=True)

fire_points = active_hazards["fires"]
closest_fire_dist = active_hazards["nearest_fire"]
flood_warnings = active_hazards["ea_items"]
river_discharge_peak = active_hazards["peak_discharge"]
surge_ratio_active = active_hazards["surge_ratio"]
flood_source_label = active_hazards["source_label"]

fire_threat_str = f"{closest_fire_dist:.2f} KM" if closest_fire_dist != float('inf') else "CLEAR"
flood_count = len(flood_warnings)
discharge_str = f"{river_discharge_peak:.1f} m³/s" if river_discharge_peak is not None else "N/A"
ratio_str = f"{surge_ratio_active:.1f}× mean" if surge_ratio_active is not None else "Baseline N/A"

# --- 7. Five-Tab Command Navigation (Home Defence Far Right) ---
tab_fire, tab_flood, tab_blackout, tab_relays, tab_defence = st.tabs([
    "🔥 FIRE COMMAND",
    "🌊 FLOOD COMMAND",
    "⬛ BLACKOUT STEALTH OPS",
    "👥 EMERGENCY RELAYS",
    "🛡️ HOME DEFENCE (VIP)"
])

# ==========================================
# TAB 1: FIRE COMMAND MATRIX
# ==========================================
with tab_fire:
    is_fire_breach = len(fire_points) > 0 and closest_fire_dist <= st.session_state.fire_alert_km
    if is_fire_breach:
        st.markdown(f"""
        <div class="tactical-header-container header-alert">
            <h1 class="tactical-title" style="color: #ff4757;">FIRE BREACH DETECTED: {selected_prop.upper()}</h1>
        </div>
        <div class="sub-status-bar" style="background-color: #170a0a; border: 1px solid #7c1a1a;">
            <span style="color: #ff4757;">⚠️ NEAREST THERMAL HOTSPOT: {fire_threat_str}</span>
            <span style="color: #ff4757;">ASSET W3W: {house_w3w}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="tactical-header-container header-nominal">
            <h1 class="tactical-title" style="color: #2ed573;">FIRE MATRIX NOMINAL: {selected_prop.upper()}</h1>
        </div>
        <div class="sub-status-bar" style="background-color: #0a170f; border: 1px solid #1a7c3e;">
            <span style="color: #2ed573;">🟢 GLOBAL VIIRS SATELLITE: {fire_threat_str}</span>
            <span style="color: #2ed573;">ASSET W3W: {house_w3w}</span>
        </div>
        """, unsafe_allow_html=True)

    f_col1, f_col2 = st.columns(2)
    with f_col1:
        with st.container(border=True):
            render_panel_header(f"📡 SATELLITE THERMAL RADAR — {len(st.session_state.properties)} SAVED LOCATIONS")
            m_fire = folium.Map(
                location=[house_lat, house_lon],
                zoom_start=11,
                tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                attr="Esri"
            )
            if fire_points:
                heatmap_coords = [[float(pt[0]), float(pt[1]), float(pt[2])] for pt in fire_points]
                HeatMap(data=heatmap_coords, radius=25, blur=15).add_to(m_fire)

            for p_name, p_info in st.session_state.properties.items():
                p_w3w = get_what3words(p_info["lat"], p_info["lon"], w3w_api_key)
                if p_name == selected_prop:
                    folium.Marker(
                        [p_info["lat"], p_info["lon"]],
                        popup=f"🏡 ACTIVE: {p_name} ({p_w3w})",
                        tooltip=f"🏡 {p_name}",
                        icon=folium.Icon(color="red", icon="home")
                    ).add_to(m_fire)
                else:
                    folium.Marker(
                        [p_info["lat"], p_info["lon"]],
                        popup=f"⭐ FAVORITE: {p_name} ({p_w3w})",
                        tooltip=f"⭐ {p_name}",
                        icon=folium.Icon(color="orange", icon="star")
                    ).add_to(m_fire)

            folium.Marker(
                [user_lat, user_lon],
                popup=f"🏃 OPERATOR GPS ({user_w3w})",
                tooltip="🏃 Current User GPS",
                icon=folium.Icon(color="blue", icon="user")
            ).add_to(m_fire)
            st_folium(m_fire, width=650, height=340, key="fire_map")

    with f_col2:
        with st.container(border=True):
            render_panel_header("📊 FIRE TELEMETRY & LIVE PROXIMITY THREAT MATRIX")
            st.markdown(f"""
            <div class="status-pill-container">
                <div class="status-pill"><div style="font-size:10px; color:#8b949e;">ACTIVE HOTSPOTS</div><div class="pill-val" style="color:#ff9f43;">{len(fire_points)}</div></div>
                <div class="status-pill"><div style="font-size:10px; color:#8b949e;">FIRE DISTANCE</div><div class="pill-val" style="color:#ff4757;">{fire_threat_str}</div></div>
                <div class="status-pill"><div style="font-size:10px; color:#8b949e;">USER SEPARATION</div><div class="pill-val" style="color:#52a3ff;">{separation_dist:.2f} KM</div></div>
            </div>
            <div class="w3w-badge">🏡 <b>{selected_prop}:</b> {house_w3w} ({house_lat:.4f}, {house_lon:.4f})</div>
            <div class="w3w-badge">🏃 <b>OPERATOR GPS:</b> {user_w3w} ({user_lat:.5f}, {user_lon:.5f})</div>
            """, unsafe_allow_html=True)

            st.dataframe(pd.DataFrame(threat_matrix_rows), hide_index=True, width="stretch")

        with st.container(border=True):
            render_panel_header("📡 FIRE EMERGENCY BROADCASTER")
            contact_opts = [f"{c['Name']} ({c['Relation']})" for c in st.session_state.next_of_kin] or ["No Contacts Logged"]
            chosen_fire_contact = st.selectbox("Select Relay Contact", contact_opts, key="fire_contact")
            fire_msg = (
                f"FIRE ALERT ({selected_prop}): Nearest hotspot at {fire_threat_str}. "
                f"Location W3W: {house_w3w} | Operator: {user_w3w} "
                f"(https://www.google.com/maps?q={user_lat},{user_lon})"
            )
            wa_fire = f"https://api.whatsapp.com/send?text={urllib.parse.quote(fire_msg)}"
            st.markdown(f'<a href="{wa_fire}" target="_blank" class="btn-broadcast">🚀 SEND FIRE LOCATION TO {chosen_fire_contact.upper()}</a>', unsafe_allow_html=True)

# ==========================================
# TAB 2: FLOOD COMMAND MATRIX (UK + EUROPE)
# ==========================================
with tab_flood:
    has_active_flood_alarm = any(item.get("parsed_severity") in (1, 2) for item in flood_warnings) or (
        surge_ratio_active is not None and surge_ratio_active >= st.session_state.discharge_ratio_threshold
    )
    if has_active_flood_alarm:
        st.markdown(f"""
        <div class="tactical-header-container header-alert">
            <h1 class="tactical-title" style="color: #ff4757;">FLOOD WARNING ACTIVE: {selected_prop.upper()}</h1>
        </div>
        <div class="sub-status-bar" style="background-color: #170a0a; border: 1px solid #7c1a1a;">
            <span style="color: #ff4757;">🌊 FEED: {flood_source_label}</span>
            <span style="color: #ff4757;">FLOW: {discharge_str} ({ratio_str})</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="tactical-header-container header-nominal">
            <h1 class="tactical-title" style="color: #2ed573;">FLOOD MATRIX NOMINAL: {selected_prop.upper()}</h1>
        </div>
        <div class="sub-status-bar" style="background-color: #0a170f; border: 1px solid #1a7c3e;">
            <span style="color: #2ed573;">🌊 FEED: {flood_source_label}</span>
            <span style="color: #2ed573;">FLOW: {discharge_str} ({ratio_str})</span>
        </div>
        """, unsafe_allow_html=True)

    fl_col1, fl_col2 = st.columns(2)
    with fl_col1:
        with st.container(border=True):
            render_panel_header(f"🌊 HYDROLOGICAL MAP — {len(st.session_state.properties)} SAVED LOCATIONS")
            m_flood = folium.Map(
                location=[house_lat, house_lon],
                zoom_start=11,
                tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                attr="Esri"
            )
            folium.Circle(
                location=[house_lat, house_lon],
                radius=scan_radius_km * 1000,
                color="#52a3ff",
                fill=True,
                fill_opacity=0.08
            ).add_to(m_flood)

            for p_name, p_info in st.session_state.properties.items():
                p_w3w = get_what3words(p_info["lat"], p_info["lon"], w3w_api_key)
                if p_name == selected_prop:
                    folium.Marker(
                        [p_info["lat"], p_info["lon"]],
                        popup=f"🏡 ACTIVE: {p_name} ({p_w3w})",
                        tooltip=f"🏡 {p_name}",
                        icon=folium.Icon(color="red", icon="home")
                    ).add_to(m_flood)
                else:
                    folium.Marker(
                        [p_info["lat"], p_info["lon"]],
                        popup=f"⭐ FAVORITE: {p_name} ({p_w3w})",
                        tooltip=f"⭐ {p_name}",
                        icon=folium.Icon(color="orange", icon="star")
                    ).add_to(m_flood)

            folium.Marker(
                [user_lat, user_lon],
                popup=f"🏃 OPERATOR GPS ({user_w3w})",
                tooltip="🏃 Current User GPS",
                icon=folium.Icon(color="blue", icon="user")
            ).add_to(m_flood)
            st_folium(m_flood, width=650, height=340, key="flood_map")

    with fl_col2:
        with st.container(border=True):
            render_panel_header("📊 EUROPEAN & UK FLOOD TELEMETRY")
            st.markdown(f"""
            <div class="status-pill-container">
                <div class="status-pill"><div style="font-size:10px; color:#8b949e;">UK EA ACTIVE</div><div class="pill-val" style="color:#52a3ff;">{flood_count}</div></div>
                <div class="status-pill"><div style="font-size:10px; color:#8b949e;">GLOFAS FLOW</div><div class="pill-val" style="color:#2ed573;">{discharge_str}</div></div>
                <div class="status-pill"><div style="font-size:10px; color:#8b949e;">SURGE RATIO</div><div class="pill-val" style="color:#ffa502;">{ratio_str}</div></div>
            </div>
            <div class="w3w-badge">🏡 <b>{selected_prop}:</b> {house_w3w}</div>
            <div class="w3w-badge">🌐 <b>COVERAGE ENGINE:</b> {flood_source_label}</div>
            """, unsafe_allow_html=True)

            if flood_warnings:
                for w in flood_warnings[:4]:
                    sev = w.get("parsed_severity", 3)
                    desc = w.get("description", "Flood Zone")
                    if sev == 1:
                        st.error(f"🚨 **SEVERITY 1 — SEVERE FLOOD WARNING (DANGER TO LIFE):** {desc}")
                    elif sev == 2:
                        st.error(f"🌊 **SEVERITY 2 — FLOOD WARNING (FLOODING EXPECTED):** {desc}")
                    else:
                        st.warning(f"⚠️ **SEVERITY 3 — FLOOD ALERT (BE PREPARED):** {desc}")
            else:
                st.info(f"Copernicus GloFAS 3-day peak river discharge near {selected_prop}: **{discharge_str}** ({ratio_str}).")

        with st.container(border=True):
            render_panel_header("📡 FLOOD EMERGENCY BROADCASTER")
            chosen_flood_contact = st.selectbox("Select Relay Contact", contact_opts, key="flood_contact")
            flood_msg = (
                f"FLOOD STATUS ({selected_prop}): EA Warnings: {flood_count} | River Flow: {discharge_str} ({ratio_str}). "
                f"Location: {house_w3w} | Operator: {user_w3w} "
                f"(https://www.google.com/maps?q={user_lat},{user_lon})"
            )
            wa_flood = f"https://api.whatsapp.com/send?text={urllib.parse.quote(flood_msg)}"
            st.markdown(f'<a href="{wa_flood}" target="_blank" class="btn-broadcast">🚀 SEND FLOOD LOCATION TO {chosen_flood_contact.upper()}</a>', unsafe_allow_html=True)

# ==========================================
# TAB 3: BLACKOUT STEALTH OPS
# ==========================================
with tab_blackout:
    st.markdown(f"""
    <div class="blackout-box">
        <div class="blackout-title">⬛ BLACKOUT STEALTH OPS — ZERO-GLARE NIGHT VISION MODE</div>
        <p style="margin:0; font-size:12px;">ACTIVE ASSET: {selected_prop.upper()} | CLEARANCE TIER: {st.session_state.auth_tier}</p>
    </div>
    """, unsafe_allow_html=True)

    b_col1, b_col2 = st.columns(2)
    with b_col1:
        st.markdown(f"""
        <div class="blackout-box">
            <div class="blackout-title">WHAT3WORDS & GPS COORDINATE LOCK</div>
            <p style="margin:4px 0; font-size:12px;">OPERATOR W3W TAG:</p>
            <div class="blackout-val">{user_w3w}</div>
            <p style="margin:4px 0 12px 0; font-size:11px;">GPS: {user_lat:.5f}, {user_lon:.5f}</p>
            <p style="margin:4px 0; font-size:12px;">{selected_prop.upper()} W3W TAG:</p>
            <div class="blackout-val">{house_w3w}</div>
            <p style="margin:4px 0 0 0; font-size:11px;">SEPARATION: {separation_dist:.2f} KM</p>
        </div>
        """, unsafe_allow_html=True)

    with b_col2:
        st.markdown(f"""
        <div class="blackout-box">
            <div class="blackout-title">THREAT & DEFENCE SUMMARY</div>
            <p style="margin:6px 0; font-size:14px;">• NEAREST FIRE VECTOR: <b>{fire_threat_str}</b></p>
            <p style="margin:6px 0; font-size:14px;">• GLOFAS RIVER DISCHARGE: <b>{discharge_str} ({ratio_str})</b></p>
            <p style="margin:6px 0; font-size:14px;">• PERIMETER DEADBOLTS: <b>{'LOCKED' if hw_state['deadbolts_locked'] else 'UNLOCKED'}</b></p>
            <p style="margin:6px 0; font-size:14px;">• SPRINKLERS / BARRIERS: <b>{'ARMED' if hw_state['sprinkler_armed'] or hw_state['flood_barrier_deployed'] else 'STANDBY'}</b></p>
        </div>
        """, unsafe_allow_html=True)

    sos_msg = f"STEALTH SOS ({selected_prop}): Operator at {user_w3w} ({user_lat:.5f}, {user_lon:.5f}). Fire: {fire_threat_str} | Flow: {discharge_str}."
    wa_sos = f"https://api.whatsapp.com/send?text={urllib.parse.quote(sos_msg)}"
    st.markdown(f'<a href="{wa_sos}" target="_blank" class="btn-blackout-sos">TRANSMIT RED-CHANNEL SOS BEACON</a>', unsafe_allow_html=True)

# ==========================================
# TAB 4: EMERGENCY RELAYS & LOG EXPORT
# ==========================================
with tab_relays:
    r_col1, r_col2 = st.columns(2)
    with r_col1:
        with st.container(border=True):
            render_panel_header("🗃️ EMERGENCY CONTACTS / NEXT OF KIN")
            with st.form("kin_entry_form", clear_on_submit=True):
                k1, k2, k3 = st.columns(3)
                with k1:
                    new_name = st.text_input("Next of Kin Name")
                with k2:
                    new_rel = st.text_input("Relationship")
                with k3:
                    new_vec = st.text_input("Phone / Email")
                if st.form_submit_button("➕ LOG CONTACT ENTRY") and new_name and new_vec:
                    st.session_state.next_of_kin.append({
                        "Name": new_name,
                        "Relation": new_rel,
                        "Contact": new_vec
                    })
                    st.toast(f"Logged safety node for {new_name}.", icon="✅")
                    st.rerun()
            st.dataframe(pd.DataFrame(st.session_state.next_of_kin), hide_index=True, width="stretch")

    with r_col2:
        with st.container(border=True):
            render_panel_header("💾 MULTI-PROPERTY TELEMETRY LOG EXPORT")
            ts_now = time.strftime("%Y-%m-%d %H:%M:%S")
            log_dump = (
                f"==================================================\n"
                f"        TACTICAL MATRIX OPERATIONS RECORD          \n"
                f"==================================================\n"
                f"TIMESTAMP LOGGED       : {ts_now}\n"
                f"ACTIVE LOCATION        : {selected_prop}\n"
                f"LOCATION W3W           : {house_w3w}\n"
                f"OPERATOR W3W           : {user_w3w}\n"
                f"NEAREST FIRE VECTOR    : {fire_threat_str}\n"
                f"RIVER DISCHARGE PEAK   : {discharge_str} ({ratio_str})\n"
                f"SAVED LOCATIONS COUNT  : {len(st.session_state.properties)}/{MAX_LOCATIONS}\n"
                f"==================================================\n"
            )
            st.download_button(
                label="📥 DOWNLOAD INCIDENT LOG FILE (.LOG)",
                data=log_dump,
                file_name=f"tactical_dump_{int(time.time())}.log",
                mime="text/plain",
                width="stretch"
            )

# ==========================================
# TAB 5: HOME DEFENCE & SECURITY (FAR RIGHT - SUBSCRIPTIONS ONLY)
# ==========================================
with tab_defence:
    pro_secret = get_secret_safe("PRO_ACCESS_KEY", "PRO-2026")
    vip_secret = get_secret_safe("VIP_ACCESS_KEY", "VIP-2026")
    override_pin_secret = get_secret_safe("HARDWARE_PIN", "1234")

    if st.session_state.auth_tier == "FREE":
        st.markdown("""
        <div class="tactical-header-container header-vip">
            <h1 class="tactical-title" style="color: #ffa502;">🔒 SUBSCRIPTION REQUIRED: HOME DEFENCE & SECURITY</h1>
        </div>
        """, unsafe_allow_html=True)

        with st.container(border=True):
            render_panel_header("👑 TWO-TIER SUBSCRIPTION AUTHENTICATION GATE")
            now = time.time()
            if now < st.session_state.lockout_until:
                rem = int(st.session_state.lockout_until - now)
                st.error(f"🚨 SECURITY LOCKOUT ACTIVE: Too many invalid attempts. Retry in {rem}s.")
            else:
                st.info(
                    "**Choose Your Clearance Tier:**\n"
                    "* **PRO TIER (`PRO-2026`):** Unlocks Multi-Property Smart Deadbolts, Perimeter Sensors & CCTV Feeds.\n"
                    "* **VIP TIER (`VIP-2026`):** Unlocks Full Perimeter Security **PLUS** Remote Fire Sprinklers, Flood Barriers & Emergency Lockdown."
                )
                sub_c1, sub_c2 = st.columns([3, 1])
                with sub_c1:
                    entered_key = st.text_input(
                        "Enter Subscription Access Key",
                        type="password",
                        placeholder="PRO-2026 or VIP-2026",
                        key="defence_sub_input"
                    )
                with sub_c2:
                    st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                    if st.button("🔓 AUTHENTICATE", width="stretch", key="defence_auth_btn"):
                        if entered_key == vip_secret:
                            st.session_state.auth_tier = "VIP"
                            st.session_state.failed_attempts = 0
                            st.session_state.security_logs.append(f"[{time.strftime('%H:%M:%S')}] VIP clearance granted.")
                            st.rerun()
                        elif entered_key == pro_secret:
                            st.session_state.auth_tier = "PRO"
                            st.session_state.failed_attempts = 0
                            st.session_state.security_logs.append(f"[{time.strftime('%H:%M:%S')}] PRO clearance granted.")
                            st.rerun()
                        else:
                            st.session_state.failed_attempts += 1
                            st.session_state.security_logs.append(f"[{time.strftime('%H:%M:%S')}] Failed auth attempt #{st.session_state.failed_attempts}.")
                            if st.session_state.failed_attempts >= 3:
                                st.session_state.lockout_until = time.time() + 60
                                st.error("🚨 3 failed attempts. Terminal locked for 60 seconds.")
                            else:
                                st.error(f"Invalid key ({st.session_state.failed_attempts}/3 attempts before lockout).")
    else:
        hdr_col1, hdr_col2 = st.columns([4, 1])
        with hdr_col1:
            st.markdown(f"""
            <div class="tactical-header-container header-vip">
                <h1 class="tactical-title" style="color: #ffa502;">🛡️ {st.session_state.auth_tier} DEFENCE MATRIX — {selected_prop.upper()}</h1>
            </div>
            """, unsafe_allow_html=True)
        with hdr_col2:
            st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
            if st.button("🔒 LOCK SESSION", width="stretch"):
                st.session_state.auth_tier = "FREE"
                st.rerun()

        def_prop = st.selectbox(
            "🎯 TARGET LOCATION FOR HARDWARE ACTUATION",
            list(st.session_state.properties.keys()),
            index=list(st.session_state.properties.keys()).index(selected_prop),
            key="defence_prop_selector"
        )
        if def_prop != selected_prop:
            st.session_state.active_property = def_prop
            st.rerun()

        def_hw = st.session_state.property_hardware[def_prop]

        with st.container(border=True):
            render_panel_header(f"🔐 PERIMETER SECURITY & INTRUSION MATRIX — {def_prop.upper()} ({st.session_state.auth_tier} ACCESS)")
            sec1, sec2, sec3 = st.columns(3)
            with sec1:
                def_hw["deadbolts_locked"] = st.toggle(
                    "Smart Perimeter Deadbolts",
                    value=def_hw["deadbolts_locked"],
                    key=f"db_{def_prop}"
                )
                st.caption("Status: SEALED" if def_hw["deadbolts_locked"] else "Status: UNLOCKED")
            with sec2:
                def_hw["perimeter_sensors"] = st.toggle(
                    "Infrared & Motion Perimeter Grid",
                    value=def_hw["perimeter_sensors"],
                    key=f"ps_{def_prop}"
                )
                st.caption("4 Zones Armed" if def_hw["perimeter_sensors"] else "Sensors Bypassed")
            with sec3:
                def_hw["cctv_active"] = st.toggle(
                    "Encrypted CCTV Cloud Recording",
                    value=def_hw["cctv_active"],
                    key=f"cc_{def_prop}"
                )
                st.caption("4K Night-IR Streaming" if def_hw["cctv_active"] else "Cameras Offline")

        if st.session_state.auth_tier != "VIP":
            with st.container(border=True):
                render_panel_header("👑 VIP HARDWARE ACTUATORS (UPGRADE REQUIRED)")
                st.warning(
                    "You are logged in with **PRO Tier** (Security Only). Upgrade to **VIP Tier (`VIP-2026`)** to unlock remote **Fire Suppression Sprinklers**, **Hydraulic Flood Barriers**, and **PIN-Protected Emergency Lockdown**."
                )
        else:
            d1, d2, d3 = st.columns(3)
            with d1:
                with st.container(border=True):
                    render_panel_header("🔥 FIRE SUPPRESSION PUMPS")
                    def_hw["sprinkler_armed"] = st.toggle(
                        "Arm Roof & Perimeter Sprinklers",
                        value=def_hw["sprinkler_armed"],
                        key=f"sp_{def_prop}"
                    )
                    def_hw["target_psi"] = st.slider(
                        "Line Pressure (PSI)", 40, 120, def_hw["target_psi"],
                        key=f"psi_{def_prop}"
                    )
                    st.metric("Water Reservoir", "96% (4,800 L)", delta="Active" if def_hw["sprinkler_armed"] else "Standby")

            with d2:
                with st.container(border=True):
                    render_panel_header("🌊 FLOOD BARRIERS & SUMP")
                    def_hw["flood_barrier_deployed"] = st.toggle(
                        "Deploy Hydraulic Flood Gates",
                        value=def_hw["flood_barrier_deployed"],
                        key=f"fb_{def_prop}"
                    )
                    def_hw["sump_pump_active"] = st.toggle(
                        "Dual Submersible Sump Pumps",
                        value=def_hw["sump_pump_active"],
                        key=f"sm_{def_prop}"
                    )
                    def_hw["flow_rate"] = st.slider(
                        "Discharge Rate (L/min)", 100, 600, def_hw["flow_rate"],
                        key=f"fl_{def_prop}"
                    )
                    st.metric("Sump Pit Level", "12 cm", delta=f"{def_hw['flow_rate']} L/min")

            with d3:
                with st.container(border=True):
                    render_panel_header("🚨 PIN-PROTECTED LOCKDOWN")
                    def_hw["shutters_locked"] = st.toggle(
                        "Steel Storm & Ember Shutters",
                        value=def_hw["shutters_locked"],
                        key=f"sh_{def_prop}"
                    )
                    pin_input = st.text_input("4-Digit Hardware PIN (Demo: 1234)", type="password", max_chars=4, key=f"pin_{def_prop}")
                    if st.button("🚨 EXECUTE FULL LOCKDOWN", width="stretch", key=f"ld_{def_prop}"):
                        if pin_input == override_pin_secret:
                            def_hw["sprinkler_armed"] = True
                            def_hw["flood_barrier_deployed"] = True
                            def_hw["sump_pump_active"] = True
                            def_hw["deadbolts_locked"] = True
                            def_hw["shutters_locked"] = True
                            st.session_state.security_logs.append(f"[{time.strftime('%H:%M:%S')}] FULL LOCKDOWN executed for {def_prop}.")
                            st.toast(f"FULL LOCKDOWN EXECUTED: {def_prop}", icon="🚨")
                            st.rerun()
                        else:
                            st.error("Invalid 4-digit Hardware Override PIN.")

        with st.container(border=True):
            render_panel_header("📜 SECURITY & HARDWARE AUDIT LOG")
            for entry in reversed(st.session_state.security_logs[-6:]):
                st.code(entry, language="text")
