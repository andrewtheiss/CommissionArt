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
