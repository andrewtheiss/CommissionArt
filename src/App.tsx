import { useState } from 'react'
import './App.css'
import NetworkSelector from './components/NetworkSelector'
import './components/NetworkSelector.css'
import ContractInteraction from './components/ContractInteraction'
import AbiConfig from './components/AbiConfig'
import ContractImage from './components/ContractImage'
import { useBlockchain } from './utils/BlockchainContext'

function App() {
  const [imageData, setImageData] = useState<string | null>(null);
  const [rawData, setRawData] = useState<string | null>(null);
  const [combinedHex, setCombinedHex] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'interaction' | 'config' | 'view'>('view');
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
        
        // Create combined hex string without spaces, prefixed with 0x
        const combinedHexString = '0x' + Array.from(uint8Array)
          .map(b => b.toString(16).padStart(2, '0'))
          .join('');
        
        setCombinedHex(combinedHexString);
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

      <div className="tab-navigation">
        <button 
          className={`tab-button ${activeTab === 'view' ? 'active' : ''}`}
          onClick={() => setActiveTab('view')}
        >
          View Contract Image
        </button>
        <button 
          className={`tab-button ${activeTab === 'interaction' ? 'active' : ''}`}
          onClick={() => setActiveTab('interaction')}
        >
          Contract Interaction
        </button>
        <button 
          className={`tab-button ${activeTab === 'config' ? 'active' : ''}`}
          onClick={() => setActiveTab('config')}
        >
          ABI Configuration
        </button>
      </div>
      
      {activeTab === 'view' ? (
        <ContractImage />
      ) : activeTab === 'interaction' ? (
        <>
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
              {combinedHex && (
                <div className="combined-hex">
                  <h3>Combined Hex Data</h3>
                  <div className="hex-string">{combinedHex}</div>
                </div>
              )}
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
        </>
      ) : (
        <AbiConfig />
      )}
    </div>
  )
}

export default App
