import React, { useState, useEffect } from 'react';
import { ethers } from 'ethers';
import { useBlockchain } from '../utils/BlockchainContext';
import abiLoader from '../utils/abiLoader';
import useContractConfig from '../utils/useContractConfig';
import './BridgeTest.css';

// Interface for contract addresses
interface ContractAddresses {
  l1: {
    testnet: string;
    mainnet: string;
  };
  l2: {
    testnet: string;
    mainnet: string;
  };
}

// Interface for contract ABIs with ABI files
interface ContractConfig {
  addresses: ContractAddresses;
  abiFiles: {
    l1: string;
    l2: string;
  };
}

// NFT query form state
interface NFTQuery {
  contractAddress: string;
  tokenId: string;
  isSubmitting: boolean;
  transactionHash: string;
  result: string;
}

// LocalStorage key for saving/loading contract config
const LOCAL_STORAGE_KEY = 'bridge_test_contract_config';

const BridgeTest: React.FC = () => {
  // State for network selection
  const [layer, setLayer] = useState<'l1' | 'l2'>('l1');
  const [environment, setEnvironment] = useState<'testnet' | 'mainnet'>('testnet');
  
  // Get blockchain context
  const { networkType, switchNetwork, connectWallet, walletAddress, isConnected } = useBlockchain();
  
  // Get contract configuration
  const { loading: configLoading, config: contractsConfig, getContract, reloadConfig } = useContractConfig();
  
  // State for NFT query
  const [nftQuery, setNftQuery] = useState<NFTQuery>({
    contractAddress: '',
    tokenId: '',
    isSubmitting: false,
    transactionHash: '',
    result: ''
  });
  
  // State to track listening for events
  const [isListening, setIsListening] = useState(false);
  
  // Default config
  const defaultConfig: ContractConfig = {
    addresses: {
      l1: {
        testnet: '', // Sepolia
        mainnet: '', // Ethereum
      },
      l2: {
        testnet: '', // Arbitrum Sepolia
        mainnet: '', // Arbitrum One
      }
    },
    abiFiles: {
      l1: 'L1QueryOwner',
      l2: 'L2Relay'
    }
  };
  
  // State for contract addresses and ABIs - initialize with saved data or defaults
  const [contractConfig, setContractConfig] = useState<ContractConfig>(() => {
    // Try to load from localStorage
    const savedConfig = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (savedConfig) {
      try {
        return JSON.parse(savedConfig);
      } catch (e) {
        console.error('Failed to parse saved configuration:', e);
      }
    }
    return defaultConfig;
  });
  
  // Selected ABI objects based on contract type
  const [selectedABI, setSelectedABI] = useState<any>(abiLoader.loadABI('L1QueryOwner'));
  
  // Available ABI names
  const [availableAbis, setAvailableAbis] = useState<string[]>(abiLoader.getAvailableABIs());
  
  // Method names for the selected ABI
  const [methodNames, setMethodNames] = useState<string[]>([]);
  
  // Message state
  const [message, setMessage] = useState<string>('');
  const [bridgeStatus, setBridgeStatus] = useState<string>('');
  
  // Save config to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(contractConfig));
  }, [contractConfig]);
  
  // Load contract addresses from configuration when it's available
  useEffect(() => {
    if (contractsConfig && !configLoading) {
      // Load the deployed contract addresses from the configuration
      const newAddresses = {
        l1: {
          testnet: getContract('testnet', 'l1')?.address || '',
          mainnet: getContract('mainnet', 'l1')?.address || '',
        },
        l2: {
          testnet: getContract('testnet', 'l2')?.address || '',
          mainnet: getContract('mainnet', 'l2')?.address || '',
        }
      };
      
      // Update contract ABIs based on configuration
      const newAbiFiles = {
        l1: getContract('testnet', 'l1')?.contract || 'L1QueryOwner',
        l2: getContract('testnet', 'l2')?.contract || 'L2Relay'
      };
      
      // Update the contract configuration if any address has changed
      if (
        newAddresses.l1.testnet !== contractConfig.addresses.l1.testnet ||
        newAddresses.l1.mainnet !== contractConfig.addresses.l1.mainnet ||
        newAddresses.l2.testnet !== contractConfig.addresses.l2.testnet ||
        newAddresses.l2.mainnet !== contractConfig.addresses.l2.mainnet ||
        newAbiFiles.l1 !== contractConfig.abiFiles.l1 ||
        newAbiFiles.l2 !== contractConfig.abiFiles.l2
      ) {
        setContractConfig({
          addresses: newAddresses,
          abiFiles: newAbiFiles
        });
        
        setBridgeStatus(prev => {
          return `${prev ? prev + '\n\n' : ''}Loaded contract addresses from configuration.`;
        });
      }
    }
  }, [contractsConfig, configLoading, getContract]);
  
  // Update network when layer changes
  useEffect(() => {
    if (layer === 'l1') {
      if (environment === 'testnet') {
        switchNetwork('dev'); // Switch to Sepolia
      } else {
        switchNetwork('prod'); // Switch to Ethereum Mainnet
      }
    } else { // L2 
      if (environment === 'testnet') {
        switchNetwork('arbitrum_testnet'); // Switch to Arbitrum Sepolia
        setBridgeStatus('Connected to Arbitrum Sepolia testnet');
      } else {
        switchNetwork('arbitrum_mainnet'); // Switch to Arbitrum One
        setBridgeStatus('Connected to Arbitrum One mainnet');
      }
    }
    
    // Force reload the contract config when changing networks
    if (!configLoading && contractsConfig) {
      // Small delay to ensure network switch completes first
      setTimeout(() => {
        // Reload the contract configuration
        reloadConfig();
        
        // Update the UI with new addresses
        const newAddresses = {
          l1: {
            testnet: getContract('testnet', 'l1')?.address || '',
            mainnet: getContract('mainnet', 'l1')?.address || '',
          },
          l2: {
            testnet: getContract('testnet', 'l2')?.address || '',
            mainnet: getContract('mainnet', 'l2')?.address || '',
          }
        };
        
        setContractConfig(prev => ({
          ...prev,
          addresses: newAddresses
        }));
        
        setBridgeStatus(prev => {
          return `${prev ? prev + '\n\n' : ''}Updated contract addresses for ${layer === 'l1' ? 'Ethereum' : 'Arbitrum'} ${environment}.`;
        });
      }, 500);
    }
  }, [layer, environment, switchNetwork]);
  
  // Update selected ABI when layer or ABI file changes
  useEffect(() => {
    const abiFileName = contractConfig.abiFiles[layer];
    const abi = abiLoader.loadABI(abiFileName);
    
    if (abi) {
      setSelectedABI(abi);
      
      // Get method names for this ABI
      const methods = abiLoader.getMethodNames(abiFileName);
      setMethodNames(methods);
      
      // Show available methods
      const methodsStr = methods.join(', ');
      setBridgeStatus(prev => {
        // Keep connection status if it exists
        if (prev.includes('Connected to')) {
          return `${prev}\n\nSelected ABI: ${abiFileName}\nAvailable methods: ${methodsStr}`;
        }
        return `Selected ABI: ${abiFileName}\nAvailable methods: ${methodsStr}`;
      });
    } else {
      setBridgeStatus(prev => {
        // Keep connection status if it exists
        if (prev.includes('Connected to')) {
          return `${prev}\n\nError: Could not load ABI for ${abiFileName}`;
        }
        return `Error: Could not load ABI for ${abiFileName}`;
      });
    }
  }, [layer, contractConfig.abiFiles]);
  
  // Handle contract address changes
  const handleAddressChange = (layer: 'l1' | 'l2', env: 'testnet' | 'mainnet', value: string) => {
    setContractConfig(prev => ({
      ...prev,
      addresses: {
        ...prev.addresses,
        [layer]: {
          ...prev.addresses[layer],
          [env]: value
        }
      }
    }));
  };
  
  // Handle ABI selection changes
  const handleABIChange = (layer: 'l1' | 'l2', value: string) => {
    setContractConfig(prev => ({
      ...prev,
      abiFiles: {
        ...prev.abiFiles,
        [layer]: value
      }
    }));
  };
  
  // Reset contract configuration to defaults
  const handleResetConfig = () => {
    if (window.confirm('Are you sure you want to reset all contract configuration to defaults?')) {
      setContractConfig(defaultConfig);
      setBridgeStatus('Configuration reset to defaults');
    }
  };
  
  // Load from contract config file
  const handleLoadFromConfig = () => {
    if (configLoading || !contractsConfig) {
      setBridgeStatus('Contract configuration is still loading...');
      return;
    }
    
    if (window.confirm('Load contract addresses from the application configuration file?')) {
      // Load the deployed contract addresses from the configuration
      const newAddresses = {
        l1: {
          testnet: getContract('testnet', 'l1')?.address || '',
          mainnet: getContract('mainnet', 'l1')?.address || '',
        },
        l2: {
          testnet: getContract('testnet', 'l2')?.address || '',
          mainnet: getContract('mainnet', 'l2')?.address || '',
        }
      };
      
      // Update contract ABIs based on configuration
      const newAbiFiles = {
        l1: getContract('testnet', 'l1')?.contract || 'L1QueryOwner',
        l2: getContract('testnet', 'l2')?.contract || 'L2Relay'
      };
      
      setContractConfig({
        addresses: newAddresses,
        abiFiles: newAbiFiles
      });
      
      setBridgeStatus('Contract addresses loaded from configuration file.');
    }
  };
  
  // Function to send a message across the bridge
  const sendBridgeMessage = async () => {
    try {
      setBridgeStatus('Preparing to send message...');
      
      // In a real implementation, this would use the actual bridge mechanism
      // For now, we'll just simulate the process
      
      const selectedAddress = contractConfig.addresses[layer][environment];
      
      if (!selectedAddress) {
        setBridgeStatus('Error: Contract address is not set');
        return;
      }
      
      if (!contractConfig.abiFiles[layer]) {
        setBridgeStatus('Error: Contract ABI is not selected');
        return;
      }
      
      // Get the ABI file name
      const abiFileName = contractConfig.abiFiles[layer];
      
      // Suggest appropriate method based on layer
      let suggestedMethod = '';
      if (layer === 'l1' && methodNames.includes('queryNFTAndSendBack')) {
        suggestedMethod = 'queryNFTAndSendBack';
      } else if (layer === 'l2' && methodNames.includes('requestNFTOwner')) {
        suggestedMethod = 'requestNFTOwner';
      }
      
      setBridgeStatus(`Would send message from ${layer.toUpperCase()} (${environment}): ${message}`);
      
      if (suggestedMethod) {
        setBridgeStatus(prev => `${prev}\nSuggested method to call: ${suggestedMethod}`);
      }
      
      // Network info based on selected layer and environment
      const networkInfo = layer === 'l1' 
        ? (environment === 'testnet' ? 'Sepolia' : 'Ethereum') 
        : (environment === 'testnet' ? 'Arbitrum Sepolia' : 'Arbitrum One');
      
      setBridgeStatus(prev => `${prev}\nNetwork: ${networkInfo}`);
      
      // Display the command that would be executed with ape framework
      setBridgeStatus(prev => 
        `${prev}\n\nAPE command that would be executed:\n` +
        `ape run scripts/bridge_message.py --network ${environment === 'testnet' ? 'sepolia' : 'mainnet'} ` +
        `--layer ${layer} --contract ${selectedAddress} --message "${message}" --abi-path "src/assets/abis/${abiFileName}.json"`
      );
      
      // Show a preview of the selected ABI
      const abiPreview = selectedABI ? JSON.stringify(selectedABI.slice(0, 1), null, 2) : 'No ABI selected';
      setBridgeStatus(prev => 
        `${prev}\n\nSelected ABI: ${abiFileName}\n` +
        `First ABI entry: ${abiPreview}`
      );
      
    } catch (error) {
      console.error('Error sending bridge message:', error);
      setBridgeStatus(`Error: ${error instanceof Error ? error.message : String(error)}`);
    }
  };
  
  // Handle NFT query form change
  const handleNftQueryChange = (field: keyof NFTQuery, value: string) => {
    setNftQuery(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Connect wallet and listen for events
  const setupEventListening = async () => {
    if (!isConnected) {
      await connectWallet();
    }
    
    if (isListening) return; // Already listening
    
    try {
      // Get the L2Relay contract address for current environment
      const l2Address = contractConfig.addresses.l2[environment];
      if (!l2Address) {
        setBridgeStatus('Error: L2Relay contract address not set');
        return;
      }
      
      // Setup event listening only if not already listening
      const provider = new ethers.BrowserProvider(window.ethereum);
      
      // Load the L2Relay ABI
      const l2RelayABI = abiLoader.loadABI('L2Relay');
      if (!l2RelayABI) {
        setBridgeStatus('Error: Could not load L2Relay ABI');
        return;
      }
      
      // Create contract instance
      const contract = new ethers.Contract(l2Address, l2RelayABI, provider);
      
      // Listen for RequestSent events
      contract.removeAllListeners(); // Clear previous listeners
      
      contract.on('RequestSent', (nftContract, tokenId, uniqueId, event) => {
        setBridgeStatus(prev => 
          `${prev}\n\nNFT Query Request Sent!\nContract: ${nftContract}\nToken ID: ${tokenId}\nRequest ID: ${uniqueId}`
        );
      });
      
      // Listen for OwnerReceived events
      contract.on('OwnerReceived', (owner, event) => {
        setBridgeStatus(prev => 
          `${prev}\n\nOwner Received from L1!\nNFT Owner: ${owner}`
        );
        
        // Update the query result
        setNftQuery(prev => ({
          ...prev,
          isSubmitting: false,
          result: `NFT owner: ${owner}`
        }));
      });
      
      setIsListening(true);
      setBridgeStatus(prev => `${prev}\n\nListening for L2Relay events...`);
    } catch (error) {
      console.error('Error setting up event listeners:', error);
      setBridgeStatus(prev => `${prev}\n\nError setting up event listeners: ${error}`);
    }
  };
  
  // Submit NFT query to the L2Relay contract
  const submitNftQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Ensure we're on L2
    if (layer !== 'l2') {
      setBridgeStatus('Please switch to L2 (Arbitrum) to query NFT ownership');
      setLayer('l2');
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
    
    // Set up event listening
    await setupEventListening();
    
    try {
      setNftQuery(prev => ({ ...prev, isSubmitting: true }));
      
      // Get the L2Relay contract address for current environment
      const l2Address = contractConfig.addresses.l2[environment];
      if (!l2Address) {
        setBridgeStatus('Error: L2Relay contract address not set');
        setNftQuery(prev => ({ ...prev, isSubmitting: false }));
        return;
      }
      
      // Connect to the provider with signer
      const provider = new ethers.BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();
      
      // Load the L2Relay ABI
      const l2RelayABI = abiLoader.loadABI('L2Relay');
      if (!l2RelayABI) {
        setBridgeStatus('Error: Could not load L2Relay ABI');
        setNftQuery(prev => ({ ...prev, isSubmitting: false }));
        return;
      }
      
      // Create contract instance with signer
      const contract = new ethers.Contract(l2Address, l2RelayABI, signer);
      
      // Validate inputs
      if (!ethers.isAddress(nftQuery.contractAddress)) {
        setBridgeStatus('Error: Invalid NFT contract address');
        setNftQuery(prev => ({ ...prev, isSubmitting: false }));
        return;
      }
      
      const tokenId = parseInt(nftQuery.tokenId);
      if (isNaN(tokenId) || tokenId < 0) {
        setBridgeStatus('Error: Invalid token ID');
        setNftQuery(prev => ({ ...prev, isSubmitting: false }));
        return;
      }
      
      // Call requestNFTOwner
      setBridgeStatus(`Submitting query for NFT contract ${nftQuery.contractAddress} with token ID ${tokenId}...`);
      
      // Convert token ID to BigInt for safer handling of large numbers
      const tokenIdBigInt = BigInt(tokenId);
      
      const tx = await contract.requestNFTOwner(nftQuery.contractAddress, tokenIdBigInt);
      
      // Update state with transaction hash
      setNftQuery(prev => ({ ...prev, transactionHash: tx.hash }));
      
      // Wait for the transaction to be mined
      setBridgeStatus(prev => `${prev}\n\nTransaction sent. Hash: ${tx.hash}\nWaiting for confirmation...`);
      
      const receipt = await tx.wait();
      
      setBridgeStatus(prev => `${prev}\n\nTransaction confirmed with ${receipt.gasUsed} gas used.`);
      setBridgeStatus(prev => `${prev}\n\nWaiting for cross-chain message to be processed...`);
      
      // Don't set isSubmitting to false here, only when we receive the OwnerReceived event
      
    } catch (error: any) {
      console.error('Error submitting NFT query:', error);
      setBridgeStatus(prev => `${prev}\n\nError: ${error.message || 'Unknown error'}`);
      setNftQuery(prev => ({ ...prev, isSubmitting: false }));
    }
  };

  // Render the NFT query form
  const renderNftQueryForm = () => {
    return (
      <div className="nft-query-section">
        <h3>Query NFT Ownership</h3>
        <form onSubmit={submitNftQuery} className="nft-query-form">
          <div className="input-group">
            <label>NFT Contract Address:</label>
            <input 
              type="text" 
              value={nftQuery.contractAddress} 
              onChange={(e) => handleNftQueryChange('contractAddress', e.target.value)}
              placeholder="0x..."
              disabled={nftQuery.isSubmitting}
            />
          </div>
          
          <div className="input-group">
            <label>Token ID:</label>
            <input 
              type="text" 
              value={nftQuery.tokenId} 
              onChange={(e) => handleNftQueryChange('tokenId', e.target.value)}
              placeholder="1"
              disabled={nftQuery.isSubmitting}
            />
          </div>
          
          <div className="action-buttons">
            {!isConnected && (
              <button
                type="button"
                className="connect-button"
                onClick={connectWallet}
              >
                Connect Wallet
              </button>
            )}
            
            <button
              type="submit"
              className="submit-button"
              disabled={!nftQuery.contractAddress || !nftQuery.tokenId || nftQuery.isSubmitting}
            >
              {nftQuery.isSubmitting ? 'Submitting...' : 'Query NFT Owner'}
            </button>
          </div>
        </form>
        
        {nftQuery.transactionHash && (
          <div className="transaction-info">
            <h4>Transaction Details</h4>
            <p>
              <strong>Transaction Hash:</strong>{' '}
              <a 
                href={`${environment === 'testnet' ? 'https://sepolia.arbiscan.io/tx/' : 'https://arbiscan.io/tx/'}${nftQuery.transactionHash}`} 
                target="_blank" 
                rel="noopener noreferrer"
              >
                {nftQuery.transactionHash.substring(0, 10)}...{nftQuery.transactionHash.substring(nftQuery.transactionHash.length - 8)}
              </a>
            </p>
          </div>
        )}
        
        {nftQuery.result && (
          <div className="query-result">
            <h4>Query Result</h4>
            <p>{nftQuery.result}</p>
          </div>
        )}
      </div>
    );
  };
  
  return (
    <div className="bridge-test-container">
      <h2>Bridge Test</h2>
      
      <div className="network-selector-container">
        <div className="selector-group">
          <label>Layer:</label>
          <div className="toggle-buttons">
            <button 
              className={`toggle-button ${layer === 'l1' ? 'active' : ''}`}
              onClick={() => setLayer('l1')}
            >
              L1 (Ethereum)
            </button>
            <button 
              className={`toggle-button ${layer === 'l2' ? 'active' : ''}`}
              onClick={() => setLayer('l2')}
            >
              L2 (Arbitrum)
            </button>
          </div>
        </div>
        
        <div className="selector-group">
          <label>Environment:</label>
          <div className="toggle-buttons">
            <button 
              className={`toggle-button ${environment === 'testnet' ? 'active' : ''}`}
              onClick={() => setEnvironment('testnet')}
            >
              Testnet
            </button>
            <button 
              className={`toggle-button ${environment === 'mainnet' ? 'active' : ''}`}
              onClick={() => setEnvironment('mainnet')}
            >
              Mainnet
            </button>
          </div>
        </div>
      </div>
      
      {/* Display NFT query form */}
      {renderNftQueryForm()}
      
      <div className="contract-config">
        <h3>Contract Configuration</h3>
        <div className="config-buttons">
          <button 
            className="config-button reset-button"
            onClick={handleResetConfig}
            title="Reset to default values"
          >
            Reset
          </button>
          <button 
            className="config-button load-button"
            onClick={handleLoadFromConfig}
            disabled={configLoading || !contractsConfig}
            title="Load addresses from the contract config file"
          >
            Load from Config
          </button>
        </div>
        
        <div className="config-section">
          <h4>L1 Contracts</h4>
          <div className="input-group">
            <label>Testnet Address:</label>
            <input 
              type="text" 
              value={contractConfig.addresses.l1.testnet} 
              onChange={(e) => handleAddressChange('l1', 'testnet', e.target.value)}
              placeholder="0x..."
            />
          </div>
          <div className="input-group">
            <label>Mainnet Address:</label>
            <input 
              type="text" 
              value={contractConfig.addresses.l1.mainnet} 
              onChange={(e) => handleAddressChange('l1', 'mainnet', e.target.value)}
              placeholder="0x..."
            />
          </div>
          <div className="input-group">
            <label>ABI File:</label>
            <select 
              value={contractConfig.abiFiles.l1}
              onChange={(e) => handleABIChange('l1', e.target.value)}
              className="abi-selector"
            >
              {availableAbis.map(abi => (
                <option key={abi} value={abi}>{abi}</option>
              ))}
            </select>
          </div>
        </div>
        
        <div className="config-section">
          <h4>L2 Contracts</h4>
          <div className="input-group">
            <label>Testnet Address:</label>
            <input 
              type="text" 
              value={contractConfig.addresses.l2.testnet} 
              onChange={(e) => handleAddressChange('l2', 'testnet', e.target.value)}
              placeholder="0x..."
            />
          </div>
          <div className="input-group">
            <label>Mainnet Address:</label>
            <input 
              type="text" 
              value={contractConfig.addresses.l2.mainnet} 
              onChange={(e) => handleAddressChange('l2', 'mainnet', e.target.value)}
              placeholder="0x..."
            />
          </div>
          <div className="input-group">
            <label>ABI File:</label>
            <select 
              value={contractConfig.abiFiles.l2}
              onChange={(e) => handleABIChange('l2', e.target.value)}
              className="abi-selector"
            >
              {availableAbis.map(abi => (
                <option key={abi} value={abi}>{abi}</option>
              ))}
            </select>
          </div>
        </div>
      </div>
      
      <div className="message-section">
        <h3>Send Bridge Message</h3>
        <div className="input-group">
          <label>Message:</label>
          <textarea 
            value={message} 
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Enter message to send across the bridge"
            rows={4}
          />
        </div>
        
        <button 
          className="send-button"
          onClick={sendBridgeMessage}
          disabled={!message.trim()}
        >
          Send Message
        </button>
      </div>
      
      {bridgeStatus && (
        <div className="status-box">
          <h3>Status</h3>
          <pre>{bridgeStatus}</pre>
        </div>
      )}
    </div>
  );
};

export default BridgeTest; 