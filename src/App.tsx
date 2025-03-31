import { useState } from 'react'
import './App.css'
import NetworkSelector from './components/NetworkSelector'
import './components/NetworkSelector.css'
import ContractInteraction from './components/ContractInteraction'
import { useBlockchain } from './utils/BlockchainContext'

function App() {
  const [imageData, setImageData] = useState<string | null>(null);
  const [rawData, setRawData] = useState<string | null>(null);
  const { isConnected, networkType, network, isLoading } = useBlockchain();

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    
    // Read the file as DataURL (base64)
    reader.readAsDataURL(file);
    
    reader.onload = () => {
      const dataUrl = reader.result as string;
      setImageData(dataUrl);
      
      // Convert to raw data (array buffer)
      const rawReader = new FileReader();
      rawReader.readAsArrayBuffer(file);
      
      rawReader.onload = () => {
        const arrayBuffer = rawReader.result as ArrayBuffer;
        const uint8Array = new Uint8Array(arrayBuffer);
        
        // Convert to hex string for display
        const hexString = Array.from(uint8Array)
          .map(b => b.toString(16).padStart(2, '0'))
          .join(' ');
        
        setRawData(hexString);
      };
    };
  };

  return (
    <div className="container">
      <h1>Commission Art</h1>
      
      <NetworkSelector />
      
      <div className={`blockchain-status ${isLoading ? 'loading' : ''}`}>
        {isConnected ? (
          <p>
            Connected to 
            <span className="network-name">{network.name}</span>
            (Chain ID: {network.chainId})
            <span className="environment">{networkType.toUpperCase()}</span>
          </p>
        ) : (
          <p className="disconnected">Not connected to blockchain</p>
        )}
      </div>
      
      <ContractInteraction />
      
      <div className="upload-section">
        <label htmlFor="image-upload" className="upload-button">
          Choose Image
          <input
            id="image-upload"
            type="file"
            accept="image/*"
            onChange={handleFileUpload}
            style={{ display: 'none' }}
          />
        </label>
      </div>
      
      {imageData && (
        <div className="image-preview">
          <h2>Image Preview</h2>
          <img src={imageData} alt="Uploaded preview" />
        </div>
      )}
      
      {rawData && (
        <div className="raw-data">
          <h2>Raw Image Data (Hex)</h2>
          <div className="data-container">
            {rawData}
          </div>
        </div>
      )}
    </div>
  )
}

export default App
