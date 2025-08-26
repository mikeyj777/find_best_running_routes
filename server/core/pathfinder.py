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
        self.graph = graph
        self.params = search_params
        self.found_routes = []
        self.target_distance = self.params.get('pathDistance', 1.0)
        self.max_routes_to_find = 10

    def find_routes(self):
        logging.info("Starting pathfinding process...")
        if not self.graph or self.graph.number_of_nodes() == 0:
            logging.warning("Graph is empty. Cannot find routes.")
            return []

        all_nodes = list(self.graph.nodes(data=True))
        starting_nodes = random.sample(all_nodes, k=min(200, len(all_nodes))) # Increased starting points

        for start_node_id, _ in starting_nodes:
            if len(self.found_routes) >= self.max_routes_to_find:
                break
            
            self._traverse(path=[start_node_id], current_distance=0.0)
        
        logging.info(f"Pathfinding complete. Found {len(self.found_routes)} routes.")
        return self._format_routes()

    def _traverse(self, path, current_distance):
        """
        A greedy traversal function that prioritizes segments whose incline
        is closest to the target incline.
        """
        # Stop searching if we have enough routes
        if len(self.found_routes) >= self.max_routes_to_find:
            return

        last_node_id = path[-1]
        
        best_neighbor = None
        lowest_cost = float('inf')

        # Look at all possible next steps from the current node
        for neighbor_id in self.graph.neighbors(last_node_id):
            # Don't immediately go back on the same path
            if len(path) > 1 and neighbor_id == path[-2]:
                continue

            # --- Calculate the "cost" of this potential segment ---
            node1_data = self.graph.nodes[last_node_id]
            node2_data = self.graph.nodes[neighbor_id]
            
            if 'elevation' not in node1_data or 'elevation' not in node2_data:
                continue

            rise_m = node2_data['elevation'] - node1_data['elevation']
            run_m = self.graph[last_node_id][neighbor_id]['weight'] * 1609.34
            
            if run_m == 0: continue
            
            segment_incline = (rise_m / run_m) * 100
            
            # The cost is how much the segment's incline deviates from our target.
            # Squaring it heavily penalizes large deviations.
            cost = (segment_incline - self.params.get('optimalIncline', 2.0))**2
            
            # Keep track of the neighbor with the lowest cost (the best option)
            if cost < lowest_cost:
                lowest_cost = cost
                best_neighbor = neighbor_id

        # If we found a best next step, proceed down that path
        if best_neighbor:
            segment_distance = self.graph[last_node_id][best_neighbor]['weight']
            new_distance = current_distance + segment_distance
            new_path = path + [best_neighbor]
            
            # We still validate the entire path to ensure its overall average is good
            is_valid, _ = self._is_path_valid(new_path)
            if is_valid:
                if new_distance >= self.target_distance:
                    # Success: The path is long enough and valid
                    self.found_routes.append(new_path)
                else:
                    # The path is good so far, but not long enough. Continue searching.
                    self._traverse(path=new_path, current_distance=new_distance)

    def _is_path_valid(self, path):
        if len(path) < 2:
            return True, "Path too short to validate"

        total_distance_miles = 0
        out_of_tolerance_distance = 0
        
        optimal_incline = self.params.get('optimalIncline', 2.0)
        overall_tolerance_percent = self.params.get('overallTolerance', 0.10)
        local_tolerance_fraction = self.params.get('localTolerance', 0.01)

        # *** REVISED LOGIC: Define a wider, more forgiving range for individual segments ***
        # This allows for short steep hills or downhills without immediate penalty.
        local_incline_min = -2.0 # Allow for some downhill
        local_incline_max = 5.0  # Allow for steeper sections

        for i in range(len(path) - 1):
            node1_id, node2_id = path[i], path[i+1]
            node1_data, node2_data = self.graph.nodes[node1_id], self.graph.nodes[node2_id]

            if 'elevation' not in node1_data or 'elevation' not in node2_data:
                return False, "Missing elevation data"

            rise_m = node2_data['elevation'] - node1_data['elevation']
            run_miles = self.graph[node1_id][node2_id]['weight']
            run_m = run_miles * 1609.34
            
            if run_m == 0: continue

            segment_incline = (rise_m / run_m) * 100
            total_distance_miles += run_miles

            # Check if the segment is outside our new, forgiving local range
            if not (local_incline_min <= segment_incline <= local_incline_max):
                out_of_tolerance_distance += run_miles

        # Check if the path has too much "bad" terrain
        max_allowed_oot_distance = self.target_distance * local_tolerance_fraction
        if out_of_tolerance_distance > max_allowed_oot_distance:
            return False, f"Violates Local Tolerance: OOT distance {out_of_tolerance_distance:.2f} > {max_allowed_oot_distance:.2f}"

        # Now, check the average incline of the ENTIRE path so far
        start_node_elev = self.graph.nodes[path[0]]['elevation']
        end_node_elev = self.graph.nodes[path[-1]]['elevation']
        total_rise_m = end_node_elev - start_node_elev
        total_run_m = total_distance_miles * 1609.34
        
        if total_run_m == 0: return True, "Path is valid"

        # overall_incline = (total_rise_m / total_run_m) * 100
        
        # Check if the overall average is within the user's desired range
        # min_overall_incline = optimal_incline * (1 - overall_tolerance_percent)
        # max_overall_incline = optimal_incline * (1 + overall_tolerance_percent)

        # if not (min_overall_incline <= overall_incline <= max_overall_incline):
        #     return False, f"Violates Overall Tolerance: Avg incline {overall_incline:.2f} not in [{min_overall_incline:.2f}, {max_overall_incline:.2f}]"

        return True, "Path is valid"

    def _format_routes(self):
        formatted_routes = []
        for i, path in enumerate(self.found_routes):
            route_coords = [
                {'lat': self.graph.nodes[node_id]['lat'], 'lng': self.graph.nodes[node_id]['lon']}
                for node_id in path
            ]
            formatted_routes.append({"id": i + 1, "path": route_coords})
        return formatted_routes