from flask import Flask, jsonify, request
from flask_cors import CORS
import logging

# Import the main orchestrator and the final engine
from core.data_pipeline import prepare_data_for_pathfinding
from core.pathfinder import PathfindingEngine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://emo.riskspace.net"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

@app.route("/")
def home():
    return jsonify({"message": "This is the API."})

@app.route("/api/find-routes", methods=['POST'])
def find_routes_endpoint():
    """
    The main API endpoint that orchestrates the entire process.
    """
    logging.info("Received request on /api/find-routes")
    search_params = request.get_json()
    
    if not search_params:
        return jsonify({"error": "Invalid request: Missing JSON body"}), 400

    try:
        # Step 1: Prepare all the data (fetch OSM, build graph, get elevation)
        logging.info("--- Starting Data Preparation ---")
        enriched_graph = prepare_data_for_pathfinding(search_params)
        
        if not enriched_graph or enriched_graph.number_of_nodes() == 0:
            logging.error("Failed to build the enriched graph.")
            return jsonify({"error": "Could not prepare map data for the selected area."}), 500
        
        # Step 2: Run the pathfinding algorithm on the prepared data
        logging.info("--- Starting Pathfinding Engine ---")
        engine = PathfindingEngine(graph=enriched_graph, search_params=search_params)
        found_routes = engine.find_routes()

        # Step 3: Return the results
        logging.info(f"--- Process Complete. Found {len(found_routes)} routes. ---")
        return jsonify({
            "status": "success",
            "routes": found_routes
        }), 200

    except Exception as e:
        logging.critical(f"An unexpected error occurred in the main endpoint: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred"}), 500


if __name__ == '__main__':
    app.run("0.0.0.0", debug=True)