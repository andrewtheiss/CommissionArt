import React, { useState, useEffect } from 'react';
import { ethers } from 'ethers';
import { useBlockchain } from '../../utils/BlockchainContext';
import abiLoader from '../../utils/abiLoader';
import './L3OwnerLookup.css';

// L3 Owner Lookup form state
interface L3LookupQuery {
  contractAddress: string;
  tokenId: string;
  isSubmitting: boolean;
  result: string;
  commissionHub: string;
  lastUpdated: string;
  queryType: 'owner' | 'commissionHub' | 'lastUpdated' | 'l2relay' | 'commissionHubTemplate' | 'contractOwner';
}

// Interface for contract configuration
interface ContractConfig {
  addresses: {
    l1: {
      testnet: string;
      mainnet: string;
    };
    l2: {
      testnet: string;
      mainnet: string;
    };
    l3: {
      testnet: string;
      mainnet: string;
    };
  };
  abiFiles: {
    l1: string;
    l2: string;
    l3: string;
  };
}

// Props for L3OwnerLookup component
interface L3OwnerLookupProps {
  environment: 'testnet' | 'mainnet';
  contractConfig: ContractConfig;
  setBridgeStatus: (status: string | ((prev: string) => string)) => void;
}

const L3OwnerLookup: React.FC<L3OwnerLookupProps> = ({
  environment,
  contractConfig,
  setBridgeStatus
}) => {
  // Get blockchain context
  const { connectWallet, isConnected, networkType, switchNetwork } = useBlockchain();
  
  // State for L3 lookup query
  const [l3LookupQuery, setL3LookupQuery] = useState<L3LookupQuery>({
    contractAddress: environment === 'testnet' ? '0x3cF3dada5C03F32F0b77AAE7Ae19F61Ab89dbD06' : '', // Default NFT contract address
    tokenId: environment === 'testnet' ? '1' : '',
    isSubmitting: false,
    result: '',
    commissionHub: '',
    lastUpdated: '',
    queryType: 'owner'
  });

  // State for registry info (public variables)
  const [registryInfo, setRegistryInfo] = useState({
    l2relay: '',
    commissionHubTemplate: '',
    contractOwner: '',
    contractAddress: environment === 'testnet' 
      ? contractConfig.addresses.l3?.testnet || ''
      : contractConfig.addresses.l3?.mainnet || ''
  });

  // Update NFT contract address when environment changes
  useEffect(() => {
    if (environment === 'testnet') {
      setL3LookupQuery(prev => ({
        ...prev,
        contractAddress: '0x3cF3dada5C03F32F0b77AAE7Ae19F61Ab89dbD06',
        tokenId: prev.tokenId || '1'
      }));
      
      setRegistryInfo(prev => ({
        ...prev,
        contractAddress: contractConfig.addresses.l3?.testnet || ''
      }));
    } else {
      setRegistryInfo(prev => ({
        ...prev,
        contractAddress: contractConfig.addresses.l3?.mainnet || ''
      }));
    }
  }, [environment, contractConfig.addresses.l3]);
  
  // Handle L3 lookup form change
  const handleL3LookupChange = (field: keyof L3LookupQuery, value: string) => {
    setL3LookupQuery(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Helper function to format a timestamp as a human-readable date
  const formatTimestamp = (timestamp: number): string => {
    if (!timestamp) return 'Never';
    
    const date = new Date(timestamp * 1000); // Convert seconds to milliseconds
    return date.toLocaleString();
  };

  // Load contract public variables
  const loadContractInfo = async () => {
    // Ensure we're on the right network
    if (networkType !== 'arbitrum_testnet' && environment === 'testnet') {
      setBridgeStatus('Automatically switching to Arbitrum Sepolia to query L3 OwnerRegistry...');
      switchNetwork('arbitrum_testnet');
      return;
    } else if (networkType !== 'arbitrum_mainnet' && environment === 'mainnet') {
      setBridgeStatus('Automatically switching to Arbitrum One to query L3 OwnerRegistry...');
      switchNetwork('arbitrum_mainnet');
      return;
    }
    
    // Connect wallet if not connected
    if (!isConnected) {
      await connectWallet();
      if (!isConnected) {
        setBridgeStatus('Please connect your wallet to continue');
        return;
      }
    }
    
    try {
      // Get the OwnerRegistry contract address
      const l3Address = contractConfig.addresses.l3[environment];
      if (!l3Address) {
        throw new Error('L3 OwnerRegistry contract address not set');
      }
      
      // Create a provider
      let provider;
      try {
        const ethereum = window.ethereum as any;
        provider = new ethers.BrowserProvider(ethereum);
      } catch (error) {
        console.error('Failed to create provider:', error);
        throw new Error('Failed to connect to Ethereum provider');
      }
      
      // Load ABI
      let ownerRegistryABI;
      try {
        ownerRegistryABI = abiLoader.loadABI('OwnerRegistry');
      } catch (error) {
        console.log('Could not load OwnerRegistry ABI, using minimal ABI');
        // Define minimal ABI with needed functions
        ownerRegistryABI = [
          "function l2relay() view returns (address)",
          "function commission_hub_template() view returns (address)",
          "function owner() view returns (address)",
          "function lookupRegsiteredOwner(address nft_contract, uint256 token_id) view returns (address)",
          "function getLastUpdated(address nft_contract, uint256 token_id) view returns (uint256)",
          "function getCommissionHubByOwner(address nft_contract, uint256 token_id) view returns (address)"
        ];
      }
      
      // Create contract instance
      const contract = new ethers.Contract(l3Address, ownerRegistryABI, provider);
      
      // Query public variables
      const l2relay = await contract.l2relay();
      const commissionHubTemplate = await contract.commission_hub_template();
      const contractOwner = await contract.owner();
      
      // Update state
      setRegistryInfo({
        l2relay,
        commissionHubTemplate,
        contractOwner,
        contractAddress: l3Address
      });
      
      setBridgeStatus(`OwnerRegistry Info:\nAddress: ${l3Address}\nL2 Relay: ${l2relay}\nCommission Hub Template: ${commissionHubTemplate}\nOwner: ${contractOwner}`);
      
    } catch (error) {
      console.error('Error loading contract info:', error);
      setBridgeStatus(prev => 
        `${prev}\n\nError loading OwnerRegistry info: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    }
  };

  // Submit L3 lookup query to the OwnerRegistry contract
  const submitL3Lookup = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Ensure we're on Arbitrum - auto switch if needed
    if (networkType !== 'arbitrum_testnet' && environment === 'testnet') {
      setBridgeStatus('Automatically switching to Arbitrum Sepolia to query L3 OwnerRegistry...');
      switchNetwork('arbitrum_testnet');
      return;
    } else if (networkType !== 'arbitrum_mainnet' && environment === 'mainnet') {
      setBridgeStatus('Automatically switching to Arbitrum One to query L3 OwnerRegistry...');
      switchNetwork('arbitrum_mainnet');
      return;
    }
    
    // Connect wallet if not connected
    if (!isConnected) {
      await connectWallet();
      if (!isConnected) {
        setBridgeStatus('Please connect your wallet to continue');
        return;
      }
    }
    
    try {
      // Start submitting
      setL3LookupQuery(prev => ({
        ...prev,
        isSubmitting: true,
        result: '',
        commissionHub: '',
        lastUpdated: ''
      }));
      
      // Get the OwnerRegistry contract address
      const l3Address = contractConfig.addresses.l3[environment];
      if (!l3Address) {
        throw new Error('L3 OwnerRegistry contract address not set');
      }
      
      setBridgeStatus(prev => `${prev}\nUsing L3 OwnerRegistry address: ${l3Address}`);
      
      // Create a provider - use a type assertion to handle window.ethereum
      let provider;
      try {
        // Use a type assertion to avoid TypeScript errors
        const ethereum = window.ethereum as any;
        provider = new ethers.BrowserProvider(ethereum);
      } catch (error) {
        console.error('Failed to create provider:', error);
        throw new Error('Failed to connect to Ethereum provider');
      }
      
      // We need an ABI for the OwnerRegistry contract
      // If not available in abiLoader, we'll create a minimal ABI for the functions we need
      let ownerRegistryABI;
      try {
        ownerRegistryABI = abiLoader.loadABI('OwnerRegistry');
      } catch (error) {
        console.log('Could not load OwnerRegistry ABI, using minimal ABI');
        // Define minimal ABI with needed functions
        ownerRegistryABI = [
          "function l2relay() view returns (address)",
          "function commission_hub_template() view returns (address)",
          "function owner() view returns (address)",
          "function lookupRegsiteredOwner(address nft_contract, uint256 token_id) view returns (address)",
          "function getLastUpdated(address nft_contract, uint256 token_id) view returns (uint256)",
          "function getCommissionHubByOwner(address nft_contract, uint256 token_id) view returns (address)"
        ];
      }
      
      // Create contract instance
      const contract = new ethers.Contract(l3Address, ownerRegistryABI, provider);
      
      const { contractAddress, tokenId, queryType } = l3LookupQuery;
      
      let result = '';
      let commissionHub = '';
      let lastUpdated = '';
      
      // Handle token-specific queries
      if (['owner', 'commissionHub', 'lastUpdated'].includes(queryType)) {
        // Check that contract address is valid
        if (!ethers.isAddress(contractAddress)) {
          throw new Error('Invalid NFT contract address');
        }
        
        // Check that token ID is valid
        if (!tokenId || isNaN(parseInt(tokenId))) {
          throw new Error('Invalid token ID');
        }
        
        // Call the appropriate function based on queryType
        if (queryType === 'owner') {
          setBridgeStatus(prev => `${prev}\nQuerying registered owner for NFT contract ${contractAddress} and token ID ${tokenId}...`);
          result = await contract.lookupRegsiteredOwner(contractAddress, tokenId);
          
          // If we get an owner, query other info too
          if (result && result !== ethers.ZeroAddress) {
            commissionHub = await contract.getCommissionHubByOwner(contractAddress, tokenId);
            const lastUpdatedTimestamp = await contract.getLastUpdated(contractAddress, tokenId);
            lastUpdated = formatTimestamp(Number(lastUpdatedTimestamp));
          }
        } else if (queryType === 'commissionHub') {
          setBridgeStatus(prev => `${prev}\nQuerying commission hub for NFT contract ${contractAddress} and token ID ${tokenId}...`);
          commissionHub = await contract.getCommissionHubByOwner(contractAddress, tokenId);
          
          // If we get a commission hub, query other info too
          if (commissionHub && commissionHub !== ethers.ZeroAddress) {
            result = await contract.lookupRegsiteredOwner(contractAddress, tokenId);
            const lastUpdatedTimestamp = await contract.getLastUpdated(contractAddress, tokenId);
            lastUpdated = formatTimestamp(Number(lastUpdatedTimestamp));
          }
        } else if (queryType === 'lastUpdated') {
          setBridgeStatus(prev => `${prev}\nQuerying last updated timestamp for NFT contract ${contractAddress} and token ID ${tokenId}...`);
          const lastUpdatedTimestamp = await contract.getLastUpdated(contractAddress, tokenId);
          lastUpdated = formatTimestamp(Number(lastUpdatedTimestamp));
          
          // Also get the owner and commission hub
          result = await contract.lookupRegsiteredOwner(contractAddress, tokenId);
          if (result && result !== ethers.ZeroAddress) {
            commissionHub = await contract.getCommissionHubByOwner(contractAddress, tokenId);
          }
        }
      }
      // Handle contract-level queries (will be shown separately in the registry info section)
      else if (['l2relay', 'commissionHubTemplate', 'contractOwner'].includes(queryType)) {
        // These queries don't need NFT contract or token ID
        if (queryType === 'l2relay') {
          setBridgeStatus(prev => `${prev}\nQuerying L2 relay address...`);
          result = await contract.l2relay();
        } else if (queryType === 'commissionHubTemplate') {
          setBridgeStatus(prev => `${prev}\nQuerying commission hub template address...`);
          result = await contract.commission_hub_template();
        } else if (queryType === 'contractOwner') {
          setBridgeStatus(prev => `${prev}\nQuerying contract owner address...`);
          result = await contract.owner();
        }
        
        // Update registry info
        await loadContractInfo();
      }
      
      // Update state with result
      setL3LookupQuery(prev => ({
        ...prev,
        isSubmitting: false,
        result: result === ethers.ZeroAddress ? 'Not set / Zero Address' : result,
        commissionHub: commissionHub === ethers.ZeroAddress ? '' : commissionHub,
        lastUpdated: lastUpdated
      }));
      
      // Update bridge status
      if (['owner', 'commissionHub', 'lastUpdated'].includes(queryType)) {
        setBridgeStatus(prev => 
          `${prev}\n\nQuery Result:\nNFT Contract: ${contractAddress}\nToken ID: ${tokenId}\nOwner: ${result === ethers.ZeroAddress ? 'Not registered' : result}\nCommission Hub: ${commissionHub === ethers.ZeroAddress ? 'Not created' : commissionHub}\nLast Updated: ${lastUpdated}`
        );
      } else {
        setBridgeStatus(prev => 
          `${prev}\n\nQuery Result: ${result}`
        );
      }
      
    } catch (error) {
      console.error('Error querying L3 OwnerRegistry:', error);
      
      // Update state to show error
      setL3LookupQuery(prev => ({
        ...prev,
        isSubmitting: false,
        result: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`
      }));
      
      // Update bridge status
      setBridgeStatus(prev => 
        `${prev}\n\nError querying L3 OwnerRegistry: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    }
  };

  return (
    <div className="l3-lookup-section">
      <h3>L3 Owner Registry Explorer</h3>
      
      <div className="registry-info">
        <h4>Registry Contract Details</h4>
        <div className="info-item">
          <span className="info-label">Contract Address:</span>
          <span className="info-value">{registryInfo.contractAddress || 'Not set'}</span>
        </div>
        <div className="info-item">
          <span className="info-label">L2 Relay:</span>
          <span className="info-value">{registryInfo.l2relay || 'Not loaded'}</span>
        </div>
        <div className="info-item">
          <span className="info-label">Commission Hub Template:</span>
          <span className="info-value">{registryInfo.commissionHubTemplate || 'Not loaded'}</span>
        </div>
        <div className="info-item">
          <span className="info-label">Contract Owner:</span>
          <span className="info-value">{registryInfo.contractOwner || 'Not loaded'}</span>
        </div>
        <button 
          className="load-info-button" 
          onClick={loadContractInfo}
        >
          Load Contract Info
        </button>
      </div>
      
      <hr className="registry-divider" />
      
      <form className="l3-lookup-form" onSubmit={submitL3Lookup}>
        <div className="query-type-selector">
          <label htmlFor="query-type">Query Type:</label>
          <select
            id="query-type"
            value={l3LookupQuery.queryType}
            onChange={(e) => handleL3LookupChange('queryType', e.target.value as any)}
          >
            <option value="owner">Owner Lookup</option>
            <option value="commissionHub">Commission Hub</option>
            <option value="lastUpdated">Last Updated</option>
            <option value="l2relay">L2 Relay Address</option>
            <option value="commissionHubTemplate">Commission Hub Template</option>
            <option value="contractOwner">Contract Owner</option>
          </select>
        </div>
        
        {['owner', 'commissionHub', 'lastUpdated'].includes(l3LookupQuery.queryType) && (
          <>
            <div className="input-group">
              <label htmlFor="nft-contract-address">NFT Contract Address</label>
              <input
                id="nft-contract-address"
                type="text"
                value={l3LookupQuery.contractAddress}
                onChange={(e) => handleL3LookupChange('contractAddress', e.target.value)}
                placeholder="0x..."
                required
              />
            </div>
            
            <div className="input-group">
              <label htmlFor="token-id">Token ID</label>
              <input
                id="token-id"
                type="text"
                value={l3LookupQuery.tokenId}
                onChange={(e) => handleL3LookupChange('tokenId', e.target.value)}
                placeholder="1"
                required
              />
            </div>
          </>
        )}
        
        <div className="button-group">
          <button
            type="submit"
            className="l3-lookup-button"
            disabled={l3LookupQuery.isSubmitting}
          >
            {l3LookupQuery.isSubmitting ? 'Querying...' : `Query ${l3LookupQuery.queryType}`}
          </button>
        </div>
      </form>
      
      {l3LookupQuery.result && (
        <div className="l3-lookup-result">
          <h4>Query Result:</h4>
          <div className="result-info">
            {['owner', 'commissionHub', 'lastUpdated'].includes(l3LookupQuery.queryType) && (
              <>
                <p>
                  <strong>NFT Contract:</strong> 
                  <span className="result-address">{l3LookupQuery.contractAddress}</span>
                </p>
                <p>
                  <strong>Token ID:</strong> 
                  <span className="result-value">{l3LookupQuery.tokenId}</span>
                </p>
              </>
            )}
            
            {(['owner', 'l2relay', 'commissionHubTemplate', 'contractOwner'].includes(l3LookupQuery.queryType) || l3LookupQuery.result) && (
              <p>
                <strong>{l3LookupQuery.queryType === 'owner' ? 'Owner:' : 
                  l3LookupQuery.queryType === 'l2relay' ? 'L2 Relay:' :
                  l3LookupQuery.queryType === 'commissionHubTemplate' ? 'Commission Hub Template:' :
                  l3LookupQuery.queryType === 'contractOwner' ? 'Contract Owner:' : 'Result:'}</strong> 
                <span className="result-address">{l3LookupQuery.result}</span>
              </p>
            )}
            
            {(l3LookupQuery.queryType === 'commissionHub' || l3LookupQuery.commissionHub) && (
              <p>
                <strong>Commission Hub:</strong> 
                <span className="result-address">{l3LookupQuery.commissionHub || 'Not created'}</span>
              </p>
            )}
            
            {(l3LookupQuery.queryType === 'lastUpdated' || l3LookupQuery.lastUpdated) && (
              <p>
                <strong>Last Updated:</strong> 
                <span className="result-timestamp">{l3LookupQuery.lastUpdated || 'Never'}</span>
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default L3OwnerLookup; 