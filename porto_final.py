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

# 3. CSS (v23 + שיפורים)
st.markdown("""
    <style>
    .stApp { background-color: #1e1e1e !important; }
    header { visibility: hidden; height: 0px !important; }
    .block-container { padding-top: 0.5rem !important; padding-left: 0.5rem !important; padding-right: 0.5rem !important; max-width: 550px !important; margin: auto !important; }
    div.stButton > button { width: 100% !important; background-color: #333333 !important; color: #ffffff !important; border: 1px solid #555 !important; height: 40px !important; font-size: 13px !important; font-weight: bold !important; border-radius: 4px !important; }
    .custom-label { color: white !important; font-size: 13px; font-weight: bold; margin-bottom: 5px; }
    div[data-baseweb="select"] > div { background-color: #333333 !important; border: 1px solid #555 !important; }
    div[data-baseweb="select"] * { color: white !important; }
    .refresh-text { color: #ffffff !important; font-size: 12px; text-align: center; margin-top: 10px; }
    .stop-info { background-color: #262730; border-left: 4px solid #ffff00; padding: 10px; color: white; margin-top: 10px; border-radius: 4px; }
    </style>
    """, unsafe_allow_html=True)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 
    dLat, dLon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dLat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dLon/2)**2
    return R * 2 * asin(sqrt(a))

def get_bus_data():
    url = "https://broker.fiware.urbanplatform.portodigital.pt/v2/entities?q=vehicleType==bus&limit=600"
    try:
        r = requests.get(url, verify=False, timeout=8)
        return r.json() if r.status_code == 200 else []
    except: return []

# פונקציית שליפת תחנות משופרת
def get_stops_for_line(line_id):
    # ננסה לשלוף תחנות שיש להן את שם הקו בתוך ה-name שלהן
    url = f"https://broker.fiware.urbanplatform.portodigital.pt/v2/entities?type=busStop&limit=500"
    try:
        r = requests.get(url, verify=False, timeout=5)
        if r.status_code == 200:
            return r.json()
    except: pass
    return []

# --- ביצוע ---
buses_raw = get_bus_data()
loc = get_geolocation()
user_lat, user_lon = (loc['coords']['latitude'], loc['coords']['longitude']) if (st.session_state.location_mode == 'gps' and loc) else st.session_state.get('map_center', (41.1485, -8.6110))

# עיבוד אוטובוסים
all_buses = []
for e in buses_raw:
    parts = str(e.get('name', {}).get('value', '')).split()
    if len(parts) >= 2:
        line = parts[1]
        coords = e.get('location', {}).get('value', {}).get('coordinates', [0,0])
        dist = haversine(user_lat, user_lon, coords[1], coords[0])
        all_buses.append({'line': line, 'lat': coords[1], 'lon': coords[0], 'dist': dist, 'heading': e.get('heading', {}).get('value', 0)})

unique_lines = sorted(list(set([b['line'] for b in all_buses if b['line'].isdigit()])), key=int)

st.markdown('<p class="custom-label">SELECT BUS LINE</p>', unsafe_allow_html=True)
target = st.selectbox("Line:", ["Nearby Buses"] + unique_lines, label_visibility="collapsed")

display_buses = sorted(all_buses, key=lambda x: x['dist'])[:12] if target == "Nearby Buses" else [b for b in all_buses if b['line'] == target]

# מפה
m = folium.Map(location=[user_lat, user_lon], zoom_start=16)
folium.Marker([user_lat, user_lon], icon=folium.Icon(color='red', icon='user', prefix='fa')).add_to(m)

# 1. החזרת מספרי הקווים והחיצים למפה
for b in display_buses:
    icon_html = f'''
    <div style="background-color: #00ccff; width: 30px; height: 30px; border-radius: 50%; border: 2px solid white; display: flex; align-items: center; justify-content: center; color: black; transform: rotate({b["heading"]}deg); font-weight: bold;">↑</div>
    <div style="background: rgba(0,0,0,0.85); padding: 1px 4px; border-radius: 3px; font-size: 11px; position: absolute; top: 32px; color: white; white-space: nowrap; font-weight: bold; border: 0.5px solid #fff;">{b["line"]}</div>
    '''
    folium.Marker([b['lat'], b['lon']], icon=folium.DivIcon(icon_size=(30, 30), html=icon_html)).add_to(m)

# 2. חיפוש תחנות ברגע שנבחר קו
nearby_stops = []
if target != "Nearby Buses":
    stops_data = get_stops_for_line(target)
    for s in stops_data:
        s_coords = s.get('location', {}).get('value', {}).get('coordinates', [0,0])
        s_dist = haversine(user_lat, user_lon, s_coords[1], s_coords[0])
        if s_dist <= 0.5: # רדיוס 500 מטר ליתר ביטחון
            s_name = s.get('name', {}).get('value', 'Stop').replace("Paragem: ", "")
            nearby_stops.append({'name': s_name, 'dist': s_dist, 'lat': s_coords[1], 'lon': s_coords[0]})
            # נצייר את התחנות על המפה
            folium.CircleMarker(
                location=[s_coords[1], s_coords[0]], radius=6, color='#ffff00', fill=True, fill_opacity=0.9,
                popup=f"🚏 {s_name}"
            ).add_to(m)

st_folium(m, width=None, height=450, key=f"map_v39_{target}", use_container_width=True)

# 3. תצוגת מידע תחנות מתחת למפה
if target != "Nearby Buses":
    if nearby_stops:
        closest = min(nearby_stops, key=lambda x: x['dist'])
        st.markdown(f'<div class="stop-info">🚏 Closest Stop: <b>{closest["name"]}</b><br>📏 Distance: {int(closest["dist"]*1000)}m away</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<p style="color:#ff4b4b; font-size:13px; text-align:center;">No stops for line {target} found within 500m.</p>', unsafe_allow_html=True)

# כפתורים ורענון
c1, c2 = st.columns(2)
with c1:
    if st.button("📍 GPS"): st.session_state.location_mode = 'gps'; st.rerun()
with c2:
    if st.button("🏠 HOME"): st.session_state.location_mode = 'manual'; st.rerun()

t = st.empty()
for i in range(45, 0, -1):
    t.markdown(f'<p class="refresh-text">Refreshing in {i}s...</p>', unsafe_allow_html=True)
    time.sleep(1)
st.rerun()
