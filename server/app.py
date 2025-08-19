from flask import Flask, jsonify, request
from flask_cors import CORS
import logging

# Import the new helper function
from core.data_fetcher import process_elevation_request

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

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
def find_routes():
    """
    API endpoint for finding routes. This function now acts as a thin
    controller that passes the request data to a processing function.
    """
    logging.info("Received request on /api/find-routes")
    
    # Get the JSON data from the request
    data = request.get_json()
    
    # Call the helper function to do all the work
    response_data, status_code = process_elevation_request(data)
    
    # Return the result from the helper function
    return jsonify(response_data), status_code


if __name__ == '__main__':
    app.run("0.0.0.0", debug=True)