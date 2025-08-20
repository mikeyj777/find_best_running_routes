# test_pathfinder.py
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from core.data_pipeline import prepare_data_for_pathfinding
from core.pathfinder import PathfindingEngine

# Configure logging so we can see detailed output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == '__main__':
    # 1. Define the search parameters for the test
    test_search_params = {
        'origin': {'lat': 36.512916, 'lng': -82.531524},
        'searchRadius': 1, # Smaller radius for a faster test
        'pathDistance': 1.5, # Find routes that are 1.5 miles long
        'optimalIncline': 2.0,
        'overallTolerance': 0.25, # 25% tolerance (1.5% to 2.5%)
        'localTolerance': 0.10,   # 10% of the path can be outside the range
    }

    # 2. Run the data preparation pipeline to get the 3D road network
    print("--- Step 1: Preparing Data (This may take a minute) ---")
    enriched_graph = prepare_data_for_pathfinding(test_search_params)
    
    if not enriched_graph or enriched_graph.number_of_nodes() == 0:
        print("❌ Data preparation failed. Exiting test.")
    else:
        print(f"✅ Data preparation successful. Graph has {enriched_graph.number_of_nodes()} nodes.")

        # 3. Instantiate and run the PathfindingEngine
        print("\n--- Step 2: Running Pathfinding Engine ---")
        engine = PathfindingEngine(graph=enriched_graph, search_params=test_search_params)
        found_routes = engine.find_routes()

        # 4. Print the final results
        print("\n--- Test Complete ---")
        if found_routes:
            print(f"✅ Success! Pathfinding engine found {len(found_routes)} routes.")
            # Print details of the first route found
            first_route = found_routes[0]
            print(f"   - First route has {len(first_route['path'])} points.")
            print(f"   - Starting point: {first_route['path'][0]}")
            print(f"   - Ending point: {first_route['path'][-1]}")
        else:
            print("❌ No routes were found that met the specified criteria.")