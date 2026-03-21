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

# --- מאגר תחנות (v48 מורחב) ---
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

# 2. CSS משופר לרשימת התחנות
st.markdown("""
    <style>
    .stApp { background-color: #1e1e1e !important; }
    .block-container { padding: 0.5rem !important; max-width: 550px !important; margin: auto !important; }
    .stop-card { background-color: #262730; border-left: 5px solid #9933ff; padding: 12px; border-radius: 5px; margin-bottom: 10px; color: white; }
    .stop-title { font-size: 16px; font-weight: bold; margin-bottom: 4px; color: #ffffff; }
    .stop-info { font-size: 13px; color: #cccccc; }
    .bus-arrival { color: #ffff00; font-weight: bold; }
    .refresh-text { color: #888; font-size: 11px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

def get_bus_data():
    url = "https://broker.fiware.urbanplatform.portodigital.pt/v2/entities?q=vehicleType==bus&limit=1000"
    try:
        r = requests.get(url, verify=False, timeout=10)
        return r.json() if r.status_code == 200 else []
    except: return []

# --- לוגיקה מרכזית ---
buses_raw = get_bus_data()
STATIC_STOPS = get_all_stops()

loc = get_geolocation()
u_lat, u_lon = (loc['coords']['latitude'], loc['coords']['longitude']) if (loc and 'coords' in loc and st.session_state.get('location_mode') == 'gps') else st.session_state.get('map_center', (41.1485, -8.6110))

# עיבוד נתוני אוטובוסים
all_active_buses = []
for e in buses_raw:
    parts = str(e.get('name', {}).get('value', '')).split()
    if len(parts) >= 2:
        coords = e.get('location', {}).get('value', {}).get('coordinates', [0,0])
        all_active_buses.append({'line': parts[1], 'lat': coords[1], 'lon': coords[0]})

# --- תצוגת מפה (v48 המוכר) ---
m = folium.Map(location=[u_lat, u_lon], zoom_start=17)
folium.Marker([u_lat, u_lon], icon=folium.Icon(color='red', icon='user', prefix='fa')).add_to(m)

nearby_stops_data = []
for stop in STATIC_STOPS:
    dist = haversine(u_lat, u_lon, stop['lat'], stop['lon'])
    if dist <= 0.4: # מציג תחנות ברדיוס 400 מטר
        folium.CircleMarker(
            location=[stop['lat'], stop['lon']], radius=9, color='#ffffff', weight=2, 
            fill=True, fill_color='#9933ff', fill_opacity=0.9, tooltip=stop['name']
        ).add_to(m)
        
        # חישוב אוטובוסים קרובים לתחנה הספציפית הזו
        arrivals = []
        for bus in all_active_buses:
            b_dist = haversine(bus['lat'], bus['lon'], stop['lat'], stop['lon'])
            if b_dist < 2.0: # מחפש אוטובוסים ברדיוס 2 ק"מ מהתחנה
                eta = int((b_dist / 20) * 60) + 1 # חישוב דקות לפי 20 קמ"ש
                arrivals.append(f"Line {bus['line']} ({eta} min)")
        
        nearby_stops_data.append({
            'name': stop['name'],
            'dist': int(dist * 1000),
            'arrivals': sorted(arrivals, key=lambda x: int(x.split('(')[1].split()[0]))[:2] # 2 הכי קרובים
        })

st_folium(m, width=None, height=400, key="map_v49", use_container_width=True)

# --- רשימת התחנות מתחת למפה ---
st.markdown("### 🚏 Nearby Stops")
if not nearby_stops_data:
    st.write("No stops found within 400m.")
else:
    for s in sorted(nearby_stops_data, key=lambda x: x['dist']):
        bus_text = " | ".join(s['arrivals']) if s['arrivals'] else "No incoming buses"
        st.markdown(f"""
            <div class="stop-card">
                <div class="stop-title">{s['name']}</div>
                <div class="stop-info">
                    📏 {s['dist']}m away • <span class="bus-arrival">Next: {bus_text}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

# כפתורים
c1, c2 = st.columns(2)
with c1:
    if st.button("📍 GPS"): st.session_state.location_mode = 'gps'; st.rerun()
with c2:
    if st.button("🏠 CENTRO"): st.session_state.location_mode = 'manual'; st.session_state.map_center = (41.1485, -8.6110); st.rerun()

time.sleep(1) # מניעת רענון מהיר מדי
st.rerun()
