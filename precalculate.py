"""
Pre-calculate all data for the Clinic Finder app.
Run this script whenever the source data changes.
"""
import json
import geopandas as gpd
import numpy as np
from shapely.geometry import Point
from geopy.distance import geodesic
import time

def load_source_data():
    """Load all source data files"""
    print("Loading source data...")
    
    gdf = gpd.read_file('netherlands_Netherlands_Country_Boundary.shp')
    
    with open('nl_population.json') as f:
        population_centers = json.load(f)
    
    with open('nl_ortho.json') as f:
        clinics = json.load(f)
    
    # Load dental clinics
    dental_clinics = []
    with open('nl_dental.json') as f:
        dental_data = json.load(f)
        for element in dental_data.get('elements', []):
            lat = element.get('lat') or element.get('center', {}).get('lat')
            lon = element.get('lon') or element.get('center', {}).get('lon')
            if lat and lon:
                tags = element.get('tags', {})
                dental_clinics.append({
                    'latitude': lat,
                    'longitude': lon,
                    'name': tags.get('name', 'Dental Clinic'),
                    'address': f"{tags.get('addr:street', '')} {tags.get('addr:housenumber', '')}".strip(),
                    'city': tags.get('addr:city', ''),
                    'postcode': tags.get('addr:postcode', ''),
                    'phone': tags.get('contact:phone', tags.get('phone', '')),
                    'website': tags.get('contact:website', tags.get('website', ''))
                })
    
    # Load schools
    schools = []
    with open('nl_schools.json') as f:
        schools_data = json.load(f)
        for element in schools_data.get('elements', []):
            lat = element.get('lat') or element.get('center', {}).get('lat')
            lon = element.get('lon') or element.get('center', {}).get('lon')
            if lat and lon:
                tags = element.get('tags', {})
                schools.append({
                    'latitude': lat,
                    'longitude': lon,
                    'name': tags.get('name', 'School'),
                    'address': f"{tags.get('addr:street', '')} {tags.get('addr:housenumber', '')}".strip(),
                    'city': tags.get('addr:city', ''),
                    'postcode': tags.get('addr:postcode', '')
                })
    
    print(f"  Population centers: {len(population_centers)}")
    print(f"  Orthodontic clinics: {len(clinics)}")
    print(f"  Dental clinics: {len(dental_clinics)}")
    print(f"  Schools: {len(schools)}")
    
    return gdf, population_centers, clinics, dental_clinics, schools

def calculate_potential_locations(gdf, population_centers, clinics, dental_clinics, schools):
    """
    Calculate potential clinic locations using weighted scoring.
    
    Score = (Population / 10,000) + (Schools × 2) + (Dental clinics × 1) - (Orthodontic clinics × 20)
    """
    print("\nCalculating potential locations...")
    start_time = time.time()
    
    minx, miny, maxx, maxy = gdf.total_bounds
    x_coords = np.linspace(minx, maxx, num=25)
    y_coords = np.linspace(miny, maxy, num=25)
    grid_points = [Point(x, y) for x in x_coords for y in y_coords]
    country_polygon = gdf.unary_union
    valid_points = [point for point in grid_points if point.within(country_polygon)]
    
    print(f"  Grid points to analyze: {len(valid_points)}")
    
    pois = [{'latitude': point.y, 'longitude': point.x} for point in valid_points]
    
    potential_locations = []
    for i, poi in enumerate(pois):
        if (i + 1) % 50 == 0:
            print(f"  Processing point {i + 1}/{len(pois)}...")
        
        point = (poi["latitude"], poi["longitude"])
        
        # Count population within 10km
        total_population = 0
        for pc in population_centers:
            target_point = (pc["latitude"], pc["longitude"])
            distance = geodesic(target_point, point).kilometers
            if distance <= 10:
                total_population += pc["population"]
        
        # Count orthodontic clinics within 10km
        ortho_count = 0
        for clinic in clinics:
            target_point = (clinic["latitude"], clinic["longitude"])
            distance = geodesic(target_point, point).kilometers
            if distance <= 10:
                ortho_count += 1
        
        # Count dental clinics within 10km
        dental_count = 0
        for dental in dental_clinics:
            target_point = (dental["latitude"], dental["longitude"])
            distance = geodesic(target_point, point).kilometers
            if distance <= 10:
                dental_count += 1
        
        # Count schools within 10km
        school_count = 0
        for school in schools:
            target_point = (school["latitude"], school["longitude"])
            distance = geodesic(target_point, point).kilometers
            if distance <= 10:
                school_count += 1
        
        # Check if potential location's 10km circle would overlap with any ortho clinic's 1km circle
        # This means the center must be at least 11km away from any ortho clinic
        in_ortho_exclusion_zone = False
        for clinic in clinics:
            target_point = (clinic["latitude"], clinic["longitude"])
            distance = geodesic(target_point, point).kilometers
            if distance <= 11:  # 10km (potential circle) + 1km (ortho circle) = 11km minimum distance
                in_ortho_exclusion_zone = True
                break
        
        # Calculate weighted score
        score = (total_population / 10000) + (school_count * 2) + (dental_count * 1) - (ortho_count * 20)
        
        # Stricter thresholds: Score > 50, fewer than 3 orthodontists, minimum population, NOT in exclusion zone
        if score > 50 and ortho_count < 3 and total_population >= 50000 and not in_ortho_exclusion_zone:
            potential_locations.append({
                'latitude': poi["latitude"],
                'longitude': poi["longitude"],
                'population': total_population,
                'ortho_count': ortho_count,
                'dental_count': dental_count,
                'school_count': school_count,
                'score': round(score, 1)
            })
    
    # Sort by score descending
    potential_locations.sort(key=lambda x: x['score'], reverse=True)
    
    elapsed = time.time() - start_time
    print(f"  Found {len(potential_locations)} potential locations in {elapsed:.1f}s")
    
    return potential_locations

def save_precalculated_data(dental_clinics, schools, potential_locations):
    """Save all pre-calculated data to JSON files"""
    print("\nSaving pre-calculated data...")
    
    # Save processed dental clinics
    with open('data/dental_clinics.json', 'w') as f:
        json.dump(dental_clinics, f)
    print(f"  Saved data/dental_clinics.json ({len(dental_clinics)} records)")
    
    # Save processed schools
    with open('data/schools.json', 'w') as f:
        json.dump(schools, f)
    print(f"  Saved data/schools.json ({len(schools)} records)")
    
    # Save potential locations
    with open('data/potential_locations.json', 'w') as f:
        json.dump(potential_locations, f)
    print(f"  Saved data/potential_locations.json ({len(potential_locations)} records)")
    
    print("\nPre-calculation complete!")

if __name__ == "__main__":
    import os
    
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Load source data
    gdf, population_centers, clinics, dental_clinics, schools = load_source_data()
    
    # Calculate potential locations
    potential_locations = calculate_potential_locations(
        gdf, population_centers, clinics, dental_clinics, schools
    )
    
    # Save everything
    save_precalculated_data(dental_clinics, schools, potential_locations)
