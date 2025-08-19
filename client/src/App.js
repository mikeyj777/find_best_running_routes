// src/App.js
import React, { useEffect, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AppStateProvider, AppStateContext } from './context/AppStateContext';
import Home from './components/Home';
import RouteFinder from './components/RouteFinder';
import './index.css'; // Assuming you moved global styles here
import './styles/global.css'; // Import global styles

// Helper component to manage loading side-effects like Leaflet
const AppLoader = ({ children }) => {
  const { setLeafletLoaded } = useContext(AppStateContext);

  useEffect(() => {
    // Load Leaflet CSS
    const leafletCss = document.createElement('link');
    leafletCss.rel = 'stylesheet';
    leafletCss.href = 'https://unpkg.com/leaflet@1.7.1/dist/leaflet.css';
    document.head.appendChild(leafletCss);

    // Load Leaflet JS
    const leafletJs = document.createElement('script');
    leafletJs.src = 'https://unpkg.com/leaflet@1.7.1/dist/leaflet.js';
    leafletJs.async = true;
    leafletJs.onload = () => {
      setLeafletLoaded(true);
    };
    document.head.appendChild(leafletJs);

    return () => {
      document.head.removeChild(leafletCss);
      document.head.removeChild(leafletJs);
    };
  }, [setLeafletLoaded]);

  return <>{children}</>;
};

export default function App() {
  return (
    // The Provider must be outside the Router
    <AppStateProvider>
      <Router>
        <AppLoader>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/routes" element={<RouteFinder />} />
          </Routes>
        </AppLoader>
      </Router>
    </AppStateProvider>
  );
}