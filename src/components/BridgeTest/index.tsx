import React, { useState, useEffect } from 'react';
import { useBlockchain } from '../../utils/BlockchainContext';
import useContractConfig from '../../utils/useContractConfig';
import abiLoader from '../../utils/abiLoader';
import NFTOwnershipQuery from './NFTOwnershipQuery';
import './BridgeTest.css';
import { ethers } from 'ethers';
import { parseEther, toBigInt } from "ethers";

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

// Network configuration for MetaMask
interface NetworkParams {
  chainId: string;
  chainName: string;
  rpcUrls: string[];
  nativeCurrency: {
    name: string;
    symbol: string;
    decimals: number;
  };
  blockExplorerUrls: string[];
}

// LocalStorage key for saving/loading contract config
const LOCAL_STORAGE_KEY = 'bridge_test_contract_config';

// Network configurations for MetaMask
const NETWORK_CONFIG = {
  sepolia: {
    chainId: "0xaa36a7", // 11155111 in decimal
    chainName: "Sepolia Testnet",
    rpcUrls: [
      "https://eth-sepolia.public.blastapi.io",
      "https://ethereum-sepolia.blockpi.network/v1/rpc/public",
      "https://sepolia.infura.io/v3/9aa3d95b3bc440fa88ea12eaa4456161" // Public Infura ID
    ],
    nativeCurrency: {
      name: "Sepolia ETH",
      symbol: "ETH",
      decimals: 18
    },
    blockExplorerUrls: ["https://sepolia.etherscan.io"]
  },
  arbitrumSepolia: {
    chainId: "0x66eee", // 421614 in decimal
    chainName: "Arbitrum Sepolia Testnet",
    rpcUrls: [
      "https://sepolia-rollup.arbitrum.io/rpc",
      "https://arbitrum-sepolia.infura.io/v3/9aa3d95b3bc440fa88ea12eaa4456161", // Public Infura ID
      "https://arb-sepolia.g.alchemy.com/v2/demo", // Alchemy demo key
      "https://arbitrum-sepolia.publicnode.com"
    ],
    nativeCurrency: {
      name: "Arbitrum Sepolia ETH",
      symbol: "ETH",
      decimals: 18
    },
    blockExplorerUrls: ["https://sepolia.arbiscan.io"]
  }
};

const BridgeTest: React.FC = () => {
  // State for network selection
  const [layer, setLayer] = useState<'l1' | 'l2'>('l1');
  const [environment, setEnvironment] = useState<'testnet' | 'mainnet'>('testnet');
  
  // State for showing/hiding MetaMask actions dropdown
  const [showMetaMaskActions, setShowMetaMaskActions] = useState(false);
  
  // Get blockchain context
  const { networkType, switchNetwork, connectWallet, walletAddress, isConnected } = useBlockchain();
  
  // Get contract configuration
  const { loading: configLoading, config: contractsConfig, getContract, reloadConfig } = useContractConfig();
  
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
  
  // Bridge status
  const [bridgeStatus, setBridgeStatus] = useState<string>('');
  
  // State for showing/hiding contract configuration
  const [showContractConfig, setShowContractConfig] = useState(false);
  
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
  
  // Functions to add networks to MetaMask
  const addNetworkToMetaMask = async (network: 'sepolia' | 'arbitrumSepolia') => {
    if (!window.ethereum) {
      alert('MetaMask is not installed. Please install it to use this feature.');
      return;
    }
    
    try {
      const params = NETWORK_CONFIG[network];
      await window.ethereum.request({
        method: 'wallet_addEthereumChain',
        params: [params],
      });
      
      setBridgeStatus(prev => 
        `${prev ? prev + '\n\n' : ''}Successfully added ${params.chainName} to your wallet.`
      );
    } catch (error: any) {
      console.error(`Error adding ${network} to MetaMask:`, error);
      setBridgeStatus(prev => 
        `${prev ? prev + '\n\n' : ''}Error adding network to MetaMask: ${error.message || error}`
      );
    }
  };
  
  // Function to switch networks in MetaMask
  const switchNetworkInMetaMask = async (network: 'sepolia' | 'arbitrumSepolia') => {
    if (!window.ethereum) {
      alert('MetaMask is not installed. Please install it to use this feature.');
      return;
    }
    
    try {
      const chainIdHex = NETWORK_CONFIG[network].chainId;
      
      try {
        // First try to switch to the network
        await window.ethereum.request({
          method: 'wallet_switchEthereumChain',
          params: [{ chainId: chainIdHex }],
        });
        
        setBridgeStatus(prev => 
          `${prev ? prev + '\n\n' : ''}Successfully switched to ${NETWORK_CONFIG[network].chainName}.`
        );
      } catch (switchError: any) {
        // If the error code is 4902, the network isn't added yet
        if (switchError.code === 4902) {
          // Add the network first and then try to switch again
          await addNetworkToMetaMask(network);
          await window.ethereum.request({
            method: 'wallet_switchEthereumChain',
            params: [{ chainId: chainIdHex }],
          });
          
          setBridgeStatus(prev => 
            `${prev ? prev + '\n\n' : ''}Successfully added and switched to ${NETWORK_CONFIG[network].chainName}.`
          );
        } else {
          throw switchError;
        }
      }
    } catch (error: any) {
      console.error(`Error switching to ${network} in MetaMask:`, error);
      setBridgeStatus(prev => 
        `${prev ? prev + '\n\n' : ''}Error switching network in MetaMask: ${error.message || error}`
      );
    }
  };

  // Function to call queryNFTAndSendBack on the deployed L1QueryOwner contract
  const callQueryNFTAndSendBack = async () => {
    if (!isConnected) {
      setBridgeStatus('Please connect your wallet to continue');
      return;
    }

    // Ensure we're on L1 testnet
    if (layer !== 'l1' || environment !== 'testnet') {
      setLayer('l1');
      setEnvironment('testnet');
      setBridgeStatus('Switching to L1 (Sepolia) network...');
      setTimeout(callQueryNFTAndSendBack, 1000); // Try again after network change
      return;
    }

    try {
      setBridgeStatus('Preparing to query NFT ownership and send result to L2...');

      // Get form values or use defaults
      const nftContractElement = document.getElementById('nftContract') as HTMLInputElement;
      const tokenIdElement = document.getElementById('tokenId') as HTMLInputElement;
      const l2ReceiverElement = document.getElementById('l2Receiver') as HTMLInputElement;
      const ethValueElement = document.getElementById('ethValue') as HTMLInputElement;

      // Use the form values or fallback to defaults
      const nftContract = nftContractElement?.value || '0x3cF3dada5C03F32F0b77AAE7Ae19F61Ab89dbD06';
      const tokenId = tokenIdElement?.value || '0';
      const l2Receiver = l2ReceiverElement?.value || '0xef02F150156e45806aaF17A60B5541D079FE13e6';
      const ethValue = ethValueElement?.value || '0.001';

      // The deployed contract address on Sepolia
      const contractAddress = '0xbd25dC4bDe33A14AE54c4BEeDE14297E4235a4e2';
      
      setBridgeStatus(`Calling queryNFTAndSendBack on contract ${contractAddress} with parameters:
- NFT Contract: ${nftContract}
- Token ID: ${tokenId}
- L2 Receiver: ${l2Receiver}
- ETH Value: ${ethValue} ETH`);

      // Create contract instance
      const provider = new ethers.BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();
      
      // Confirm we're on the right network
      const network = await provider.getNetwork();
      const isSepoliaChainId = network.chainId === 11155111n; // Sepolia
      
      if (!isSepoliaChainId) {
        setBridgeStatus(prev => `${prev}\n\nError: Please make sure your wallet is connected to Sepolia`);
        return;
      }

      // L1QueryOwner contract ABI (only the function we need)
      const l1QueryOwnerABI = [
        "function queryNFTAndSendBack(address nftContract, uint256 tokenId, address l2Receiver) external payable",
        "event OwnerQueried(address indexed nftContract, uint256 indexed tokenId, address owner, uint256 ticketId)"
      ];
      
      // Create contract instance
      const contract = new ethers.Contract(contractAddress, l1QueryOwnerABI, signer);
      
      // Convert ETH value to wei
      const ethValueWei = parseEther(ethValue);
      
      // Call the contract function
      const tx = await contract.queryNFTAndSendBack(
        nftContract,
        tokenId,
        l2Receiver,
        { value: ethValueWei }
      );
      
      setBridgeStatus(prev => `${prev}\n\nTransaction submitted: ${tx.hash}`);
      
      // Wait for transaction confirmation
      const receipt = await tx.wait();
      
      setBridgeStatus(prev => `${prev}\n\nTransaction confirmed! Transaction hash: ${tx.hash}`);
      
      // Find the OwnerQueried event
      const ownerQueriedEvents = receipt.logs
        .filter((log: any) => log.fragment?.name === 'OwnerQueried');
      
      if (ownerQueriedEvents.length > 0) {
        const event = ownerQueriedEvents[0];
        const ticketId = event.args[3]; // Get the ticket ID from the event
        
        setBridgeStatus(prev => `${prev}\n\nSuccess! NFT ownership query sent to Arbitrum.
Ticket ID: ${ticketId}
You can monitor the status at: https://sepolia-retryable-tx-dashboard.arbitrum.io/tx/${tx.hash}`);
      } else {
        setBridgeStatus(prev => `${prev}\n\nTransaction succeeded but no OwnerQueried event was found.`);
      }
      
    } catch (error: any) {
      console.error('Error calling queryNFTAndSendBack:', error);
      setBridgeStatus(prev => `${prev}\n\nError: ${error.message || String(error)}`);
    }
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
      
      {environment === 'testnet' && (
        <div className="metamask-dropdown">
          <button 
            className="dropdown-toggle" 
            onClick={() => setShowMetaMaskActions(!showMetaMaskActions)}
          >
            <span className="metamask-icon"></span>
            MetaMask Network Tools
            <span className={`dropdown-arrow ${showMetaMaskActions ? 'open' : ''}`}>▼</span>
          </button>
          
          {showMetaMaskActions && (
            <div className="metamask-actions">
              <div className="action-group">
                <h4>Add Network to MetaMask</h4>
                <div className="button-group">
                  <button 
                    className="metamask-button add-network" 
                    onClick={() => addNetworkToMetaMask('sepolia')}
                    title="Add Sepolia to MetaMask"
                  >
                    Add Sepolia
                  </button>
                  <button 
                    className="metamask-button add-network" 
                    onClick={() => addNetworkToMetaMask('arbitrumSepolia')}
                    title="Add Arbitrum Sepolia to MetaMask"
                  >
                    Add Arbitrum Sepolia
                  </button>
                </div>
              </div>
              
              <div className="action-group">
                <h4>Switch Network in MetaMask</h4>
                <div className="button-group">
                  <button 
                    className="metamask-button switch-network" 
                    onClick={() => switchNetworkInMetaMask('sepolia')}
                    title="Switch to Sepolia in MetaMask"
                  >
                    Switch to Sepolia
                  </button>
                  <button 
                    className="metamask-button switch-network" 
                    onClick={() => switchNetworkInMetaMask('arbitrumSepolia')}
                    title="Switch to Arbitrum Sepolia in MetaMask"
                  >
                    Switch to Arbitrum Sepolia
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* Query NFT Ownership Form */}
      <div className="nft-query-form-section">
        <h3>Call queryNFTAndSendBack on Sepolia</h3>
        <div className="info-message">
          This will query the NFT ownership on L1 and send the result to L2 via a retryable ticket.
        </div>
        
        <div className="form-container">
          <div className="input-group">
            <label>NFT Contract Address:</label>
            <input 
              type="text" 
              id="nftContract"
              defaultValue="0x3cF3dada5C03F32F0b77AAE7Ae19F61Ab89dbD06"
              placeholder="0x3cF3dada5C03F32F0b77AAE7Ae19F61Ab89dbD06"
            />
          </div>
          
          <div className="input-group">
            <label>Token ID:</label>
            <input 
              type="text" 
              id="tokenId"
              defaultValue="0"
              placeholder="0"
            />
          </div>
          
          <div className="input-group">
            <label>L2 Receiver Address:</label>
            <input 
              type="text" 
              id="l2Receiver"
              defaultValue="0xef02F150156e45806aaF17A60B5541D079FE13e6"
              placeholder="0xef02F150156e45806aaF17A60B5541D079FE13e6"
            />
          </div>
          
          <div className="input-group">
            <label>ETH Value (for cross-chain fees):</label>
            <input 
              type="text" 
              id="ethValue"
              defaultValue="0.001"
              placeholder="0.001"
            />
            <div className="field-help">
              Amount of ETH to send with the transaction. This covers cross-chain fees, gas costs, and L2 execution.
            </div>
          </div>
          
          <div className="contract-info">
            <p>Contract: <span>0xbd25dC4bDe33A14AE54c4BEeDE14297E4235a4e2</span> (Sepolia)</p>
            <a 
              href="https://sepolia-retryable-tx-dashboard.arbitrum.io/" 
              target="_blank" 
              rel="noopener noreferrer"
              className="arb-link"
            >
              View on Arbitrum Retryable Dashboard
            </a>
          </div>
          
          <button 
            className="query-button"
            onClick={callQueryNFTAndSendBack}
          >
            Submit Query
          </button>
        </div>
      </div>
      
      {/* NFT Ownership Query Component */}
      <NFTOwnershipQuery 
        layer={layer}
        environment={environment}
        contractConfig={contractConfig}
        setBridgeStatus={setBridgeStatus}
        isListening={isListening}
        setIsListening={setIsListening}
        setLayer={setLayer}
      />
      
      {/* Contract Configuration Dropdown */}
      <div className="contract-config-dropdown">
        <button 
          className="dropdown-toggle" 
          onClick={() => setShowContractConfig(!showContractConfig)}
        >
          Contract Configuration
          <span className={`dropdown-arrow ${showContractConfig ? 'open' : ''}`}>▼</span>
        </button>
        
        {showContractConfig && (
          <div className="contract-config">
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
        )}
      </div>
      
      <div className="status-box">
        <h3>Status</h3>
        <pre>{bridgeStatus || 'No status updates yet. Actions will be displayed here.'}</pre>
      </div>
    </div>
  );
};

export default BridgeTest; 