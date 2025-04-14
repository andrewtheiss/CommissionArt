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
    commissionHub: ''
  });

  // Update NFT contract address when environment changes
  useEffect(() => {
    if (environment === 'testnet') {
      setL3LookupQuery(prev => ({
        ...prev,
        contractAddress: '0x3cF3dada5C03F32F0b77AAE7Ae19F61Ab89dbD06',
        tokenId: prev.tokenId || '1'
      }));
    }
  }, [environment]);
  
  // Handle L3 lookup form change
  const handleL3LookupChange = (field: keyof L3LookupQuery, value: string) => {
    setL3LookupQuery(prev => ({
      ...prev,
      [field]: value
    }));
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
        commissionHub: ''
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
        ownerRegistryABI = abiLoader.loadABI('OwnerRegistry') || abiLoader.loadABI('Registry');
      } catch (error) {
        console.log('Could not load OwnerRegistry ABI, using minimal ABI');
      }
      
      // If no ABI is found, use a minimal ABI with just the functions we need
      if (!ownerRegistryABI) {
        ownerRegistryABI = [
          {
            "inputs": [
              {
                "name": "nft_contract",
                "type": "address"
              },
              {
                "name": "token_id",
                "type": "uint256"
              }
            ],
            "name": "lookupRegsiteredOwner",
            "outputs": [
              {
                "name": "",
                "type": "address"
              }
            ],
            "stateMutability": "view",
            "type": "function"
          },
          {
            "inputs": [
              {
                "name": "nft_contract",
                "type": "address"
              },
              {
                "name": "token_id",
                "type": "uint256"
              }
            ],
            "name": "getCommissionHubByOwner",
            "outputs": [
              {
                "name": "",
                "type": "address"
              }
            ],
            "stateMutability": "view",
            "type": "function"
          }
        ];
      }
      
      // Create contract instance
      const contract = new ethers.Contract(l3Address, ownerRegistryABI, provider);
      
      // Get NFT contract address and token ID from form
      const { contractAddress, tokenId } = l3LookupQuery;
      
      // Check that contract address is valid
      if (!ethers.isAddress(contractAddress)) {
        throw new Error('Invalid NFT contract address');
      }
      
      // Check that token ID is valid
      if (!tokenId || isNaN(parseInt(tokenId))) {
        throw new Error('Invalid token ID');
      }
      
      setBridgeStatus(prev => `${prev}\nQuerying registered owner for NFT contract ${contractAddress} and token ID ${tokenId}...`);
      
      // Call the lookupRegsiteredOwner function
      const owner = await contract.lookupRegsiteredOwner(contractAddress, tokenId);
      
      // If we get an owner, also try to query the commission hub
      let commissionHub = ethers.ZeroAddress;
      if (owner && owner !== ethers.ZeroAddress) {
        try {
          commissionHub = await contract.getCommissionHubByOwner(contractAddress, tokenId);
        } catch (error) {
          console.error('Failed to query commission hub:', error);
        }
      }
      
      // Update state with result
      setL3LookupQuery(prev => ({
        ...prev,
        isSubmitting: false,
        result: owner === ethers.ZeroAddress ? 'No registered owner found' : owner,
        commissionHub: commissionHub === ethers.ZeroAddress ? '' : commissionHub
      }));
      
      // Update bridge status
      setBridgeStatus(prev => 
        `${prev}\n\nRegistered Owner Lookup Result:\nNFT Contract: ${contractAddress}\nToken ID: ${tokenId}\nOwner: ${owner === ethers.ZeroAddress ? 'Not registered' : owner}\nCommission Hub: ${commissionHub === ethers.ZeroAddress ? 'Not created' : commissionHub}`
      );
      
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
      <h3>L3 Owner Registry Lookup</h3>
      
      <form className="l3-lookup-form" onSubmit={submitL3Lookup}>
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
        
        <div className="button-group">
          <button
            type="submit"
            className="primary-button l3-lookup-button"
            disabled={l3LookupQuery.isSubmitting}
          >
            {l3LookupQuery.isSubmitting ? 'Looking Up...' : 'Lookup Registered Owner'}
          </button>
        </div>
      </form>
      
      {l3LookupQuery.result && (
        <div className="l3-lookup-result">
          <h4>Lookup Result:</h4>
          <div className="result-info">
            <p>
              <strong>Owner:</strong> 
              <span className="result-address">{l3LookupQuery.result}</span>
            </p>
            {l3LookupQuery.commissionHub && (
              <p>
                <strong>Commission Hub:</strong> 
                <span className="result-address">{l3LookupQuery.commissionHub}</span>
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default L3OwnerLookup; 