import streamlit as st
import requests
import time
import folium
from streamlit_folium import st_folium
from math import radians, cos, sin, asin, sqrt
from streamlit_js_eval import get_geolocation

# 1. הגדרות עמוד
st.set_page_config(page_title="Porto Bus Tracker", layout="wide")

# פונקציית מרחק
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 
    dLat, dLon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dLat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dLon/2)**2
    return R * 2 * asin(sqrt(a))

# --- מאגר תחנות זמני ---
def get_all_stops():
    return [
        {"name": "Aliados", "lat": 41.1485, "lon": -8.6110},
        {"name": "Pr. Liberdade", "lat": 41.1478, "lon": -8.6112},
        {"name": "Praça da República", "lat": 41.1554, "lon": -8.6133},
        {"name": "Trindade", "lat": 41.1523, "lon": -8.6125},
        {"name": "S. Bento Station", "lat": 41.1456, "lon": -8.6103},
        {"name": "Casa da Música", "lat": 41.1587, "lon": -8.6307},
        {"name": "Cordoaria", "lat": 41.1465, "lon": -8.6148},
        {"name": "Hospital S. João", "lat": 41.1804, "lon": -8.6015},
        {"name": "Marquês", "lat": 41.1602, "lon": -8.6061},
        {"name": "Rotunda Boavista", "lat": 41.1579, "lon": -8.6291}
    ]

# 2. CSS (v52 המעוצב מחדש)
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
    
    .distance-box { background-color: #262730; border: 1px solid #00ccff; padding: 10px; border-radius: 5px; text-align: center; color: white; margin-top: 10px; margin-bottom: 10px; font-size: 14px; }
    .distance-box b { color: #ffff00; }
    
    .stop-card { background-color: #262730; border-radius: 8px; padding: 12px; margin-bottom: 8px; border: 1px solid #444; }
    .stop-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
    .stop-title { font-size: 15px; font-weight: bold; color: #ffffff; }
    .stop-dist-tag { font-size: 13px; color: #aaa; background: #333; padding: 2px 6px; border-radius: 4px; }
    .arrival-row { font-size: 14px; color: #ffff00; font-weight: bold; display: flex; gap: 8px; flex-wrap: wrap; }
    .bus-item { display: flex; align-items: center; gap: 4px; background: rgba(255,255,0,0.1); padding: 2px 6px; border-radius: 4px; }
    
    .refresh-text { color: #888; font-size: 11px; text-align: center; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

def get_bus_data():
    url = "https://broker.fiware.urbanplatform.portodigital.pt/v2/entities?q=vehicleType==bus&limit=1000"
    try:
        r = requests.get(url, verify=False, timeout=10)
        return r.json() if r.status_code == 200 else []
    except: return []

# --- אתחול ---
buses_raw = get_bus_data()
STATIC_STOPS = get_all_stops()
if 'location_mode' not in st.session_state: st.session_state.location_mode = 'gps'
if 'map_center' not in st.session_state: st.session_state.map_center = (41.1485, -8.6110)

# בחירת קו
st.markdown('<p class="custom-label">SELECT BUS LINE</p>', unsafe_allow_html=True)
active_lines = [str(e.get('name', {}).get('value', '')).split()[1] for e in buses_raw if len(str(e.get('name', {}).get('value', '')).split()) >= 2 and str(e.get('name', {}).get('value', '')).split()[1].isdigit()]
unique_lines = sorted(list(set(active_lines)), key=lambda x: int(x))
target = st.selectbox("Line:", ["Nearby Buses"] + unique_lines, label_visibility="collapsed")

loc = get_geolocation()
u_lat, u_lon = (loc['coords']['latitude'], loc['coords']['longitude']) if (st.session_state.location_mode == 'gps' and loc) else st.session_state.map_center

# --- מפה ---
m = folium.Map(location=[u_lat, u_lon], zoom_start=17)
folium.Marker([u_lat, u_lon], icon=folium.Icon(color='red', icon='user', prefix='fa')).add_to(m)

all_active_buses = []
for e in buses_raw:
    parts = str(e.get('name', {}).get('value', '')).split()
    if len(parts) >= 2:
        coords = e.get('location', {}).get('value', {}).get('coordinates', [0,0])
        all_active_buses.append({'line': parts[1], 'lat': coords[1], 'lon': coords[0], 'dist': haversine(u_lat, u_lon, coords[1], coords[0]), 'heading': e.get('heading', {}).get('value', 0)})

display_buses = sorted(all_active_buses, key=lambda x: x['dist'])[:10] if target == "Nearby Buses" else [b for b in all_active_buses if b['line'] == target]

for b in display_buses:
    stcp_url = f"https://stcp.pt/en/line?line={b['line']}"
    popup_html = f'<div style="text-align:center;"><b>Line {b["line"]}</b><br><a href="{stcp_url}" target="_blank" style="color:#00ccff;">➔ Route</a></div>'
    icon_html = f'<div style="background-color: #00ccff; width: 30px; height: 30px; border-radius: 50%; border: 2px solid white; display: flex; align-items: center; justify-content: center; transform: rotate({b["heading"]}deg); font-weight: bold;">↑</div><div style="background: rgba(0,0,0,0.8); padding: 1px 3px; border-radius: 3px; font-size: 10px; position: absolute; top: 32px; color: white; font-weight: bold;">{b["line"]}</div>'
    folium.Marker([b['lat'], b['lon']], icon=folium.DivIcon(icon_size=(30, 30), html=icon_html), popup=folium.Popup(popup_html, max_width=150)).add_to(m)

# עיבוד תחנות
nearby_stops_data = []
for stop in STATIC_STOPS:
    dist = haversine(u_lat, u_lon, stop['lat'], stop['lon'])
    if dist <= 0.4:
        folium.CircleMarker(location=[stop['lat'], stop['lon']], radius=9, color='#ffffff', weight=2, fill=True, fill_color='#9933ff', fill_opacity=0.9).add_to(m)
        
        # חישוב הגעות
        arrivals = []
        for bus in all_active_buses:
            b_stop_dist = haversine(bus['lat'], bus['lon'], stop['lat'], stop['lon'])
            if b_stop_dist < 1.5:
                eta = int((b_stop_dist / 20) * 60) + 1
                arrivals.append({'line': bus['line'], 'eta': eta})
        
        nearby_stops_data.append({
            'name': stop['name'], 
            'dist': int(dist * 1000), 
            'arrivals': sorted(arrivals, key=lambda x: x['eta'])[:3]
        })

st_folium(m, width=None, height=400, key="map_v52", use_container_width=True)

# תיבת מרחק
if display_buses:
    closest = min(display_buses, key=lambda x: x['dist'])
    st.markdown(f'<div class="distance-box">🚍 Closest: <b>Line {closest["line"]}</b> is <b>{closest["dist"]:.2f} km</b> away</div>', unsafe_allow_html=True)

# כפתורים
c1, c2 = st.columns(2)
with c1:
    if st.button("📍 GPS"): st.session_state.location_mode = 'gps'; st.rerun()
with c2:
    if st.button("🏠 CENTRO"): st.session_state.location_mode = 'manual'; st.session_state.map_center = (41.1485, -8.6110); st.rerun()

# --- רשימת תחנות (v52 החדשה) ---
for s in sorted(nearby_stops_data, key=lambda x: x['dist']):
    # בניית שורת האוטובוסים
    bus_html = ""
    if s['arrivals']:
        for a in s['arrivals']:
            bus_html += f'<div class="bus-item">🚌 {a["line"]} ({a["eta"]}m 🕒)</div>'
    else:
        bus_html = '<span style="color:#888; font-size:12px;">No incoming buses</span>'

    st.markdown(f"""
        <div class="stop-card">
            <div class="stop-header">
                <div class="stop-title">📍 {s['name']}</div>
                <div class="stop-dist-tag">{s['dist']}m</div>
            </div>
            <div class="arrival-row">
                {bus_html}
            </div>
        </div>
    """, unsafe_allow_html=True)

# רענון
t = st.empty()
for i in range(45, 0, -1):
    t.markdown(f'<p class="refresh-text">Next update in {i}s...</p>', unsafe_allow_html=True)
    time.sleep(1)
st.rerun()
