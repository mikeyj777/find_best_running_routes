// src/components/RouteFinder.jsx
import React, { useContext, useCallback } from 'react';
import { AppStateContext } from '../context/AppStateContext';
import { mockApi } from '../utils/api';
// import Controls from './panels/Controls';
// import MapView from './panels/MapView';
// import StatusBar from './panels/StatusBar';
// import ElevationProfile from './panels/ElevationProfile';
import styles from '../styles/RouteFinder.module.css';

const RouteFinder = () => {
  const { searchParams, setSearchStatus, setErrorMessage, setRoutes, setSelectedRouteId } = useContext(AppStateContext);

  const handleFindRoutes = useCallback(async () => {
    setSearchStatus('pending');
    setRoutes([]);
    setSelectedRouteId(null);
    setErrorMessage('');
    try {
      const result = await mockApi.findRoutes(searchParams);
      setRoutes(result.routes);
      setSearchStatus('success');
    } catch (error) {
      setErrorMessage(error.message);
      setSearchStatus('error');
    }
  }, [searchParams, setSearchStatus, setRoutes, setSelectedRouteId, setErrorMessage]);

  return (
    <div className={styles.container}>
      {/* <div className={styles.mapView}><MapView /></div>
      <div className={styles.controls}><Controls onFindRoutes={handleFindRoutes} /></div>
      <div className={styles.elevationProfile}><ElevationProfile /></div>
      <div className={styles.statusBar}><StatusBar /></div> */}
    </div>
  );
};

export default RouteFinder;