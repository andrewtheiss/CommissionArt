import React, { useState, useEffect } from 'react';
import { ethers } from 'ethers';
import './MainTab.css';
import ImageCompressor from './ImageCompressor';
import BridgeTestContainer from './BridgeTest';
import ErrorBoundary from './ErrorBoundary';
import NFTRegistration from './NFTRegistration';
import ArtCommissionHub from './ArtCommissionHub';
import Account from './Account';
import L2OwnershipRelayTester from './L2RelayTester';
import L2L3Test from './L2L3Test';
import { BlockchainProvider } from '../utils/BlockchainContext';
import useContractConfig from '../utils/useContractConfig';
import AddArt from './AddArt/AddArt';

// ABI fragments for Registry contract functions we need
const REGISTRY_ABI = [
  'function imageDataContracts(uint256) view returns (address)',
  'function owner() view returns (address)'
];

// ABI fragments for CommissionedArt functions
const COMMISSIONED_ART_ABI = [
  'function get_image_data() view returns (bytes)',
  'function get_owner() view returns (address)',
  'function get_artist() view returns (address)'
];

// Global variable for maximum Azuki ID (can be adjusted as needed)
const MAX_AZUKI_ID = 9999; // Adjust this value as needed

interface ImageContract {
  id: number;
  address: string;
  owner: string;
  artist: string;
  imageUrl: string;
}

// SafeBlockchainProvider to handle case when MetaMask is not available
const SafeBlockchainProvider: React.FC<{children: React.ReactNode}> = ({ children }) => {
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    // Check if window.ethereum exists
    if (typeof window === 'undefined' || !window.ethereum) {
      console.warn("MetaMask is not installed or not accessible");
      setHasError(true);
    } else {
      setHasError(false);
    }
  }, []);

  if (hasError) {
    return (
      <div className="blockchain-error-container">
        <div className="error-message">
          <h3>Wallet Connection Error</h3>
          <p>MetaMask or a compatible wallet is required to use all features.</p>
          <p>Please ensure you have MetaMask installed and accessible.</p>
          <a 
            href="https://metamask.io/download/" 
            target="_blank" 
            rel="noopener noreferrer"
            className="install-metamask-btn"
          >
            Install MetaMask
          </a>
          <p>If MetaMask is already installed, please unlock your wallet and reload the page.</p>
          <button onClick={() => window.location.reload()}>Reload Page</button>
        </div>
        {children}
      </div>
    );
  }

  return <BlockchainProvider>{children}</BlockchainProvider>;
};

const MainTabContent: React.FC = () => {
  const { getContractAddress } = useContractConfig();
  
  // Get registry address from config
  const registryAddress = getContractAddress('profileFactoryAndRegistry') || '';
  
  const [selectedAzukiId, setSelectedAzukiId] = useState<string>('');
  const [selectedContract, setSelectedContract] = useState<ImageContract | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fetchingSpecific, setFetchingSpecific] = useState(false);
  const [isImageLoading, setIsImageLoading] = useState(false);
  
  // Initialize activeTab from localStorage or default to 'account'
  const [activeTab, setActiveTab] = useState<'viewer' | 'compressor' | 'bridge' | 'commissioned' | 'registration' | 'account' | 'l2relay' | 'l2l3test' | 'add-art'>(() => {
    const savedTab = localStorage.getItem('active_tab');
    if (savedTab === 'viewer' || savedTab === 'compressor' || savedTab === 'bridge' || 
        savedTab === 'commissioned' || savedTab === 'registration' || savedTab === 'account' || 
        savedTab === 'l2relay' || savedTab === 'l2l3test' || savedTab === 'add-art') {
      return savedTab;
    }
    return 'account';
  });
  
  // Save activeTab to localStorage when it changes
  useEffect(() => {
    localStorage.setItem('active_tab', activeTab);
  }, [activeTab]);

  // Helper function to detect image type from hex data
  const detectImageType = (hexData: string): string => {
    // Check for AVIF signature (ftyp+avif or ftyp+avis)
    // This is a simplified check, AVIF detection can be more complex
    const hexLower = hexData.toLowerCase();
    if (hexLower.includes('66747970617669') || hexLower.includes('6674797061766973')) {
      return 'image/avif';
    }
    
    // Check for other common image formats as fallback
    const firstBytes = hexData.substring(0, 8).toLowerCase();
    
    if (firstBytes.startsWith('89504e47')) {
      return 'image/png';
    } else if (firstBytes.startsWith('ffd8ffe0') || 
               firstBytes.startsWith('ffd8ffe1') || 
               firstBytes.startsWith('ffd8ffee') || 
               firstBytes.startsWith('ffd8ffdb')) {
      return 'image/jpeg';
    } else if (firstBytes.startsWith('47494638')) {
      return 'image/gif';
    } else if (firstBytes.startsWith('52494646') && hexData.substring(16, 24).toLowerCase() === '57454250') {
      return 'image/webp';
    }
    
    // Default to AVIF since we're looking for AVIF images
    return 'image/avif';
  };

  // Function to fetch a specific contract by Azuki ID
  const fetchSpecificContract = async (azukiId: number) => {
    try {
      setFetchingSpecific(true);
      setIsImageLoading(true);
      
      // If we have a current image, mark it as loading
      if (selectedContract) {
        setSelectedContract({
          ...selectedContract,
          imageUrl: selectedContract.imageUrl
        });
      }
      
      // Connect to AnimeChain
      const provider = new ethers.JsonRpcProvider('https://rpc-animechain-39xf6m45e3.t.conduit.xyz');
      
      // Create Registry contract instance
      const registryContract = new ethers.Contract(
        registryAddress,
        REGISTRY_ABI,
        provider
      );
      
      // Get image contract address from registry
      const contractAddress = await registryContract.imageDataContracts(azukiId);
      
      if (contractAddress && contractAddress !== ethers.ZeroAddress) {
        // Create contract instance for the image contract
        const imageContract = new ethers.Contract(
          contractAddress,
          COMMISSIONED_ART_ABI,
          provider
        );
        
        // Get image data, owner, and artist
        const imageData = await imageContract.get_image_data();
        const imageOwner = await imageContract.get_owner();
        const imageArtist = await imageContract.get_artist();
        
        // Convert the hex string to binary for image display
        const hexString = imageData.startsWith('0x') ? imageData.slice(2) : imageData;
        const byteArray = new Uint8Array(hexString.match(/.{1,2}/g)!.map((byte: string) => parseInt(byte, 16)));
        
        // Detect image type
        const imageType = detectImageType(hexString);
        
        // Create a blob and convert to data URL
        const blob = new Blob([byteArray], { type: imageType });
        const imageUrl = URL.createObjectURL(blob);
        
        // Set selected contract
        const contractData = {
          id: azukiId,
          address: contractAddress,
          owner: imageOwner,
          artist: imageArtist,
          imageUrl: imageUrl
        };
        
        setSelectedContract(contractData);
        setError(null);
      } else {
        setSelectedContract(null);
        setError(`No contract found for Azuki ID ${azukiId}`);
      }
      
      setFetchingSpecific(false);
      // We keep isImageLoading true until the image actually loads
      // The onLoad handler on the image will set this to false
    } catch (err) {
      console.error(`Error fetching contract for Azuki ID ${azukiId}:`, err);
      setError(err instanceof Error ? err.message : "Unknown error occurred");
      setSelectedContract(null);
      setFetchingSpecific(false);
      setIsImageLoading(false);
    }
  };

  // Handle input change
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSelectedAzukiId(e.target.value);
  };

  // Handle form submission
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const id = parseInt(selectedAzukiId, 10);
    
    if (isNaN(id) || id < 0 || id > MAX_AZUKI_ID) {
      setError(`Please enter a valid Azuki ID (0-${MAX_AZUKI_ID})`);
      return;
    }
    
    fetchSpecificContract(id);
  };

  // Handle showing a random Azuki
  const handleRandomAzuki = () => {
    const randomId = Math.floor(Math.random() * (MAX_AZUKI_ID + 1)); // 0 to MAX_AZUKI_ID
    setSelectedAzukiId(randomId.toString());
    setIsImageLoading(true);
    fetchSpecificContract(randomId);
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(false);
      } catch (err) {
        console.error("Error fetching registry data:", err);
        setError(err instanceof Error ? err.message : "Unknown error occurred");
        setLoading(false);
      }
    };
    
    fetchData();
    
    // Cleanup function to revoke object URLs on unmount
    return () => {
      if (selectedContract) {
        URL.revokeObjectURL(selectedContract.imageUrl);
      }
    };
  }, []);

  if (loading) {
    return <div className="main-container loading">Loading...</div>;
  }

  return (
    <SafeBlockchainProvider>
      <div className="main-container">
        <div className="tab-buttons">
          <button 
            className={`tab-button ${activeTab === 'account' ? 'active' : ''}`}
            onClick={() => setActiveTab('account')}
          >
            Account
          </button>
          <button 
            className={`tab-button ${activeTab === 'commissioned' ? 'active' : ''}`}
            onClick={() => setActiveTab('commissioned')}
          >
            Commissioned Art
          </button>
          <button 
            className={`tab-button ${activeTab === 'registration' ? 'active' : ''}`}
            onClick={() => setActiveTab('registration')}
          >
            NFT Registration
          </button>
          <button 
            className={`tab-button ${activeTab === 'l2l3test' ? 'active' : ''}`}
            onClick={() => setActiveTab('l2l3test')}
          >
            L2L3 Test
          </button>
          <button 
            className={`tab-button ${activeTab === 'l2relay' ? 'active' : ''}`}
            onClick={() => setActiveTab('l2relay')}
          >
            L2 Relay Test
          </button>
          <button 
            className={`tab-button ${activeTab === 'viewer' ? 'active' : ''}`}
            onClick={() => setActiveTab('viewer')}
          >
            Azuki Viewer
          </button>
          <button 
            className={`tab-button ${activeTab === 'compressor' ? 'active' : ''}`}
            onClick={() => setActiveTab('compressor')}
          >
            Image Compressor
          </button>
          <button 
            className={`tab-button ${activeTab === 'bridge' ? 'active' : ''}`}
            onClick={() => setActiveTab('bridge')}
          >
            Bridge Test
          </button>
          <button
            className={`nav-button ${activeTab === 'add-art' ? 'active' : ''}`}
            onClick={() => setActiveTab('add-art')}
          >
            Add Art
          </button>
        </div>

        {activeTab === 'account' ? (
          <Account />
        ) : activeTab === 'commissioned' ? (
          <ErrorBoundary fallback={
            <div className="error-message-container">
              <h3>Error in Commission Hub Component</h3>
              <p>There was an error loading the Commission Hub component. This might be due to:</p>
              <ul>
                <li>Connection issues with the Owner Registry contract</li>
                <li>Network connectivity issues</li>
                <li>MetaMask connection problems</li>
              </ul>
              <p>Please check the console for more details.</p>
            </div>
          }>
            <ArtCommissionHub />
          </ErrorBoundary>
        ) : activeTab === 'registration' ? (
          <NFTRegistration />
        ) : activeTab === 'l2l3test' ? (
          <ErrorBoundary fallback={
            <div className="error-message-container">
              <h3>Error in L2L3 Test Component</h3>
              <p>There was an error loading the L2L3 Test component. This might be due to:</p>
              <ul>
                <li>Network connectivity issues</li>
                <li>MetaMask connection problems</li>
                <li>Contract interaction issues</li>
              </ul>
              <p>Please check the console for more details.</p>
            </div>
          }>
            <L2L3Test />
          </ErrorBoundary>
        ) : activeTab === 'l2relay' ? (
          <ErrorBoundary fallback={
            <div className="error-message-container">
              <h3>Error in L2 Relay Tester Component</h3>
              <p>There was an error loading the L2 Relay Tester component. This might be due to:</p>
              <ul>
                <li>Network connectivity issues</li>
                <li>MetaMask connection problems</li>
              </ul>
              <p>Please check the console for more details.</p>
            </div>
          }>
            <L2OwnershipRelayTester />
          </ErrorBoundary>
        ) : activeTab === 'viewer' ? (
          <>
            <div className="search-container">
              <form onSubmit={handleSubmit} className="azuki-form">
                <input 
                  type="number" 
                  min="0" 
                  max={MAX_AZUKI_ID} 
                  value={selectedAzukiId} 
                  onChange={handleInputChange} 
                  placeholder={`Azuki ID (0-${MAX_AZUKI_ID})`} 
                  className="azuki-input"
                />
                <button type="submit" className="view-button" disabled={fetchingSpecific}>
                  {fetchingSpecific ? 'Loading...' : 'View'}
                </button>
              </form>
              <button 
                className="random-button" 
                onClick={handleRandomAzuki}
                disabled={fetchingSpecific}
              >
                Show Random Azuki
              </button>
            </div>
            
            {error && <div className="error-message">{error}</div>}
            
            {selectedContract && (
              <div className="image-container">
                <div className="image-wrapper">
                  <img 
                    src={selectedContract.imageUrl} 
                    alt={`Azuki #${selectedContract.id}`} 
                    className={`azuki-image ${isImageLoading ? 'loading' : ''}`}
                    onLoad={() => setIsImageLoading(false)}
                  />
                  {isImageLoading && (
                    <div 
                      className="image-loading-overlay"
                      style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: '100%',
                        height: '100%'
                      }}
                    >
                      <div className="spinner"></div>
                    </div>
                  )}
                </div>
                <a 
                  href={`https://explorer-animechain-39xf6m45e3.t.conduit.xyz/address/${selectedContract.address}?tab=contract`} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="explorer-link"
                >
                  View On-Chain Data
                </a>
              </div>
            )}
          </>
        ) : activeTab === 'compressor' ? (
          <ImageCompressor />
        ) : activeTab === 'add-art' ? (
          <ErrorBoundary fallback={
            <div className="error-message-container">
              <h3>Error in Add Art Component</h3>
              <p>There was an error loading the Add Art component. This might be due to:</p>
              <ul>
                <li>Contract configuration issues</li>
                <li>Network connectivity problems</li>
                <li>MetaMask connection issues</li>
              </ul>
              <p>Please check the console for more details.</p>
            </div>
          }>
            <AddArt />
          </ErrorBoundary>
        ) : (
          <ErrorBoundary fallback={
            <div className="error-message-container">
              <h3>Error in Bridge Test Component</h3>
              <p>There was an error loading the Bridge Test component. This might be due to:</p>
              <ul>
                <li>Missing or incorrect contract configuration</li>
                <li>Network connectivity issues</li>
                <li>MetaMask connection problems</li>
              </ul>
              <p>Please check the console for more details.</p>
            </div>
          }>
            <BridgeTestContainer />
          </ErrorBoundary>
        )}
      </div>
    </SafeBlockchainProvider>
  );
};

const MainTab: React.FC = () => {
  return <MainTabContent />;
};

export default MainTab; 