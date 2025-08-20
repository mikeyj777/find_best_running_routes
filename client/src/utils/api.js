// src/utils/api.js

// The base URL of your running Flask server
const API_BASE_URL = 'http://localhost:5000'; 

/**
 * Calls the final backend endpoint to find routes based on search parameters.
 * @param {object} searchParams - The complete search parameters object from the context.
 * @returns {Promise<object>} - A promise that resolves to the API response.
 */
export const findRoutes = async (searchParams) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/find-routes`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      // Send the entire searchParams object in the body
      body: JSON.stringify(searchParams), 
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
    }

    return await response.json();

  } catch (error) {
    console.error("Error finding routes:", error);
    throw error; 
  }
};