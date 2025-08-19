# core/data_pipeline.py
import logging
from core.road_network import OSMConnector, build_road_graph
from core.data_fetcher import ElevationConnector
from utils.geo_utils import get_bounding_box

def prepare_data_for_pathfinding(search_params):
    """
    Orchestrates the entire data preparation process.
    """
    # Step 1: Define Bounding Box
    origin = search_params.get('origin', {'lat': 36.51, 'lng': -82.53})
    search_radius_miles = search_params.get('searchRadius', 5)
    path_distance_miles = search_params.get('pathDistance', 1)

    # *** NEW: Calculate the total radius for the data fetch area ***
    total_fetch_radius = search_radius_miles + path_distance_miles
    
    bbox = get_bounding_box(origin['lat'], origin['lng'], total_fetch_radius)

    # ... (The rest of the function remains the same) ...
    
    # Step 2: Fetch Road Network
    osm_connector = OSMConnector()
    osm_data = osm_connector.get_road_network(bbox)
    if not osm_data: return None

    # Step 3: Build High-Resolution Graph
    road_graph = build_road_graph(osm_data)
    if road_graph.number_of_nodes() == 0: return None
    
    # Step 4: Fetch Elevation Data
    all_nodes = list(road_graph.nodes(data=True))
    coordinates_to_fetch = [
        {'latitude': data['lat'], 'longitude': data['lon']}
        for _, data in all_nodes
    ]
    
    elevation_connector = ElevationConnector()
    elevation_results = elevation_connector.fetch_elevation_for_coords(coordinates_to_fetch)
    if not elevation_results: return None

    elevation_map = {
        (round(res['latitude'], 6), round(res['longitude'], 6)): res['elevation']
        for res in elevation_results
    }

    # Step 5: Enrich the Graph
    nodes_to_remove = []
    for node_id, data in all_nodes:
        lat, lon = round(data['lat'], 6), round(data['lon'], 6)
        elevation = elevation_map.get((lat, lon))
        if elevation is not None:
            road_graph.nodes[node_id]['elevation'] = elevation
        else:
            logging.warning(f"Node {node_id} missing elevation data. Marking for removal.")
            nodes_to_remove.append(node_id)
            
    road_graph.remove_nodes_from(nodes_to_remove)
            
    logging.info(f"Successfully enriched graph. Final node count: {road_graph.number_of_nodes()}")
    return road_graph