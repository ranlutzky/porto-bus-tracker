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

# 3. CSS לעיצוב הממשק
st.markdown("""
    <style>
    .stApp { background-color: #1e1e1e !important; }
    header { visibility: hidden; height: 0px !important; }
    .block-container { 
        padding-top: 0.5rem !important; padding-left: 0.5rem !important;
        padding-right: 0.5rem !important; max-width: 550px !important; margin: auto !important;
    }
    div.stButton > button {
        width: 100% !important; background-color: #333333 !important;
        color: #ffffff !important; border: 1px solid #555 !important;
        height: 40px !important; font-size: 13px !important; font-weight: bold !important;
    }
    .bus-card {
        background-color: #262730; border-left: 4px solid #00ccff;
        padding: 12px; margin-bottom: 10px; border-radius: 4px; color: white;
    }
    .bus-line-title { font-weight: bold; font-size: 17px; color: #ffffff; margin-bottom: 3px; }
    .bus-meta { font-size: 13px; color: #bbb; }
    .eta-highlight { color: #ffff00; font-weight: bold; }
    .custom-label { color: white !important; font-size: 13px; font-weight: bold; margin-bottom: 5px; margin-top: 15px; }
    div[data-baseweb="select"] > div { background-color: #333333 !important; border: 1px solid #555 !important; }
    div[data-baseweb="select"] * { color: white !important; }
    .refresh-text { color: #ffffff !important; font-size: 11px; text-align: center; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 
    dLat, dLon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dLat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dLon/2)**2
    return R * 2 * asin(sqrt(a))

@st.cache_data(ttl=60) # שמירה בזיכרון לדקה כדי לא להעמיס על ה-API
def get_porto_data(q_type):
    url = f"https://broker.fiware.urbanplatform.portodigital.pt/v2/entities?type={q_type}&limit=500"
    try:
        r = requests.get(url, verify=False, timeout=5)
        return r.json() if r.status_code == 200 else []
    except: return []

# --- שליפת נתונים ---
buses_raw = get_porto_data("bus")
stops_raw = get_porto_data("busStop")

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

# עיבוד תחנות קרובות (עד 500 מטר)
nearby_stops = []
for s in stops_raw:
    s_coords = s.get('location', {}).get('value', {}).get('coordinates', [0,0])
    s_dist = haversine(user_lat, user_lon, s_coords[1], s_coords[0])
    if s_dist <= 0.5: # הגבלה ל-500 מטר
        s_name = s.get('name', {}).get('value', 'Unknown Stop')
        # ניקוי קל לשם התחנה (למשל הורדת המילה "Paragem")
        s_name = s_name.replace("Paragem ", "").strip()
        nearby_stops.append({'name': s_name, 'dist': s_dist, 'lat': s_coords[1], 'lon': s_coords[0]})

# --- ממשק משתמש ---
st.markdown('<p class="custom-label">SELECT BUS LINE</p>', unsafe_allow_html=True)
unique_lines = sorted(list(set([b['line'] for b in all_buses])), key=lambda x: int(x) if x.isdigit() else 0)
target = st.selectbox("Line:", ["Nearby Buses"] + unique_lines, label_visibility="collapsed")

display_buses = sorted(all_buses, key=lambda x: x['dist'])[:10] if target == "Nearby Buses" else [b for b in all_buses if b['line'] == target]

# מפה
m = folium.Map(location=[user_lat, user_lon], zoom_start=16)
folium.Marker([user_lat, user_lon], icon=folium.Icon(color='red', icon='user', prefix='fa')).add_to(m)

for b in display_buses:
    stcp_url = f"https://stcp.pt/en/line?line={b['line']}"
    popup_html = f'<div style="text-align:center;"><b>Line {b["line"]}</b><br><a href="{stcp_url}" target="_blank">Route</a></div>'
    icon_html = f'<div style="background-color: #00ccff; width: 30px; height: 30px; border-radius: 50%; border: 2px solid white; display: flex; align-items: center; justify-content: center; color: black; transform: rotate({b["heading"]}deg); font-weight: bold;">↑</div>'
    folium.Marker([b['lat'], b['lon']], icon=folium.DivIcon(icon_size=(30, 30), html=icon_html), popup=folium.Popup(popup_html, max_width=150)).add_to(m)

st_folium(m, width=None, height=400, key=f"map_v29_{target}", use_container_width=True)

# כפתורי מיקום
c1, c2 = st.columns(2)
with c1:
    if st.button("📍 MY LOCATION"): st.session_state.location_mode = 'gps'; st.rerun()
with c2:
    if st.button("🏠 HOME (PORTO)"): st.session_state.location_mode = 'manual'; st.session_state.map_center = (41.1485, -8.6110); st.rerun()

# --- רשימת ה-Cards המעודכנת ---
st.markdown('<p class="custom-label">STOPS & INCOMING BUSES (<500m)</p>', unsafe_allow_html=True)

# אנחנו מציגים את התחנות הקרובות ביותר, ועבור כל אחת מחפשים את האוטובוס הכי קרוב
sorted_nearby_stops = sorted(nearby_stops, key=lambda x: x['dist'])[:4]

if not sorted_nearby_stops:
    st.info("No official stops found within 500m.")
else:
    for stop in sorted_nearby_stops:
        # מוצאים את האוטובוס הכי קרוב לתחנה הזו (כדי לתת ETA)
        eta = "N/A"
        relevant_bus = "---"
        
        # חיפוש אוטובוס בטווח 2 ק"מ מהתחנה
        bus_dists = [(b['line'], haversine(b['lat'], b['lon'], stop['lat'], stop['lon'])) for b in all_buses]
        if bus_dists:
            closest_bus_line, bus_stop_dist = min(bus_dists, key=lambda x: x[1])
            if bus_stop_dist < 3.0: # אם יש אוטובוס בטווח סביר
                relevant_bus = closest_bus_line
                eta = f"{int(bus_stop_dist * 5) + 1} min"

        st.markdown(f"""
            <div class="bus-card">
                <div class="bus-line-title">🚍 Line {relevant_bus}</div>
                <div class="bus-meta">
                    📍 {stop['name']}<br>
                    🚶 <b>{int(stop['dist']*1000)}m</b> | 🕒 Arrival: <span class="eta-highlight">~{eta}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

# רענון
t_place = st.empty()
for i in range(45, 0, -1):
    t_place.markdown(f'<p class="refresh-text">Refreshing in {i}s...</p>', unsafe_allow_html=True)
    time.sleep(1)
st.rerun()
