// src/components/RouteFinder.jsx
import React, { useContext, useCallback } from 'react';
import { AppStateContext } from '../context/AppStateContext';
import { getElevationForPath } from '../utils/api';
import { haversineDistance } from '../utils/geoUtils'; 
import Controls from './panels/Controls';
import MapView from './panels/MapView';
import StatusBar from './panels/StatusBar';
import ElevationProfile from './panels/ElevationProfile';
import styles from '../styles/RouteFinder.module.css';

const RouteFinder = () => {
  const { setSearchStatus, setErrorMessage, setRoutes, setSelectedRouteId } = useContext(AppStateContext);

  const handleFindRoutes = useCallback(async () => {
    setSearchStatus('pending');
    setRoutes([]);
    setSelectedRouteId(null);
    setErrorMessage('');
    try {
      const testPath = [
        { lat: 36.512916, lng: -82.531524 },
        { lat: 36.520000, lng: -82.540000 },
        { lat: 36.530000, lng: -82.550000 },
        { lat: 36.540000, lng: -82.560000 }
      ];

      const result = await getElevationForPath(testPath);
      
      console.log("Response from backend:", result);

      let cumulativeDistance = 0;
      // The backend response uses 'latitude'/'longitude', so we need a slightly different processor here
      const processedProfile = result.elevationProfile.map((point, index) => {
        if (index > 0) {
          const prevPoint = result.elevationProfile[index - 1];
          // haversineDistance expects {lat, lng}, so we need to map the keys
          cumulativeDistance += haversineDistance(
            { lat: prevPoint.latitude, lng: prevPoint.longitude },
            { lat: point.latitude, lng: point.longitude }
          );
        }
        return {
          distance: cumulativeDistance,
          elevation: point.elevation * 3.28084 
        };
      });

      const finalRoute = {
          id: 1,
          path: testPath,
          elevationProfile: processedProfile
      };

      setRoutes([finalRoute]);
      setSearchStatus('success');

    } catch (error) {
      setErrorMessage(error.message);
      setSearchStatus('error');
    }
  }, [setSearchStatus, setRoutes, setSelectedRouteId, setErrorMessage]);

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