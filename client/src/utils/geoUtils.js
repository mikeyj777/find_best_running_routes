// src/utils/geoUtils.js

/**
 * Calculates the distance between two GPS coordinates in miles using the Haversine formula.
 * @param {{lat: number, lng: number}} p1 - The first point.
 * @param {{lat: number, lng: number}} p2 - The second point.
 * @returns {number} The distance in miles.
 */
export const haversineDistance = (p1, p2) => {
  if (!p1 || !p2) return 0;
  const R = 3958.8; // Earth's radius in miles
  const rad = (x) => x * Math.PI / 180;
  const dLat = rad(p2.lat - p1.lat);
  const dLon = rad(p2.lng - p1.lng);
  const lat1 = rad(p1.lat);
  const lat2 = rad(p2.lat);
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) + Math.sin(dLon / 2) * Math.sin(dLon / 2) * Math.cos(lat1) * Math.cos(lat2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
};

/**
 * Processes a raw route path to calculate cumulative distance and simulate elevation.
 * This function creates the data structure needed for the elevation profile chart.
 * Used by the mock API to generate realistic test data.
 * @param {Array<{lat: number, lng: number}>} path - An array of coordinate points.
 * @returns {Array<{distance: number, elevation: number}>} An array of data points for charting.
 */
export const processRouteForElevation = (path) => {
  if (!path || path.length < 2) return [];

  let cumulativeDistance = 0;
  let currentElevation = 500; // Starting elevation in feet
  
  const profileData = [{ distance: 0, elevation: currentElevation }];

  for (let i = 1; i < path.length; i++) {
    const segmentDistance = haversineDistance(path[i - 1], path[i]);
    cumulativeDistance += segmentDistance;

    // Simulate elevation change: add a random value between -20 and +20 feet
    currentElevation += (Math.random() - 0.5) * 40;
    // Ensure elevation doesn't go below a certain floor
    if (currentElevation < 300) currentElevation = 300;

    profileData.push({
      distance: cumulativeDistance,
      elevation: currentElevation,
    });
  }

  return profileData;
};

/**
 * Parses a KML text string into an XML Document.
 * @param {string} kmlText The raw string content of a KML file.
 * @returns {XMLDocument} A parsed XML document.
 */
export const parseKML = (kmlText) => {
  if (!kmlText || typeof kmlText !== 'string') {
    kmlText = '<?xml version="1.0" encoding="UTF-8"?>';
  }
  const parser = new DOMParser();
  return parser.parseFromString(kmlText, 'text/xml');
};

/**
 * Extracts an array of {lat, lng} coordinate objects from KML text.
 * @param {string} kmlText The raw string content of a KML file.
 * @returns {Array<{lat: number, lng: number}>|null} An array of coordinate objects.
 */
export const getCoordsFromKML = (kmlText) => {
  if (!kmlText) return null;
  const kmlDoc = parseKML(kmlText);
  const coordinatesNode = kmlDoc.querySelector('coordinates');
  if (!coordinatesNode) {
    console.error("No <coordinates> tag found in KML file.");
    return null;
  }
  const coordinatesString = coordinatesNode.textContent;
  return coordinatesString.trim().split(/\s+/).map(coordString => {
    const [longitude, latitude] = coordString.split(',');
    return { lat: parseFloat(latitude), lng: parseFloat(longitude) };
  }).filter(loc => !isNaN(loc.lat) && !isNaN(loc.lng));
};