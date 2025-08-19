import logging

from core.road_network import OSMConnector, build_road_graph

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # Bounding box for our search area (south, west, north, east)
    # A small box around the default origin point for a quick test
    test_bbox = (36.50, -82.55, 36.52, -82.52)
    
    # 1. Fetch the data
    connector = OSMConnector()
    data = connector.get_road_network(test_bbox)
    
    if data:
        # 2. Build the graph
        road_graph = build_road_graph(data)
        
        if road_graph.number_of_nodes() > 0:
            print("\nSuccessfully built the road graph!")
            # Example: Find the neighbors of the first node in the graph
            first_node = list(road_graph.nodes)[0]
            print(f"Sample Node ID: {first_node}")
            print(f"Sample Node Data: {road_graph.nodes[first_node]}")
            print(f"Neighbors of this node: {list(road_graph.neighbors(first_node))}")