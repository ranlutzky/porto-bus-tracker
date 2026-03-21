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
    st.session_state.location_mode = 'gps' # ברירת מחדל GPS

# CSS: Mobile Optimized - יישור גבהים ופיצול כפתורים
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
        margin-bottom: 2px;
        text-transform: uppercase;
    }

    /* עיצוב הכפתורים המפוצלים - גובה 68px ליישור סופי */
    .stButton>button {
        width: 100%;
        background-color: #333333 !important;
        color: white !important;
        border: 1px solid #555 !important;
        height: 68px !important; 
        padding: 0px !important;
        font-size: 11px !important;
        font-weight: bold;
    }
    .stButton>button:hover { border-color: #00ccff !important; color: #00ccff !important; }

    /* עיצוב תיבת הבחירה */
    div[data-baseweb="select"] > div { 
        background-color: #333333 !important; 
        border: 1px solid #555 !important;
        height: 42px !important;
    }
    div[data-baseweb="select"] * { color: white !important; }

    .stInfo { 
        background-color: #262730 !important; 
        border: 1px solid #00ccff !important; 
        color: white !important; 
        text-align: center;
        padding: 0.4rem !important;
        margin-top: 8px !important;
    }
    </style>
    """, unsafe_allow_html=True)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 
    dLat, dLon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dLat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dLon/2)**2
    return R * 2 * asin(sqrt(a))

# שורה עליונה - חלוקה ל-3 עמודות (חיפוש, בית, מיקום שלי)
col_search, col_home, col_gps = st.columns([2.2, 0.6, 0.6])

with col_home:
    if st.button("🏠 HOME"):
        st.session_state.location_mode = 'manual'
        st.session_state.map_center = (41.1485, -8.6110)
        st.rerun()

with col_gps:
    if st.button("📍 MY LOC"):
        st.session_state.location_mode = 'gps'
        st.rerun()

# לוגיקת מיקום חכמה
loc = get_geolocation()
if st.session_state.location_mode == 'gps' and loc:
    user_lat, user_lon = loc['coords']['latitude'], loc['coords']['longitude']
else:
    user_lat, user_lon = st.session_state.map_center

with col_search:
    st.markdown('<p class="custom-label">SELECT BUS LINE</p>', unsafe_allow_html=True)
    def get_bus_data():
        url = "https://broker.fiware.urbanplatform.portodigital.pt/v2/entities?q=vehicleType==bus&limit=1000"
        try:
            r = requests.get(url, verify=False, timeout=10)
            return r.json() if r.status_code == 200 else []
        except: return []
    
    buses_raw = get_bus_data()
    active_lines = []
    for e in buses_raw:
        name = str(e.get('name', {}).get('value', ''))
        parts = name.split()
        if len(parts) >= 2 and parts[1].isdigit(): active_lines.append(parts[1])
    
    unique_lines = sorted(list(set(active_lines)), key=lambda x: int(x))
    target = st.selectbox("Line:", ["Nearby Buses"] + unique_lines, label_visibility="collapsed")

# עיבוד אוטובוסים למפה
all_buses = []
for e in buses_raw:
    name = str(e.get('name', {}).get('value', ''))
    parts = name.split()
    if len(parts) >= 2:
        coords = e.get('location', {}).get('value', {}).get('coordinates', [0,0])
        if len(coords) == 2:
            l_num = parts[1]
            b_lat, b_lon = coords[1], coords[0]
            dist = haversine(user_lat, user_lon, b_lat, b_lon)
            all_buses.append({'line': l_num, 'lat': b_lat, 'lon': b_lon, 'dist': dist, 'heading': e.get('heading', {}).get('value', 0)})

display_buses = sorted(all_buses, key=lambda x: x['dist'])[:10] if target == "Nearby Buses" else [b for b in all_buses if b['line'] == target]

if display_buses:
    closest = min(display_buses, key=lambda x: x['dist'])
    st.info(f"🚍 **Closest: L-{closest['line']} ({closest['dist']:.2f} km)**")

# מפה
m = folium.Map(location=[user_lat, user_lon], zoom_start=16)
folium.Marker([user_lat, user_lon], icon=folium.Icon(color='red', icon='user', prefix='fa')).add_to(m)

for b in display_buses:
    icon_html = f'<div style="background-color: #00ccff; width: 30px; height: 30px; border-radius: 50%; border: 2px solid white; display: flex; align-items: center; justify-content: center; color: black; transform: rotate({b["heading"]}deg); font-weight: bold;">↑</div><div style="background: rgba(0,0,0,0.8); padding: 1px 3px; border-radius: 3px; font-size: 10px; position: absolute; top: 32px; color: white; white-space: nowrap;">{b["line"]}</div>'
    folium.Marker(location=[b['lat'], b['lon']], icon=folium.DivIcon(icon_size=(30, 30), icon_anchor=(15, 15), html=icon_html)).add_to(m)

st_folium(m, width=None, height=480, key=f"map_v10_{target}", use_container_width=True)

# רענון
t_place = st.empty()
for i in range(30, 0, -1):
    t_place.write(f"Refreshing in {i}s...")
    time.sleep(1)
st.rerun()
