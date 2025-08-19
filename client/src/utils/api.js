// src/utils/api.js

/**
 * Mocks a backend API call to find routes.
 * @param {object} searchParams - The search parameters from the UI.
 * @returns {Promise<object>} - A promise that resolves with the simulated route data.
 */
export const mockApi = {
  findRoutes: async (searchParams) => {
    console.log("Mock API called with:", searchParams);

    // Simulate network delay to mimic a real API call
    await new Promise(resolve => setTimeout(resolve, 1500));

    // Simulate a random chance of the search failing
    if (Math.random() < 0.2) {
      throw new Error("No routes found in this area.");
    }

    // If the search succeeds, generate some mock route data
    const num_routes = Math.floor(Math.random() * 5) + 2; // Generate 2 to 6 routes
    const routes = [];
    for (let i = 1; i <= num_routes; i++) {
      const { origin, pathDistance } = searchParams;
      const path = [];
      // Create a path with 20 coordinate points
      for (let j = 0; j < 20; j++) {
        const step = j / 19;
        // Add some random deviation to make the path look more natural
        const lat_offset = (Math.random() - 0.5) * 0.01 * pathDistance;
        const lng_offset = (Math.random() - 0.5) * 0.01 * pathDistance;
        path.push({
          lat: origin.lat + (step * 0.01 * pathDistance) + lat_offset,
          lng: origin.lng + (step * 0.01 * pathDistance) + lng_offset,
        });
      }
      routes.push({ id: i, path });
    }
    
    return { routes };
  }
};