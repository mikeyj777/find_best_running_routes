import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from './components/Home';
import './App.css';
import './styles/global.css';
import RouteFinder from './components/RouteFinder';

const App = () => {
  return (
    <Router>
      <div>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/routes" element={<RouteFinder />} />
          
        </Routes>
      </div>
    </Router>
  );
};

export default App;