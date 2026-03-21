import streamlit as st
import requests
import time
import folium
from streamlit_folium import st_folium
from math import radians, cos, sin, asin, sqrt
from streamlit_js_eval import get_geolocation

# 1. הגדרות עמוד
st.set_page_config(page_title="Porto Bus Tracker", layout="wide")

# 2. אתחול משתני מערכת (v23)
if 'map_center' not in st.session_state:
    st.session_state.map_center = (41.1485, -8.6110)
if 'location_mode' not in st.session_state:
    st.session_state.location_mode = 'gps'

# 3. CSS יציב (v23)
st.markdown("""
    <style>
    .stApp { background-color: #1e1e1e !important; }
    header { visibility: hidden; height: 0px !important; }
    #MainMenu, footer, .stDeployButton, [data-testid="stStatusWidget"] { visibility: hidden; display: none !important; }
    .block-container { padding-top: 0.5rem !important; padding-left: 0.5rem !important; padding-right: 0.5rem !important; max-width: 550px !important; margin: auto !important; }
    div.stButton > button { width: 100% !important; background-color: #333333 !important; color: #ffffff !important; border: 1px solid #555 !important; height: 40px !important; font-size: 13px !important; font-weight: bold !important; border-radius: 4px; }
    .custom-label { color: white !important; font-size: 13px; font-weight: bold; margin-bottom: 5px; }
    div[data-baseweb="select"] > div { background-color: #333333 !important; border: 1px solid #555 !important; }
    div[data-baseweb="select"] * { color: white !important; }
    .refresh-text { color: #ffffff !important; font-size: 12px; text-align: center; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 
    dLat, dLon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dLat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dLon/2)**2
    return R * 2 * asin(sqrt(a))

# פונקציית שליפה בסיסית ללא פילטרים גיאוגרפיים (שלא יחסם)
def get_porto_entities(e_type, limit=500):
    url = f"https://broker.fiware.urbanplatform.portodigital.pt/v2/entities?type={e_type}&limit={limit}"
    try:
        r = requests.get(url, verify=False, timeout=10)
        return r.json() if r.status_code == 200 else []
    except: return []

# --- שליפת נתונים ---
buses_raw = get_porto_entities("bus", 500)
stops_raw = get_porto_entities("busStop", 400) # הגבלה ל-400 תחנות כדי לשמור על מהירות

# מיקום משתמש
loc = get_geolocation()
if st.session_state.location_mode == 'gps' and loc and 'coords' in loc:
    user_lat, user_lon = loc['coords']['latitude'], loc['coords']['longitude']
else:
    user_lat, user_lon = st.session_state.get('map_center', (41.1485, -8.6110))

# עיבוד אוטובוסים
all_buses = []
for e in buses_raw:
    parts = str(e.get('name', {}).get('value', '')).split()
    if len(parts) >= 2:
        coords = e.get('location', {}).get('value', {}).get('coordinates', [0,0])
        dist = haversine(user_lat, user_lon, coords[1], coords[0])
        all_buses.append({'line': parts[1], 'lat': coords[1], 'lon': coords[0], 'dist': dist, 'heading': e.get('heading', {}).get('value', 0)})

# --- ממשק משתמש ---
st.markdown('<p class="custom-label">SELECT BUS LINE</p>', unsafe_allow_html=True)
active_lines = sorted(list(set([b['line'] for b in all_buses if b['line'].isdigit()])), key=int)
target = st.selectbox("Line:", ["Nearby Buses"] + active_lines, label_visibility="collapsed")

display_buses = sorted(all_buses, key=lambda x: x['dist'])[:12] if target == "Nearby Buses" else [b for b in all_buses if b['line'] == target]

# מפה
m = folium.Map(location=[user_lat, user_lon], zoom_start=16)
folium.Marker([user_lat, user_lon], icon=folium.Icon(color='red', icon='user', prefix='fa')).add_to(m)

# 1. הצגת תחנות (סינון מקומי בלבד)
for s in stops_raw:
    s_coords = s.get('location', {}).get('value', {}).get('coordinates', [0,0])
    # חישוב מרחק מקומי
    s_dist = haversine(user_lat, user_lon, s_coords[1], s_coords[0])
    if s_dist <= 0.4: # מציג רק מה שברדיוס 400 מטר ממך
        s_name = s.get('name', {}).get('value', 'Bus Stop').replace("Paragem: ", "")
        folium.CircleMarker(
            location=[s_coords[1], s_coords[0]],
            radius=5, color='#888', fill=True, fill_color='#00ccff', fill_opacity=0.8,
            popup=f"🚏 {s_name}"
        ).add_to(m)

# 2. הצגת אוטובוסים
for b in display_buses:
    icon_html = f'<div style="background-color: #00ccff; width: 30px; height: 30px; border-radius: 50%; border: 2px solid white; display: flex; align-items: center; justify-content: center; color: black; transform: rotate({b["heading"]}deg); font-weight: bold;">↑</div><div style="background: rgba(0,0,0,0.8); padding: 1px 3px; border-radius: 3px; font-size: 10px; position: absolute; top: 32px; color: white; white-space: nowrap;">{b["line"]}</div>'
    folium.Marker([b['lat'], b['lon']], icon=folium.DivIcon(icon_size=(30, 30), html=icon_html)).add_to(m)

st_folium(m, width=None, height=450, key=f"v36_map", use_container_width=True)

# כפתורים
c1, c2 = st.columns(2)
with c1:
    if st.button("📍 MY LOCATION"): st.session_state.location_mode = 'gps'; st.rerun()
with c2:
    if st.button("🏠 HOME"): st.session_state.location_mode = 'manual'; st.session_state.map_center = (41.1485, -8.6110); st.rerun()

# רענון
t_place = st.empty()
for i in range(45, 0, -1):
    t_place.markdown(f'<p class="refresh-text">Refreshing in {i}s...</p>', unsafe_allow_html=True)
    time.sleep(1)
st.rerun()
