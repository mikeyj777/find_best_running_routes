// src/components/RouteFinder.jsx
import React, { useContext, useCallback } from 'react';
import { AppStateContext } from '../context/AppStateContext';
import { findRoutes } from '../utils/api'; // Import the final api function
import { processRouteForElevation } from '../utils/geoUtils'; // To process the results
import Controls from './panels/Controls';
import MapView from './panels/MapView';
import StatusBar from './panels/StatusBar';
import ElevationProfile from './panels/ElevationProfile';
import styles from '../styles/RouteFinder.module.css';

const RouteFinder = () => {
  const { searchParams, setSearchStatus, setErrorMessage, setRoutes, setSelectedRouteId } = useContext(AppStateContext);

  const handleFindRoutes = useCallback(async () => {
    setSearchStatus('pending');
    setRoutes([]);
    setSelectedRouteId(null);
    setErrorMessage('');
    try {
      // 1. Call the final backend endpoint with the user's search parameters
      const result = await findRoutes(searchParams);
      
      console.log("Response from backend:", result);

      // 2. Process the results: The backend sends paths, the frontend creates the elevation profiles for charting
      const routesWithProfiles = result.routes.map(route => ({
        ...route,
        elevationProfile: processRouteForElevation(route.path)
      }));

      // 3. Update the global state with the final, processed routes
      setRoutes(routesWithProfiles);
      setSearchStatus('success');

    } catch (error) {
      setErrorMessage(error.message);
      setSearchStatus('error');
    }
  }, [searchParams, setSearchStatus, setRoutes, setSelectedRouteId, setErrorMessage]);

  return (
    <div className={styles.container}>
      <div className={styles.mapView}><MapView /></div>
      <div className={styles.controls}><Controls onFindRoutes={handleFindRoutes} /></div>
      <div className={styles.elevationProfile}><ElevationProfile /></div>
      <div className={styles.statusBar}><StatusBar /></div>
    </div>
  );
};

export default RouteFinder;