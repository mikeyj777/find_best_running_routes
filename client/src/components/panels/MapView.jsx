// src/components/panels/MapView.jsx
import React, { useEffect, useRef, useContext } from 'react';
import { AppStateContext } from '../../context/AppStateContext';
import styles from '../../styles/MapView.module.css';

const MapView = () => {
  // Get the selected route and leaflet loading status from the global context
  const { selectedRouteData, leafletLoaded } = useContext(AppStateContext);
  
  // Use refs to hold the map container element and the map instance itself
  // This prevents them from being re-created on every render
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const routeLayerRef = useRef(null);

  // This effect runs once when the Leaflet library is loaded
  useEffect(() => {
    // Exit if Leaflet isn't ready or if the map is already initialized
    if (!leafletLoaded || mapInstanceRef.current || !mapContainerRef.current) return;
    
    // The Leaflet library is attached to the global window object
    const L = window.L;
    
    // A necessary fix to make sure Leaflet's default icons load correctly
    delete L.Icon.Default.prototype._getIconUrl;
    L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon-2x.png',
        iconUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-shadow.png',
    });

    // Create the map instance and set its initial view
    mapInstanceRef.current = L.map(mapContainerRef.current).setView([36.512916, -82.531524], 13);
    
    // Add the base tile layer from OpenStreetMap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(mapInstanceRef.current);
  }, [leafletLoaded]);
  
  // This effect runs whenever the selected route changes
  useEffect(() => {
    // Exit if the map isn't ready yet
    if (!leafletLoaded || !mapInstanceRef.current) return;
    
    const L = window.L;
    const map = mapInstanceRef.current;

    // If there's an old route layer on the map, remove it first
    if (routeLayerRef.current) {
      map.removeLayer(routeLayerRef.current);
    }
    
    // If there is new selected route data, draw it on the map
    if (selectedRouteData?.path) {
      // Convert our path data to Leaflet's LatLng format
      const latLngs = selectedRouteData.path.map(p => [p.lat, p.lng]);
      // Create the polyline with our accent color
      const polyline = L.polyline(latLngs, { color: 'var(--accent-blue)', weight: 5 });
      // Store the new layer in our ref and add it to the map
      routeLayerRef.current = polyline;
      map.addLayer(routeLayerRef.current);
      // Automatically zoom the map to fit the bounds of the new route
      map.fitBounds(polyline.getBounds().pad(0.1));
    }
  }, [selectedRouteData, leafletLoaded]);

  return <div ref={mapContainerRef} className={styles.mapContainer} />;
};

export default MapView;