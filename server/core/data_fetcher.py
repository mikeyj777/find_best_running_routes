# core/data_fetcher.py
import requests
import json
import logging
import time

# --- NEW HELPER FUNCTION ---
def process_elevation_request(request_data):
    """
    Handles the logic for an elevation data request. It validates the input,
    formats coordinates, fetches data, and returns a structured result.

    Args:
        request_data (dict): The JSON data from the Flask request.

    Returns:
        tuple: A tuple containing a dictionary (the response data) and an
               HTTP status code.
    """
    logging.info("Processing elevation request...")
    
    if not request_data or 'path' not in request_data:
        logging.error("Invalid request: Missing 'path' in JSON body")
        return {"error": "Invalid request: Missing 'path' in JSON body"}, 400

    # The frontend sends coordinates as {lat, lng}, but our connector needs {latitude, longitude}
    coordinates = [
        {'latitude': p['lat'], 'longitude': p['lng']} for p in request_data['path']
    ]

    try:
        logging.debug("Instantiating ElevationConnector")
        elevation_connector = ElevationConnector()
        
        logging.debug(f"Fetching elevation for {len(coordinates)} coordinates")
        elevation_data = elevation_connector.fetch_elevation_for_coords(coordinates)
        
        if elevation_data:
            logging.info("Successfully fetched elevation data.")
            return {
                "status": "success",
                "elevationProfile": elevation_data
            }, 200
        else:
            logging.error("ElevationConnector failed to fetch data.")
            return {"error": "Failed to fetch elevation data from external API"}, 500

    except Exception as e:
        logging.critical(f"An unexpected error occurred: {e}", exc_info=True)
        return {"error": "An internal server error occurred"}, 500


class ElevationConnector:
    """
    A class to connect to the Open-Elevation API and fetch elevation data.
    Includes logic to automatically batch large requests.
    """
    
    def __init__(self, batch_size=1000):
        """
        Initializes the connector with the API endpoint URL and a batch size.
        """
        self.api_url = "https://api.open-elevation.com/api/v1/lookup"
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        self.batch_size = batch_size

    def fetch_elevation_for_coords(self, coordinates):
        """
        Fetches elevation data for a list of coordinates, automatically handling batching.
        """
        if not coordinates:
            logging.error("Error: No coordinates provided to ElevationConnector.")
            return None

        all_results = []
        
        # Split the coordinates into smaller chunks (batches)
        for i in range(0, len(coordinates), self.batch_size):
            batch = coordinates[i:i + self.batch_size]
            logging.info(f"Fetching batch {i // self.batch_size + 1} of {len(coordinates) // self.batch_size + 1}...")
            
            payload = {"locations": batch}

            try:
                response = requests.post(
                    self.api_url, 
                    headers=self.headers, 
                    data=json.dumps(payload)
                )
                response.raise_for_status()
                data = response.json()
                
                batch_results = data.get('results', [])
                if batch_results:
                    logging.info(f"Batch {i // self.batch_size + 1} fetched successfully.")
                    all_results.extend(batch_results)
                
                # Be a good citizen and pause briefly between requests
                time.sleep(1)

            except requests.exceptions.HTTPError as http_err:
                logging.error(f"HTTP error on batch: {http_err} - {response.text}")
                # Decide if you want to stop or continue on a failed batch
                # For now, we'll stop and return what we have so far.
                return all_results if all_results else None
            except requests.exceptions.RequestException as req_err:
                logging.error(f"Request error on batch: {req_err}")
                return all_results if all_results else None
            except json.JSONDecodeError:
                logging.error("Error decoding JSON from response on batch.")
                return all_results if all_results else None
        
        return all_results