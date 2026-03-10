from flask import Flask, render_template, request
from waitress import serve
import ee
import geemap
import json
import os
import requests
import geopandas as gpd
import numpy as np
from shapely.geometry import Point, Polygon
from geemap import geojson_to_ee, ee_to_geojson
from ipywidgets import HTML, widgets,interact,AppLayout,Layout, VBox, HBox
from ipyleaflet import DrawControl, GeoJSON, Marker, MarkerCluster, basemaps, basemap_to_tiles, CircleMarker, Circle, LayerGroup, AwesomeIcon, Icon, Popup, ZoomControl, LayersControl, SearchControl, LegendControl
import pandas as pd
import urllib.request, json 
from shapely import union_all
from pyproj import Transformer
from geopy.distance import geodesic

app = Flask(__name__)

@app.route('/')
def mapme():
    return render_template('map.html')

@app.route('/config')
def hello_world():
    os.environ["GOOGLE_MAPS_API_KEY"] = "AIzaSyCE1lhWE9-YtSUnrUANqClgtI4uyfZAM48"
    Map = geemap.Map(attribution_ctrl=False, scale_ctrl=False, layer_ctrl=False, search_ctrl=False, data_ctrl=False, toolbar_ctrl=False, draw_ctrl=False, zoom_ctrl=False, zoom=5)
    Map.zoom_control = False
    Map.setCenter(4.9041, 52.3676, 8)
    Map.add(ZoomControl(position='bottomright'))
    #Map.add(LayersControl(position='bottomleft'))

    def on_drag(event=None, **kwargs):
        circle = Circle(location=(marker.location), radius=10000, color="blue", fill_color="blue")   
        Map.add_layer(circle)
        print(f"Marker dragged to new location: {marker.location}")

    marker = Marker(icon=AwesomeIcon(name="check", marker_color='green', icon_color='darkgreen'), draggable=True)
    marker.observe(on_drag, names='location')
    Map.add(SearchControl(
      position="topleft",
      url='https://nominatim.openstreetmap.org/search?format=json&q={s}',
      zoom=9,
      marker=marker
    ))

    draw_control = DrawControl(position="bottomleft")
    draw_control.polyline =  {
        "shapeOptions": {
            "color": "#6bc2e5",
            "weight": 8,
            "opacity": 1.0
        }
    }
    draw_control.polygon = {
        "shapeOptions": {
            "fillColor": "#6be5c3",
            "color": "#6be5c3",
            "fillOpacity": 1.0
        },
        "drawError": {
            "color": "#dd253b",
            "message": "Oups!"
        },
        "allowIntersection": False
    }
    draw_control.circle = {
        "shapeOptions": {
            "fillColor": "#efed69",
            "color": "#efed69",
            "fillOpacity": 1.0
        }
    }
    draw_control.rectangle = {
        "shapeOptions": {
            "fillColor": "#fca45d",
            "color": "#fca45d",
            "fillOpacity": 1.0
        }
    }

    Map.add(draw_control)

    #dataset = ee.FeatureCollection('WM/geoLab/geoBoundaries/600/ADM2');
    world = ee.FeatureCollection("users/geonextgis/World_Administrative_Boundaries")

    world_style = {
        "fillColor": "00000000", # transparent color code
        "color": "black", # color of the stroke
        "width": 1 # stroke width
    }
    Map.addLayer(world.style(**world_style), {}, "World_Administrative_Boundaries")

    legend = LegendControl({"low":"#FAA", "medium":"#A55", "High":"#500"}, title="Legend", position="bottomleft")
    Map.add(legend)
    # Set/Get legend title
    legend.title = "Legend"  # Set title

    # Set/Get legend content
    legend.legend = {"Population Center":"#FAA", "Existing Ortho":"#A55", "POI":"#500"}  # Set content

    legend.add_legend_element("el5","#000")  # Add a legend element
    legend.remove_legend_element("el5")  # Remove a legend element

    markers = []
    layer_group = LayerGroup(name="Clinic Location Research")

    gdf = gpd.read_file('netherlands_Netherlands_Country_Boundary.shp')
    minx, miny, maxx, maxy = gdf.total_bounds
    x_coords = np.linspace(minx, maxx, num=20)  # Adjust num for resolution
    y_coords = np.linspace(miny, maxy, num=20)
    grid_points = [Point(x, y) for x in x_coords for y in y_coords]
    country_polygon = gdf.unary_union
    valid_points = [point for point in grid_points if point.within(country_polygon)]
    pois = []
    transformer = Transformer.from_crs("EPSG:3035", "EPSG:4326")
    for point in valid_points:
        pois.append({'latitude': point.y, 'longitude': point.x})

    with open('nl_population.json') as nlp:
        population_centers = json.load(nlp)

    with open('nl_ortho.json') as nlor:
        clinics = json.load(nlor)

    for poi in pois:
        nearby_points = []
        nearby_orthos = []
        for population_center in population_centers:
            target_point = (population_center["latitude"], population_center["longitude"])
            point = (poi["latitude"], poi["longitude"])
            distance = geodesic(target_point, point).kilometers
            if distance <= 10:
                nearby_points.append(population_center["population"])
        if len(nearby_points) >= 1:
            total_sum = sum(nearby_points)
            if total_sum >= 80000:
                for clinic in clinics:
                    target_point = (clinic["latitude"], clinic["longitude"])
                    distance = geodesic(target_point, point).kilometers
                    if distance <= 10:
                        nearby_orthos.append("found")
                if len(nearby_orthos) < 2:        
                    circle = Circle(location=(poi["latitude"], poi["longitude"]), radius=10000, color="black", fill_color="gold")
                    mark_title = '('+str(poi["latitude"])+', '+str(poi["longitude"])+', '+str(total_sum)+')'
                    circle.weight = 1
                    circle.popup = HTML(value=mark_title)
                    layer_group.add_layer(circle)


    with open('nl_population.json') as nlp:
        population_centers = json.load(nlp)
        P_max = 741636
        P_min = 500
        r_max = 15
        r_min = 2
        # Define the custom sub-ranges and corresponding colors
        sub_ranges = [
            (500, 20000, '#FF9D00'),   # Light Yellow
            (20001, 40000, '#FECC5C'),  # Light Orange
            (40001, 80000, '#FD8D3C'), # Medium Orange
            (80000, 300000, '#FF6701'),# Dark Orange
            (300000, 741636, 'purple')# Red
        ]
        for population_center in population_centers:
            population = population_center["population"]
            mark_title = population_center["name"]+' ('+str(population)+')'
            radius = (r_min + (r_max - r_min) * (population - P_min) / (P_max - P_min))*1000
            for lower, upper, color in sub_ranges:
                if lower <= population <= upper:
                    circle_color = color
            if population > 20000:
                circle = Circle(location=(population_center["latitude"], population_center["longitude"]),                                         radius=round(radius), color=circle_color, fill_color=circle_color)
                circle.popup = HTML(value=mark_title)
                circle.weight = 1
                layer_group.add_layer(circle)


    with open('nl_ortho.json') as nlor:
        clinics = json.load(nlor)
        for clinic in clinics:
            mark_title = clinic["name"]
            if not mark_title:
                mark_title = "No name"
            if clinic["website"]:    
                website = clinic["website"]
            else:
                website = "No Website"     
            popup_text = '<b>'+mark_title+'</b><br>'+clinic["street"]+' '+clinic["house_number"]+'<br>'+clinic["postal_code"]+' '+clinic["city"]+'<br>'+website
            circle = Circle(location=(clinic["latitude"], clinic["longitude"]), radius=1000, color="red", fill_color="red")       
            circle.popup = HTML(value=popup_text)
            circle.weight = 2
            layer_group.add_layer(circle)
    
    Map.add(layer_group)
    Map
    Map.save('templates/map.html')
    return render_template('map.html')
    
if __name__ == "__main__":
    serve(app, host='0.0.0.0', port=8080)
