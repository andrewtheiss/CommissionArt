import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import App from './App';
import { BlockchainProvider } from './utils/BlockchainContext';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <BlockchainProvider>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
      </Routes>
    </BrowserRouter>
  </BlockchainProvider>
);