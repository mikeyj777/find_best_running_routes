# test_pipeline.py
import logging
from core.data_pipeline import prepare_data_for_pathfinding

# Configure logging so we can see detailed output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == '__main__':
    # Define the same search parameters our frontend would send.
    # We now include 'pathDistance' as it's needed for the bounding box calculation.
    test_search_params = {
        'origin': {'lat': 36.512916, 'lng': -82.531524},
        'searchRadius': 2, # Using a smaller radius for a quicker test
        'pathDistance': 5, # The desired length of the route to find
    }

    print("--- Starting Data Preparation Pipeline Test ---")
    
    # Run the main data preparation function
    enriched_graph = prepare_data_for_pathfinding(test_search_params)
    
    print("\n--- Test Complete ---")

    if enriched_graph and enriched_graph.number_of_nodes() > 0:
        print(f"✅ Success! The enriched graph was built successfully.")
        print(f"   - Final Node Count: {enriched_graph.number_of_nodes()}")
        
        # Check a sample node to confirm it has elevation data
        sample_node = list(enriched_graph.nodes(data=True))[0]
        print(f"   - Sample Node Data: {sample_node}")
    else:
        print("❌ Failure. The data preparation pipeline did not complete successfully.")
        print("   - Check the log messages above for errors from the API connectors.")