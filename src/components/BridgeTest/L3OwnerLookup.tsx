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
  artCommissionHub: string;
  lastUpdated: string;
  queryType: 'owner' | 'artCommissionHub' | 'lastUpdated' | 'l2relay' | 'artCommissionHubTemplate' | 'contractOwner';
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
  const { connectWallet, isConnected, networkType, switchNetwork, switchToLayer, walletAddress } = useBlockchain();
  
  // State for L3 lookup query
  const [l3LookupQuery, setL3LookupQuery] = useState<L3LookupQuery>({
    contractAddress: environment === 'testnet' ? '0xED5AF388653567Af2F388E6224dC7C4b3241C544' : '', // Default NFT contract address
    tokenId: environment === 'testnet' ? '1' : '',
    isSubmitting: false,
    result: '',
    artCommissionHub: '',
    lastUpdated: '',
    queryType: 'owner'
  });

  // State for registry info (public variables)
  const [registryInfo, setRegistryInfo] = useState({
    l2relay: '',
    artCommissionHubTemplate: '',
    contractOwner: '',
    contractAddress: environment === 'testnet' 
      ? contractConfig.addresses.l3?.testnet || ''
      : contractConfig.addresses.l3?.mainnet || ''
  });

  // State for admin functions
  const [isOwner, setIsOwner] = useState(false);
  const [newL2OwnershipRelayAddress, setNewL2OwnershipRelayAddress] = useState('');
  const [isSettingL2OwnershipRelay, setIsSettingL2OwnershipRelay] = useState(false);
  const [showAdminPanel, setShowAdminPanel] = useState(false);

  // Add state for direct registration form
  const [directRegisterParams, setDirectRegisterParams] = useState({
    chainId: '1',
    nftContract: environment === 'testnet' ? '0xED5AF388653567Af2F388E6224dC7C4b3241C544' : '',
    tokenId: '0',
    ownerAddress: '0x3afb0b4ca9ab60165e207cb14067b07a04114413',
    isSubmitting: false
  });

  // Update NFT contract address when environment changes
  useEffect(() => {
    if (environment === 'testnet') {
      setL3LookupQuery(prev => ({
        ...prev,
        contractAddress: '0xED5AF388653567Af2F388E6224dC7C4b3241C544',
        tokenId: prev.tokenId || '1'
      }));
      
      setRegistryInfo(prev => ({
        ...prev,
        contractAddress: contractConfig.addresses.l3?.testnet || ''
      }));
      
      // Autopopulate the L2OwnershipRelay address from config
      setNewL2OwnershipRelayAddress(contractConfig.addresses.l2?.testnet || '');
    } else {
      setRegistryInfo(prev => ({
        ...prev,
        contractAddress: contractConfig.addresses.l3?.mainnet || ''
      }));
      
      // Autopopulate the L2OwnershipRelay address from config
      setNewL2OwnershipRelayAddress(contractConfig.addresses.l2?.mainnet || '');
    }
  }, [environment, contractConfig.addresses.l3, contractConfig.addresses.l2]);
  
  // Check if the connected account is the contract owner
  useEffect(() => {
    if (isConnected && walletAddress && registryInfo.contractOwner) {
      setIsOwner(walletAddress.toLowerCase() === registryInfo.contractOwner.toLowerCase());
    } else {
      setIsOwner(false);
    }
  }, [isConnected, walletAddress, registryInfo.contractOwner]);

  // Update NFT contract address in direct registration form when environment changes
  useEffect(() => {
    if (environment === 'testnet') {
      setDirectRegisterParams(prev => ({
        ...prev,
        nftContract: '0xED5AF388653567Af2F388E6224dC7C4b3241C544'
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

  // Handle change in direct registration form
  const handleDirectRegisterChange = (field: string, value: string) => {
    setDirectRegisterParams(prev => ({
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

  // Add a helper function to handle common contract errors
  const handleContractError = (error: any, functionName: string) => {
    console.error(`Error calling ${functionName}:`, error);
    
    // Check if it's an ABI mismatch error
    if (
      error.message?.includes('missing revert data') || 
      error.message?.includes('invalid argument') ||
      error.message?.includes('no method with that name')
    ) {
      setBridgeStatus(prev => 
        `${prev}\n\nERROR: ABI mismatch detected. The contract interface has changed or the ABI is outdated. ` +
        `Function: ${functionName}\nError: ${error.message}\n` +
        `Please try reloading the page or contact support.`
      );
    } else {
      setBridgeStatus(prev => `${prev}\n\nError calling ${functionName}: ${error.message}`);
    }
  };

  // Load contract public variables
  const loadContractInfo = async () => {
    // Ensure we're on the right network
    if (networkType !== 'arbitrum_testnet' && environment === 'testnet') {
      setBridgeStatus('Automatically switching to Arbitrum Sepolia to query ArtCommissionHubOwners...');
      switchToLayer('l3', 'testnet');
      return;
    } else if (networkType !== 'animechain' && environment === 'mainnet') {
      setBridgeStatus('Automatically switching to Animechain L3 to query ArtCommissionHubOwners...');
      switchToLayer('l3', 'mainnet');
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
      // Get the ArtCommissionHubOwners contract address
      const l3Address = contractConfig.addresses.l3[environment];
      if (!l3Address) {
        throw new Error('ArtCommissionHubOwners contract address not set');
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
      
      // Load ABI from JSON file
      const artCommissionHubOwnersABI = abiLoader.loadABI('ArtCommissionHubOwners');
      if (!artCommissionHubOwnersABI) {
        throw new Error('Failed to load ArtCommissionHubOwners ABI');
      }
      
      // Create contract instance
      const contract = new ethers.Contract(l3Address, artCommissionHubOwnersABI, provider);
      
      // Query public variables - use try/catch for each to handle potential errors
      let l2relay = ethers.ZeroAddress;
      let artCommissionHubTemplate = ethers.ZeroAddress;
      let contractOwner = ethers.ZeroAddress;
      
      try {
        l2relay = await contract.l2OwnershipRelay();
      } catch (error) {
        handleContractError(error, 'l2OwnershipRelay()');
      }
      
      try {
        artCommissionHubTemplate = await contract.artCommissionHubTemplate();
      } catch (error) {
        handleContractError(error, 'artCommissionHubTemplate()');
      }
      
      try {
        contractOwner = await contract.owner();
      } catch (error) {
        handleContractError(error, 'owner()');
      }
      
      // Update state
      setRegistryInfo({
        l2relay,
        artCommissionHubTemplate,
        contractOwner,
        contractAddress: l3Address
      });
      
      // Autopopulate the L2OwnershipRelay form with current value
      setNewL2OwnershipRelayAddress(l2relay);
      
      setBridgeStatus(`ArtCommissionHubOwners Info:\nAddress: ${l3Address}\nL2 Relay: ${l2relay}\nCommission Hub Template: ${artCommissionHubTemplate}\nOwner: ${contractOwner}`);
      
    } catch (error) {
      console.error('Error loading contract info:', error);
      setBridgeStatus(prev => 
        `${prev}\n\nError loading ArtCommissionHubOwners info: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    }
  };

  // Submit L3 lookup query to the ArtCommissionHubOwners contract
  const submitL3Lookup = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Ensure we're on the right network
    if (networkType !== 'arbitrum_testnet' && environment === 'testnet') {
      setBridgeStatus('Automatically switching to Arbitrum Sepolia to query ArtCommissionHubOwners...');
      switchToLayer('l3', 'testnet');
      return;
    } else if (networkType !== 'animechain' && environment === 'mainnet') {
      setBridgeStatus('Automatically switching to Animechain L3 to query ArtCommissionHubOwners...');
      switchToLayer('l3', 'mainnet');
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
        artCommissionHub: '',
        lastUpdated: ''
      }));
      
      // Get the ArtCommissionHubOwners contract address
      const l3Address = contractConfig.addresses.l3[environment];
      if (!l3Address) {
        throw new Error('L3 ArtCommissionHubOwners contract address not set');
      }
      
      setBridgeStatus(prev => `${prev}\nUsing L3 ArtCommissionHubOwners address: ${l3Address}`);
      
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
      
      // Load ABI from JSON file
      const artCommissionHubOwnersABI = abiLoader.loadABI('ArtCommissionHubOwners');
      if (!artCommissionHubOwnersABI) {
        throw new Error('Failed to load ArtCommissionHubOwners ABI');
      }
      
      // Create contract instance
      const contract = new ethers.Contract(l3Address, artCommissionHubOwnersABI, provider);
      
      const { contractAddress, tokenId, queryType } = l3LookupQuery;
      
      let result = '';
      let artCommissionHub = '';
      let lastUpdated = '';
      
      // Handle token-specific queries
      if (['owner', 'artCommissionHub', 'lastUpdated'].includes(queryType)) {
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
          // Convert tokenId to BigNumber
          const tokenIdBN = ethers.toBigInt(tokenId);
          // Use chain ID 1 by default (for Ethereum)
          const chainId = 1n;
          result = await contract.lookupRegisteredOwner(chainId, contractAddress, tokenIdBN);
          
          // If we get an owner, query other info too
          if (result && result !== ethers.ZeroAddress) {
            artCommissionHub = await contract.getArtCommissionHubByOwner(chainId, contractAddress, tokenIdBN);
            const lastUpdatedTimestamp = await contract.getLastUpdated(chainId, contractAddress, tokenIdBN);
            lastUpdated = formatTimestamp(Number(lastUpdatedTimestamp));
          }
        } else if (queryType === 'artCommissionHub') {
          setBridgeStatus(prev => `${prev}\nQuerying commission hub for NFT contract ${contractAddress} and token ID ${tokenId}...`);
          // Convert tokenId to BigNumber
          const tokenIdBN = ethers.toBigInt(tokenId);
          // Use chain ID 1 by default (for Ethereum)
          const chainId = 1n;
          artCommissionHub = await contract.getArtCommissionHubByOwner(chainId, contractAddress, tokenIdBN);
          
          // If we get a commission hub, query other info too
          if (artCommissionHub && artCommissionHub !== ethers.ZeroAddress) {
            result = await contract.lookupRegisteredOwner(chainId, contractAddress, tokenIdBN);
            const lastUpdatedTimestamp = await contract.getLastUpdated(chainId, contractAddress, tokenIdBN);
            lastUpdated = formatTimestamp(Number(lastUpdatedTimestamp));
          }
        } else if (queryType === 'lastUpdated') {
          setBridgeStatus(prev => `${prev}\nQuerying last updated timestamp for NFT contract ${contractAddress} and token ID ${tokenId}...`);
          // Convert tokenId to BigNumber
          const tokenIdBN = ethers.toBigInt(tokenId);
          // Use chain ID 1 by default (for Ethereum)
          const chainId = 1n;
          const lastUpdatedTimestamp = await contract.getLastUpdated(chainId, contractAddress, tokenIdBN);
          lastUpdated = formatTimestamp(Number(lastUpdatedTimestamp));
          
          // Also get the owner and commission hub
          result = await contract.lookupRegisteredOwner(chainId, contractAddress, tokenIdBN);
          if (result && result !== ethers.ZeroAddress) {
            artCommissionHub = await contract.getArtCommissionHubByOwner(chainId, contractAddress, tokenIdBN);
          }
        }
      }
      // Handle contract-level queries (will be shown separately in the registry info section)
      else if (['l2relay', 'artCommissionHubTemplate', 'contractOwner'].includes(queryType)) {
        // These queries don't need NFT contract or token ID
        if (queryType === 'l2relay') {
          setBridgeStatus(prev => `${prev}\nQuerying L2 relay address...`);
          try {
            result = await contract.l2OwnershipRelay();
          } catch (error) {
            handleContractError(error, 'l2OwnershipRelay()');
            throw error;
          }
        } else if (queryType === 'artCommissionHubTemplate') {
          setBridgeStatus(prev => `${prev}\nQuerying commission hub template address...`);
          try {
            result = await contract.artCommissionHubTemplate();
          } catch (error) {
            handleContractError(error, 'artCommissionHubTemplate()');
            throw error;
          }
        } else if (queryType === 'contractOwner') {
          setBridgeStatus(prev => `${prev}\nQuerying contract owner address...`);
          try {
            result = await contract.owner();
          } catch (error) {
            handleContractError(error, 'owner()');
            throw error;
          }
        }
        
        // Update registry info
        await loadContractInfo();
      }
      
      // Update state with result
      setL3LookupQuery(prev => ({
        ...prev,
        isSubmitting: false,
        result: result === ethers.ZeroAddress ? 'Not set / Zero Address' : result,
        artCommissionHub: artCommissionHub === ethers.ZeroAddress ? '' : artCommissionHub,
        lastUpdated: lastUpdated
      }));
      
      // Update bridge status
      if (['owner', 'artCommissionHub', 'lastUpdated'].includes(queryType)) {
        setBridgeStatus(prev => 
          `${prev}\n\nQuery Result:\nNFT Contract: ${contractAddress}\nToken ID: ${tokenId}\nOwner: ${result === ethers.ZeroAddress ? 'Not registered' : result}\nCommission Hub: ${artCommissionHub === ethers.ZeroAddress ? 'Not created' : artCommissionHub}\nLast Updated: ${lastUpdated}`
        );
      } else {
        setBridgeStatus(prev => 
          `${prev}\n\nQuery Result: ${result}`
        );
      }
      
    } catch (error) {
      console.error('Error querying L3 ArtCommissionHubOwners:', error);
      
      // Update state to show error
      setL3LookupQuery(prev => ({
        ...prev,
        isSubmitting: false,
        result: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`
      }));
      
      // Update bridge status
      setBridgeStatus(prev => 
        `${prev}\n\nError querying L3 ArtCommissionHubOwners: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    }
  };

  // Set L2 Relay address in the ArtCommissionHubOwners contract
  const setL2OwnershipRelayAddress = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Ensure we're on the right network
    if (networkType !== 'arbitrum_testnet' && environment === 'testnet') {
      setBridgeStatus('Automatically switching to Arbitrum Sepolia...');
      switchToLayer('l3', 'testnet');
      return;
    } else if (networkType !== 'animechain' && environment === 'mainnet') {
      setBridgeStatus('Automatically switching to Animechain L3...');
      switchToLayer('l3', 'mainnet');
      return;
    }
    
    // Validate the L2 relay address
    if (!ethers.isAddress(newL2OwnershipRelayAddress)) {
      setBridgeStatus(prev => `${prev}\n\nError: Invalid L2 relay address format`);
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
      setIsSettingL2OwnershipRelay(true);
      
      // Get the ArtCommissionHubOwners contract address
      const l3Address = contractConfig.addresses.l3[environment];
      if (!l3Address) {
        throw new Error('L3 ArtCommissionHubOwners contract address not set');
      }
      
      // Create a provider and signer
      const ethereum = window.ethereum as any;
      const provider = new ethers.BrowserProvider(ethereum);
      const signer = await provider.getSigner();
      
      // Load ABI for ArtCommissionHubOwners
      let artCommissionHubOwnersABI;
      try {
        artCommissionHubOwnersABI = abiLoader.loadABI('ArtCommissionHubOwners');
      } catch (error) {
        console.log('Could not load ArtCommissionHubOwners ABI, using minimal ABI with setL2OwnershipRelay');
        artCommissionHubOwnersABI = [
          "function l2OwnershipRelay() view returns (address)",
          "function owner() view returns (address)",
          "function setL2OwnershipRelay(address _new_l2relay) external"
        ];
      }
      
      // Create contract instance with signer
      const contract = new ethers.Contract(l3Address, artCommissionHubOwnersABI, signer);
      
      // We'll attempt to set the L2 relay address regardless of ownership
      // Note: The contract will reject this call if the sender is not the owner
      
      // Set the L2 relay address
      setBridgeStatus(prev => `${prev}\n\nSetting L2 relay address to ${newL2OwnershipRelayAddress}...`);
      const tx = await contract.setL2OwnershipRelay(newL2OwnershipRelayAddress);
      
      // Wait for transaction to be mined
      setBridgeStatus(prev => `${prev}\nTransaction submitted. Waiting for confirmation...`);
      const receipt = await tx.wait();
      
      // Update status and reload contract info
      setBridgeStatus(prev => `${prev}\nTransaction confirmed! L2 relay address updated successfully.`);
      await loadContractInfo();
      
    } catch (error) {
      console.error('Error setting L2 relay address:', error);
      
      // Provide a more user-friendly error message for the ownership check failure
      if (error instanceof Error && 
          (error.message.includes("Only owner can set L2 relay") || 
           error.message.includes("execution reverted"))) {
        setBridgeStatus(prev => 
          `${prev}\n\nTransaction failed: Only the contract owner can set the L2 relay address. This is enforced by the contract's code.`
        );
      } else {
        setBridgeStatus(prev => 
          `${prev}\n\nError setting L2 relay address: ${error instanceof Error ? error.message : 'Unknown error'}`
        );
      }
    } finally {
      setIsSettingL2OwnershipRelay(false);
    }
  };

  // Direct call to registerNFTOwnerFromParentChain (bypassing L2 relay for testing)
  const callRegisterNFTOwnerFromParentChain = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Ensure we're on the right network
    if (networkType !== 'arbitrum_testnet' && environment === 'testnet') {
      setBridgeStatus('Automatically switching to Arbitrum Sepolia...');
      switchToLayer('l3', 'testnet');
      return;
    } else if (networkType !== 'animechain' && environment === 'mainnet') {
      setBridgeStatus('Automatically switching to Animechain L3...');
      switchToLayer('l3', 'mainnet');
      return;
    }
    
    // Validate input parameters
    if (!ethers.isAddress(directRegisterParams.nftContract)) {
      setBridgeStatus(prev => `${prev}\n\nError: Invalid NFT contract address format`);
      return;
    }
    
    if (!ethers.isAddress(directRegisterParams.ownerAddress)) {
      setBridgeStatus(prev => `${prev}\n\nError: Invalid owner address format`);
      return;
    }
    
    // Validate chain ID and token ID as numbers
    let chainId: number;
    let tokenId: number;
    
    try {
      chainId = parseInt(directRegisterParams.chainId);
      if (isNaN(chainId) || chainId <= 0) {
        throw new Error("Invalid chain ID");
      }
      
      tokenId = parseInt(directRegisterParams.tokenId);
      if (isNaN(tokenId) || tokenId < 0) {
        throw new Error("Invalid token ID");
      }
    } catch (error) {
      setBridgeStatus(prev => `${prev}\n\nError: ${error instanceof Error ? error.message : 'Invalid numeric input'}`);
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
      setDirectRegisterParams(prev => ({ ...prev, isSubmitting: true }));
      
      // Get the ArtCommissionHubOwners contract address
      const l3Address = contractConfig.addresses.l3[environment];
      if (!l3Address) {
        throw new Error('L3 ArtCommissionHubOwners contract address not set');
      }
      
      // Create a provider and signer
      const ethereum = window.ethereum as any;
      const provider = new ethers.BrowserProvider(ethereum);
      const signer = await provider.getSigner();
      
      // Simplified ABI with no parameter names to avoid ethers.js parsing issues
      const artCommissionHubOwnersABI = [
        "function registerNFTOwnerFromParentChain(uint256, address, uint256, address) external",
        "function l2relay() view returns (address)",
        "function owner() view returns (address)",
        "function lookupRegisteredOwner(uint256, address, uint256) view returns (address)"
      ];
      
      // Create contract instance with signer
      const contract = new ethers.Contract(l3Address, artCommissionHubOwnersABI, signer);
      
      // Convert parameters to appropriate types
      const chainIdBN = ethers.toBigInt(chainId);
      const tokenIdBN = ethers.toBigInt(tokenId);
      
      // Get the L2 relay address for the warning message
      let l2OwnershipRelayAddress;
      try {
        l2OwnershipRelayAddress = await contract.l2relay();
      } catch (error) {
        console.error("Error getting L2 relay address:", error);
        l2OwnershipRelayAddress = "unknown";
      }
      
      setBridgeStatus(prev => 
        `${prev}\n\nAttempting direct call to registerNFTOwnerFromParentChain:
        Chain ID: ${chainIdBN}
        NFT Contract: ${directRegisterParams.nftContract}
        Token ID: ${tokenIdBN}
        Owner: ${directRegisterParams.ownerAddress}
        
        NOTE: This call will likely fail unless your wallet is the L2 Relay address (${l2OwnershipRelayAddress})`
      );
      
      // Log the exact parameters for debugging
      console.log("Calling registerNFTOwnerFromParentChain with params:", {
        chainId: chainIdBN.toString(),
        nftContract: directRegisterParams.nftContract,
        tokenId: tokenIdBN.toString(),
        owner: directRegisterParams.ownerAddress
      });
      
      // Attempt the transaction
      const tx = await contract.registerNFTOwnerFromParentChain(
        chainIdBN,
        directRegisterParams.nftContract,
        tokenIdBN,
        directRegisterParams.ownerAddress
      );
      
      // Wait for transaction to be mined
      setBridgeStatus(prev => `${prev}\nTransaction submitted. Waiting for confirmation...`);
      const receipt = await tx.wait();
      
      // Update status and reload contract info
      setBridgeStatus(prev => `${prev}\nTransaction confirmed! Owner registered successfully.`);
      
      // Query the registered owner to confirm - use same parameter order as in the ABI
      try {
        const registeredOwner = await contract.lookupRegisteredOwner(
          chainIdBN,                              // Chain ID
          directRegisterParams.nftContract,       // NFT Contract
          tokenIdBN                               // Token ID
        );
        
        setBridgeStatus(prev => `${prev}\nVerification: Registered owner is now ${registeredOwner}`);
      } catch (lookupError) {
        console.error("Error verifying registration:", lookupError);
        setBridgeStatus(prev => `${prev}\nCould not verify registration: ${lookupError instanceof Error ? lookupError.message : 'Unknown error'}`);
      }
      
    } catch (error) {
      console.error('Error with direct registration:', error);
      
      // Provide a more user-friendly error message
      if (error instanceof Error) {
        if (error.message.includes("Only L2OwnershipRelay can register NFT owners") || 
            error.message.includes("execution reverted")) {
          setBridgeStatus(prev => 
            `${prev}\n\nTransaction failed: Only the L2OwnershipRelay contract can call this function directly. ` +
            `This is enforced by the contract's code (assert msg.sender == self.l2relay).`
          );
        } else if (error.message.includes("no matching fragment")) {
          setBridgeStatus(prev => 
            `${prev}\n\nTransaction failed: ABI mismatch error. ` +
            `Please check developer console for more details and report this issue.`          );
        } else {
          setBridgeStatus(prev => `${prev}\n\nError with direct registration: ${error.message}`);
        }
      } else {
        setBridgeStatus(prev => `${prev}\n\nUnknown error with direct registration`);
      }
    } finally {
      setDirectRegisterParams(prev => ({ ...prev, isSubmitting: false }));
    }
  };

  return (
    <div className="l3-owner-lookup-container">
      <h3>Owner Registry ({environment === 'testnet' ? 'Arbitrum Sepolia' : 'Animechain L3'})</h3>
      
      <div className="explorer-links">
        {environment === 'testnet' && (
          <a 
            href={`https://sepolia.arbiscan.io/address/${contractConfig.addresses.l3.testnet}`} 
            target="_blank" 
            rel="noopener noreferrer"
            className="explorer-link"
          >
            View ArtCommissionHubOwners on Arbitrum Sepolia
          </a>
        )}
        {environment === 'mainnet' && contractConfig.addresses.l3.mainnet && (
          <a 
            href={`https://explorer-animechain-39xf6m45e3.t.conduit.xyz/address/${contractConfig.addresses.l3.mainnet}`} 
            target="_blank" 
            rel="noopener noreferrer"
            className="explorer-link"
          >
            View ArtCommissionHubOwners on Animechain L3
          </a>
        )}
      </div>

      <div className="l3-form-container">
        <div className="network-action-bar">
          <button 
            className="network-switch-button" 
            onClick={() => switchToLayer('l3', environment)}
            title={`Switch to ${environment === 'testnet' ? 'Arbitrum Sepolia' : 'Animechain L3'} to connect to ArtCommissionHubOwners`}
          >
            Switch to {environment === 'testnet' ? 'Arbitrum Sepolia' : 'Animechain L3'}
          </button>
          <div className="network-status">
            {((networkType === 'arbitrum_testnet' && environment === 'testnet') || 
              (networkType === 'animechain' && environment === 'mainnet')) ? 
              <span className="connected-status">✓ Connected to {environment === 'testnet' ? 'Arbitrum Sepolia' : 'Animechain L3'}</span> : 
              <span className="disconnected-status">Not connected to {environment === 'testnet' ? 'Arbitrum Sepolia' : 'Animechain L3'}</span>
            }
          </div>
        </div>
        
        <div className="registry-info">
          <h4>ArtCommissionHubOwners Contract</h4>
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
            <span className="info-value">{registryInfo.artCommissionHubTemplate || 'Not loaded'}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Contract Owner:</span>
            <span className="info-value">{registryInfo.contractOwner || 'Not loaded'}</span>
            {isOwner && <span className="owner-badge">You are the owner</span>}
          </div>
          <button 
            className="load-info-button" 
            onClick={loadContractInfo}
          >
            Load Contract Info
          </button>
        </div>
        
        <div className="admin-toggle-container">
          <button 
            className="admin-toggle-button" 
            onClick={() => setShowAdminPanel(!showAdminPanel)}
            aria-expanded={showAdminPanel}
          >
            {showAdminPanel ? 'Hide Admin Panel' : 'Show Admin Panel'}
          </button>
        </div>
        
        {showAdminPanel && (
          <div className="admin-panel">
            <h4>Admin Controls</h4>
            
            <h5>L2 Relay Configuration</h5>
            <form onSubmit={setL2OwnershipRelayAddress} className="l2-relay-form">
              <div className="input-group">
                <label htmlFor="l2-relay-address">
                  L2 Relay Address 
                  {!isOwner && <span className="owner-required-badge">Owner Required</span>}
                </label>
                <input
                  type="text"
                  id="l2-relay-address"
                  value={newL2OwnershipRelayAddress}
                  onChange={(e) => setNewL2OwnershipRelayAddress(e.target.value)}
                  placeholder={contractConfig.addresses.l2?.[environment] || "Enter L2 relay address"}
                  disabled={isSettingL2OwnershipRelay}
                />
              </div>

              <div className="button-group">
                <button 
                  type="submit" 
                  className="admin-button"
                  disabled={isSettingL2OwnershipRelay}
                  title={!isOwner ? "Note: Transaction will fail due to contract-side owner check" : ""}
                >
                  {isSettingL2OwnershipRelay ? 'Setting L2 Relay...' : 'Set L2 Relay Address'}
                </button>
              </div>

              {!isOwner && (
                <p className="owner-note">Note: Only the contract owner can set the L2 relay address. The transaction will be rejected by the contract if you are not the owner.</p>
              )}
            </form>
            
            <hr className="admin-divider" />
            
            <h5>Direct NFT Registration (Bypass L2 Relay)</h5>
            <div className="direct-registration-info">
              <p className="warning-note">
                This bypasses the normal flow and attempts to call <code>registerNFTOwnerFromParentChain</code> directly.
                The call will likely fail unless your wallet is the L2 Relay address set in the contract.
              </p>
            </div>
            
            <form onSubmit={callRegisterNFTOwnerFromParentChain} className="direct-register-form">
              <div className="input-group">
                <label htmlFor="chain-id">Chain ID</label>
                <input
                  type="text"
                  id="chain-id"
                  value={directRegisterParams.chainId}
                  onChange={(e) => handleDirectRegisterChange('chainId', e.target.value)}
                  placeholder="1"
                />
              </div>
              
              <div className="input-group">
                <label htmlFor="nft-contract-direct">NFT Contract Address</label>
                <input
                  type="text"
                  id="nft-contract-direct"
                  value={directRegisterParams.nftContract}
                  onChange={(e) => handleDirectRegisterChange('nftContract', e.target.value)}
                  placeholder="0xED5AF388653567Af2F388E6224dC7C4b3241C544"
                />
              </div>
              
              <div className="input-group">
                <label htmlFor="token-id-direct">Token ID</label>
                <input
                  type="text"
                  id="token-id-direct"
                  value={directRegisterParams.tokenId}
                  onChange={(e) => handleDirectRegisterChange('tokenId', e.target.value)}
                  placeholder="0"
                />
              </div>
              
              <div className="input-group">
                <label htmlFor="owner-address">Owner Address</label>
                <input
                  type="text"
                  id="owner-address"
                  value={directRegisterParams.ownerAddress}
                  onChange={(e) => handleDirectRegisterChange('ownerAddress', e.target.value)}
                  placeholder="0x3afb0b4ca9ab60165e207cb14067b07a04114413"
                />
              </div>
              
              <div className="button-group">
                <button
                  type="submit"
                  className="admin-button"
                  disabled={directRegisterParams.isSubmitting}
                >
                  {directRegisterParams.isSubmitting ? 'Registering...' : 'Register Directly'}
                </button>
              </div>
            </form>
          </div>
        )}
        
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
              <option value="artCommissionHub">Commission Hub</option>
              <option value="lastUpdated">Last Updated</option>
              <option value="l2relay">L2 Relay Address</option>
              <option value="artCommissionHubTemplate">Commission Hub Template</option>
              <option value="contractOwner">Contract Owner</option>
            </select>
          </div>
          
          {['owner', 'artCommissionHub', 'lastUpdated'].includes(l3LookupQuery.queryType) && (
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
              {['owner', 'artCommissionHub', 'lastUpdated'].includes(l3LookupQuery.queryType) && (
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
              
              {(['owner', 'l2relay', 'artCommissionHubTemplate', 'contractOwner'].includes(l3LookupQuery.queryType) || l3LookupQuery.result) && (
                <p>
                  <strong>{l3LookupQuery.queryType === 'owner' ? 'Owner:' : 
                    l3LookupQuery.queryType === 'l2relay' ? 'L2 Relay:' :
                    l3LookupQuery.queryType === 'artCommissionHubTemplate' ? 'Commission Hub Template:' :
                    l3LookupQuery.queryType === 'contractOwner' ? 'Contract Owner:' : 'Result:'}</strong> 
                  <span className="result-address">{l3LookupQuery.result}</span>
                </p>
              )}
              
              {(l3LookupQuery.queryType === 'artCommissionHub' || l3LookupQuery.artCommissionHub) && (
                <p>
                  <strong>Commission Hub:</strong> 
                  <span className="result-address">{l3LookupQuery.artCommissionHub || 'Not created'}</span>
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
    </div>
  );
};

export default L3OwnerLookup; 
