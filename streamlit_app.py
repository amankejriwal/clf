import streamlit as st
import json
import folium
from folium.plugins import Draw, Geocoder
from streamlit_folium import st_folium

st.set_page_config(page_title="Clinic Finder", layout="wide", initial_sidebar_state="collapsed")

@st.cache_data(ttl=60)  # Cache for 60 seconds only
def load_data():
    """Load all pre-calculated data files for fast startup - v2"""
    # Load simplified boundary GeoJSON (much faster than shapefile)
    with open('data/netherlands_boundary.geojson') as f:
        boundary_geojson = json.load(f)
    
    with open('nl_population.json') as f:
        population_centers = json.load(f)
    
    with open('nl_ortho.json') as f:
        clinics = json.load(f)
    
    # Load pre-calculated dental clinics
    with open('data/dental_clinics.json') as f:
        dental_clinics = json.load(f)
    
    # Load pre-calculated schools
    with open('data/schools.json') as f:
        schools = json.load(f)
    
    # Load pre-calculated potential locations
    with open('data/potential_locations.json') as f:
        potential_locations = json.load(f)
    
    return boundary_geojson, population_centers, clinics, dental_clinics, schools, potential_locations

def create_map(boundary_geojson, population_centers, clinics, dental_clinics, schools, potential_locations, show_population, show_clinics, show_dental, show_schools, show_potential):
    """Create the folium map with all layers"""
    # Initialize map centered on Netherlands
    m = folium.Map(location=[52.3676, 4.9041], zoom_start=8, tiles='OpenStreetMap')
    
    # Add draw control
    Draw(export=True).add_to(m)
    
    # Add search control
    Geocoder().add_to(m)
    
    # Add Netherlands boundary
    folium.GeoJson(
        boundary_geojson,
        name="Netherlands Boundary",
        style_function=lambda x: {
            'fillColor': 'transparent',
            'color': 'black',
            'weight': 2
        }
    ).add_to(m)
    
    # Population centers layer
    if show_population:
        population_group = folium.FeatureGroup(name="Population Centers")
        
        P_max = 741636
        P_min = 500
        r_max = 15
        r_min = 2
        
        sub_ranges = [
            (500, 20000, '#FF9D00'),
            (20001, 40000, '#FECC5C'),
            (40001, 80000, '#FD8D3C'),
            (80000, 300000, '#FF6701'),
            (300000, 741636, 'purple')
        ]
        
        for pc in population_centers:
            population = pc["population"]
            if population > 20000:
                radius = (r_min + (r_max - r_min) * (population - P_min) / (P_max - P_min)) * 100
                
                circle_color = '#FF9D00'
                for lower, upper, color in sub_ranges:
                    if lower <= population <= upper:
                        circle_color = color
                        break
                
                folium.Circle(
                    location=[pc["latitude"], pc["longitude"]],
                    radius=radius * 10,
                    color=circle_color,
                    fill=True,
                    fill_color=circle_color,
                    fill_opacity=0.6,
                    weight=1,
                    popup=f"<b>{pc['name']}</b><br>Population: {population:,}"
                ).add_to(population_group)
        
        population_group.add_to(m)
    
    # Dental clinics layer
    if show_dental:
        dental_group = folium.FeatureGroup(name="Dental Clinics")
        
        for clinic in dental_clinics:
            name = clinic.get("name") or "Dental Clinic"
            address = clinic.get("address", "")
            city = clinic.get("city", "")
            postcode = clinic.get("postcode", "")
            phone = clinic.get("phone", "")
            website = clinic.get("website", "")
            
            popup_parts = [f"<b>{name}</b>"]
            if address:
                popup_parts.append(address)
            if postcode or city:
                popup_parts.append(f"{postcode} {city}".strip())
            if phone:
                popup_parts.append(f"📞 {phone}")
            if website:
                popup_parts.append(f"🌐 <a href='{website}' target='_blank'>Website</a>")
            
            popup_text = "<br>".join(popup_parts)
            
            folium.Circle(
                location=[clinic["latitude"], clinic["longitude"]],
                radius=5000,  # 5km radius
                color="#007FFF",  # Azure blue
                fill=True,
                fill_color="#007FFF",
                fill_opacity=0.3,
                weight=2,
                popup=popup_text
            ).add_to(dental_group)
        
        dental_group.add_to(m)
    
    # Schools layer
    if show_schools:
        schools_group = folium.FeatureGroup(name="Schools")
        
        for school in schools:
            name = school.get("name") or "School"
            address = school.get("address", "")
            city = school.get("city", "")
            postcode = school.get("postcode", "")
            
            popup_parts = [f"<b>{name}</b>"]
            if address:
                popup_parts.append(address)
            if postcode or city:
                popup_parts.append(f"{postcode} {city}".strip())
            
            popup_text = "<br>".join(popup_parts)
            
            folium.Circle(
                location=[school["latitude"], school["longitude"]],
                radius=5000,  # 5km radius
                color="#90EE90",  # Light green
                fill=True,
                fill_color="#90EE90",
                fill_opacity=0.3,
                weight=1,
                popup=popup_text
            ).add_to(schools_group)
        
        schools_group.add_to(m)
    
    # Potential locations layer
    if show_potential:
        potential_group = folium.FeatureGroup(name="Potential New Clinic Locations")
        
        for loc in potential_locations:
            rank = loc.get('rank', 0)
            distance_weesp = loc.get('distance_from_weesp', 0)
            rank_score = loc.get('rank_score', 0)
            
            # Top 5 get green, rest get gold
            is_top = rank <= 5
            
            popup_text = f"""
                <b>🏆 Rank #{rank}</b><br>
                <hr style='margin:5px 0'>
                <b>Final Score: {rank_score:.3f}</b><br>
                (70% opportunity + 30% proximity)<br>
                <hr style='margin:5px 0'>
                ⭐ Opportunity Score: {loc['score']}<br>
                📍 Distance from Weesp: {distance_weesp} km<br>
                <hr style='margin:5px 0'>
                👥 Population (10km): {loc['population']:,}<br>
                🏫 Schools (10km): {loc['school_count']}<br>
                🦷 Dental clinics (10km): {loc['dental_count']}<br>
                🤓 Orthodontists (10km): {loc['ortho_count']}
            """
            
            # Draw the circle
            folium.Circle(
                location=[loc["latitude"], loc["longitude"]],
                radius=10000,
                color="darkgreen" if is_top else "black",
                fill=True,
                fill_color="lime" if is_top else "gold",
                fill_opacity=0.5 if is_top else 0.3,
                weight=2 if is_top else 1,
                popup=popup_text
            ).add_to(potential_group)
            
            # Add numbered marker at center
            folium.Marker(
                location=[loc["latitude"], loc["longitude"]],
                popup=popup_text,
                icon=folium.DivIcon(
                    html=f'<div style="font-size: 14px; font-weight: bold; color: white; background-color: {"#228B22" if is_top else "#B8860B"}; border-radius: 50%; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">{rank}</div>',
                    icon_size=(28, 28),
                    icon_anchor=(14, 14)
                )
            ).add_to(potential_group)
        
        potential_group.add_to(m)
    
    # Existing orthodontic clinics layer (added last to be on top)
    if show_clinics:
        clinics_group = folium.FeatureGroup(name="Existing Orthodontic Clinics")
        
        for clinic in clinics:
            name = clinic.get("name") or "No name"
            website = clinic.get("website") or "No Website"
            street = clinic.get("street", "")
            house_number = clinic.get("house_number", "")
            postal_code = clinic.get("postal_code", "")
            city = clinic.get("city", "")
            
            popup_text = f"""
                <b>{name}</b><br>
                {street} {house_number}<br>
                {postal_code} {city}<br>
                {website}
            """
            
            folium.Circle(
                location=[clinic["latitude"], clinic["longitude"]],
                radius=1000,
                color="red",
                fill=True,
                fill_color="red",
                fill_opacity=0.7,
                weight=2,
                popup=popup_text
            ).add_to(clinics_group)
        
        clinics_group.add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    return m

# Load pre-calculated data (fast!)
with st.spinner("Loading data..."):
    boundary_geojson, population_centers, clinics, dental_clinics, schools, potential_locations = load_data()

# Left Sidebar - Title and Controls (collapsible via Streamlit's built-in sidebar toggle)
st.sidebar.title("🏥 Clinic Location Finder")
st.sidebar.caption("Netherlands")
st.sidebar.markdown("---")

with st.sidebar.expander("🗺️ Map Controls", expanded=True):
    show_population = st.checkbox("Show Population Centers", value=True)
    show_clinics = st.checkbox("Show Orthodontic Clinics", value=True)
    show_dental = st.checkbox("Show Dental Clinics", value=True)
    show_schools = st.checkbox("Show Schools", value=False)
    show_potential = st.checkbox("Show Potential Locations", value=True)

with st.sidebar.expander("🔍 Filters", expanded=False):
    rent_range = st.slider(
        "Monthly Rent Range (€)",
        min_value=500,
        max_value=5000,
        value=(1000, 3000),
        step=100
    )
    eur_m2_range = st.slider(
        "Price per m² (€/m²)",
        min_value=10,
        max_value=50,
        value=(15, 35),
        step=1
    )

with st.sidebar.expander("📊 Statistics", expanded=False):
    col1, col2 = st.columns(2)
    col1.metric("Ortho", len(clinics))
    col2.metric("Dental", len(dental_clinics))
    col1.metric("Schools", len(schools))
    col2.metric("Potential", len(potential_locations))

# Session state for right panel visibility
if 'show_right_panel' not in st.session_state:
    st.session_state.show_right_panel = False

# Main layout with chevron toggle on right edge
if st.session_state.show_right_panel:
    map_col, list_col, chevron_col = st.columns([14, 5, 1])
else:
    map_col, chevron_col = st.columns([19, 1])
    list_col = None

with map_col:
    m = create_map(boundary_geojson, population_centers, clinics, dental_clinics, schools, potential_locations, show_population, show_clinics, show_dental, show_schools, show_potential)
    st_folium(m, width=None, height=700, use_container_width=True)

if st.session_state.show_right_panel and list_col:
    with list_col:
        st.markdown("### 🏆 Ranked Locations")
        st.markdown(f"*€{rent_range[0]}-{rent_range[1]}/mo*")
        st.markdown("---")
        
        for loc in potential_locations:
            rank = loc.get('rank', 0)
            score = loc.get('score', 0)
            distance = loc.get('distance_from_weesp', 0)
            population = loc.get('population', 0)
            
            badge_color = "#228B22" if rank <= 5 else "#B8860B"
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, {badge_color}22, {badge_color}11); 
                        border-left: 4px solid {badge_color}; 
                        padding: 8px; 
                        margin-bottom: 6px; 
                        border-radius: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 18px; font-weight: bold; color: {badge_color};">#{rank}</span>
                    <span style="font-size: 11px; color: #666;">⭐ {score}</span>
                </div>
                <div style="font-size: 11px; color: #444; margin-top: 3px;">
                    📍 {distance} km | 👥 {population:,}
                </div>
            </div>
            """, unsafe_allow_html=True)

# Chevron toggle on right edge
with chevron_col:
    chevron = "›" if not st.session_state.show_right_panel else "‹"
    if st.button(chevron, key="right_panel_toggle", help="Toggle ranked locations"):
        st.session_state.show_right_panel = not st.session_state.show_right_panel
        st.rerun()
