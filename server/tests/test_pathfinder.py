import sys
import os
import logging
import pickle  # Import the pickle library

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.data_pipeline import prepare_data_for_pathfinding
from core.pathfinder import PathfindingEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the name for our cache file
CACHE_FILE = 'graph_cache.pkl'

if __name__ == '__main__':
    test_search_params = {
        'origin': {'lat': 36.512916, 'lng': -82.531524},
        'searchRadius': 1,
        'pathDistance': 1.5,
        'optimalIncline': 2.0,
        'overallTolerance': 0.50,
        'localTolerance': 0.20,
    }

    enriched_graph = None

    # --- NEW CACHING LOGIC ---
    # Check if the cached graph file exists
    if os.path.exists(CACHE_FILE):
        print("--- Loading enriched graph from cache ---")
        with open(CACHE_FILE, 'rb') as f:
            enriched_graph = pickle.load(f)
        print(f"✅ Graph loaded from '{CACHE_FILE}' successfully.")
    else:
        # If no cache exists, run the full data pipeline
        print("--- No cache found. Running full data preparation pipeline (This may take a minute) ---")
        enriched_graph = prepare_data_for_pathfinding(test_search_params)
        
        if enriched_graph and enriched_graph.number_of_nodes() > 0:
            # Save the newly created graph to the cache file for next time
            print(f"--- Saving new graph to cache file: '{CACHE_FILE}' ---")
            with open(CACHE_FILE, 'wb') as f:
                pickle.dump(enriched_graph, f)
            print("✅ Graph saved successfully.")

    # --- Run the Pathfinding Engine ---
    if not enriched_graph or enriched_graph.number_of_nodes() == 0:
        print("❌ Data preparation failed. Exiting test.")
    else:
        print("\n--- Step 2: Running Pathfinding Engine ---")
        engine = PathfindingEngine(graph=enriched_graph, search_params=test_search_params)
        found_routes = engine.find_routes()

        print("\n--- Test Complete ---")
        if found_routes:
            print(f"✅ Success! Pathfinding engine found {len(found_routes)} routes.")
            first_route = found_routes[0]
            print(f"   - First route has {len(first_route['path'])} points.")
        else:
            print("❌ No routes were found that met the specified criteria.")