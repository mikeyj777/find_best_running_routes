# core/road_network.py
import requests
import networkx as nx
import logging
from utils.geo_utils import haversine_distance

class OSMConnector:
    """
    Connects to the Overpass API to fetch road network data.
    """
    def __init__(self):
        self.api_url = "https://overpass-api.de/api/interpreter"

    def get_road_network(self, bounding_box):
        """
        Fetches runnable roads and paths within a given bounding box.

        Args:
            bounding_box (tuple): A tuple of (south, west, north, east) coordinates.

        Returns:
            dict or None: The raw OSM data in JSON format, or None on failure.
        """
        bbox_str = f"{bounding_box[0]},{bounding_box[1]},{bounding_box[2]},{bounding_box[3]}"
        
        # This Overpass QL query looks for ways (roads/paths) suitable for running
        overpass_query = f"""
            [out:json];
            (
              way["highway"~"^(residential|tertiary|unclassified|path|track|footway)$"]({bbox_str});
            );
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

def build_road_graph(osm_data):
    """
    Builds a NetworkX graph from raw OSM data returned with 'out geom;'.

    Args:
        osm_data (dict): The JSON data from the Overpass API.

    Returns:
        networkx.Graph: A graph representing the road network.
    """
    graph = nx.Graph()
    
    if not osm_data or 'elements' not in osm_data:
        return graph

    # Iterate through all elements, which should be of type 'way'
    for element in osm_data['elements']:
        if element['type'] == 'way':
            node_ids = element.get('nodes', [])
            geometry = element.get('geometry', [])

            # The 'geometry' array contains the coordinates for the nodes in the 'nodes' array.
            # They should have the same length.
            if len(node_ids) != len(geometry):
                logging.warning(f"Skipping way {element['id']} due to mismatched nodes and geometry.")
                continue

            # Create an edge between each consecutive pair of nodes in the way
            for i in range(len(node_ids) - 1):
                node1_id = node_ids[i]
                node2_id = node_ids[i+1]
                
                node1_geom = geometry[i]
                node2_geom = geometry[i+1]

                # Ensure the geometry contains lat/lon data
                if 'lat' not in node1_geom or 'lon' not in node1_geom:
                    continue

                # Add/update node data in the graph
                graph.add_node(node1_id, lat=node1_geom['lat'], lon=node1_geom['lon'])
                graph.add_node(node2_id, lat=node2_geom['lat'], lon=node2_geom['lon'])
                
                # Calculate the distance (weight) for the edge
                distance = haversine_distance(
                    {'lat': node1_geom['lat'], 'lon': node1_geom['lon']},
                    {'lat': node2_geom['lat'], 'lon': node2_geom['lon']}
                )
                
                # Add the edge to the graph
                graph.add_edge(node1_id, node2_id, weight=distance)

    logging.info(f"Built road network graph with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges.")
    return graph

# --- Example Usage ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # Bounding box for our search area (south, west, north, east)
    test_bbox = (36.50, -82.55, 36.52, -82.52)
    
    # 1. Fetch the data
    connector = OSMConnector()
    data = connector.get_road_network(test_bbox)
    
    if data:
        # 2. Build the graph
        road_graph = build_road_graph(data)
        
        if road_graph.number_of_nodes() > 0:
            print("\nSuccessfully built the road graph!")
            first_node = list(road_graph.nodes)[0]
            print(f"Sample Node ID: {first_node}")
            print(f"Sample Node Data: {road_graph.nodes[first_node]}")
            print(f"Neighbors of this node: {list(road_graph.neighbors(first_node))}")