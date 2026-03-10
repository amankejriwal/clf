"""
Export the Clinic Finder map as a standalone HTML file.
No server needed - just open the HTML file in any browser.
"""
import json
import folium
from folium.plugins import Draw, Geocoder

# Load all data
print("Loading data...")
with open('data/netherlands_boundary.geojson') as f:
    boundary_geojson = json.load(f)

with open('nl_population.json') as f:
    population_centers = json.load(f)

with open('nl_ortho.json') as f:
    clinics = json.load(f)

with open('data/dental_clinics.json') as f:
    dental_clinics = json.load(f)

with open('data/schools.json') as f:
    schools = json.load(f)

with open('data/potential_locations.json') as f:
    potential_locations = json.load(f)

print(f"  Population centers: {len(population_centers)}")
print(f"  Orthodontic clinics: {len(clinics)}")
print(f"  Dental clinics: {len(dental_clinics)}")
print(f"  Schools: {len(schools)}")
print(f"  Potential locations: {len(potential_locations)}")

# Create the map
print("\nCreating map...")
m = folium.Map(location=[52.3676, 4.9041], zoom_start=8, tiles='OpenStreetMap')

# Add draw and search controls
Draw(export=True).add_to(m)
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
print("  Adding population centers...")
population_group = folium.FeatureGroup(name="Population Centers", show=True)
sub_ranges = [
    (500, 20000, '#FF9D00'),
    (20001, 40000, '#FECC5C'),
    (40001, 80000, '#FD8D3C'),
    (80000, 300000, '#FF6701'),
    (300000, 1000000, 'purple')
]
P_max, P_min = 741636, 500
r_max, r_min = 15, 2

for pc in population_centers:
    population = pc["population"]
    if population > 20000:
        radius = (r_min + (r_max - r_min) * (population - P_min) / (P_max - P_min)) * 1000
        circle_color = '#FF9D00'
        for lower, upper, color in sub_ranges:
            if lower <= population <= upper:
                circle_color = color
                break
        
        folium.Circle(
            location=[pc["latitude"], pc["longitude"]],
            radius=round(radius),
            color=circle_color,
            fill=True,
            fill_color=circle_color,
            fill_opacity=0.6,
            weight=1,
            popup=f"{pc.get('name', 'Unknown')} ({population:,})"
        ).add_to(population_group)

population_group.add_to(m)

# Dental clinics layer
print("  Adding dental clinics...")
dental_group = folium.FeatureGroup(name="Dental Clinics", show=True)
for clinic in dental_clinics:
    name = clinic.get("name") or "Dental Clinic"
    folium.Circle(
        location=[clinic["latitude"], clinic["longitude"]],
        radius=5000,
        color="#007FFF",
        fill=True,
        fill_color="#007FFF",
        fill_opacity=0.3,
        weight=2,
        popup=f"<b>{name}</b>"
    ).add_to(dental_group)
dental_group.add_to(m)

# Schools layer (hidden by default - too many)
print("  Adding schools...")
schools_group = folium.FeatureGroup(name="Schools", show=False)
for school in schools:
    name = school.get("name") or "School"
    folium.Circle(
        location=[school["latitude"], school["longitude"]],
        radius=5000,
        color="#90EE90",
        fill=True,
        fill_color="#90EE90",
        fill_opacity=0.3,
        weight=1,
        popup=f"<b>{name}</b>"
    ).add_to(schools_group)
schools_group.add_to(m)

# Potential locations layer
print("  Adding potential locations...")
potential_group = folium.FeatureGroup(name="Potential Locations", show=True)
for loc in potential_locations:
    rank = loc.get('rank', 0)
    score = loc.get('score', 0)
    distance_weesp = loc.get('distance_from_weesp', 0)
    population = loc.get('population', 0)
    is_top = rank <= 5
    
    popup_text = f"""
        <b>🏆 Rank #{rank}</b><br>
        <hr style='margin:5px 0'>
        ⭐ Opportunity Score: {score}<br>
        📍 Distance from Weesp: {distance_weesp} km<br>
        <hr style='margin:5px 0'>
        👥 Population (10km): {population:,}<br>
        🏫 Schools (10km): {loc.get('school_count', 0)}<br>
        🦷 Dental clinics (10km): {loc.get('dental_count', 0)}<br>
        🤓 Orthodontists (10km): {loc.get('ortho_count', 0)}
    """
    
    # Draw circle
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
    
    # Add rank marker
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

# Orthodontic clinics layer (on top)
print("  Adding orthodontic clinics...")
clinics_group = folium.FeatureGroup(name="Orthodontic Clinics", show=True)
for clinic in clinics:
    name = clinic.get("name") or "No name"
    website = clinic.get("website") or ""
    street = clinic.get("street", "")
    city = clinic.get("city", "")
    
    popup_text = f"<b>{name}</b><br>{street}<br>{city}"
    if website:
        popup_text += f"<br><a href='{website}' target='_blank'>Website</a>"
    
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

# Build ranked locations panel HTML
locations_html = ""
for loc in potential_locations:
    rank = loc.get('rank', 0)
    score = loc.get('score', 0)
    distance = loc.get('distance_from_weesp', 0)
    population = loc.get('population', 0)
    badge_color = "#228B22" if rank <= 5 else "#B8860B"
    locations_html += f"""
    <div style="background: linear-gradient(135deg, {badge_color}22, {badge_color}11); 
                border-left: 4px solid {badge_color}; 
                padding: 8px; 
                margin-bottom: 6px; 
                border-radius: 4px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 16px; font-weight: bold; color: {badge_color};">#{rank}</span>
            <span style="font-size: 11px; color: #666;">⭐ {score}</span>
        </div>
        <div style="font-size: 11px; color: #444; margin-top: 3px;">
            📍 {distance} km | 👥 {population:,}
        </div>
    </div>
    """

# Custom HTML with sidebars
custom_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>🏥 Clinic Location Finder - Netherlands</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ margin: 0; padding: 0; }}
        #map {{ position: absolute; top: 0; left: 0; right: 0; bottom: 0; }}
        
        /* Left sidebar */
        .left-sidebar {{
            position: fixed;
            top: 0;
            left: 0;
            width: 280px;
            height: 100vh;
            background: #f8f9fa;
            border-right: 1px solid #ddd;
            padding: 1rem;
            overflow-y: auto;
            transform: translateX(-100%);
            transition: transform 0.3s ease;
            z-index: 1000;
            box-sizing: border-box;
        }}
        .left-sidebar.open {{ transform: translateX(0); }}
        
        .left-chevron {{
            position: fixed;
            top: 50%;
            left: 0;
            transform: translateY(-50%);
            width: 24px;
            height: 60px;
            background: #f8f9fa;
            border: 1px solid #ddd;
            border-left: none;
            border-radius: 0 8px 8px 0;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            color: #666;
            z-index: 1001;
            transition: left 0.3s ease;
        }}
        .left-chevron:hover {{ background: #e9ecef; }}
        .left-chevron.open {{ left: 280px; }}
        
        /* Right sidebar */
        .right-sidebar {{
            position: fixed;
            top: 0;
            right: 0;
            width: 280px;
            height: 100vh;
            background: #f8f9fa;
            border-left: 1px solid #ddd;
            padding: 1rem;
            overflow-y: auto;
            transform: translateX(100%);
            transition: transform 0.3s ease;
            z-index: 1000;
            box-sizing: border-box;
        }}
        .right-sidebar.open {{ transform: translateX(0); }}
        
        .right-chevron {{
            position: fixed;
            top: 50%;
            right: 0;
            transform: translateY(-50%);
            width: 24px;
            height: 60px;
            background: #f8f9fa;
            border: 1px solid #ddd;
            border-right: none;
            border-radius: 8px 0 0 8px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            color: #666;
            z-index: 1001;
            transition: right 0.3s ease;
        }}
        .right-chevron:hover {{ background: #e9ecef; }}
        .right-chevron.open {{ right: 280px; }}
        
        h2 {{ margin-top: 0; font-size: 18px; }}
        h3 {{ margin-top: 0; font-size: 16px; }}
        hr {{ border: none; border-top: 1px solid #ddd; margin: 10px 0; }}
        
        .legend-item {{ display: flex; align-items: center; margin: 5px 0; font-size: 13px; }}
        .legend-dot {{ width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }}
    </style>
</head>
<body>
    <!-- Left Sidebar -->
    <div id="left-chevron" class="left-chevron" onclick="toggleLeft()">›</div>
    <div id="left-sidebar" class="left-sidebar">
        <h2>🏥 Clinic Location Finder</h2>
        <p style="color: #666; margin-top: -10px;">Netherlands</p>
        <hr>
        <h3>🎨 Legend</h3>
        <p><b>Population Centers:</b></p>
        <div class="legend-item"><div class="legend-dot" style="background: #FF9D00;"></div> 500 - 20,000</div>
        <div class="legend-item"><div class="legend-dot" style="background: #FECC5C;"></div> 20,001 - 40,000</div>
        <div class="legend-item"><div class="legend-dot" style="background: #FD8D3C;"></div> 40,001 - 80,000</div>
        <div class="legend-item"><div class="legend-dot" style="background: #FF6701;"></div> 80,000 - 300,000</div>
        <div class="legend-item"><div class="legend-dot" style="background: purple;"></div> 300,000+</div>
        <hr>
        <p><b>Clinics:</b></p>
        <div class="legend-item"><div class="legend-dot" style="background: red;"></div> Orthodontic (1km)</div>
        <div class="legend-item"><div class="legend-dot" style="background: #007FFF;"></div> Dental (5km)</div>
        <hr>
        <p><b>Other:</b></p>
        <div class="legend-item"><div class="legend-dot" style="background: #90EE90;"></div> Schools (5km)</div>
        <div class="legend-item"><div class="legend-dot" style="background: lime;"></div> Top 5 Potential</div>
        <div class="legend-item"><div class="legend-dot" style="background: gold;"></div> Other Potential</div>
        <hr>
        <p><b>Ranking Formula:</b></p>
        <p style="font-size: 12px; color: #666;">70% Opportunity + 30% Proximity to Weesp</p>
        <p style="font-size: 11px; color: #888;">Score = (Pop/10k) + (Schools×2) + (Dental×1) - (Ortho×20)</p>
    </div>
    
    <!-- Right Sidebar -->
    <div id="right-chevron" class="right-chevron" onclick="toggleRight()">‹</div>
    <div id="right-sidebar" class="right-sidebar">
        <h3>🏆 Ranked Locations</h3>
        <hr>
        {locations_html}
    </div>
    
    <script>
        function toggleLeft() {{
            document.getElementById('left-sidebar').classList.toggle('open');
            document.getElementById('left-chevron').classList.toggle('open');
            const chevron = document.getElementById('left-chevron');
            chevron.innerHTML = chevron.classList.contains('open') ? '‹' : '›';
        }}
        function toggleRight() {{
            document.getElementById('right-sidebar').classList.toggle('open');
            document.getElementById('right-chevron').classList.toggle('open');
            const chevron = document.getElementById('right-chevron');
            chevron.innerHTML = chevron.classList.contains('open') ? '›' : '‹';
        }}
    </script>
</body>
</html>
"""

# Save the map
print("\nSaving HTML file...")
map_html = m._repr_html_()

# Inject our custom sidebars into the map HTML
# Find the </body> tag and insert our custom HTML before it
final_html = map_html.replace('</head>', custom_html.split('<body>')[0].split('<head>')[1] + '</head>')
final_html = final_html.replace('<body>', '<body>' + custom_html.split('<body>')[1].split('</body>')[0])

# Save
with open('clinic_finder.html', 'w') as f:
    f.write(final_html)

print("✅ Exported to clinic_finder.html")
print("\nJust open this file in any browser - no server needed!")
