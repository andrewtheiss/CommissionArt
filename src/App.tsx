/*
 * Copyright (c) 2025 Andrew Theiss
 * This work is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
 * To view a copy of this license, visit https://creativecommons.org/licenses/by-nc/4.0/
 * 
 * Permission is hereby granted to use, share, and modify this code for non-commercial purposes only,
 * provided that appropriate credit is given to the original author.
 * For commercial use, please contact the author for permission.
 */

import React from 'react';
import './App.css';
import MainTab from './components/MainTab';
import { BlockchainProvider } from './utils/BlockchainContext';

function App() {
  return (
    <BlockchainProvider>
      <div className="app-container">
        <h1>Commission Art</h1>
        <MainTab />
      </div>
    </BlockchainProvider>
  );
}

export default App;
