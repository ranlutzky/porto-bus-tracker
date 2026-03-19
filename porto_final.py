import streamlit as st
import requests
import time
import folium
from streamlit_folium import st_folium
from math import radians, cos, sin, asin, sqrt
import os
import base64

# הגדרות עמוד
st.set_page_config(page_title="Porto Bus Tracker", layout="centered")

def get_image_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None

img_base64 = get_image_base64("bus_icon.png")

# --- CSS מעודכן לסידור המרווחים ---
st.markdown(f"""
    <style>
    .stApp {{
        background-color: #1e1e1e !important;
    }}
    
    /* טקסט לבן */
    .stApp, .stApp p, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3 {{
        color: #ffffff !important;
    }}
    
    /* הוספת מרווח בראש הדף כדי שהכותרת לא תיחתך */
    .block-container {{
        padding-top: 3.5rem !important; 
        padding-bottom: 1rem !important;
    }}

    /* עיצוב כותרת ולוגו */
    .header-container {{
        display: flex;
        align-items: center;
        gap: 15px;
        margin-bottom: 0px; /* ביטול מרווח תחתון של הכותרת */
    }}
    .header-logo {{
        width: 120px;
        height: auto;
    }}
    .header-text {{
        margin: 0 !important;
        padding: 0 !important;
    }}

    /* צמצום הרווח של הקו המפריד */
    hr {{
        margin-top: 10px !important;
        margin-bottom: 15px !important;
        border-top: 1px solid #444 !important;
    }}

    /* צמצום הרווח מעל תיבת הבחירה */
    div[data-testid="stWidgetLabel"] {{
        margin-bottom: -10px !important;
    }}

    /* תיבת בחירה */
    div[data-baseweb="select"] > div {{
        background-color: #333333 !important;
        border: 1px solid #555 !important;
    }}
    
    /* הודעת המרחק - צמודה יותר לתיבה מעליה */
    .stInfo {{
        background-color: #0e2f44 !important;
        color: #ffffff !important;
        border: 1px solid #00ccff !important;
        margin-top: 5px !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- כותרת ---
if img_base64:
    st.markdown(f"""
        <div class="header-container">
            <img src="data:image/png;base64,{img_base64}" class="header-logo">
            <h1 class="header-text">Porto Bus Live</h1>
        </div>
        """, unsafe_allow_html=True)
else:
    st.title("🚌 Porto Bus Live")

st.divider()

# --- לוגיקה ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6372.8 
    dLat, dLon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dLat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dLon/2)**2
    return R * 2 * asin(sqrt(a))

if 'home_coords' not in st.session_state:
    st.session_state.home_coords = (41.1478, -8.6231)

HOME_LAT, HOME_LON = st.session_state.home_coords

def get_bus_data():
    url = "https://broker.fiware.urbanplatform.portodigital.pt/v2/entities?q=vehicleType==bus&limit=1000"
    try:
        r = requests.get(url, verify=False, timeout=5)
        return r.json() if r.status_code == 200 else []
    except: return []

raw_data = get_bus_data()
all_buses = []
active_lines = []

if raw_data:
    for e in raw_data:
        name = str(e.get('name', {}).get('value', ''))
        parts = name.split()
        if len(parts) >= 2:
            coords = e.get('location', {}).get('value', {}).get('coordinates', [0,0])
            if coords != [0,0]:
                line_num = parts[1]
                lat, lon = coords[1], coords[0]
                dist = haversine(HOME_LAT, HOME_LON, lat, lon)
                if line_num.isdigit(): active_lines.append(line_num)
                all_buses.append({
                    'line': line_num, 'lat': lat, 'lon': lon, 'dist': dist,
                    'heading': e.get('heading', {}).get('value', 0)
                })

unique_lines = sorted(list(set(active_lines)), key=lambda x: int(x))
target = st.selectbox("🎯 Select Bus Line:", ["Nearby (10 Closest)"] + unique_lines)

if target == "Nearby (10 Closest)":
    display_buses = sorted(all_buses, key=lambda x: x['dist'])[:10]
else:
    display_buses = [b for b in all_buses if b['line'] == target]

if display_buses:
    closest = min(display_buses, key=lambda x: x['dist'])
    st.info(f"🚍 **Closest Bus (Line {closest['line']}):** {closest['dist']:.2f} km away")

# --- מפה ---
m = folium.Map(location=[HOME_LAT, HOME_LON], zoom_start=15)
folium.Marker([HOME_LAT, HOME_LON], icon=folium.Icon(color='red', icon='home')).add_to(m)

for b in display_buses:
    icon_html = f"""
        <div style="background-color: #00ccff; width: 32px; height: 32px; border-radius: 50%; border: 2px solid white; display: flex; align-items: center; justify-content: center; color: black; transform: rotate({b['heading']}deg); font-weight: bold; box-shadow: 0px 0px 5px rgba(0,0,0,0.5);">
        ↑
        </div>
        <div style="background: rgba(0,0,0,0.7); border: 1px solid white; padding: 1px 4px; border-radius: 4px; font-size: 11px; position: absolute; top: 35px; color: white; white-space: nowrap; font-weight: bold;">
        {b['line']} ({b['dist']:.1f}km)
        </div>
    """
    folium.Marker(
        location=[b['lat'], b['lon']],
        icon=folium.DivIcon(icon_size=(32, 32), icon_anchor=(16, 16), html=icon_html)
    ).add_to(m)

st_folium(m, width=700, height=500, key=f"map_v2_{target}")

# טיימר
t_place = st.empty()
for i in range(20, 0, -1):
    t_place.write(f"Refreshing in {i}s...")
    time.sleep(1)
st.rerun()