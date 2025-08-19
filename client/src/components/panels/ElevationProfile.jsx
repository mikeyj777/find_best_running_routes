// src/components/panels/ElevationProfile.jsx
import React, { useContext, useMemo } from 'react';
import { AppStateContext } from '../../context/AppStateContext';
import styles from '../../styles/ElevationProfile.module.css';

// Define SVG constants, including padding for axes
const SVG_WIDTH = 1000;
const SVG_HEIGHT = 150;
const PADDING = { top: 10, right: 20, bottom: 25, left: 60 };

const CHART_WIDTH = SVG_WIDTH - PADDING.left - PADDING.right;
const CHART_HEIGHT = SVG_HEIGHT - PADDING.top - PADDING.bottom;

const ElevationProfile = () => {
  const { selectedRouteData } = useContext(AppStateContext);

  // useMemo will recalculate chart metrics only when the selected route changes
  const chartData = useMemo(() => {
    const profile = selectedRouteData?.elevationProfile;
    if (!profile || profile.length < 2) return null;

    const elevations = profile.map(p => p.elevation);
    const minElev = Math.min(...elevations);
    const maxElev = Math.max(...elevations);
    const elevationRange = maxElev - minElev || 1; // Avoid division by zero
    const totalDistance = profile[profile.length - 1].distance;

    // Map data points to SVG coordinates
    const points = profile.map(p => {
      const x = PADDING.left + (p.distance / totalDistance) * CHART_WIDTH;
      const y = PADDING.top + CHART_HEIGHT - ((p.elevation - minElev) / elevationRange) * CHART_HEIGHT;
      return `${x},${y}`;
    });

    // Create the SVG path string for the area chart
    const firstPoint = PADDING.left + "," + (CHART_HEIGHT + PADDING.top);
    const lastPoint = (PADDING.left + CHART_WIDTH) + "," + (CHART_HEIGHT + PADDING.top);
    const pathD = `M ${firstPoint} L ${points.join(" L ")} L ${lastPoint} Z`;

    return { pathD, minElev, maxElev, totalDistance };
  }, [selectedRouteData]);

  // If there's no data to chart, show the default message
  if (!chartData) {
    return (
      <div className={styles.container}>
        <p>Select a route to view its elevation profile.</p>
      </div>
    );
  }

  // If there is data, render the SVG chart
  return (
    <div className={styles.container}>
      <svg className={styles.svg} viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}>
        {/* Y-Axis Labels (Elevation) */}
        <text x={PADDING.left - 8} y={PADDING.top + 5} className={styles.axisLabel}>
          {Math.round(chartData.maxElev)} ft
        </text>
        <text x={PADDING.left - 8} y={PADDING.top + CHART_HEIGHT} className={styles.axisLabel}>
          {Math.round(chartData.minElev)} ft
        </text>

        {/* X-Axis Labels (Distance) */}
        <text x={PADDING.left} y={SVG_HEIGHT - PADDING.bottom + 15} className={styles.axisLabel}>
          0 mi
        </text>
        <text x={PADDING.left + CHART_WIDTH} y={SVG_HEIGHT - PADDING.bottom + 15} className={styles.axisLabel}>
          {chartData.totalDistance.toFixed(1)} mi
        </text>

        {/* The main elevation path */}
        <path className={styles.path} d={chartData.pathD} />
      </svg>
    </div>
  );
};

export default ElevationProfile;