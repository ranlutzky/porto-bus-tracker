import streamlit as st
import requests
import time
import folium
from streamlit_folium import st_folium
from math import radians, cos, sin, asin, sqrt
from streamlit_js_eval import get_geolocation

# הגדרות עמוד
st.set_page_config(page_title="Porto Bus Tracker", layout="wide")

# אתחול מצבי מיקום ב-Session State
if 'map_center' not in st.session_state:
    st.session_state.map_center = (41.1485, -8.6110)
if 'location_mode' not in st.session_state:
    st.session_state.location_mode = 'gps'

# CSS: שליטה מלאה ברוחב, צבעים ויישור
st.markdown("""
    <style>
    .stApp { background-color: #1e1e1e !important; }
    header { visibility: hidden; height: 0px !important; }
    #MainMenu, footer, .stDeployButton, [data-testid="stStatusWidget"] { visibility: hidden; display: none !important; }
    
    .block-container { 
        padding-top: 0.5rem !important; 
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 550px !important;
        margin: auto !important;
    }

    .custom-label {
        color: white !important;
        font-size: 13px;
        font-weight: bold;
        margin-bottom: 5px;
        text-transform: uppercase;
    }

    /* תיבת בחירה - רוחב מלא */
    div[data-baseweb="select"] > div { 
        background-color: #333333 !important; 
        border: 1px solid #555 !important;
        height: 45px !important;
    }
    div[data-baseweb="select"] * { color: white !important; }

    /* כפתורים - הכרחת רוחב 100% וביטול שוליים */
    .stButton>button {
        width: 100% !important;
        display: block !important;
        background-color: #333333 !important;
        color: #ffffff !important;
        border: 1px solid #555 !important;
        height: 60px !important; 
        font-size: 13px !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        margin-top: 5px !important;
    }
    .stButton>button:hover { border-color: #00ccff !important; color: #00ccff !important; }

    /* ביטול ה-Padding של העמודות כדי שהכפתורים ייצמדו לקצוות המפה */
    [data-testid="column"] {
        padding-left: 0px !important;
        padding-right: 0px !important;
    }

    /* תיבת המרחק - טקסט לבן וצהוב */
    [data-testid="stNotification"] {
        background-color: #262730 !important;
        border: 1px solid #00ccff !important;
    }
    [data-testid="stNotification"] div { color: #ffffff !important; }
    .stInfo b, .stInfo strong { color: #ffff00 !important; }

    /* טיימר רענון */
    .refresh-text {
        color: #ffffff !important;
        font-size: 13px;
        text-align: center;
        margin-top: 15px;
    }
    .refresh-text b { color: #ffff00 !important; }
    </style>
    """, unsafe_allow_html=True)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 
    dLat, dLon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dLat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dLon/2)**2
    return R * 2 * asin(sqrt(a))

# --- חלק 1: חיפוש (רוחב מלא) ---
st.markdown('<p class="custom-label">SELECT BUS LINE</p>', unsafe_allow_html=True)

def get_bus_data():
    url = "https://broker.fiware.urbanplatform.portodigital.pt/v2/entities?q=vehicleType==bus&limit=1000"
    try:
        r = requests.get(url, verify=False, timeout=10)
        return r.json() if r.status_code == 200 else []
    except: return []

buses_raw = get_bus_data()
active_lines = [str(e.get('name', {}).get('value', '')).split()[1] for e in buses_raw if len(str(e.get('name', {}).get('value', '')).split()) >= 2 and str(e.get('name', {}).get('value', '')).split()[1].isdigit()]
unique_lines = sorted(list(set(active_lines)), key=lambda x: int(x))
target = st.selectbox("Line:", ["Nearby Buses"] + unique_lines, label_visibility="collapsed")

# לוגיקת מיקום
loc = get_geolocation()
if st.session_state.location_mode == 'gps' and loc and 'coords' in loc:
    user_lat, user_lon = loc['coords']['latitude'], loc['coords']['longitude']
else:
    user_lat, user_lon = st.session_state.map_center

# חלק 2: הודעת מרחק
all_buses = []
for e in buses_raw:
    parts = str(e.get('name', {}).get('value', '')).split()
    if len(parts) >= 2:
        coords = e.get('location', {}).get('value', {}).get('coordinates', [0,0])
        dist = haversine(user_lat, user_lon, coords[1], coords[0])
        all_buses.append({'line': parts[1], 'lat': coords[1], 'lon': coords[0], 'dist': dist, 'heading': e.get('heading', {}).get('value', 0)})

display_buses = sorted(all_buses, key=lambda x: x['dist'])[:10] if target == "Nearby Buses" else [b for b in all_buses if b['line'] == target]

if display
