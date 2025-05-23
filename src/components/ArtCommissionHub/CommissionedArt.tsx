import React, { useState } from 'react';
import { ethers } from 'ethers';
import { useBlockchain } from '../../utils/BlockchainContext';
import ArtCommissionHubModal from './ArtCommissionHubModal';
import './CommissionedArt.css';

// ABI fragment for ArtCommissionHubOwners contract functions
const OWNER_REGISTRY_ABI = [
  'function lookupRegisteredOwner(uint256, address, uint256) view returns (address)',
  'function getLastUpdated(uint256, address, uint256) view returns (uint256)',
  'function getArtCommissionHubByOwner(uint256, address, uint256) view returns (address)'
];

interface ArtCommissionHubOwnersResult {
  owner: string;
  lastUpdated: string;
  artCommissionHub: string;
}

const CommissionedArt: React.FC = () => {
  const { networkType, isConnected, connectWallet, switchToLayer } = useBlockchain();
  
  const [contractAddress, setContractAddress] = useState<string>('');
  const [chainId, setChainId] = useState<string>('1');
  const [tokenId, setTokenId] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ArtCommissionHubOwnersResult | null>(null);
  const [registryAddress, setRegistryAddress] = useState<string>('0x4904FA96366e15c66C21a2aE8D4a7D605089d5Da'); // Default address from contract_config.json
  
  // For ArtCommissionHub modal
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [hubAddress, setHubAddress] = useState<string>('');
  const [directHubAddress, setDirectHubAddress] = useState<string>('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);

    if (!contractAddress) {
      setError('Please enter a contract address');
      return;
    }

    if (!tokenId || isNaN(parseInt(tokenId))) {
      setError('Please enter a valid token ID');
      return;
    }

    if (!chainId || isNaN(parseInt(chainId))) {
      setError('Please enter a valid chain ID');
      return;
    }

    // Make sure we're connected to L3
    if (networkType !== 'animechain') {
      try {
        await switchToLayer('l3', 'testnet');
      } catch (err) {
        setError('Failed to switch to L3 network. Please switch manually.');
        return;
      }
    }

    try {
      setLoading(true);
      await queryArtCommissionHubOwners();
    } catch (err: any) {
      console.error('Error querying owner registry:', err);
      setError(err.message || 'An error occurred while querying the owner registry');
    } finally {
      setLoading(false);
    }
  };

  const queryArtCommissionHubOwners = async () => {
    if (!isConnected) {
      await connectWallet();
    }

    if (!window.ethereum) {
      throw new Error('MetaMask is not installed');
    }

    const provider = new ethers.BrowserProvider(window.ethereum);
    const artCommissionHubOwners = new ethers.Contract(
      registryAddress,
      OWNER_REGISTRY_ABI,
      provider
    );

    const chainIdNum = parseInt(chainId);
    const tokenIdNum = parseInt(tokenId);

    // Query the owner registry
    const owner = await artCommissionHubOwners.lookupRegisteredOwner(chainIdNum, contractAddress, tokenIdNum);
    
    // Only proceed if we found an owner
    if (owner && owner !== ethers.ZeroAddress) {
      const lastUpdatedBN = await artCommissionHubOwners.getLastUpdated(chainIdNum, contractAddress, tokenIdNum);
      const lastUpdated = new Date(Number(lastUpdatedBN) * 1000).toLocaleString();
      
      const artCommissionHub = await artCommissionHubOwners.getArtCommissionHubByOwner(chainIdNum, contractAddress, tokenIdNum);
      
      setResult({
        owner,
        lastUpdated,
        artCommissionHub
      });

      // If artCommissionHub exists, save it for potential modal use
      if (artCommissionHub && artCommissionHub !== ethers.ZeroAddress) {
        setHubAddress(artCommissionHub);
      }
    } else {
      setError('No owner found for the given parameters');
    }
  };

  const openHubModal = (address: string) => {
    setHubAddress(address);
    setIsModalOpen(true);
  };

  const handleDirectHubLookup = (e: React.FormEvent) => {
    e.preventDefault();
    if (directHubAddress && ethers.isAddress(directHubAddress)) {
      openHubModal(directHubAddress);
    } else {
      setError('Please enter a valid ArtCommissionHub address');
    }
  };

  return (
    <div className="commissioned-art-container">
      <h2>NFT Owner Registry Query</h2>
      <p>Query the owner registry to find ownership information for an NFT</p>
      
      <div className="tabs-container">
        <div className="tab-buttons">
          <button className="tab-button active">Registry Lookup</button>
          <button className="tab-button" onClick={handleDirectHubLookup}>Direct Hub Lookup</button>
        </div>

        <div className="direct-hub-input">
          <input
            type="text"
            value={directHubAddress}
            onChange={(e) => setDirectHubAddress(e.target.value)}
            placeholder="Enter ArtCommissionHub Address"
            className="registry-address-input"
          />
          <button 
            className="query-button"
            onClick={handleDirectHubLookup}
          >
            Look Up Hub
          </button>
        </div>
      </div>
      
      <div className="registry-address-container">
        <label htmlFor="registryAddress">Owner Registry Address:</label>
        <input
          id="registryAddress"
          type="text"
          value={registryAddress}
          onChange={(e) => setRegistryAddress(e.target.value)}
          placeholder="Owner Registry Contract Address"
          className="registry-address-input"
        />
      </div>

      <form onSubmit={handleSubmit} className="query-form">
        <div className="form-group">
          <label htmlFor="chainId">Chain ID:</label>
          <input
            id="chainId"
            type="number"
            value={chainId}
            onChange={(e) => setChainId(e.target.value)}
            placeholder="Chain ID (e.g. 1 for Ethereum)"
            required
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="contractAddress">NFT Contract Address:</label>
          <input
            id="contractAddress"
            type="text"
            value={contractAddress}
            onChange={(e) => setContractAddress(e.target.value)}
            placeholder="NFT Contract Address"
            required
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="tokenId">Token ID:</label>
          <input
            id="tokenId"
            type="number"
            value={tokenId}
            onChange={(e) => setTokenId(e.target.value)}
            placeholder="Token ID"
            required
          />
        </div>
        
        <button 
          type="submit" 
          className="query-button"
          disabled={loading}
        >
          {loading ? 'Querying...' : 'Query Owner Registry'}
        </button>
      </form>
      
      {error && (
        <div className="error-message">
          {error}
        </div>
      )}
      
      {result && (
        <div className="result-container">
          <h3>Query Result</h3>
          <div className="result-item">
            <strong>Owner:</strong> 
            <span className="result-value">{result.owner}</span>
            <a 
              href={`https://explorer-animechain-39xf6m45e3.t.conduit.xyz/address/${result.owner}`} 
              target="_blank" 
              rel="noopener noreferrer"
              className="explorer-link"
            >
              View on Explorer
            </a>
          </div>
          
          <div className="result-item">
            <strong>Last Updated:</strong> 
            <span className="result-value">{result.lastUpdated}</span>
          </div>
          
          <div className="result-item">
            <strong>Commission Hub:</strong> 
            <span className="result-value">{result.artCommissionHub}</span>
            {result.artCommissionHub && result.artCommissionHub !== ethers.ZeroAddress && (
              <>
                <a 
                  href={`https://explorer-animechain-39xf6m45e3.t.conduit.xyz/address/${result.artCommissionHub}`} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="explorer-link"
                >
                  View on Explorer
                </a>
                <button 
                  className="hub-details-button"
                  onClick={() => openHubModal(result.artCommissionHub)}
                >
                  View Hub Details
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* ArtCommissionHub Modal */}
      <ArtCommissionHubModal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)} 
        hubAddress={hubAddress} 
      />
    </div>
  );
};

export default CommissionedArt; 