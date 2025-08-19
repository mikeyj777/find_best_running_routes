// src/components/panels/Controls.jsx
import React, { useContext } from 'react';
import { AppStateContext } from '../../context/AppStateContext';
import styles from '../../styles/Controls.module.css';

const Controls = ({ onFindRoutes }) => {
  // Destructure all the necessary state and functions from the global context
  const { 
    searchParams, 
    updateSearchParams, 
    searchStatus, 
    routes, 
    selectedRouteId, 
    setSelectedRouteId 
  } = useContext(AppStateContext);

  // A single handler for updating any search parameter
  const handleParamChange = (param, value) => {
    updateSearchParams({ [param]: parseFloat(value) });
  };

  // A boolean to easily check if a search is in progress
  const isSearching = searchStatus === 'pending';

  return (
    <div className={styles.panel}>
      {/* Group for all the input parameters */}
      <div className={styles.group}>
        <label className={styles.label}>Search Parameters</label>
        
        {/* Path Distance Slider */}
        <div className={styles.sliderContainer}>
          <label htmlFor="pathDistance" className={styles.sliderLabel}>Path Distance</label>
          <div className={styles.sliderRow}>
            <input
              type="range"
              id="pathDistance"
              min="0.5" max="20" step="0.5"
              value={searchParams.pathDistance}
              onChange={(e) => handleParamChange('pathDistance', e.target.value)}
              className={styles.slider}
            />
            <span className={styles.sliderValue}>{searchParams.pathDistance.toFixed(1)} mi</span>
          </div>
        </div>

        {/* Target Incline Slider */}
        <div className={styles.sliderContainer}>
          <label htmlFor="optimalIncline" className={styles.sliderLabel}>Target Incline</label>
          <div className={styles.sliderRow}>
            <input
              type="range"
              id="optimalIncline"
              min="0.5" max="8" step="0.1"
              value={searchParams.optimalIncline}
              onChange={(e) => handleParamChange('optimalIncline', e.target.value)}
              className={styles.slider}
            />
            <span className={styles.sliderValue}>{searchParams.optimalIncline.toFixed(1)}%</span>
          </div>
        </div>
      </div>
      
      {/* Group for the main action button */}
      <div className={styles.group}>
        <button
          className={styles.findButton}
          onClick={onFindRoutes}
          disabled={isSearching}
        >
          {isSearching ? 'Searching...' : 'Find Routes'}
        </button>
      </div>

      {/* This group only appears after a successful search */}
      {routes.length > 0 && (
        <div className={styles.group}>
          <label className={styles.label} htmlFor="results-select">Found Routes</label>
          <select
            id="results-select"
            className={styles.resultsSelect}
            value={selectedRouteId || ''}
            onChange={(e) => setSelectedRouteId(parseInt(e.target.value, 10))}
          >
            <option value="" disabled>Select a route...</option>
            {routes.map(route => (
              <option key={route.id} value={route.id}>
                Route #{route.id}
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
};

export default Controls;