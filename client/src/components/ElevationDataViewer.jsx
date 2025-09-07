import React, { useState, useCallback, useEffect, useMemo } from 'react';
import Plot from 'react-plotly.js';
import Papa from 'papaparse';

// Define constants for clarity and easy maintenance
const METERS_TO_FEET = 3.28084;
const DEFAULT_CSV_PATH = '/data/elevation_data.csv';

// Helper function to validate and process a single row of data
// This is the corrected version.
const processDataRow = (row) => {
  // Coerce values to numbers
  const latitude = Number(row.latitude);
  const longitude = Number(row.longitude);
  const elevationInMeters = Number(row.elevation);

  // Robustly check for invalid, null, or non-finite numbers
  if (
    !isFinite(latitude) ||
    !isFinite(longitude) ||
    !isFinite(elevationInMeters)
  ) {
    return []; // Return an empty array to be filtered out by flatMap
  }

  // Return the valid object inside an array to be kept by flatMap
  return [{
    latitude,
    longitude,
    // Perform unit conversion during initial processing
    elevation: elevationInMeters * METERS_TO_FEET,
  }];
};


const ElevationDataViewer = () => {
  const [data, setData] = useState([]);
  const [viewType, setViewType] = useState('3d');
  const [isLoading, setIsLoading] = useState(true); // Start loading on initial render
  const [dataSource, setDataSource] = useState('none');
  const [error, setError] = useState(null);

  // Centralized function for parsing, validating, and converting data
  const parseAndSetData = useCallback((csvContent, source) => {
    Papa.parse(csvContent, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        // Use flatMap to process and filter in a single pass
        const processedData = results.data.flatMap(processDataRow);

        if (processedData.length === 0) {
          setError('CSV file is empty or contains no valid data rows.');
          setData([]);
        } else {
          setData(processedData);
          setError(null);
        }
        
        setDataSource(source);
        console.log(`Loaded ${processedData.length} valid elevation points from ${source}`);
      },
      error: (err) => {
        console.error('CSV parsing error:', err);
        setError(`Error parsing CSV: ${err.message}`);
        setData([]);
      },
    });
  }, []);

  // Simplified function to load data from a URL or file upload
  const loadData = useCallback(async (sourceProvider, sourceName) => {
    setIsLoading(true);
    setError(null);
    try {
      const csvContent = await sourceProvider();
      parseAndSetData(csvContent, sourceName);
    } catch (err) {
      console.error(`Failed to load data from ${sourceName}:`, err);
      setError(`Could not load data from ${sourceName}: ${err.message}`);
      setData([]);
      setDataSource('none');
    } finally {
      setIsLoading(false);
    }
  }, [parseAndSetData]);

  const handleFileUpload = useCallback((event) => {
    const file = event.target.files[0];
    if (!file) return;

    const fileReaderProvider = () => new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = e => resolve(e.target.result);
      reader.onerror = err => reject(err);
      reader.readAsText(file);
    });

    loadData(fileReaderProvider, file.name);
    // Reset file input value to allow re-uploading the same file
    event.target.value = null;
  }, [loadData]);

  // Effect to load the default CSV file on component mount
  useEffect(() => {
    const fetchDefaultCsvProvider = async () => {
      const response = await fetch(DEFAULT_CSV_PATH);
      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`);
      }
      return response.text();
    };
    
    loadData(fetchDefaultCsvProvider, 'Default CSV');
  }, [loadData]);

  // Memoize plot configuration to prevent re-calculation on every render
  const plotConfig = useMemo(() => {
    if (!data || data.length === 0) return null;

    // No need to filter here; data is already clean
    const latitudes = data.map(d => d.latitude);
    const longitudes = data.map(d => d.longitude);
    const elevations = data.map(d => d.elevation);

    const minLat = Math.min(...latitudes);
    const maxLat = Math.max(...latitudes);
    const minLng = Math.min(...longitudes);
    const maxLng = Math.max(...longitudes);

    let plotData, layout;

    switch (viewType) {
      case '3d':
        plotData = [{
          type: 'scatter3d',
          mode: 'markers',
          x: longitudes,
          y: latitudes,
          z: elevations,
          marker: {
            size: 3,
            color: elevations,
            colorscale: 'Viridis',
            colorbar: { title: 'Elevation (ft)' },
          },
          text: data.map(d => `Lat: ${d.latitude.toFixed(6)}<br>Lng: ${d.longitude.toFixed(6)}<br>Elev: ${d.elevation.toFixed(1)} ft`),
          hovertemplate: '%{text}<extra></extra>'
        }];
        layout = {
          title: '3D Elevation Map',
          margin: { l: 0, r: 0, b: 0, t: 40 },
          scene: {
            xaxis: { title: 'Longitude' },
            yaxis: { title: 'Latitude' },
            zaxis: { title: 'Elevation (ft)' },
            camera: { eye: { x: 1.25, y: 1.25, z: 1.25 } }
          },
        };
        break;
      
      case 'contour':
        // This is a simplified interpolation and can be slow for large datasets
        const latStep = (maxLat - minLat) / 50;
        const lngStep = (maxLng - minLng) / 50;
        const latGrid = Array.from({ length: 51 }, (_, i) => minLat + i * latStep);
        const lngGrid = Array.from({ length: 51 }, (_, i) => minLng + i * lngStep);

        const elevGrid = latGrid.map(lat => {
          return lngGrid.map(lng => {
            let minDist = Infinity;
            let nearestElev = 0;
            for (const point of data) {
              const dist = Math.sqrt(
                Math.pow(point.latitude - lat, 2) + Math.pow(point.longitude - lng, 2)
              );
              if (dist < minDist) {
                minDist = dist;
                nearestElev = point.elevation;
              }
            }
            return nearestElev;
          });
        });

        plotData = [{
          type: 'contour',
          x: lngGrid,
          y: latGrid,
          z: elevGrid,
          colorscale: 'Viridis',
          colorbar: { title: 'Elevation (ft)' }
        }];
        layout = {
          title: 'Elevation Contour Map',
          xaxis: { title: 'Longitude' },
          yaxis: { title: 'Latitude' },
        };
        break;

      case 'heatmap':
        plotData = [{
          type: 'scatter',
          mode: 'markers',
          x: longitudes,
          y: latitudes,
          marker: {
            size: 8,
            color: elevations,
            colorscale: 'Viridis',
            colorbar: { title: 'Elevation (ft)' }
          },
          text: data.map(d => `Elev: ${d.elevation.toFixed(1)} ft`),
          hovertemplate: 'Lat: %{y:.6f}<br>Lng: %{x:.6f}<br>%{text}<extra></extra>'
        }];
        layout = {
          title: 'Elevation Heatmap',
          xaxis: { title: 'Longitude' },
          yaxis: { title: 'Latitude' },
        };
        break;

      default:
        return null;
    }

    // Common layout properties
    layout.height = 600;
    layout.font = { family: 'Segoe UI, Tahoma, sans-serif', color: '#334155' };

    return { data: plotData, layout };
  }, [data, viewType]);

  // Memoize statistics calculation
  const stats = useMemo(() => {
    if (!data || data.length === 0) return null;
    
    const elevations = data.map(d => d.elevation);
    const min = Math.min(...elevations);
    const max = Math.max(...elevations);
    const avg = elevations.reduce((a, b) => a + b, 0) / elevations.length;
    
    return { 
      min: min.toFixed(1),
      max: max.toFixed(1),
      avg: avg.toFixed(1),
      range: (max - min).toFixed(1),
      count: data.length.toLocaleString(),
    };
  }, [data]);

  return (
    <div className="elevation-viewer">
      <div className="app-header">
        <h1 className="title">Elevation Data Viewer</h1>
      </div>
      
      <div className="main-layout">
        <div className="content-area">
          {isLoading && (
            <div className="loading-container">
              <div className="loading-spinner"></div>
              <div className="loading-text">Loading elevation data...</div>
            </div>
          )}

          {error && !isLoading && (
            <div className="error-container">
              <div className="error-content">
                <div className="error-title">Error Loading Data</div>
                <div className="error-message">{error}</div>
                <div className="error-subtitle">
                  Please ensure the CSV file is valid and contains latitude, longitude, and elevation columns.
                </div>
              </div>
            </div>
          )}

          {!isLoading && !error && data.length === 0 && (
            <div className="empty-state">
              <div className="empty-content">
                <div className="empty-title">No data to display</div>
                <div className="empty-subtitle">Upload a valid CSV file to get started.</div>
              </div>
            </div>
          )}

          {data.length > 0 && plotConfig && !isLoading && (
            <div className="plot-container">
              <Plot
                data={plotConfig.data}
                layout={plotConfig.layout}
                config={{ 
                  responsive: true, 
                  displayModeBar: true,
                  displaylogo: false,
                  modeBarButtonsToRemove: ['pan2d', 'lasso2d']
                }}
                style={{ width: '100%', height: '100%' }}
              />
            </div>
          )}

          {stats && !isLoading && (
            <div className="stats-panel">
              <h3 className="stats-title">Elevation Statistics</h3>
              <div className="stats-grid">
                <div className="stat-item">
                  <span className="stat-label">Points:</span>
                  <div className="stat-value">{stats.count}</div>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Min:</span>
                  <div className="stat-value">{stats.min} ft</div>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Max:</span>
                  <div className="stat-value">{stats.max} ft</div>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Average:</span>
                  <div className="stat-value">{stats.avg} ft</div>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Range:</span>
                  <div className="stat-value">{stats.range} ft</div>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="sidebar">
          <div className="controls">
            <h3 className="controls-title">Controls</h3>
            
            <div className="control-group">
              <label className="control-label">
                Upload New CSV File
              </label>
              <input
                type="file"
                accept=".csv"
                onChange={handleFileUpload}
                className="file-input"
              />
            </div>
            
            <div className="control-group">
              <label className="control-label">
                Current Data Source
              </label>
              <div className="data-source">
                <span className="source-text">{dataSource}</span>
                <button
                  onClick={() => loadData(async () => {
                    const response = await fetch(DEFAULT_CSV_PATH);
                    if (!response.ok) throw new Error(`Server responded with ${response.status}`);
                    return response.text();
                  }, 'Default CSV')}
                  className="reload-btn"
                  disabled={isLoading}
                >
                  Reload Default
                </button>
              </div>
            </div>
            
            {data.length > 0 && (
              <div className="control-group">
                <label className="control-label">
                  Visualization Type
                </label>
                <select
                  value={viewType}
                  onChange={(e) => setViewType(e.target.value)}
                  className="view-select"
                >
                  <option value="3d">3D Scatter Plot</option>
                  <option value="contour">Contour Map</option>
                  <option value="heatmap">2D Heatmap</option>
                </select>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ElevationDataViewer;