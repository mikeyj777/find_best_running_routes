// src/components/panels/StatusBar.jsx
import React, { useContext } from 'react';
import { AppStateContext } from '../../context/AppStateContext';
import styles from '../../styles/StatusBar.module.css';

const StatusBar = () => {
  // Get the necessary state from the global context
  const { searchStatus, errorMessage, routes } = useContext(AppStateContext);

  // Determine the message to display based on the current search status
  let message = 'Ready to find your perfect training route.';
  if (searchStatus === 'pending') {
    message = 'Searching for routes... this may take a moment.';
  } else if (searchStatus === 'success') {
    message = `Search complete. Found ${routes.length} matching routes.`;
  } else if (searchStatus === 'error') {
    message = `Error: ${errorMessage}`;
  }

  return (
    <div className={styles.statusBar}>
      <p>{message}</p>
    </div>
  );
};

export default StatusBar;