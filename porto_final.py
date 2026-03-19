import streamlit as st
import requests
import time
import folium
from streamlit_folium import st_folium
from math import radians, cos, sin, asin, sqrt
import os
import base64
from streamlit_js_eval import get_geolocation

# הגדרות עמוד
st.set_page_config(page_title="Porto Bus Tracker", layout="centered")

def get_image_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None

img_base64 = get_image_base64("bus_icon.png")

# CSS: עיצוב נקי והסתרת ממשק ענן
st.markdown(f"""
    <style>
    .stApp {{ background-color: #1e1e1e !important; }}
    .stApp, .stApp p, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3 {{ color: #ffffff !important; }}
    #MainMenu, footer, .stDeployButton, [data-testid="stStatusWidget"] {{ visibility: hidden; display: none !important; }}
    .header-container {{ display: flex; align-items: center; gap: 15px; }}
    .header-logo {{ width: 80px; height: auto; }}
    div[data-baseweb="select"] > div {{ background-color: #333333 !important; border: 1px solid #555 !important; }}
    .stInfo {{ background-color: #262730 !important; border: 1px solid #00ccff !important; color: white !important; }}
    </style>
    """, unsafe_allow_html=True)

if img_base64:
    st.markdown(f'<div class="header-container"><img src="data:image/png;base64,{img_base64}" class="header-logo"><h1 class="header-text">Porto Bus Live</h1></div>', unsafe_allow_html=True)
st.divider()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 
    dLat, dLon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dLat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dLon/2)**2
    return R * 2 * asin(sqrt(a))

# --- GPS REAL-TIME ---
loc = get_geolocation()
if loc:
    user_lat = loc['coords']['latitude']
    user_lon = loc['coords']['longitude']
else:
    # ברירת מחדל לפורטו אם ה-GPS עוד לא נטען
    user_lat, user_lon = 41.1485, -8.6110

def get_bus_data():
    url = "https://broker.fiware.urbanplatform.portodigital.pt/v2/entities?q=vehicleType==bus&limit=1000"
    try:
        r = requests.get(url, verify=False, timeout=10)
        return r.json() if r.status_code == 200 else []
    except: return []

buses_raw = get_bus_data()
all_buses = []
active_lines = []

for e in buses_raw:
    name = str(e.get('name', {}).get('value', ''))
    parts = name.split()
    if len(parts) >= 2:
        coords = e.get('location', {}).get('value', {}).get('coordinates', [0,0])
        if len(coords) == 2:
            line_num = parts[1]
            b_lat, b_lon = coords[1], coords[0]
            dist = haversine(user_lat, user_lon, b_lat, b_lon)
            if line_num.isdigit(): active_lines.append(line_num)
            all_buses.append({
                'line': line_num, 'lat': b_lat, 'lon': b_lon, 'dist': dist,
                'heading': e.get('heading', {}).get('value', 0)
            })

unique_lines = sorted(list(set(active_lines)), key=lambda x: int(x))
target = st.selectbox("🎯 Select Bus Line:", ["Nearby (10 Closest)"] + unique_lines)
display_buses = sorted(all_buses, key=lambda x: x['dist'])[:10] if target == "Nearby (10 Closest)" else [b for b in all_buses if b['line'] == target]

# תצוגת אוטובוס קרוב
if display_buses:
    closest = min(display_buses, key=lambda x: x['dist'])
    st.info(f"🚍 **Closest Bus (Line {closest['line']}):** {closest['dist']:.2f} km from you")

# מפה
m = folium.Map(location=[user_lat, user_lon], zoom_start=16)
folium.Marker([user_lat, user_lon], tooltip="You are here", icon=folium.Icon(color='blue', icon='user', prefix='fa')).add_to(m)

for b in display_buses:
    icon_html = f'<div style="background-color: #00ccff; width: 30px; height: 30px; border-radius: 50%; border: 2px solid white; display: flex; align-items: center; justify-content: center; color: black; transform: rotate({b["heading"]}deg); font-weight: bold;">↑</div><div style="background: rgba(0,0,0,0.8); padding: 1px 3px; border-radius: 3px; font-size: 10px; position: absolute; top: 32px; color: white; white-space: nowrap;">{b["line"]}</div>'
    folium.Marker(location=[b['lat'], b['lon']], icon=folium.DivIcon(icon_size=(30, 30), icon_anchor=(15, 15), html=icon_html)).add_to(m)

st_folium(m, width=700, height=500, key=f"map_stable_{target}")

# רענון כל 30 שניות ליציבות
t_place = st.empty()
for i in range(30, 0, -1):
    t_place.write(f"Refreshing in {i}s...")
    time.sleep(1)
st.rerun()
