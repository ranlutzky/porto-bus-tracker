import streamlit as st
import requests
import time
import folium
from streamlit_folium import st_folium
from math import radians, cos, sin, asin, sqrt
from streamlit_js_eval import get_geolocation

# 1. הגדרות בסיס
st.set_page_config(page_title="Porto Bus", layout="wide")

# 2. אתחול מיקום
if 'map_center' not in st.session_state:
    st.session_state.map_center = (41.1485, -8.6110)
if 'location_mode' not in st.session_state:
    st.session_state.location_mode = 'gps'

# 3. CSS מינימליסטי וקריא
st.markdown("""
    <style>
    .stApp { background-color: #1e1e1e !important; }
    .block-container { padding: 1rem !important; max-width: 550px !important; margin: auto !important; }
    header { visibility: hidden; }
    .custom-label { color: white !important; font-weight: bold; margin-bottom: 5px; }
    .refresh-text { color: #ffffff !important; font-size: 12px; text-align: center; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 
    dLat, dLon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dLat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dLon/2)**2
    return R * 2 * asin(sqrt(a))

# 4. פונקציית שליפה פשוטה (רק אוטובוסים!)
def get_buses():
    url = "https://broker.fiware.urbanplatform.portodigital.pt/v2/entities?type=bus&limit=500"
    try:
        r = requests.get(url, verify=False, timeout=10)
        return r.json() if r.status_code == 200 else []
    except:
        return []

# --- ביצוע ---
buses_raw = get_buses()

# זיהוי מיקום
loc = get_geolocation()
if st.session_state.location_mode == 'gps' and loc and 'coords' in loc:
    u_lat, u_lon = loc['coords']['latitude'], loc['coords']['longitude']
else:
    u_lat, u_lon = st.session_state.map_center

# עיבוד רשימת קווים לבחירה
active_lines = []
all_buses_data = []
for e in buses_raw:
    name_val = e.get('name', {}).get('value', '')
    parts = str(name_val).split()
    if len(parts) >= 2:
        line = parts[1]
        coords = e.get('location', {}).get('value', {}).get('coordinates', [0,0])
        dist = haversine(u_lat, u_lon, coords[1], coords[0])
        heading = e.get('heading', {}).get('value', 0)
        all_buses_data.append({'line': line, 'lat': coords[1], 'lon': coords[0], 'dist': dist, 'heading': heading})
        if line.isdigit(): active_lines.append(line)

unique_lines = sorted(list(set(active_lines)), key=int)

st.markdown('<p class="custom-label">LINE SELECTION</p>', unsafe_allow_html=True)
target = st.selectbox("Select:", ["All Nearby"] + unique_lines, label_visibility="collapsed")

# סינון אוטובוסים להצגה
display = sorted(all_buses_data, key=lambda x: x['dist'])[:15] if target == "All Nearby" else [b for b in all_buses_data if b['line'] == target]

# מפה
m = folium.Map(location=[u_lat, u_lon], zoom_start=15)
folium.Marker([u_lat, u_lon], icon=folium.Icon(color='red', icon='user', prefix='fa')).add_to(m)

for b in display:
    # אייקון חץ כחול פשוט
    icon_html = f'''<div style="background-color: #00ccff; width: 30px; height: 30px; border-radius: 50%; border: 2px solid white; display: flex; align-items: center; justify-content: center; transform: rotate({b['heading']}deg); font-weight: bold; color: black;">↑</div>
                   <div style="background: black; color: white; font-size: 10px; padding: 1px 3px; border-radius: 3px; position: absolute; top: 30px;">{b['line']}</div>'''
    folium.Marker(
        [b['lat'], b['lon']], 
        icon=folium.DivIcon(icon_size=(30, 30), html=icon_html),
        popup=f"Line {b['line']}"
    ).add_to(m)

st_folium(m, width=None, height=450, key=f"v33_map_{target}", use_container_width=True)

# כפתורים
c1, c2 = st.columns(2)
with c1:
    if st.button("📍 GPS"): st.session_state.location_mode = 'gps'; st.rerun()
with c2:
    if st.button("🏠 HOME"): st.session_state.location_mode = 'manual'; st.rerun()

# רענון
t = st.empty()
for i in range(30, 0, -1):
    t.markdown(f'<p class="refresh-text">Update in {i}s...</p>', unsafe_allow_html=True)
    time.sleep(1)
st.rerun()
