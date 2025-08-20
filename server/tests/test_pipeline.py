# server/tests/test_pathfinder.py
import sys
import os
import logging

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.data_pipeline import prepare_data_for_pathfinding
from core.pathfinder import PathfindingEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == '__main__':
    test_search_params = {
        'origin': {'lat': 36.512916, 'lng': -82.531524},
        'searchRadius': 1,
        'pathDistance': 1.5,
        'optimalIncline': 2.0,
        'overallTolerance': 0.50, # Loosened for testing: 1.0% to 3.0%
        'localTolerance': 0.20,   # Loosened for testing: 20% of path can be "bad"
    }

    print("--- Step 1: Preparing Data (This may take a minute) ---")
    enriched_graph = prepare_data_for_pathfinding(test_search_params)
    
    if not enriched_graph or enriched_graph.number_of_nodes() == 0:
        print("❌ Data preparation failed. Exiting test.")
    else:
        print(f"✅ Data preparation successful. Graph has {enriched_graph.number_of_nodes()} nodes.")

        print("\n--- Step 2: Running Pathfinding Engine ---")
        engine = PathfindingEngine(graph=enriched_graph, search_params=test_search_params)
        found_routes = engine.find_routes()

        print("\n--- Test Complete ---")
        if found_routes:
            print(f"✅ Success! Pathfinding engine found {len(found_routes)} routes.")
            first_route = found_routes[0]
            print(f"   - First route has {len(first_route['path'])} points.")
            print(f"   - Starting point: {first_route['path'][0]}")
            print(f"   - Ending point: {first_route['path'][-1]}")
        else:
            print("❌ No routes were found that met the specified criteria.")
            print("   - Try loosening the tolerance parameters in the test script or increasing the searchRadius.")
            # Print some graph stats to help debug
            elevations = [data.get('elevation', 0) for _, data in enriched_graph.nodes(data=True) if 'elevation' in data]
            if elevations:
                print(f"   - Graph elevation stats (meters): Min={min(elevations):.2f}, Max={max(elevations):.2f}, Avg={sum(elevations)/len(elevations):.2f}")