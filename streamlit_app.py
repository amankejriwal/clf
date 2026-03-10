import streamlit as st
import json
import folium
from folium.plugins import Draw, Geocoder
from streamlit_folium import st_folium

st.set_page_config(page_title="Clinic Finder", layout="wide")
st.title("🏥 Clinic Location Finder - Netherlands")

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

# Sidebar controls
st.sidebar.header("🗺️ Map Controls")

show_population = st.sidebar.checkbox("Show Population Centers", value=True)
show_clinics = st.sidebar.checkbox("Show Orthodontic Clinics", value=True)
show_dental = st.sidebar.checkbox("Show Dental Clinics", value=True)
show_schools = st.sidebar.checkbox("Show Schools", value=False)
show_potential = st.sidebar.checkbox("Show Potential Locations", value=True)

st.sidebar.markdown("---")
st.sidebar.header("📊 Statistics")
st.sidebar.metric("Population Centers", len([p for p in population_centers if p["population"] > 20000]))
st.sidebar.metric("Orthodontic Clinics", len(clinics))
st.sidebar.metric("Dental Clinics", len(dental_clinics))
st.sidebar.metric("Schools", len(schools))
st.sidebar.metric("Potential Locations", len(potential_locations))

st.sidebar.markdown("---")
st.sidebar.header("🎨 Legend")
st.sidebar.markdown("""
**Population Centers:**
- 🟠 Light Orange: 500 - 20,000
- 🟠 Orange: 20,001 - 40,000
- 🟠 Dark Orange: 40,001 - 80,000
- 🟠 Darker Orange: 80,000 - 300,000
- 🟣 Purple: 300,000+

**Clinics:**
- 🔴 Red: Existing orthodontic clinics
- 🔵 Azure Blue: Dental clinics (5km radius)

**Schools:**
- 🟢 Light Green: Primary & secondary schools (5km radius)

**Potential Locations (Ranked):**
- 🟢 Lime (#1-5): Top ranked locations
- 🟡 Gold (#6+): Other good locations

**Ranking Formula:**
`70% Opportunity Score + 30% Proximity to Weesp`

**Opportunity Score:**
`(Pop/10k) + (Schools×2) + (Dental×1) - (Ortho×20)`
""")

# Create and display map
m = create_map(boundary_geojson, population_centers, clinics, dental_clinics, schools, potential_locations, show_population, show_clinics, show_dental, show_schools, show_potential)

st_folium(m, width=None, height=600, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("*Clinic Finder - Identifying underserved areas for new orthodontic clinics in the Netherlands*")
