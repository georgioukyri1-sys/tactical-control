import os
import io
import time
import json
import hmac
import math
import hashlib
import secrets
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

try:
    import folium
    from folium.plugins import HeatMap, Fullscreen
    from streamlit_folium import st_folium
    HAS_FOLIUM = True
except ImportError:
    HAS_FOLIUM = False

try:
    from streamlit_js_eval import get_geolocation
    HAS_JS_EVAL = True
except ImportError:
    HAS_JS_EVAL = False

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

try:
    import qrcode
    HAS_QR = True
except ImportError:
    HAS_QR = False


# ==============================================================================
# 1. PAGE CONFIG & TACTICAL DARK THEME
# ==============================================================================
st.set_page_config(
    page_title="TACTICAL COMMAND MATRIX // A.G.E.H.I.C. & PFR",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0b111a;
        color: #e2e8f0;
    }
    .tactical-banner {
        background: linear-gradient(90deg, #064e3b 0%, #0f172a 100%);
        border: 1px solid #10b981;
        border-radius: 6px;
        padding: 10px 16px;
        font-weight: 700;
        font-size: 15px;
        color: #ecfdf5;
        margin-bottom: 12px;
        letter-spacing: 0.5px;
    }
    .tactical-card {
        background-color: #111827;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 12px 14px;
        margin-bottom: 10px;
    }
    .card-header {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        color: #94a3b8;
        letter-spacing: 0.8px;
        margin-bottom: 4px;
    }
    .status-val-green { font-size: 22px; font-weight: 800; color: #10b981; }
    .status-val-red { font-size: 22px; font-weight: 800; color: #ef4444; }
    .status-val-cyan { font-size: 22px; font-weight: 800; color: #38bdf8; }
    .stealth-hud {
        background-color: #000000;
        border: 1px solid #7f1d1d;
        border-radius: 8px;
        padding: 20px;
        color: #f87171;
        font-family: monospace;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# 2. SESSION STATE INITIALIZATION
# ==============================================================================
ARDUINO_HMAC_KEY = b"AGEHIC_9910_HMAC_KEY_CHANGE_ME"

if "properties" not in st.session_state:
    st.session_state.properties = [
        {"name": "Primary Residence (Harlow HQ)", "lat": 51.7765, "lon": 0.1066, "postcode": "CM20 1AA"}
    ]

if "op_coords" not in st.session_state:
    st.session_state.op_coords = {"lat": 51.7765, "lon": 0.1066, "source": "DEFAULT"}

if "gps_trail" not in st.session_state:
    st.session_state.gps_trail = []

if "nok_tracking_active" not in st.session_state:
    st.session_state.nok_tracking_active = False

if "nok_session_token" not in st.session_state:
    st.session_state.nok_session_token = f"TRK-{secrets.token_hex(3).upper()}"

if "nok_webhook_url" not in st.session_state:
    st.session_state.nok_webhook_url = ""

if "last_webhook_push" not in st.session_state:
    st.session_state.last_webhook_push = 0.0

if "contacts" not in st.session_state:
    st.session_state.contacts = [
        {"name": "Primary Next of Kin", "phone": "+447700900001", "role": "Family / Emergency"}
    ]

if "pro_unlocked" not in st.session_state:
    st.session_state.pro_unlocked = False
if "vip_unlocked" not in st.session_state:
    st.session_state.vip_unlocked = False
if "vip_safety_armed" not in st.session_state:
    st.session_state.vip_safety_armed = False
if "vip_last_active" not in st.session_state:
    st.session_state.vip_last_active = time.time()
if "pin_attempts" not in st.session_state:
    st.session_state.pin_attempts = 0
if "security_log" not in st.session_state:
    st.session_state.security_log = []

if "arduino_port" not in st.session_state:
    st.session_state.arduino_port = "NONE"
if "arduino_conn" not in st.session_state:
    st.session_state.arduino_conn = None
if "arduino_telemetry" not in st.session_state:
    st.session_state.arduino_telemetry = {}
if "last_synced_cmds" not in st.session_state:
    st.session_state.last_synced_cmds = {}
if "last_ping_sent" not in st.session_state:
    st.session_state.last_ping_sent = 0.0

if "hw" not in st.session_state:
    st.session_state.hw = {
        "master_shutdown": False,
        "agehic_pump_mode": "AUTO (FIRMS / THERMAL)",
        "pulse_cycle": "FULL ON (100%)",
        "zone1_ridge": False,
        "zone2_eaves": False,
        "zone3_perim": False,
        "intake_valve": True,
        "thermogal_inject": False,
        "thermogal_mode": "AUTO-THERMAL (65°C)",
        "thermogal_valve_deployed": False,
        "thermogal_tank_litres": 200,
        "ac_breaker_cut": False,
        "barrier_mode": "AUTO-BUOYANCY",
        "barrier_front": False,
        "barrier_rear": False,
        "barrier_garage": False,
        "airbricks_sealed": False,
        "sewer_valve_locked": False,
        "letterbox_sealed": False,
        "sump_mode": "AUTO (FLOAT)",
        "sump_pit_mm": 120,
        "cistern_litres": 9400,
        "ambient_temp_c": 22,
        "vault_temp_c": 20,
        "peltier_cooler_on": True,
        "micromist_cooling_on": False,
        "batt_a_pct": 98,
        "batt_b_pct": 97,
        "batt_a_fuse_ok": True,
        "batt_b_fuse_ok": True,
    }


# ==============================================================================
# 3. HELPER FUNCTIONS (GEOCODING, GPS TRAIL, QR, HAZARDS & ARDUINO BRIDGE)
# ==============================================================================
def log_security_event(msg: str):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    st.session_state.security_log.insert(0, f"[{ts}] {msg}")
    st.session_state.security_log = st.session_state.security_log[:50]


def record_operator_position(lat: float, lon: float):
    trail = st.session_state.gps_trail
    if not trail or abs(trail[-1]["lat"] - lat) > 0.00005 or abs(trail[-1]["lon"] - lon) > 0.00005:
        trail.append({
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "ts": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
        })
        st.session_state.gps_trail = trail[-50:]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def compass_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> str:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    brng = (math.degrees(math.atan2(y, x)) + 360) % 360
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[round(brng / 45) % 8]


def to_w3w_hash(lat: float, lon: float) -> str:
    words_a = ["shield", "beacon", "harbour", "summit", "cedar", "granite", "anchor", "falcon"]
    words_b = ["ridge", "stream", "ember", "watch", "crest", "valley", "bridge", "forge"]
    words_c = ["north", "spark", "river", "stone", "flame", "haven", "tower", "pulse"]
    h = hashlib.sha256(f"{lat:.5f},{lon:.5f}".encode()).digest()
    return f"///{words_a[h[0] % 8]}.{words_b[h[1] % 8]}.{words_c[h[2] % 8]}"


@st.cache_data(ttl=3600)
def geocode_postcode_or_address(query: str):
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": "AGEHIC-Command-Matrix/1.0"},
            timeout=6,
        )
        data = r.json()
        if data:
            return {
                "lat": round(float(data[0]["lat"]), 6),
                "lon": round(float(data[0]["lon"]), 6),
                "label": data[0].get("display_name", query).split(",")[0].strip(),
            }
    except Exception:
        pass
    return None


@st.cache_data(ttl=600)
def reverse_geocode_place(lat: float, lon: float) -> str:
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": round(lat, 4), "lon": round(lon, 4), "format": "json"},
            headers={"User-Agent": "AGEHIC-Command-Matrix/1.0"},
            timeout=5,
        )
        addr = r.json().get("address", {})
        place = addr.get("town") or addr.get("city") or addr.get("village") or addr.get("suburb") or addr.get("county")
        if place:
            return str(place).upper()
    except Exception:
        pass
    return "LOCAL SECTOR"


def generate_qr_png(payload: str):
    if not HAS_QR:
        return None
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def push_nok_webhook_update(active_prop: dict, hazards: dict):
    url = st.session_state.nok_webhook_url.strip()
    if not url or not st.session_state.nok_tracking_active:
        return
    now = time.time()
    if now - st.session_state.last_webhook_push < 10.0:
        return
    st.session_state.last_webhook_push = now
    payload = {
        "token": st.session_state.nok_session_token,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "operator_lat": st.session_state.op_coords["lat"],
        "operator_lon": st.session_state.op_coords["lon"],
        "property": active_prop["name"],
        "fires_detected": len(hazards.get("fires", [])),
        "river_surge": hazards.get("river_surge", 1.0),
        "maps_url": f"https://maps.google.com/?q={st.session_state.op_coords['lat']:.6f},{st.session_state.op_coords['lon']:.6f}",
    }
    try:
        requests.post(url, json=payload, timeout=3)
    except Exception:
        pass


@st.cache_data(ttl=300)
def scan_location_hazards(lat: float, lon: float, radius_km: float, firms_key: str, simulate: bool):
    fires = []
    ea_floods = []
    river_surge = 1.0

    if simulate:
        fires = [
            {"lat": round(lat + 0.018, 5), "lon": round(lon + 0.022, 5), "frp": 42.5, "dist": round(haversine_km(lat, lon, lat + 0.018, lon + 0.022), 2)},
            {"lat": round(lat - 0.014, 5), "lon": round(lon + 0.015, 5), "frp": 28.0, "dist": round(haversine_km(lat, lon, lat - 0.014, lon + 0.015), 2)},
        ]
        ea_floods = [{"area": "River Stort Lower Floodplain (SIMULATED)", "severity": 2, "lat": lat + 0.009, "lon": lon - 0.011}]
        return {"fires": fires, "ea_floods": ea_floods, "river_surge": 2.15}

    if firms_key and firms_key.strip() != "DEMO_KEY":
        try:
            delta = 0.35
            bbox = f"{lon - delta:.4f},{lat - delta:.4f},{lon + delta:.4f},{lat + delta:.4f}"
            url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{firms_key.strip()}/VIIRS_SNPP_NRT/{bbox}/1"
            df = pd.read_csv(url)
            for _, row in df.iterrows():
                flat, flon = float(row["latitude"]), float(row["longitude"])
                d = haversine_km(lat, lon, flat, flon)
                if d <= radius_km:
                    fires.append({"lat": flat, "lon": flon, "frp": float(row.get("frp", 10.0)), "dist": round(d, 2)})
        except Exception:
            pass

    try:
        r_ea = requests.get(
            "https://environment.data.gov.uk/flood-monitoring/id/floods",
            params={"lat": lat, "long": lon, "dist": 15},
            timeout=6,
        )
        for item in r_ea.json().get("items", []):
            sev = int(item.get("severityLevel", 4))
            if sev <= 3:
                flood_area = item.get("floodArea", {})
                ea_floods.append({
                    "area": item.get("eaAreaName", "EA Flood Zone"),
                    "severity": sev,
                    "lat": flood_area.get("lat"),
                    "lon": flood_area.get("long"),
                })
    except Exception:
        pass

    try:
        r_riv = requests.get(
            "https://flood-api.open-meteo.com/v1/flood",
            params={"latitude": lat, "longitude": lon, "daily": "river_discharge", "forecast_days": 2},
            timeout=6,
        )
        vals = r_riv.json().get("daily", {}).get("river_discharge", [])
        vals = [v for v in vals if v is not None and v > 0]
        if len(vals) >= 2:
            river_surge = round(max(vals) / max(0.1, vals[0]), 2)
    except Exception:
        pass

    return {"fires": fires, "ea_floods": ea_floods, "river_surge": river_surge}


def build_colour_satellite_map(active_prop: dict, op_lat: float, op_lon: float, hazards: dict, zoom_start: int = 12, trail: list = None):
    m = folium.Map(
        location=[active_prop["lat"], active_prop["lon"]],
        zoom_start=zoom_start,
        tiles=None,
        control_scale=True,
    )
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        name="Colour Satellite",
        overlay=False,
        control=True,
    ).add_to(m)
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png",
        attr="CartoDB Labels",
        name="Place & Road Labels",
        overlay=True,
        control=True,
    ).add_to(m)
    folium.TileLayer(
        tiles="OpenStreetMap",
        name="Tactical Street Map",
        overlay=False,
        control=True,
    ).add_to(m)
    Fullscreen(position="topleft", title="Full Screen Map", title_cancel="Exit Full Screen").add_to(m)
    folium.Marker([active_prop["lat"], active_prop["lon"]], tooltip=f"PROPERTY: {active_prop['name']}", icon=folium.Icon(color="blue", icon="home")).add_to(m)
    folium.Marker([op_lat, op_lon], tooltip="OPERATOR LIVE GPS", icon=folium.Icon(color="green", icon="user")).add_to(m)
    if trail and len(trail) > 1:
        folium.PolyLine([[pt["lat"], pt["lon"]] for pt in trail], color="#38bdf8", weight=3, opacity=0.85, tooltip="Operator GPS Trail").add_to(m)
    if hazards.get("fires"):
        HeatMap([[f["lat"], f["lon"], f["frp"]] for f in hazards["fires"]], radius=22, blur=15, name="Thermal Heatmap").add_to(m)
        for f in hazards["fires"]:
            folium.CircleMarker([f["lat"], f["lon"]], radius=7, color="#ef4444", fill=True, fill_opacity=0.85, tooltip=f"Hotspot ({f['dist']} km)").add_to(m)
    for fl in hazards.get("ea_floods", []):
        if fl.get("lat") and fl.get("lon"):
            folium.Marker([fl["lat"], fl["lon"]], tooltip=f"FLOOD ALERT: {fl['area']}", icon=folium.Icon(color="cadetblue", icon="tint")).add_to(m)
    folium.LayerControl(collapsed=True).add_to(m)
    return m


# --- ARDUINO HMAC-SHA256 SERIAL BRIDGE ---
def get_available_ports():
    if not HAS_SERIAL:
        return ["NONE (pyserial missing)"]
    ports = [p.device for p in serial.tools.list_ports.comports()]
    return ["NONE"] + ports


def connect_arduino(port: str):
    if not HAS_SERIAL or not port or port.startswith("NONE"):
        st.session_state.arduino_conn = None
        return False, "Disconnected (Simulation Mode)"
    conn = st.session_state.arduino_conn
    if conn is not None and getattr(conn, "is_open", False) and conn.port == port:
        return True, f"Connected ({port})"
    try:
        ser = serial.Serial(port, 115200, timeout=0.2, write_timeout=0.5)
        time.sleep(1.5)
        st.session_state.arduino_conn = ser
        st.session_state.last_synced_cmds = {}
        return True, f"Connected ({port})"
    except Exception as e:
        st.session_state.arduino_conn = None
        return False, f"Port Error: {e}"


def sign_arduino_cmd(cmd: str) -> str:
    epoch = int(time.time())
    payload = f"{cmd}|{epoch}".encode("utf-8")
    sig = hmac.new(ARDUINO_HMAC_KEY, payload, hashlib.sha256).hexdigest()[:12].upper()
    return f"{cmd}|{epoch}|{sig}\n"


def read_arduino_telemetry():
    conn = st.session_state.arduino_conn
    if not conn or not getattr(conn, "is_open", False):
        return
    try:
        while conn.in_waiting > 0:
            line = conn.readline().decode("utf-8", errors="ignore").strip()
            if line.startswith("{") and line.endswith("}"):
                data = json.loads(line)
                st.session_state.arduino_telemetry = data
                if data.get("thermo_sealed"):
                    st.session_state.hw["thermogal_valve_deployed"] = True
    except Exception:
        pass


def sync_hw_to_arduino():
    conn = st.session_state.arduino_conn
    if not conn or not getattr(conn, "is_open", False):
        return
    hw = st.session_state.hw
    any_zone = hw["zone1_ridge"] or hw["zone2_eaves"] or hw["zone3_perim"]
    pump_on = 1 if (not hw["master_shutdown"] and hw["agehic_pump_mode"] != "STANDBY OFF" and any_zone) else 0
    pulse_on = 1 if "PULSE" in hw["pulse_cycle"] else 0
    flood_on = 1 if (hw["barrier_front"] or hw["barrier_rear"] or hw["barrier_garage"]) else 0
    sump_on = 1 if (not hw["master_shutdown"] and hw["sump_mode"] != "STANDBY OFF") else 0

    desired = {
        "PUMP": pump_on,
        "PULSE": pulse_on,
        "Z1": 1 if hw["zone1_ridge"] else 0,
        "Z2": 1 if hw["zone2_eaves"] else 0,
        "Z3": 1 if hw["zone3_perim"] else 0,
        "TG_INJ": 1 if hw["thermogal_inject"] else 0,
        "TG_SEAL": 1 if hw["thermogal_valve_deployed"] else 0,
        "AC_CUT": 1 if hw["ac_breaker_cut"] else 0,
        "FLOOD": flood_on,
        "SUMP": sump_on,
    }

    sent_any = False
    try:
        for key, val in desired.items():
            if st.session_state.last_synced_cmds.get(key) != val:
                pkt = sign_arduino_cmd(f"{key}:{val}")
                conn.write(pkt.encode("utf-8"))
                st.session_state.last_synced_cmds[key] = val
                sent_any = True
                time.sleep(0.02)

        now = time.time()
        if pump_on == 1 and (sent_any or now - st.session_state.last_ping_sent >= 4.0):
            conn.write(sign_arduino_cmd("PING").encode("utf-8"))
            st.session_state.last_ping_sent = now
    except Exception:
        st.session_state.arduino_conn = None


# ==============================================================================
# 4. SIDEBAR: PROPERTY GEOCODER, EXACT GPS, THRESHOLDS & AUTHENTICATION
# ==============================================================================
with st.sidebar:
    st.markdown("## 🛡️ COMMAND MATRIX")
    prop_names = [p["name"] for p in st.session_state.properties]
    selected_idx = st.selectbox(
        "Active Monitored Property",
        range(len(prop_names)),
        format_func=lambda i: prop_names[i],
    )
    selected_idx = min(selected_idx, len(st.session_state.properties) - 1)
    active_prop = st.session_state.properties[selected_idx]

    with st.expander("➕ Add / Remove Properties (Max 5)"):
        if len(st.session_state.properties) < 5:
            new_p_name = st.text_input("Property Name", placeholder="e.g. Country House")
            new_p_addr = st.text_input("UK Postcode or Address", placeholder="e.g. CM20 1AA or Harlow, Essex")
            if st.button("Lookup & Save Property", use_container_width=True):
                if new_p_name.strip() and new_p_addr.strip():
                    geo = geocode_postcode_or_address(new_p_addr)
                    if geo:
                        st.session_state.properties.append({
                            "name": f"{new_p_name.strip()} ({geo['label']})",
                            "lat": geo["lat"],
                            "lon": geo["lon"],
                            "postcode": new_p_addr.strip().upper(),
                        })
                        st.rerun()
                    else:
                        st.error("Postcode/address not found. Check spelling.")
        else:
            st.info("Maximum 5 properties saved.")

        if len(st.session_state.properties) > 1:
            if st.button("🗑️ Delete Active Property", use_container_width=True):
                st.session_state.properties.pop(selected_idx)
                st.rerun()

    st.divider()
    st.markdown("### 📍 Emergency Operator GPS")
    if HAS_JS_EVAL:
        loc_data = get_geolocation()
        if isinstance(loc_data, dict) and "coords" in loc_data:
            new_lat = round(float(loc_data["coords"]["latitude"]), 6)
            new_lon = round(float(loc_data["coords"]["longitude"]), 6)
            st.session_state.op_coords = {"lat": new_lat, "lon": new_lon, "source": "LIVE BROWSER GPS"}
            record_operator_position(new_lat, new_lon)

    st.caption(
        f"Source: **{st.session_state.op_coords['source']}**\n\n"
        f"`{st.session_state.op_coords['lat']:.6f}, {st.session_state.op_coords['lon']:.6f}`"
    )
    with st.expander("🎯 Manual Exact GPS Override"):
        m_lat = st.number_input("Exact Latitude", value=st.session_state.op_coords["lat"], format="%.6f")
        m_lon = st.number_input("Exact Longitude", value=st.session_state.op_coords["lon"], format="%.6f")
        if st.button("Set Exact Coordinates", use_container_width=True):
            st.session_state.op_coords = {"lat": round(m_lat, 6), "lon": round(m_lon, 6), "source": "MANUAL GPS"}
            record_operator_position(round(m_lat, 6), round(m_lon, 6))
            st.rerun()

    st.divider()
    st.markdown("### ⚙️ Sensor & Alert Thresholds")
    fire_radius = st.slider("Fire Proximity Radius (km)", 1.0, 50.0, 10.0, 0.5)
    surge_limit = st.slider("River Surge Ratio Alert", 1.1, 4.0, 1.8, 0.1)
    firms_key = st.text_input("NASA FIRMS API Key", value="DEMO_KEY", type="password")
    simulate_hazards = st.toggle("Enable Simulated Test Hazards", value=False)
    audio_alarm = st.toggle("Audible Alert Siren", value=False)

    st.divider()
    st.markdown("### 🔐 Tier Authentication")
    if st.session_state.pin_attempts >= 3:
        st.error("TERMINAL LOCKED (3 Failed PIN Attempts)")
    else:
        pin_input = st.text_input("Enter Access PIN (PRO / VIP)", type="password", max_chars=8)
        if st.button("Verify PIN", use_container_width=True):
            if pin_input == "4492":
                st.session_state.pro_unlocked = True
                st.session_state.pin_attempts = 0
                log_security_event("PRO Tier unlocked.")
                st.success("PRO TIER UNLOCKED")
            elif pin_input == "9910":
                st.session_state.pro_unlocked = True
                st.session_state.vip_unlocked = True
                st.session_state.vip_last_active = time.time()
                st.session_state.pin_attempts = 0
                log_security_event("VIP Hardware Tier unlocked.")
                st.success("VIP HARDWARE TIER UNLOCKED")
            else:
                st.session_state.pin_attempts += 1
                log_security_event(f"Failed PIN attempt ({st.session_state.pin_attempts}/3).")
                st.error(f"Invalid PIN ({st.session_state.pin_attempts}/3)")


# ==============================================================================
# 5. LIVE HAZARD SCAN & SIREN TRIGGER
# ==============================================================================
hazards = scan_location_hazards(active_prop["lat"], active_prop["lon"], fire_radius, firms_key, simulate_hazards)
fire_alert = len(hazards["fires"]) > 0
flood_alert = len(hazards["ea_floods"]) > 0 or hazards["river_surge"] >= surge_limit

if audio_alarm and (fire_alert or flood_alert):
    components.html(
        """
        <script>
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(660, ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.35);
            gain.gain.setValueAtTime(0.08, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + 0.4);
        } catch (e) {}
        </script>
        """,
        height=0,
    )


# ==============================================================================
# 6. STREAMLINED 3-TAB INTERFACE
# ==============================================================================
tab1, tab2, tab3 = st.tabs([
    "🛰️ Fire & Flood Command",
    "🌑 Blackout Stealth Ops",
    "🛡️ Home Defence (VIP)",
])

# --- TAB 1: FIRE & FLOOD COMMAND (NO PUMP CONTROLS, FULL/DETAILS TOGGLE, NOK QR) ---
with tab1:
    top_bar_l, top_bar_r = st.columns([3.2, 1.0])
    with top_bar_l:
        if fire_alert or flood_alert:
            st.error(
                f"🚨 ACTIVE THREAT DETECTED AT {active_prop['name'].upper()} — "
                f"FIRES: {len(hazards['fires'])} | EA FLOOD WARNINGS: {len(hazards['ea_floods'])} | "
                f"RIVER SURGE: {hazards['river_surge']}x"
            )
        else:
            st.success(f"✅ PERIMETER CLEAR — {active_prop['name']} (NO ACTIVE FIRE OR FLOOD BREACHES)")
    with top_bar_r:
        full_map_mode = st.toggle("🗺️ Full Map View", value=False, key="tog_full_map_view")

    op_lat = st.session_state.op_coords["lat"]
    op_lon = st.session_state.op_coords["lon"]
    place_label = reverse_geocode_place(op_lat, op_lon)
    dist_km = haversine_km(op_lat, op_lon, active_prop["lat"], active_prop["lon"])
    bearing = compass_bearing(op_lat, op_lon, active_prop["lat"], active_prop["lon"])
    grid_hash = to_w3w_hash(op_lat, op_lon)
    maps_pin_url = f"https://maps.google.com/?q={op_lat:.6f},{op_lon:.6f}"

    if full_map_mode:
        # Full-screen colour satellite map + compact right telemetry card
        fm_left, fm_right = st.columns([3.4, 1.1])
        with fm_left:
            if HAS_FOLIUM:
                m_full = build_colour_satellite_map(
                    active_prop, op_lat, op_lon, hazards, zoom_start=13,
                    trail=st.session_state.gps_trail if st.session_state.nok_tracking_active else None
                )
                st_folium(m_full, width=None, height=640, use_container_width=True, key="main_cmd_map_full")
            else:
                st.map(pd.DataFrame([{"lat": active_prop["lat"], "lon": active_prop["lon"]}, {"lat": op_lat, "lon": op_lon}]))
        with fm_right:
            st.markdown(
                f"""<div class="tactical-card">
                    <div class="card-header">📍 LIVE DISPATCH DATA | {place_label}</div>
                    <div style="font-size:13px; font-weight:700; color:#38bdf8;">LAT: {op_lat:.6f}° N</div>
                    <div style="font-size:13px; font-weight:700; color:#38bdf8;">LON: {op_lon:.6f}° E</div>
                    <div style="font-size:12px; color:#94a3b8; margin-top:4px;">GRID: {grid_hash}</div>
                    <div style="font-size:12px; color:#94a3b8;">RANGE: {dist_km:.2f} km {bearing}</div>
                </div>""",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"""<div class="tactical-card">
                    <div class="card-header">🔥 THERMAL / FLOOD</div>
                    <div style="font-size:14px; font-weight:700;">Hotspots: {len(hazards['fires'])} | Surge: {hazards['river_surge']}x</div>
                    <div style="font-size:12px; color:#94a3b8;">EA Warnings: {len(hazards['ea_floods'])}</div>
                </div>""",
                unsafe_allow_html=True,
            )
            if st.button("🔄 Refresh Feeds", use_container_width=True, key="btn_ref_full"):
                scan_location_hazards.clear()
                st.rerun()
    else:
        # Split Details View: Unobstructed Colour Map (Left) + Side Coordinates, Metrics & NOK QR (Right)
        col_map, col_side = st.columns([2.25, 1.25])

        with col_map:
            if HAS_FOLIUM:
                m_det = build_colour_satellite_map(
                    active_prop, op_lat, op_lon, hazards, zoom_start=13,
                    trail=st.session_state.gps_trail if st.session_state.nok_tracking_active else None
                )
                st_folium(m_det, width=None, height=450, use_container_width=True, key="main_cmd_map_details")
            else:
                st.map(pd.DataFrame([{"lat": active_prop["lat"], "lon": active_prop["lon"]}, {"lat": op_lat, "lon": op_lon}]))

            disp_c1, disp_c2 = st.columns([3.2, 1.0])
            with disp_c1:
                dispatch_text = (
                    f"OPERATOR ({place_label} / {st.session_state.op_coords['source']}): {op_lat:.6f}, {op_lon:.6f} | "
                    f"PROPERTY ({active_prop['name']}): {active_prop['lat']:.6f}, {active_prop['lon']:.6f} | "
                    f"RANGE: {dist_km:.2f} km {bearing}"
                )
                st.code(dispatch_text, language="text")
            with disp_c2:
                if st.button("🔄 Refresh Feeds", use_container_width=True, key="btn_ref_det"):
                    scan_location_hazards.clear()
                    st.rerun()

        with col_side:
            # Side-panel Auto-Generated Place Name & Lat/Lon Card (kept off the map)
            st.markdown(
                f"""<div class="tactical-card">
                    <div class="card-header">📍 LIVE DISPATCH DATA | {place_label}</div>
                    <div style="font-size:14px; font-weight:700; color:#38bdf8;">LAT: {op_lat:.6f}° N &nbsp;|&nbsp; LON: {op_lon:.6f}° E</div>
                    <div style="font-size:12px; color:#94a3b8; margin-top:4px;">GRID HASH: {grid_hash} &nbsp;|&nbsp; RANGE: {dist_km:.2f} km {bearing}</div>
                </div>""",
                unsafe_allow_html=True,
            )

            m1, m2 = st.columns(2)
            with m1:
                st.markdown(
                    f"""<div class="tactical-card">
                        <div class="card-header">🔥 Hotspots</div>
                        <div class="{'status-val-red' if len(hazards['fires']) else 'status-val-green'}">{len(hazards['fires'])}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            with m2:
                st.markdown(
                    f"""<div class="tactical-card">
                        <div class="card-header">🌊 River Surge</div>
                        <div class="{'status-val-red' if flood_alert else 'status-val-cyan'}">{hazards['river_surge']}x</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

            # Next-of-Kin Live Tracking & Instant QR Code Panel
            st.markdown('<div class="card-header">📡 NEXT-OF-KIN LIVE TRACKING & QR SHARE</div>', unsafe_allow_html=True)
            st.session_state.nok_tracking_active = st.toggle(
                "Broadcast Live GPS Beacon to Next of Kin",
                value=st.session_state.nok_tracking_active,
                key="tog_nok_beacon",
            )
            if st.session_state.nok_tracking_active:
                st.caption(f"🟢 BEACON ACTIVE — Session `{st.session_state.nok_session_token}`")

            qr_mode = st.selectbox(
                "QR Code Payload",
                ["Google Maps Live Pin", "WhatsApp SOS Dispatch"],
                key="sel_qr_mode",
            )
            primary_nok = st.session_state.contacts[0]
            sos_msg = (
                f"EMERGENCY ALERT ({active_prop['name']}): Operator at {place_label} "
                f"({op_lat:.6f}, {op_lon:.6f}) {maps_pin_url} | "
                f"Fires: {len(hazards['fires'])} | River Surge: {hazards['river_surge']}x | Session: {st.session_state.nok_session_token}"
            )
            wa_sos_url = f"https://wa.me/{primary_nok['phone'].replace('+', '')}?text={requests.utils.quote(sos_msg)}"
            qr_target = maps_pin_url if qr_mode == "Google Maps Live Pin" else wa_sos_url

            qr_bytes = generate_qr_png(qr_target)
            if qr_bytes:
                qc1, qc2 = st.columns([1.1, 1.3])
                with qc1:
                    st.image(qr_bytes, caption="Scan with Phone", use_container_width=True)
                with qc2:
                    st.download_button(
                        "⬇️ Download QR PNG",
                        data=qr_bytes,
                        file_name=f"nok_emergency_qr_{st.session_state.nok_session_token}.png",
                        mime="image/png",
                        use_container_width=True,
                    )
                    st.markdown(f"[📲 Open WhatsApp Relay]({wa_sos_url})")
            else:
                st.info("Install `qrcode[pil]` to render scannable PNG QR codes.")

            with st.expander("➕ Manage Next-of-Kin Contacts & Webhook"):
                for c in st.session_state.contacts:
                    c_msg = f"EMERGENCY ({active_prop['name']}): {op_lat:.6f},{op_lon:.6f} ({maps_pin_url})"
                    c_wa = f"https://wa.me/{c['phone'].replace('+', '')}?text={requests.utils.quote(c_msg)}"
                    st.markdown(f"- **{c['name']}** (`{c['phone']}`) — [WhatsApp]({c_wa})")
                nc1, nc2 = st.columns(2)
                new_n = nc1.text_input("Name", placeholder="e.g. Sarah", key="nok_add_name")
                new_p = nc2.text_input("Phone", placeholder="+447700900099", key="nok_add_phone")
                if st.button("Save Contact", use_container_width=True, key="btn_save_nok"):
                    if new_n.strip() and new_p.strip():
                        st.session_state.contacts.append({"name": new_n.strip(), "phone": new_p.strip(), "role": "Next of Kin"})
                        st.rerun()
                st.session_state.nok_webhook_url = st.text_input(
                    "Optional Live GPS Webhook URL (POST JSON)",
                    value=st.session_state.nok_webhook_url,
                    placeholder="https://ntfy.sh/your-private-topic",
                )


# --- TAB 2: BLACKOUT STEALTH OPS ---
with tab2:
    st.markdown(
        f"""
        <div class="stealth-hud">
            <h3>🌑 BLACKOUT STEALTH HUD // ZERO-GLARE MODE</h3>
            <p><b>UTC TIMESTAMP:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            <p><b>OPERATOR EXACT GPS:</b> {st.session_state.op_coords['lat']:.6f}, {st.session_state.op_coords['lon']:.6f} ({st.session_state.op_coords['source']})</p>
            <p><b>TARGET PROPERTY:</b> {active_prop['name']} ({active_prop['lat']:.6f}, {active_prop['lon']:.6f})</p>
            <p><b>ACTIVE FIRES IN RADIUS:</b> {len(hazards['fires'])} | <b>RIVER SURGE:</b> {hazards['river_surge']}x</p>
            <p><b>48V A.G.E.H.I.C. BUS:</b> {st.session_state.hw['batt_a_pct']}% / {st.session_state.hw['batt_b_pct']}% |
               <b>10,000L CISTERN:</b> {st.session_state.hw['cistern_litres']} L</p>
            <p><b>MASTER SHUTDOWN STATE:</b> {'ENGAGED (SAFE ISOLATION)' if st.session_state.hw['master_shutdown'] else 'DISENGAGED (ARMED)'}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --- TAB 3: HOME DEFENCE (VIP) — ALL PUMP & ACTUATOR CONTROLS ---
with tab3:
    if st.session_state.vip_unlocked and (time.time() - st.session_state.vip_last_active > 300):
        st.session_state.vip_unlocked = False
        st.session_state.vip_safety_armed = False
        log_security_event("VIP Terminal auto-locked due to 5-minute inactivity timeout.")

    if not st.session_state.vip_unlocked:
        st.warning("RESTRICTED TIER: Enter VIP PIN (9910) in the sidebar to unlock Home Defence controls.")
    else:
        st.session_state.vip_last_active = time.time()
        hw = st.session_state.hw
        read_arduino_telemetry()

        ext_t = hw["ambient_temp_c"]
        base_vault = 20 + max(0, (ext_t - 25) // 4)
        cooling_offset = (5 if hw["peltier_cooler_on"] else 0) + (4 if hw["micromist_cooling_on"] else 0)
        hw["vault_temp_c"] = max(18, min(52, base_vault - cooling_offset))

        if not hw["master_shutdown"]:
            if hw["agehic_pump_mode"] == "AUTO (FIRMS / THERMAL)" and (fire_alert or ext_t >= 45):
                hw["zone1_ridge"] = True
                hw["zone2_eaves"] = True
                hw["zone3_perim"] = True
                hw["intake_valve"] = True
                hw["ac_breaker_cut"] = True
            if (
                hw["thermogal_mode"] == "AUTO-THERMAL (65°C)"
                and ext_t >= 65
                and not hw["thermogal_valve_deployed"]
                and hw["thermogal_tank_litres"] > 0
            ):
                hw["thermogal_valve_deployed"] = True
                hw["thermogal_tank_litres"] = max(0, hw["thermogal_tank_litres"] - 20)
                log_security_event("AUTO-THERMAL (65°C): ThermoGel Shutdown Valve deployed.")

        cab_status_txt = "CABINET ISOLATED // MASTER SHUTDOWN ENGAGED" if hw["master_shutdown"] else "A.G.E.H.I.C. CABINET ENERGIZED — THERMAL SENSORS ACTIVE"
        st.markdown(
            f'<div class="tactical-banner">🛡️ {active_prop["name"].upper()} HOME DEFENCE // {cab_status_txt}</div>',
            unsafe_allow_html=True,
        )

        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        with r1c1:
            ac_on = not hw["ac_breaker_cut"]
            st.markdown(f'<div class="tactical-card"><div class="card-header">❄️ Cabinet AC</div><div class="{"status-val-green" if ac_on else "status-val-red"}">{"ON" if ac_on else "CUT"}</div></div>', unsafe_allow_html=True)
        with r1c2:
            wf_on = (hw["zone1_ridge"] or hw["zone2_eaves"] or hw["zone3_perim"]) and not hw["master_shutdown"]
            st.markdown(f'<div class="tactical-card"><div class="card-header">🔥 Wildfire System</div><div class="{"status-val-green" if wf_on else "status-val-cyan"}">{"SPRAYING" if wf_on else "ARMED"}</div></div>', unsafe_allow_html=True)
        with r1c3:
            avail_ah = (65 if hw["batt_a_fuse_ok"] else 0) + (65 if hw["batt_b_fuse_ok"] else 0)
            st.markdown(f'<div class="tactical-card"><div class="card-header">⚡ 48V Bus Ah</div><div class="status-val-cyan">{avail_ah}Ah</div></div>', unsafe_allow_html=True)
        with r1c4:
            st.markdown(f'<div class="tactical-card"><div class="card-header">🧪 Gel Tank Level</div><div class="status-val-green">{hw["thermogal_tank_litres"]}L</div></div>', unsafe_allow_html=True)

        sw_left, sw_right = st.columns([1.3, 1.1])
        with sw_left:
            st.markdown('<div class="card-header">🔥 A.G.E.H.I.C. WILDFIRE & FLOOD RELAY SWITCHES</div>', unsafe_allow_html=True)
            lock_sp = hw["master_shutdown"] or hw["agehic_pump_mode"] == "STANDBY OFF"

            def relay_row(label: str, state: bool, key: str, disabled: bool = False):
                c_lbl, c_btn = st.columns([1.8, 0.8])
                with c_lbl:
                    st.markdown(f"<div style='padding-top:6px; font-size:13px; font-weight:600;'>{label}</div>", unsafe_allow_html=True)
                with c_btn:
                    if st.button("ON" if state else "OFF", key=key, disabled=disabled, use_container_width=True):
                        return True
                return False

            if relay_row("Cabinet AC Breaker", not hw["ac_breaker_cut"], "sw_ac"):
                hw["ac_breaker_cut"] = not hw["ac_breaker_cut"]
                st.rerun()

            sump_on = hw["sump_mode"] != "STANDBY OFF"
            if relay_row("48V Sump & Pump A", sump_on, "sw_sump"):
                hw["sump_mode"] = "STANDBY OFF" if sump_on else "AUTO (FLOAT)"
                st.rerun()

            if relay_row("Zone 1 (Roofline Ridge)", hw["zone1_ridge"], "sw_z1", lock_sp):
                hw["zone1_ridge"] = not hw["zone1_ridge"]
                st.rerun()

            if relay_row("Zone 2 (Eaves)", hw["zone2_eaves"], "sw_z2", lock_sp):
                hw["zone2_eaves"] = not hw["zone2_eaves"]
                st.rerun()

            if relay_row("Zone 3 (Perimeter)", hw["zone3_perim"], "sw_z3", lock_sp):
                hw["zone3_perim"] = not hw["zone3_perim"]
                st.rerun()

            if relay_row("ThermoGel Eductor", hw["thermogal_inject"], "sw_tg"):
                hw["thermogal_inject"] = not hw["thermogal_inject"]
                st.rerun()

            if relay_row("10,000L Cistern Intake", hw["intake_valve"], "sw_cis"):
                hw["intake_valve"] = not hw["intake_valve"]
                st.rerun()

        with sw_right:
            prop_short_title = active_prop["name"].split("(")[0].strip()
            arm_col1, arm_col2 = st.columns([1.4, 1])
            with arm_col1:
                st.markdown(
                    f"**{prop_short_title}**  \n"
                    f"<span style='color:#94a3b8; font-size:12px;'>"
                    f"{'⚠️ ' + str(len(hazards['fires'])) + ' Hotspots Active' if fire_alert else 'No Hotspots in Radius'} | "
                    f"River: {hazards['river_surge']}x</span>",
                    unsafe_allow_html=True,
                )
            with arm_col2:
                st.session_state.vip_safety_armed = st.toggle(
                    "VIP Safety Armed",
                    value=st.session_state.vip_safety_armed,
                    key="tog_vip_arm_card",
                )

            if HAS_FOLIUM:
                mini_m = build_colour_satellite_map(active_prop, op_lat, op_lon, hazards, zoom_start=14)
                st_folium(mini_m, width=None, height=230, use_container_width=True, key="vip_mini_map")

        st.divider()
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            if st.button("🛑 EMERGENCY SHUTDOWN", disabled=not st.session_state.vip_safety_armed, use_container_width=True, key="btn_m_shut"):
                hw["master_shutdown"] = True
                hw["agehic_pump_mode"] = "STANDBY OFF"
                hw["zone1_ridge"] = False
                hw["zone2_eaves"] = False
                hw["zone3_perim"] = False
                hw["intake_valve"] = False
                hw["thermogal_inject"] = False
                hw["thermogal_valve_deployed"] = True
                hw["ac_breaker_cut"] = True
                hw["sump_mode"] = "STANDBY OFF"
                log_security_event("EMERGENCY MASTER SHUTDOWN triggered.")
                st.rerun()
        with m2:
            if st.button("🌊 FULL FLOOD ENVELOPE", disabled=not st.session_state.vip_safety_armed, use_container_width=True, key="btn_m_flood"):
                hw["master_shutdown"] = False
                hw["barrier_mode"] = "MANUAL OVERRIDE"
                hw["barrier_front"] = True
                hw["barrier_rear"] = True
                hw["barrier_garage"] = True
                hw["airbricks_sealed"] = True
                hw["sewer_valve_locked"] = True
                hw["letterbox_sealed"] = True
                log_security_event("Full Flood Envelope manually engaged.")
                st.rerun()
        with m3:
            if st.button("🧪 THERMOGEL SEAL", disabled=not st.session_state.vip_safety_armed, use_container_width=True, key="btn_m_gel"):
                hw["thermogal_valve_deployed"] = not hw["thermogal_valve_deployed"]
                if hw["thermogal_valve_deployed"]:
                    hw["thermogal_tank_litres"] = max(0, hw["thermogal_tank_litres"] - 20)
                st.rerun()
        with m4:
            if st.button("🔄 RESET DRY STANDBY", disabled=not st.session_state.vip_safety_armed, use_container_width=True, key="btn_m_reset"):
                hw["master_shutdown"] = False
                hw["barrier_mode"] = "AUTO-BUOYANCY"
                hw["barrier_front"] = False
                hw["barrier_rear"] = False
                hw["barrier_garage"] = False
                hw["airbricks_sealed"] = False
                hw["letterbox_sealed"] = False
                hw["sump_mode"] = "AUTO (FLOAT)"
                hw["agehic_pump_mode"] = "AUTO (FIRMS / THERMAL)"
                hw["zone1_ridge"] = False
                hw["zone2_eaves"] = False
                hw["zone3_perim"] = False
                hw["intake_valve"] = True
                hw["thermogal_inject"] = False
                hw["thermogal_valve_deployed"] = False
                hw["ac_breaker_cut"] = False
                log_security_event("System reset to Dry Standby.")
                st.rerun()

        with st.expander("🔌 Arduino Hardware Link (HMAC-SHA256 Serial Bridge) & Sliders", expanded=False):
            ac1, ac2, ac3 = st.columns([1.4, 1.2, 1])
            with ac1:
                avail_ports = get_available_ports()
                curr_idx = avail_ports.index(st.session_state.arduino_port) if st.session_state.arduino_port in avail_ports else 0
                chosen_port = st.selectbox("Select Arduino Serial Port", avail_ports, index=curr_idx, key="sel_arduino_port")
                if chosen_port != st.session_state.arduino_port:
                    st.session_state.arduino_port = chosen_port
                    st.rerun()
            with ac2:
                is_conn, conn_msg = connect_arduino(st.session_state.arduino_port)
                if is_conn:
                    read_arduino_telemetry()
                    st.success(f"🟢 {conn_msg}")
                else:
                    st.info(f"🟡 {conn_msg}")
            with ac3:
                if st.button("🔄 Force Relay Sync", use_container_width=True, key="btn_force_sync"):
                    st.session_state.last_synced_cmds = {}
                    st.rerun()

            sl1, sl2, sl3 = st.columns(3)
            with sl1:
                new_ext = st.slider("Simulated Exterior Temp (°C)", 10, 110, hw["ambient_temp_c"], 1)
                if new_ext != hw["ambient_temp_c"]:
                    hw["ambient_temp_c"] = new_ext
                    st.rerun()
            with sl2:
                new_cistern = st.slider("10,000L Cistern Level (L)", 0, 10000, hw["cistern_litres"], 250)
                if new_cistern != hw["cistern_litres"]:
                    hw["cistern_litres"] = new_cistern
                    st.rerun()
            with sl3:
                pit = st.slider("Sump Pit Water Level (mm)", 50, 600, hw["sump_pit_mm"], 10)
                if pit != hw["sump_pit_mm"]:
                    hw["sump_pit_mm"] = pit
                    st.rerun()

        with st.expander("📜 VIP Security & Hardware Audit Trail"):
            if st.session_state.security_log:
                st.code("\n".join(st.session_state.security_log), language="text")
            else:
                st.caption("No security events logged in this session yet.")


# ==============================================================================
# 7. CONTINUOUS SERIAL HEARTBEAT & NEXT-OF-KIN WEBHOOK LOOP
# ==============================================================================
@st.fragment(run_every="5s")
def background_watchdog_loop():
    sync_hw_to_arduino()
    push_nok_webhook_update(active_prop, hazards)

background_watchdog_loop()
