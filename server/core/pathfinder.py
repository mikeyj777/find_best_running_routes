# core/pathfinder.py
import logging
import random
from utils.geo_utils import haversine_distance

class PathfindingEngine:
    """
    The core engine for finding routes that meet specific criteria.
    It traverses a road network graph where each node has elevation data.
    """
    def __init__(self, graph, search_params):
        """
        Initializes the PathfindingEngine.

        Args:
            graph (networkx.Graph): The road network graph, with elevation data on each node.
            search_params (dict): A dictionary of user-defined search criteria.
        """
        self.graph = graph
        self.params = search_params
        self.found_routes = []
        # Convert distances to miles for internal calculations
        self.target_distance = self.params.get('pathDistance', 1.0)
        self.max_routes_to_find = 10 # Stop after finding a reasonable number of routes

    def find_routes(self):
        """
        The main public method to start the route-finding process.
        """
        logging.info("Starting pathfinding process...")
        if not self.graph or self.graph.number_of_nodes() == 0:
            logging.warning("Graph is empty. Cannot find routes.")
            return []

        # Find potential starting nodes within the search radius
        # For now, we'll just pick some random nodes to start from
        all_nodes = list(self.graph.nodes(data=True))
        starting_nodes = random.sample(all_nodes, k=min(100, len(all_nodes)))

        for start_node_id, _ in starting_nodes:
            if len(self.found_routes) >= self.max_routes_to_find:
                break # Stop searching if we have enough routes
            
            # Start the traversal from each starting node
            self._traverse(path=[start_node_id], current_distance=0.0)
        
        logging.info(f"Pathfinding complete. Found {len(self.found_routes)} routes.")
        return self._format_routes()

    def _traverse(self, path, current_distance):
        """
        The core recursive traversal function (a modified Depth-First Search).
        """
        if len(self.found_routes) >= self.max_routes_to_find:
            return

        last_node_id = path[-1]
        
        # Get all neighbors of the last node in the path
        neighbors = list(self.graph.neighbors(last_node_id))
        random.shuffle(neighbors) # Randomize to explore different directions

        for neighbor_id in neighbors:
            if neighbor_id in path:
                continue # Avoid simple loops

            segment_distance = self.graph[last_node_id][neighbor_id]['weight']
            new_distance = current_distance + segment_distance
            
            # Create the new potential path
            new_path = path + [neighbor_id]

            # Check if the new path is valid based on incline tolerances
            is_valid, _ = self._is_path_valid(new_path)

            if is_valid:
                if new_distance >= self.target_distance:
                    # Success! We've found a path of the required length
                    self.found_routes.append(new_path)
                    if len(self.found_routes) >= self.max_routes_to_find:
                        return
                else:
                    # The path is still valid but not long enough, so continue traversing
                    self._traverse(path=new_path, current_distance=new_distance)

    def _is_path_valid(self, path):
        """
        Checks if a given path meets the overall and local incline tolerances.
        """
        total_distance = 0
        out_of_tolerance_distance = 0
        
        # Tolerances from search params
        optimal_incline = self.params.get('optimalIncline', 2.0)
        overall_tolerance_percent = self.params.get('overallTolerance', 0.10)
        local_tolerance_fraction = self.params.get('localTolerance', 0.01)

        # Calculate the acceptable incline ranges
        min_overall_incline = optimal_incline * (1 - overall_tolerance_percent)
        max_overall_incline = optimal_incline * (1 + overall_tolerance_percent)
        
        for i in range(len(path) - 1):
            node1_id = path[i]
            node2_id = path[i+1]

            node1_data = self.graph.nodes[node1_id]
            node2_data = self.graph.nodes[node2_id]

            # Ensure nodes have elevation data
            if 'elevation' not in node1_data or 'elevation' not in node2_data:
                return False, "Missing elevation data"

            rise_m = node2_data['elevation'] - node1_data['elevation']
            run_m = self.graph[node1_id][node2_id]['weight'] * 1609.34 # convert miles to meters
            
            if run_m == 0: continue

            segment_incline = (rise_m / run_m) * 100
            total_distance += run_m / 1609.34 # Add distance in miles

            # Check Local Tolerance
            if not (min_overall_incline <= segment_incline <= max_overall_incline):
                out_of_tolerance_distance += run_m / 1609.34

        # Final check of overall path incline
        start_node_elev = self.graph.nodes[path[0]]['elevation']
        end_node_elev = self.graph.nodes[path[-1]]['elevation']
        total_rise_m = end_node_elev - start_node_elev
        total_run_m = total_distance * 1609.34
        
        if total_run_m == 0: return True, "Path is valid" # Path has no length yet

        overall_incline = (total_rise_m / total_run_m) * 100
        
        # Pruning Logic: Abandon if it violates BOTH tolerances
        max_allowed_oot_distance = self.target_distance * local_tolerance_fraction
        overall_incline_is_bad = not (min_overall_incline <= overall_incline <= max_overall_incline)
        local_tolerance_is_bad = out_of_tolerance_distance > max_allowed_oot_distance

        if local_tolerance_is_bad and overall_incline_is_bad:
            return False, "Violates both local and overall tolerances"

        return True, "Path is valid"

    def _format_routes(self):
        """
        Converts the found paths (lists of node IDs) into the format
        expected by the frontend (lists of coordinate dictionaries).
        """
        formatted_routes = []
        for i, path in enumerate(self.found_routes):
            route_coords = [
                {'lat': self.graph.nodes[node_id]['lat'], 'lng': self.graph.nodes[node_id]['lon']}
                for node_id in path
            ]
            formatted_routes.append({"id": i + 1, "path": route_coords})
        return formatted_routes