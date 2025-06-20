import React, { useState, useEffect, useRef } from 'react';
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

interface L2OwnershipRelayManagerProps {
  setBridgeStatus: (status: string | ((prev: string) => string)) => void;
}

const L2OwnershipRelayManager: React.FC<L2OwnershipRelayManagerProps> = ({ setBridgeStatus }) => {
  const { isConnected, walletAddress, networkType, switchNetwork, switchToLayer, connectWallet } = useBlockchain();
  const { getContract, loading: configLoading } = useContractConfig();

  // State variables
  const [l2OwnershipRelayAddress, setL2OwnershipRelayAddress] = useState<string>("");
  const [l1ContractAddress, setL1ContractAddress] = useState<string>("");
  const [aliasedAddress, setAliasedAddress] = useState<string>("");
  const [ownerAddress, setOwnerAddress] = useState<string>("");
  const [l3ContractAddress, setL3ContractAddress] = useState<string>("");
  const [currentL1ChainId, setCurrentL1ChainId] = useState<number>(0);
  const [currentSender, setCurrentSender] = useState<string>("");
  const [isOwnerRevoked, setIsOwnerRevoked] = useState<boolean>(false);

  // Form state for cross-chain sender
  const [newSenderAddress, setNewSenderAddress] = useState<string>("");
  const [newChainId, setNewChainId] = useState<string>("1"); // Default to Ethereum mainnet
  const [isUpdating, setIsUpdating] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [environment, setEnvironment] = useState<'testnet' | 'mainnet'>('testnet');

  // Form state for L3Contract updates
  const [newL3ContractAddress, setNewL3ContractAddress] = useState<string>("");
  const [isUpdatingL3Contract, setIsUpdatingL3Contract] = useState<boolean>(false);

  // Ref to track if initial data has been loaded
  const isDataLoadedRef = useRef(false);
  const isCurrentNetworkLoadedRef = useRef<string | null>(null);

  // Reset isDataLoadedRef only when switching to a network we haven't loaded data for yet
  useEffect(() => {
    if (networkType && isCurrentNetworkLoadedRef.current !== networkType) {
      console.log(`[L2OwnershipRelayManager] Network changed to ${networkType}, resetting loaded state`);
      isDataLoadedRef.current = false;
    }
  }, [networkType]);

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

  // Function to fetch contract data based on current chain ID
  const fetchContractData = async (chainId: number) => {
    try {
      console.log(`[L2OwnershipRelayManager] Fetching contract data for chain ID ${chainId}...`);
      if (isConnected && l2OwnershipRelayAddress && ethers.isAddress(l2OwnershipRelayAddress) && window.ethereum) {
        const provider = new ethers.BrowserProvider(window.ethereum);
        const L2OwnershipRelayABI = abiLoader.loadABI('L2OwnershipRelay');
        if (!L2OwnershipRelayABI) {
          throw new Error('Failed to load L2OwnershipRelay ABI');
        }
        const contract = new ethers.Contract(l2OwnershipRelayAddress, L2OwnershipRelayABI, provider);

        const sender = await contract.crossChainRegistryAddressByChainId(chainId);
        setCurrentSender(sender);
        setCurrentL1ChainId(chainId);
        console.log(`[L2OwnershipRelayManager] Data fetch complete for chain ID ${chainId}. Sender: ${sender}`);
      }
    } catch (error) {
      console.error(`[L2OwnershipRelayManager] Error fetching sender for chain ID ${chainId}:`, error);
    }
  };

  // Load all data
  useEffect(() => {
    const loadAllData = async () => {
      // Skip if data is already loaded for this network
      if (isDataLoadedRef.current && isCurrentNetworkLoadedRef.current === networkType) {
        console.log(`[L2OwnershipRelayManager] Data already loaded for ${networkType}, skipping load`);
        return;
      }

      try {
        console.log('[L2OwnershipRelayManager] Loading all contract data...');
        setIsLoading(true);

        // Step 1: Load contract addresses from config
        if (configLoading) {
          console.log('[L2OwnershipRelayManager] Config still loading, waiting...');
          return; // Wait for config to load
        }

        // Set environment based on network type
        const currentEnv = networkType.includes('mainnet') ? 'mainnet' : 'testnet';
        setEnvironment(currentEnv);
        console.log(`[L2OwnershipRelayManager] Environment set to: ${currentEnv}`);

        const l2Contract = getContract(currentEnv, 'l2');
        const relayAddress = l2Contract?.address || '';
        if (!relayAddress) {
          console.error("[L2OwnershipRelayManager] L2 relay address not found in configuration");
          toast.error("L2 relay address not configured");
          return;
        }
        setL2OwnershipRelayAddress(relayAddress);
        console.log(`[L2OwnershipRelayManager] L2 relay address: ${relayAddress}`);

        const l1Contract = getContract(currentEnv, 'l1');
        const l1Address = l1Contract?.address || '';
        if (!l1Address) {
          console.error("[L2OwnershipRelayManager] L1 contract address not found in configuration");
          toast.error("L1 contract address not configured");
          return;
        }
        setL1ContractAddress(l1Address);
        console.log(`[L2OwnershipRelayManager] L1 contract address: ${l1Address}`);

        const l3Contract = getContract(currentEnv, 'l3');
        const l3Address = l3Contract?.address || '';
        setL3ContractAddress(l3Address);
        console.log(`[L2OwnershipRelayManager] L3 contract address: ${l3Address || 'not set'}`);

        if (l1Address) {
          const aliased = computeAliasedAddress(l1Address);
          setAliasedAddress(aliased);
          console.log(`[L2OwnershipRelayManager] Computed aliased address: ${aliased}`);
        }

        // Step 2: Fetch contract data if connected
        if (isConnected && relayAddress && ethers.isAddress(relayAddress) && window.ethereum) {
          console.log('[L2OwnershipRelayManager] Connected to wallet, fetching contract details...');
          console.log(`[L2OwnershipRelayManager] Using relay address: ${relayAddress}`);
          console.log(`[L2OwnershipRelayManager] Current network type: ${networkType}`);
          
          const provider = new ethers.BrowserProvider(window.ethereum);
          
          // Check current network
          const network = await provider.getNetwork();
          console.log(`[L2OwnershipRelayManager] Connected to network: ${network.name} (chainId: ${network.chainId})`);
          
          const L2OwnershipRelayABI = abiLoader.loadABI('L2OwnershipRelay');
          if (!L2OwnershipRelayABI) {
            throw new Error('Failed to load L2OwnershipRelay ABI');
          }
          const contract = new ethers.Contract(relayAddress, L2OwnershipRelayABI, provider);

          // Check if contract exists by checking bytecode
          const code = await provider.getCode(relayAddress);
          if (code === '0x') {
            console.error(`[L2OwnershipRelayManager] No contract found at address ${relayAddress} on network ${network.name}`);
            throw new Error(`No contract deployed at address ${relayAddress} on network ${network.name} (chainId: ${network.chainId})`);
          }
          console.log(`[L2OwnershipRelayManager] Contract bytecode found, length: ${code.length}`);

          const owner = await contract.owner();
          setOwnerAddress(owner);
          console.log(`[L2OwnershipRelayManager] Contract owner: ${owner}`);

          const revoked = await contract.isOwnerRevoked();
          setIsOwnerRevoked(revoked);
          console.log(`[L2OwnershipRelayManager] Owner revoked: ${revoked}`);

          const l3ContractAddr = await contract.l3Contract();
          setL3ContractAddress(l3ContractAddr);
          console.log(`[L2OwnershipRelayManager] L3 contract from contract: ${l3ContractAddr}`);
          if (!isDataLoadedRef.current) {
            setNewL3ContractAddress(l3ContractAddr);
          }

          const chainId = Number(newChainId);
          await fetchContractData(chainId);

          // Mark data as loaded for this network
          isDataLoadedRef.current = true;
          isCurrentNetworkLoadedRef.current = networkType;
          console.log(`[L2OwnershipRelayManager] Initial data load complete for network ${networkType}`);
        } else {
          console.log('[L2OwnershipRelayManager] Not connected to wallet or missing relay address, skipping contract detail fetching');
          
          // Even if we couldn't get contract details, mark basic config as loaded
          if (relayAddress && l1Address) {
            isDataLoadedRef.current = true;
            isCurrentNetworkLoadedRef.current = networkType;
            console.log(`[L2OwnershipRelayManager] Basic configuration loaded for network ${networkType}`);
          }
        }
      } catch (error) {
        console.error("[L2OwnershipRelayManager] Error loading data:", error);
        if (ownerAddress || currentSender) {
          toast.error("Failed to load L2 Relay contract information");
        }
      } finally {
        setIsLoading(false);
        console.log('[L2OwnershipRelayManager] Loading complete');
      }
    };

    loadAllData();
  }, [isConnected, networkType, configLoading, getContract]);

  // Handle chain ID change for viewing current sender
  const handleChainIdChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setNewChainId(value);
    
    if (value && !isNaN(Number(value))) {
      const chainId = Number(value);
      console.log(`[L2OwnershipRelayManager] Chain ID changed to ${chainId}, fetching data...`);
      fetchContractData(chainId);
    }
  };

  // Handle cross-chain sender form submission
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
        const L2OwnershipRelayABI = abiLoader.loadABI('L2OwnershipRelay');
        if (!L2OwnershipRelayABI) {
          throw new Error('Failed to load L2OwnershipRelay ABI');
        }

        const contract = new ethers.Contract(l2OwnershipRelayAddress, L2OwnershipRelayABI, signer);

        // Check if they really want to update the config
        const chainId = Number(newChainId);
        let needsConfirmation = false;
        let confirmationMessage = '';

        // If there's already a sender for this chain ID, confirm before overwriting
        if (currentSender && currentSender !== ethers.ZeroAddress && currentL1ChainId === chainId) {
          needsConfirmation = true;
          confirmationMessage = `You're about to overwrite the current sender for chain ID ${chainId}.\nCurrent: ${currentSender}\nNew: ${newSenderAddress}\n\nProceed?`;
        }

        // Confirm if needed
        if (needsConfirmation && !window.confirm(confirmationMessage)) {
          toast.error("Update canceled by user");
          setIsUpdating(false);
          return;
        }

        // Call updateCrossChainQueryOwnerContract method
        toast.loading("Updating cross-chain sender configuration...");
        const tx = await contract.updateCrossChainQueryOwnerContract(newSenderAddress, chainId);

        // Wait for transaction to be confirmed
        await tx.wait();
        toast.dismiss();
        toast.success(`Updated cross-chain sender for chain ID ${chainId}`);

        // Update UI state
        setCurrentL1ChainId(chainId);
        setCurrentSender(newSenderAddress);
      } catch (error) {
        toast.dismiss();
        console.error("Error updating cross-chain sender:", error);
        toast.error(`Failed to update sender: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    } catch (error) {
      console.error("Error in updateSender:", error);
      toast.error(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsUpdating(false);
    }
  };

  // Handle L3Contract update form submission
  const handleUpdateL3Contract = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!newL3ContractAddress || !ethers.isAddress(newL3ContractAddress)) {
      toast.error("Please enter a valid address for the L3 contract");
      return;
    }

    try {
      setIsUpdatingL3Contract(true);

      // Check if wallet is connected
      if (!isConnected) {
        try {
          await connectWallet();
          toast("Please connect your wallet to continue");
          setIsUpdatingL3Contract(false);
          return;
        } catch (walletError) {
          console.error("Error connecting wallet:", walletError);
          toast.error("Please install and connect a Web3 wallet like MetaMask to proceed");
          setIsUpdatingL3Contract(false);
          return;
        }
      }

      // Check if we have ethereum provider
      if (!window.ethereum) {
        toast.error("Web3 provider not found. Please install MetaMask or another Web3 wallet");
        setIsUpdatingL3Contract(false);
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
          setIsUpdatingL3Contract(false);
          return;
        }
      }

      // Now update the L2 Relay contract
      try {
        // Create provider and signer
        const provider = new ethers.BrowserProvider(window.ethereum);
        const signer = await provider.getSigner();

        // Load ABI and create contract instance
        const L2OwnershipRelayABI = abiLoader.loadABI('L2OwnershipRelay');
        if (!L2OwnershipRelayABI) {
          throw new Error('Failed to load L2OwnershipRelay ABI');
        }

        const contract = new ethers.Contract(l2OwnershipRelayAddress, L2OwnershipRelayABI, signer);

        // Check if they really want to update the L3 contract
        let needsConfirmation = false;
        let confirmationMessage = '';

        // If there's already an L3 contract set, confirm before overwriting
        if (l3ContractAddress && l3ContractAddress !== ethers.ZeroAddress && l3ContractAddress !== newL3ContractAddress) {
          needsConfirmation = true;
          confirmationMessage = `You're about to update the L3 contract address.\nCurrent: ${l3ContractAddress}\nNew: ${newL3ContractAddress}\n\nProceed?`;
        }

        // Confirm if needed
        if (needsConfirmation && !window.confirm(confirmationMessage)) {
          toast.error("Update canceled by user");
          setIsUpdatingL3Contract(false);
          return;
        }

        // Call setL3Contract method
        toast.loading("Updating L3 contract address...");
        const tx = await contract.setL3Contract(newL3ContractAddress);

        // Wait for transaction to be confirmed
        await tx.wait();
        toast.dismiss();
        toast.success("Updated L3 contract address");

        // Update UI state
        setL3ContractAddress(newL3ContractAddress);
      } catch (error) {
        toast.dismiss();
        console.error("Error updating L3 contract address:", error);
        toast.error(`Failed to update L3 contract: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    } catch (error) {
      console.error("Error in updateL3Contract:", error);
      toast.error(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsUpdatingL3Contract(false);
    }
  };

  // Handle network switching
  const handleSwitchNetwork = async () => {
    try {
      if (environment === 'testnet') {
        setBridgeStatus('Switching to Arbitrum Sepolia for L2OwnershipRelay contract...');
        await switchToLayer('l2', 'testnet');
      } else {
        setBridgeStatus('Switching to Arbitrum mainnet for L2OwnershipRelay contract...');
        await switchToLayer('l2', 'mainnet');
      }
    } catch (error) {
      console.error('[L2OwnershipRelayManager] Error switching network:', error);
      toast.error('Failed to switch network. Please try manually in MetaMask.');
    }
  };

  const isL2Arbitrum = networkType === 'arbitrum_testnet' || networkType === 'arbitrum_mainnet';
  const isOwner = isConnected && ownerAddress && walletAddress &&
                 ownerAddress.toLowerCase() === walletAddress.toLowerCase() &&
                 !isOwnerRevoked;

  return (
    <div className="l2-relay-manager">
      <div className="card-content">
        <div className="connection-status">
          {isLoading ? (
            <p className="loading">Loading contract info...</p>
          ) : (
            <div className="contract-info">
              <div className="info-group">
                <p className="info-label">L2OwnershipRelay Contract Address:</p>
                <p className="info-value">{l2OwnershipRelayAddress}</p>
              </div>
              <div className="info-group">
                <p className="info-label">L2OwnershipRelay Owner:</p>
                <p className="info-value">{ownerAddress || 'Not found'}</p>
                {isOwnerRevoked && <span className="revoked-badge">Revoked</span>}
              </div>
              <br />
              <div className="info-group">
                <p className="info-label">ArtCommissionHubOwners (L3 -  Relay Destination):</p>
                <p className="info-value">{l3ContractAddress || 'Not set'}</p>
              </div>
              <div className="info-group">
                <p className="info-label">L1QueryOnwer Cross-Chain (L1 - Aliased Origin) for Chain ID {currentL1ChainId}:</p>
                <p className="info-value">{currentSender || 'Not set'}</p>
              </div>
              <br />

              {!isConnected && (
                <button className="connect-button" onClick={connectWallet}>Connect Wallet</button>
              )}

              {isConnected && !isL2Arbitrum && (
                <button className="switch-network-button" onClick={handleSwitchNetwork}>
                  Switch to Arbitrum {environment === 'mainnet' ? 'One' : 'Sepolia'}
                </button>
              )}
            </div>
          )}
        </div>

        <div className="forms-container">
          {/* L3 Contract Update Form - Always visible */}
          <div className="form-section">
            <h4>L2OwnershipRelay - Update L3 Contract Address</h4>
            <form onSubmit={handleUpdateL3Contract}>
              <div className="form-group">
                <label htmlFor="newL3ContractAddress">ArtCommissionHubOwners (L3 - Relay Destination):</label>
                <input
                  id="newL3ContractAddress"
                  type="text"
                  placeholder="0x..."
                  value={newL3ContractAddress}
                  onChange={(e) => setNewL3ContractAddress(e.target.value)}
                  required
                />
              </div>

              <div className="form-actions">
                <button
                  type="submit"
                  disabled={isUpdatingL3Contract}
                  className="enabled-button"
                >
                  {isUpdatingL3Contract ? 'Updating...' : 'Update L3 Contract'}
                </button>
              </div>
              <div className="info-note small">
                <p>This updates the L1QueryOwnership Cross-Chain (L1 - Aliased Origin) for Chain ID {currentL1ChainId}.</p>
              </div>
            </form>
          </div>

          {/* Cross-Chain Sender Update Form - Always visible */}
          <div className="form-section">
            <h4>L2 - Add/Update ALIASED Cross-Chain L1 Owner Query Sender (by NFT collection ID)</h4>
            <form onSubmit={handleUpdateSender}>
              <div className="form-group">
                <label htmlFor="newChainId">Chain ID:</label>
                <input
                  id="newChainId"
                  type="number"
                  placeholder="1 for Ethereum mainnet"
                  value={newChainId}
                  onChange={handleChainIdChange}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="newSenderAddress">Sender Address:</label>
                <input
                  id="newSenderAddress"
                  type="text"
                  placeholder="0x..."
                  value={newSenderAddress}
                  onChange={(e) => setNewSenderAddress(e.target.value)}
                  required
                />
              </div>

              <div className="form-actions">
                <button
                  type="submit"
                  disabled={isUpdating}
                  className="enabled-button"
                >
                  {isUpdating ? 'Updating...' : 'Update Sender'}
                </button>
              </div>
              <div className="info-note small">
                <p>This authorizes an address to send cross-chain messages from the specified chain.</p>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default L2OwnershipRelayManager;