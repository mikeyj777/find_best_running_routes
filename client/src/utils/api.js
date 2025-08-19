// src/utils/api.js

// The base URL of your running Flask server
const API_BASE_URL = 'http://localhost:5000'; 

/**
 * Calls the backend to fetch elevation data for a given path.
 * @param {Array<{lat: number, lng: number}>} path - The path to get elevation for.
 * @returns {Promise<object>} - A promise that resolves to the API response.
 */
export const getElevationForPath = async (path) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/find-routes`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      // Send the path in the JSON body, as the backend expects
      body: JSON.stringify({ path }), 
    });

    // Handle non-200 responses
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
    }

    return await response.json();

  } catch (error) {
    console.error("Error fetching elevation:", error);
    // Re-throw the error so the component can catch it and update the UI
    throw error; 
  }
};