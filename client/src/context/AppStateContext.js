// src/context/AppStateContext.js
import React, { createContext, useState, useMemo } from 'react';

export const AppStateContext = createContext();

export const AppStateProvider = ({ children }) => {
  // State for the user's search query
  const [searchParams, setSearchParams] = useState({
    origin: { lat: 36.512916, lng: -82.531524 },
    searchRadius: 5,
    pathDistance: 1,
    optimalIncline: 2.0,
  });

  // State to track the status of the API call
  const [searchStatus, setSearchStatus] = useState('idle'); // 'idle', 'pending', 'success', 'error'
  const [errorMessage, setErrorMessage] = useState('');

  // State for the results returned from the backend
  const [routes, setRoutes] = useState([]);
  const [selectedRouteId, setSelectedRouteId] = useState(null);

  // State to track if the external Leaflet library has loaded
  const [leafletLoaded, setLeafletLoaded] = useState(false);

  // Function to update the search parameters
  const updateSearchParams = (newParams) => {
    setSearchParams(prev => ({ ...prev, ...newParams }));
  };

  // Derived state: calculates the data for the selected route
  // useMemo ensures this only recalculates when the dependencies change
  const selectedRouteData = useMemo(() => {
    return routes.find(route => route.id === selectedRouteId) || null;
  }, [selectedRouteId, routes]);

  // The value object that will be available to all consuming components
  const value = {
    searchParams,
    updateSearchParams,
    searchStatus,
    setSearchStatus,
    errorMessage,
    setErrorMessage,
    routes,
    setRoutes,
    selectedRouteId,
    setSelectedRouteId,
    selectedRouteData,
    leafletLoaded,
    setLeafletLoaded,
  };

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
};  