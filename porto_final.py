import streamlit as st
import requests
import time
import folium
from streamlit_folium import st_folium
from math import radians, cos, sin, asin, sqrt
from streamlit_js_eval import get_geolocation

# 1. הגדרות עמוד
st.set_page_config(page_title="Porto Bus Tracker", layout="wide")

# 2. אתחול משתני מערכת
if 'map_center' not in st.session_state:
    st.session_state.map_center = (41.1485, -8.6110)
if 'location_mode' not in st.session_state:
    st.session_state.location_mode = 'gps'

# 3. CSS "סופר-אגרסיבי" - כופה רוחב 100% וגובה 40px
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

    /* כפיית רוחב מלא על העמודות ועל הכפתורים שבתוכן */
    [data-testid="column"] [data-testid="stVerticalBlock"] {
        gap: 0px !important;
    }

    /* הסלקטור הכי חזק לכפתורי Streamlit */
    div.stButton > button {
        width: 100% !important;
        background-color: #333333 !important;
        color: #ffffff !important;
        border: 1px solid #555 !important;
        height: 40px !important; /* גובה מלבני דק */
        font-size: 13px !important;
        font-weight: bold !important;
        border-radius: 4px !important;
        padding: 0px !important;
        display: block !important;
    }
    
    div.stButton > button:hover { border-color: #00ccff !important; color: #00ccff !important; }

    /* הסרת רווחים בין העמודות ליישור עם המפה */
    [data-testid="column"] {
        padding-left: 1px !important;
        padding-right: 1px !important;
    }

    .custom-label { color: white !important; font-size: 13px; font-weight: bold; margin-bottom: 5px; }

    div[data-baseweb="select"] > div { background-color: #333333 !important; border: 1px solid #555 !important; }
    div[data-baseweb="select"] * { color: white !important; }

    [data-testid="stNotification"] { background-color: #262730 !important; border: 1px solid #00ccff !important; }
    [data-testid="stNotification"] div { color: #ffffff !important; }

    .refresh-text { color: #ffffff !important; font-size: 12px; text-align: center; margin-top: 10px; }
    .refresh-text b { color: #ffff00 !important; }
    </style>
    """, unsafe_allow_html=True)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 
    dLat, dLon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dLat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dLon/2)**2
    return R * 2 * asin(sqrt(a))

def get_bus_data():
    url = "https://broker.fiware.urbanplatform.portodigital.pt/v2/entities?q=vehicleType==bus&limit=1000"
    try:
        r = requests.get(url, verify=False, timeout=10)
        return r.json() if r.status_code == 200 else []
    except: return []

# --- ממשק משתמש ---
st.markdown('<p class="custom-label">SELECT BUS LINE</p>', unsafe_allow_html=True)
buses_raw = get_bus_data()

active_lines = [str(e.get('name', {}).get('value', '')).split()[1] for e in buses_raw if len(str(e.get('name', {}).get('value', '')).split()) >= 2 and str(e.get('name', {}).get('value', '')).split()[1].isdigit()]
unique_lines = sorted(list(set(active_lines)), key=lambda x: int(x))
target = st.selectbox("Line:", ["Nearby Buses"] + unique_lines, label_visibility="collapsed")

loc = get_geolocation()
if st.session_state.location_mode == 'gps' and loc and 'coords' in loc:
    user_lat, user_lon = loc['coords']['latitude'], loc['coords']['longitude']
else:
    user_lat, user_lon = st.session_state.map_center

all_buses = []
for e in buses_raw:
    parts = str(e.get('name', {}).get('value', '')).split()
    if len(parts) >= 2:
        coords = e.get('location', {}).get('value', {}).get('coordinates', [0,0])
        dist = haversine(user_lat, user_lon, coords[1], coords[0])
        all_buses.append({'line': parts[1], 'lat': coords[1], 'lon': coords[0], 'dist': dist, 'heading': e.get('heading', {}).get('value', 0)})

display_buses = sorted(all_buses, key=lambda x: x['dist'])[:10] if target == "Nearby Buses" else [b for b in all_buses if b['line'] == target]

if display_buses:
    closest = min(display_buses, key=lambda x: x['dist'])
    st.markdown(f'<div style="background-color: #262730; border: 1px solid #00ccff; padding: 10px; border-radius: 5px; text-align: center; color: white; margin-bottom: 10px;">'
                f'🚍 Closest: <span style="color: #ffff00; font-weight: bold;">Line {closest["line"]}</span> is '
                f'<span style="color: #ffff00; font-weight: bold;">{closest["dist"]:.2f} km</span> away</div>', unsafe_allow_html=True)

# מפה
m = folium.Map(location=[user_lat, user_lon], zoom_start=16)
folium.Marker([user_lat, user_lon], icon=folium.Icon(color='red', icon='user', prefix='fa')).add_to(m)

for b in display_buses:
    icon_html = f'<div style="background-color: #00ccff; width: 30px; height: 30px; border-radius: 50%; border: 2px solid white; display: flex; align-items: center; justify-content: center; color: black; transform: rotate({b["heading"]}deg); font-weight: bold;">↑</div><div style="background: rgba(0,0,0,0.8); padding: 1px 3px; border-radius: 3px; font-size: 10px; position: absolute; top: 32px; color: white; white-space: nowrap;">{b["line"]}</div>'
    folium.Marker(location=[b['lat'], b['lon']], icon=folium.DivIcon(icon_size=(30, 30), icon_anchor=(15, 15), html=icon_html)).add_to(m)

st_folium(m, width=None, height=450, key=f"map_v20_{target}_{st.session_state.location_mode}", use_container_width=True)

# --- כפתורי מיקום: 50/50 ---
col1, col2 = st.columns(2)
with col1:
    if st.button("📍 MY LOCATION", use_container_width=True):
        st.session_state.location_mode = 'gps'
        st.rerun()
with col2:
    if st.button("🏠 HOME (PORTO)", use_container_width=True):
        st.session_state.location_mode = 'manual'
        st.session_state.map_center = (41.1485, -8.6110)
        st.rerun()

# רענון
t_place = st.empty()
for i in range(30, 0, -1):
    t_place.markdown(f'<p class="refresh-text">Refreshing in <b>{i}s</b>...</p>', unsafe_allow_html=True)
    time.sleep(1)
st.rerun()
