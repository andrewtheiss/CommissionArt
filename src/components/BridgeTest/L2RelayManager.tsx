import React, { useState, useEffect } from 'react';
import { ethers } from 'ethers';
import { useBlockchain } from '../../utils/BlockchainContext';
import { toast } from 'react-hot-toast';
import './BridgeTest.css';
import useContractConfig from '../../utils/useContractConfig';
import abiLoader from '../../utils/abiLoader';

// Alias addition constant
const ALIAS_ADDITION = "0x1111000000000000000000000000000000001111";

// Extend Window interface
declare global {
  interface Window {
    ethereum?: any;
  }
}

const L2RelayManager: React.FC = () => {
  const { isConnected, walletAddress, networkType, switchNetwork, switchToLayer, connectWallet } = useBlockchain();
  const { getContract, loading: configLoading, error: configError } = useContractConfig();
  
  // State variables
  const [l2RelayAddress, setL2RelayAddress] = useState<string>("");
  const [l1ContractAddress, setL1ContractAddress] = useState<string>("");
  const [aliasedAddress, setAliasedAddress] = useState<string>("");
  const [ownerAddress, setOwnerAddress] = useState<string>("");
  const [currentL1ChainId, setCurrentL1ChainId] = useState<number>(0);
  const [currentSender, setCurrentSender] = useState<string>("");
  
  // Form state
  const [newSenderAddress, setNewSenderAddress] = useState<string>("");
  const [newChainId, setNewChainId] = useState<string>("1"); // Default to Ethereum mainnet
  const [isUpdating, setIsUpdating] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [environment, setEnvironment] = useState<'testnet' | 'mainnet'>('testnet');

  // Update newSenderAddress when aliasedAddress changes
  useEffect(() => {
    if (aliasedAddress) {
      setNewSenderAddress(aliasedAddress);
    }
  }, [aliasedAddress]);

  // Compute aliased address from L1 address
  const computeAliasedAddress = (l1Address: string): string => {
    try {
      if (!ethers.isAddress(l1Address)) return "";
      
      // The formula is: L2 alias = L1 address + 0x1111000000000000000000000000000000001111
      const l1BigInt = ethers.toBigInt(l1Address);
      const aliasBigInt = ethers.toBigInt(ALIAS_ADDITION);
      const result = l1BigInt + aliasBigInt;
      // Convert BigInt to hex string with 0x prefix
      const aliased = "0x" + result.toString(16);
      
      return aliased;
    } catch (error) {
      console.error("Error computing aliased address:", error);
      return "";
    }
  };

  // Load contract details from contract config
  useEffect(() => {
    const loadContractInfo = async () => {
      try {
        setIsLoading(true);
        
        if (configLoading) {
          return; // Wait for config to load
        }
        
        if (configError) {
          console.error("Contract configuration error:", configError);
          toast.error("Failed to load contract configuration");
          return;
        }
        
        // Get current environment based on network
        const currentEnv: 'testnet' | 'mainnet' = networkType === 'arbitrum_mainnet' ? 'mainnet' : 'testnet';
        setEnvironment(currentEnv);
        
        // Get L2 Relay address from contract config
        const l2Contract = getContract(currentEnv, 'l2');
        const relayAddress = l2Contract?.address || '';
        
        if (!relayAddress) {
          console.error("L2 relay address not found in configuration");
          toast.error("L2 relay address not configured");
          return;
        }
        
        setL2RelayAddress(relayAddress);
        
        // Get L1 contract address
        const l1Contract = getContract(currentEnv, 'l1');
        const l1Address = l1Contract?.address || '';
        
        if (!l1Address) {
          console.error("L1 contract address not found in configuration");
          toast.error("L1 contract address not configured");
          return;
        }
        
        setL1ContractAddress(l1Address);
        
        // Calculate the aliased address
        if (l1Address) {
          const aliased = computeAliasedAddress(l1Address);
          setAliasedAddress(aliased);
        }
        
        // If connected, fetch contract data
        if (isConnected && relayAddress && ethers.isAddress(relayAddress) && window.ethereum) {
          try {
            // Load ABI from the JSON file
            const L2RelayABI = abiLoader.loadABI('L2Relay');
            if (!L2RelayABI) {
              throw new Error('Failed to load L2Relay ABI');
            }
            
            // Create provider and contract instance
            const provider = new ethers.BrowserProvider(window.ethereum);
            const contract = new ethers.Contract(relayAddress, L2RelayABI, provider);
            
            // Get owner with error handling
            try {
              const owner = await contract.owner();
              setOwnerAddress(owner);
            } catch (ownerError) {
              console.warn("Could not fetch contract owner:", ownerError);
              setOwnerAddress("");
            }
            
            // Use L1 chain ID from our form default initially
            const chainId = Number(newChainId);
            setCurrentL1ChainId(chainId);
            
            // Get current sender for this chain ID with error handling
            try {
              // Use crossChainRegistryAddressByChainId instead of crossChainSenders
              const sender = await contract.crossChainRegistryAddressByChainId(chainId);
              setCurrentSender(sender);
            } catch (senderError) {
              console.warn("Could not fetch cross chain sender:", senderError);
              setCurrentSender("");
            }
          } catch (contractError) {
            console.warn("Error initializing contract:", contractError);
          }
        } else {
          console.info("Skipping contract data fetch - prerequisites not met", {
            isConnected,
            relayAddress,
            validAddress: relayAddress ? ethers.isAddress(relayAddress) : false,
            hasEthereum: !!window.ethereum
          });
        }
      } catch (error) {
        console.error("Error loading L2 Relay info:", error);
        // Don't show toast on first load failures - too disruptive
        if (ownerAddress || currentSender) {
          toast.error("Failed to load L2 Relay contract information");
        }
      } finally {
        setIsLoading(false);
      }
    };
    
    loadContractInfo();
  }, [isConnected, networkType, ownerAddress, currentSender, configLoading, configError, getContract, newChainId]);

  // Handle form submission
  const handleUpdateSender = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!newSenderAddress || !ethers.isAddress(newSenderAddress)) {
      toast.error("Please enter a valid address for the sender");
      return;
    }
    
    if (!newChainId || isNaN(Number(newChainId)) || Number(newChainId) <= 0) {
      toast.error("Please enter a valid chain ID");
      return;
    }
    
    try {
      setIsUpdating(true);
      
      // Check if wallet is connected
      if (!isConnected) {
        try {
          await connectWallet();
          toast("Please connect your wallet to continue");
          setIsUpdating(false);
          return;
        } catch (walletError) {
          console.error("Error connecting wallet:", walletError);
          toast.error("Please install and connect a Web3 wallet like MetaMask to proceed");
          setIsUpdating(false);
          return;
        }
      }
      
      // Check if we have ethereum provider
      if (!window.ethereum) {
        toast.error("Web3 provider not found. Please install MetaMask or another Web3 wallet");
        setIsUpdating(false);
        return;
      }

      // Check if we're on the right network
      if (
        (environment === 'testnet' && networkType !== 'arbitrum_testnet') ||
        (environment === 'mainnet' && networkType !== 'arbitrum_mainnet')
      ) {
        toast.loading(`Switching to Arbitrum ${environment === 'mainnet' ? 'One' : 'Sepolia'}...`);
        
        try {
          await switchToLayer('l2', environment);
          toast.dismiss();
          toast.success(`Switched to Arbitrum ${environment === 'mainnet' ? 'One' : 'Sepolia'}`);
        } catch (switchError) {
          toast.dismiss();
          toast.error(`Failed to switch network: ${switchError instanceof Error ? switchError.message : 'Unknown error'}`);
          setIsUpdating(false);
          return;
        }
      }
      
      // Now update the L2 Relay contract
      try {
        // Create provider and signer
        const provider = new ethers.BrowserProvider(window.ethereum);
        const signer = await provider.getSigner();
        
        // Load ABI and create contract instance
        const L2RelayABI = abiLoader.loadABI('L2Relay');
        if (!L2RelayABI) {
          throw new Error('Failed to load L2Relay ABI');
        }
        
        const contract = new ethers.Contract(l2RelayAddress, L2RelayABI, signer);
        
        // Check if they really want to update the config
        const chainId = Number(newChainId);
        let needsConfirmation = false;
        let confirmationMessage = '';
        
        // Check if the current sender exists and we're changing it
        if (currentSender && currentSender !== ethers.ZeroAddress && currentSender.toLowerCase() !== newSenderAddress.toLowerCase()) {
          needsConfirmation = true;
          confirmationMessage = `You are about to replace the existing cross-chain sender (${currentSender}) for chain ID ${chainId} with a new sender (${newSenderAddress}). Are you sure?`;
        }
        
        if (needsConfirmation) {
          const isConfirmed = window.confirm(confirmationMessage);
          if (!isConfirmed) {
            toast.error("Update canceled");
            setIsUpdating(false);
            return;
          }
        }
        
        // Check if the user is the contract owner
        const owner = await contract.owner();
        if (!walletAddress || owner.toLowerCase() !== walletAddress.toLowerCase()) {
          toast.error("You are not the owner of this contract");
          setIsUpdating(false);
          return;
        }
        
        toast.loading(`Updating L2 Relay contract...`);
        
        // Call updateCrossChainQueryOwnerContract function with correct parameters
        const tx = await contract.updateCrossChainQueryOwnerContract(
          newSenderAddress,
          chainId
        );
        
        toast.dismiss();
        toast.loading(`Transaction submitted: ${tx.hash}`);
        
        // Wait for transaction to be mined
        await tx.wait();
        
        toast.dismiss();
        toast.success("Cross-chain sender updated successfully");
        
        // Refresh contract info
        setCurrentL1ChainId(chainId);
        setCurrentSender(newSenderAddress);
        
      } catch (error) {
        toast.dismiss();
        console.error("Error updating L2 Relay:", error);
        toast.error(`Failed to update L2 Relay: ${error instanceof Error ? error.message : 'Unknown error'}`);
      } finally {
        setIsUpdating(false);
      }
    } catch (error) {
      console.error("Error updating cross-chain sender:", error);
      toast.error("Failed to update cross-chain sender");
    }
  };

  const handleSwitchNetwork = async () => {
    try {
      await switchToLayer('l2', environment);
      toast.success(`Switched to ${environment === 'testnet' ? 'Arbitrum Sepolia' : 'Arbitrum One'}`);
    } catch (error) {
      console.error("Error switching network:", error);
      toast.error(`Failed to switch to ${environment === 'testnet' ? 'Arbitrum Sepolia' : 'Arbitrum One'}`);
    }
  };

  if (isLoading) {
    return <div className="contract-section">Loading L2 Relay information...</div>;
  }

  // Determine if we're on the correct network
  const isCorrectNetwork = (environment === 'testnet' && networkType === 'arbitrum_testnet') || 
                           (environment === 'mainnet' && networkType === 'arbitrum_mainnet');

  return (
    <div className="l2-relay-manager-section">
      <h3>L2 Relay Manager</h3>
      
      <div className="explorer-links">
        <a 
          href={`https://sepolia.arbiscan.io/address/${getContract('testnet', 'l2')?.address || l2RelayAddress}`} 
          target="_blank" 
          rel="noopener noreferrer"
          className="explorer-link"
        >
          View L2Relay on Sepolia Arb
        </a>
        <a 
          href={`https://arbiscan.io/address/${getContract('mainnet', 'l2')?.address || l2RelayAddress}`} 
          target="_blank" 
          rel="noopener noreferrer"
          className="explorer-link"
        >
          View L2Relay on Arbitrum
        </a>
      </div>
      
      <div className="network-status-container">
        <div className={`network-status ${isCorrectNetwork ? 'network-correct' : 'network-incorrect'}`}>
          <span className="status-indicator"></span>
          <span className="status-text">
            {isCorrectNetwork 
              ? `Connected to ${environment === 'testnet' ? 'Arbitrum Sepolia' : 'Arbitrum One'}` 
              : `Not on ${environment === 'testnet' ? 'Arbitrum Sepolia' : 'Arbitrum One'} network`}
          </span>
        </div>
        {!isCorrectNetwork && (
          <button 
            className="network-switch-button"
            onClick={handleSwitchNetwork}
          >
            Switch to {environment === 'testnet' ? 'Arbitrum Sepolia' : 'Arbitrum One'}
          </button>
        )}
      </div>
      
      <div className="contract-info">
        <div className="info-row">
          <span className="info-label">L2 Relay Contract:</span>
          <span className="info-value">{l2RelayAddress || "Not configured"}</span>
        </div>
        
        <div className="info-row">
          <span className="info-label">Contract Owner:</span>
          <span className="info-value">{ownerAddress || "Unknown"}</span>
        </div>
        
        <div className="info-row">
          <span className="info-label">Current L1 Sender (chain {currentL1ChainId}):</span>
          <span className="info-value">{currentSender || "Not set"}</span>
        </div>
      </div>
      
      <div className="l1-address-info">
        <h4>L1 to L2 Address Conversion</h4>
        
        <div className="info-row">
          <span className="info-label">Original L1 Address:</span>
          <span className="info-value">{l1ContractAddress || "Not configured"}</span>
        </div>
        
        <div className="info-row">
          <span className="info-label">Aliased L2 Address:</span>
          <span className="info-value">{aliasedAddress || "Cannot compute alias"}</span>
        </div>
        
        <div className="info-note">
          <p>The L2 alias is computed by adding <code>{ALIAS_ADDITION}</code> to the L1 address.</p>
          <p>This aliasing scheme is part of Optimism's cross-domain messaging system.</p>
        </div>
      </div>
      
      <div className="update-form">
        <h4>Update Cross-Chain Sender</h4>
        
        <form onSubmit={handleUpdateSender}>
          <div className="input-group">
            <label>New Sender Address:</label>
            <input
              type="text"
              value={newSenderAddress}
              onChange={(e) => setNewSenderAddress(e.target.value)}
              placeholder="0x..."
              className="form-input"
            />
            <div className="input-help">The contract address that will be authorized to send messages from L1</div>
          </div>
          
          <div className="input-group">
            <label>Chain ID:</label>
            <input
              type="number"
              value={newChainId}
              onChange={(e) => setNewChainId(e.target.value)}
              placeholder="1"
              className="form-input"
              min="1"
            />
            <div className="input-help">The chain ID of the source chain (1 for Ethereum mainnet)</div>
          </div>
          
          <div className="info-note warning">
            <p>Note: You must be the contract owner to update these parameters.</p>
            <p>This will authorize the specified address to send cross-chain messages to this contract.</p>
          </div>
          
          <button 
            type="submit" 
            className="update-button" 
            disabled={isUpdating || !newSenderAddress || !newChainId}
          >
            {isUpdating ? "Updating..." : "Update Cross-Chain Sender"}
          </button>
        </form>
      </div>
    </div>
  );
};

export default L2RelayManager; 