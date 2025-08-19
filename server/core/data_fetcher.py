# core/data_fetcher.py
import requests
import json
import logging

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
    """
    
    def __init__(self):
        """
        Initializes the connector with the API endpoint URL.
        """
        self.api_url = "https://api.open-elevation.com/api/v1/lookup"
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def fetch_elevation_for_coords(self, coordinates):
        """
        Fetches elevation data for a list of coordinate dictionaries.
        """
        if not coordinates:
            logging.error("Error: No coordinates provided to ElevationConnector.")
            return None

        payload = {"locations": coordinates}

        try:
            response = requests.post(
                self.api_url, 
                headers=self.headers, 
                data=json.dumps(payload)
            )
            response.raise_for_status()
            data = response.json()
            return data.get('results', [])

        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP error occurred: {http_err} - {response.text}")
            return None
        except requests.exceptions.RequestException as req_err:
            logging.error(f"An error occurred during the request: {req_err}")
            return None
        except json.JSONDecodeError:
            logging.error("Error: Failed to decode JSON from response.")
            return None