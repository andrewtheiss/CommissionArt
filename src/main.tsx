import { createRoot } from 'react-dom/client';
import App from './App';
import { BlockchainProvider } from './utils/BlockchainContext';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <BlockchainProvider>
    <App />
  </BlockchainProvider>
);