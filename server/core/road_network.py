# core/road_network.py
import requests
import networkx as nx
import logging
from utils.geo_utils import haversine_distance, interpolate_point

class OSMConnector:
    # ... (no changes to this class) ...
    def __init__(self):
        self.api_url = "https://overpass-api.de/api/interpreter"

    def get_road_network(self, bounding_box):
        bbox_str = f"{bounding_box[0]},{bounding_box[1]},{bounding_box[2]},{bounding_box[3]}"
        overpass_query = f"""
            [out:json];
            (way["highway"~"^(residential|tertiary|unclassified|path|track|footway)$"]({bbox_str}););
            out geom;
        """
        try:
            logging.info("Querying Overpass API for road network...")
            response = requests.post(self.api_url, data={'data': overpass_query})
            response.raise_for_status()
            logging.info("Successfully fetched road network data.")
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to fetch OSM data: {e}")
            return None

def build_road_graph(osm_data, subdivision_distance_miles=0.031): # Approx 50 meters
    """
    Builds a high-resolution NetworkX graph from raw OSM data, subdividing long segments.
    """
    graph = nx.Graph()
    if not osm_data or 'elements' not in osm_data:
        return graph

    # Use a high starting number for new node IDs to avoid collision with existing OSM IDs
    node_counter = 1_000_000_000 

    for element in osm_data['elements']:
        if element['type'] == 'way':
            node_ids = element.get('nodes', [])
            geometry = element.get('geometry', [])

            if len(node_ids) != len(geometry):
                continue

            for i in range(len(node_ids) - 1):
                node1_id, node2_id = node_ids[i], node_ids[i+1]
                node1_geom, node2_geom = geometry[i], geometry[i+1]

                if 'lat' not in node1_geom or 'lon' not in node1_geom:
                    continue

                graph.add_node(node1_id, lat=node1_geom['lat'], lon=node1_geom['lon'])
                
                segment_distance = haversine_distance(node1_geom, node2_geom)

                if segment_distance > subdivision_distance_miles:
                    # This segment is too long, so we subdivide it
                    num_subdivisions = int(segment_distance / subdivision_distance_miles)
                    last_node_in_segment = node1_id
                    
                    for j in range(1, num_subdivisions + 1):
                        fraction = j / (num_subdivisions + 1)
                        interp_point = interpolate_point(node1_geom, node2_geom, fraction)
                        
                        new_node_id = node_counter
                        graph.add_node(new_node_id, lat=interp_point['lat'], lon=interp_point['lon'])
                        
                        sub_segment_dist = haversine_distance(graph.nodes[last_node_in_segment], graph.nodes[new_node_id])
                        graph.add_edge(last_node_in_segment, new_node_id, weight=sub_segment_dist)
                        
                        last_node_in_segment = new_node_id
                        node_counter += 1
                    
                    # Connect the last new node to the original end node
                    graph.add_node(node2_id, lat=node2_geom['lat'], lon=node2_geom['lon'])
                    final_sub_segment_dist = haversine_distance(graph.nodes[last_node_in_segment], graph.nodes[node2_id])
                    graph.add_edge(last_node_in_segment, node2_id, weight=final_sub_segment_dist)
                else:
                    # Segment is short enough, add it directly
                    graph.add_node(node2_id, lat=node2_geom['lat'], lon=node2_geom['lon'])
                    graph.add_edge(node1_id, node2_id, weight=segment_distance)

    logging.info(f"Built high-resolution graph with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges.")
    return graph