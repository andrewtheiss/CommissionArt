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

  // Direct L1 query of NFT ownership
  const queryNFTOnL1 = async () => {
    // Ensure we're on L1
    if (layer !== 'l1') {
      setLayer('l1');
      setBridgeStatus('Switching to L1 (Ethereum) for direct NFT query...');
      setTimeout(queryNFTOnL1, 1000); // Try again after network change
      return;
    }

    try {
      // Connect wallet if not connected
      if (!isConnected) {
        await connectWallet();
        if (!isConnected) {
          setBridgeStatus('Please connect your wallet to continue');
          return;
        }
      }

      // Get the contract address and validate
      const contractAddress = document.getElementById('l1NftContract') as HTMLInputElement;
      const tokenId = document.getElementById('l1TokenId') as HTMLInputElement;

      if (!contractAddress || !tokenId || !ethers.isAddress(contractAddress.value)) {
        setBridgeStatus('Please enter a valid NFT contract address and token ID');
        return;
      }

      const networkName = environment === 'testnet' ? 'Sepolia' : 'Ethereum Mainnet';
      setBridgeStatus(`Querying NFT ownership directly on L1 (${networkName}) for contract ${contractAddress.value} and token ID ${tokenId.value}...`);

      // Connect to provider
      const provider = new ethers.BrowserProvider(window.ethereum);
      
      // Confirm we're on the right network
      const network = await provider.getNetwork();
      const isSepoliaChainId = network.chainId === 11155111n; // Sepolia
      const isMainnetChainId = network.chainId === 1n; // Ethereum mainnet
      
      if ((environment === 'testnet' && !isSepoliaChainId) || 
          (environment === 'mainnet' && !isMainnetChainId)) {
        setBridgeStatus(prev => `${prev}\n\nError: Please make sure your wallet is connected to ${networkName}`);
        return;
      }

      // Standard ERC721 interface for ownerOf
      const erc721ABI = ['function ownerOf(uint256 tokenId) view returns (address)'];
      
      // Create contract instance
      const nftContract = new ethers.Contract(contractAddress.value, erc721ABI, provider);
      
      // Query owner
      const owner = await nftContract.ownerOf(tokenId.value);
      
      setBridgeStatus(prev => `${prev}\n\nNFT Owner (from L1 ${networkName} direct query): ${owner}`);
    } catch (error: any) {
      console.error('Error querying NFT on L1:', error);
      setBridgeStatus(prev => `${prev}\n\nError querying NFT on L1: ${error.message || 'Unknown error'}`);
    }
  };

  // Create a retryable ticket via L1 contract
  const createRetryableTicket = async () => {
    if (!isConnected) {
      setBridgeStatus('Please connect your wallet to continue');
      return;
    }

    try {
      setBridgeStatus('Creating retryable ticket...');

      // Get the contract address and validate
      const contractAddress = document.getElementById('l1NftContract') as HTMLInputElement;
      const tokenId = document.getElementById('l1TokenId') as HTMLInputElement;
      const ethValueInput = document.getElementById('l1EthValue') as HTMLInputElement;
      
      // Get the advanced options
      const maxSubmissionCostInput = document.getElementById('maxSubmissionCost') as HTMLInputElement;
      const l2GasLimitInput = document.getElementById('l2GasLimit') as HTMLInputElement;
      const maxFeePerGasInput = document.getElementById('maxFeePerGas') as HTMLInputElement;

      if (!contractAddress || !tokenId || !ethers.isAddress(contractAddress.value)) {
        setBridgeStatus('Please enter a valid NFT contract address and token ID');
        return;
      }

      if (!ethValueInput || !ethValueInput.value) {
        setBridgeStatus('Please enter a valid ETH value to cover cross-chain fees');
        return;
      }

      const networkName = environment === 'testnet' ? 'Sepolia' : 'Ethereum Mainnet';
      setBridgeStatus(`Creating retryable ticket on L1 (${networkName}) for contract ${contractAddress.value} and token ID ${tokenId.value}...`);

      // Get the L1QueryOwner contract address
      const l1ContractAddress = contractConfig.addresses.l1[environment];
      if (!l1ContractAddress || !ethers.isAddress(l1ContractAddress)) {
        setBridgeStatus(prev => `${prev}\n\nError: Invalid L1QueryOwner contract address. Please check contract configuration.`);
        return;
      }

      // Get the L2Relay contract address
      const l2ContractAddress = contractConfig.addresses.l2[environment];
      if (!l2ContractAddress || !ethers.isAddress(l2ContractAddress)) {
        setBridgeStatus(prev => `${prev}\n\nError: Invalid L2Relay contract address. Please check contract configuration.`);
        return;
      }

      // Get advanced options from state or use defaults
      const maxSubmissionCost = BigInt(maxSubmissionCostInput?.value || '1000000'); // Default 0.001 ETH in wei
      const l2GasLimit = BigInt(l2GasLimitInput?.value || '100000'); // Default 100k gas
      const maxFeePerGas = BigInt(maxFeePerGasInput?.value || '1000000000'); // Default 1 gwei

      // Display parameters for user confirmation
      console.log("Creating retryable ticket with parameters:");
      console.log("- NFT Contract:", contractAddress.value);
      console.log("- Token ID:", tokenId.value);
      console.log("- L2 Receiver:", l2ContractAddress);
      console.log("- Max Submission Cost:", maxSubmissionCost, "wei");
      console.log("- Gas Limit:", l2GasLimit);
      console.log("- Max Fee Per Gas:", maxFeePerGas, "wei");

      // Convert from ETH to wei for transaction value
      const ethValue = parseEther(ethValueInput.value);
      const ethValueWei = parseEther(ethValueInput.value);

      // Create contract instance
      const provider = new ethers.BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();
      const l1QueryContract = new ethers.Contract(
        l1ContractAddress,
        [
          "function queryNFTAndSendBack(address nftContract, uint256 tokenId, address l2Receiver, uint256 maxSubmissionCost, uint256 gasLimit, uint256 maxFeePerGas) external payable",
          "event OwnerQueried(address indexed nftContract, uint256 indexed tokenId, address owner, uint256 ticketId)"
        ],
        signer
      );

      // Format parameters for Vyper contract
      const tokenIdBN = toBigInt(tokenId.value);
      const maxSubmissionCostBN = toBigInt(maxSubmissionCost);
      const gasLimitBN = toBigInt(l2GasLimit);
      const maxFeePerGasBN = toBigInt(maxFeePerGas);

      // Send transaction
      try {
        console.log('Sending transaction with params:', {
          nftContract: contractAddress.value,
          tokenId: tokenIdBN,
          l2Receiver: l2ContractAddress,
          maxSubmissionCost: maxSubmissionCostBN,
          gasLimit: gasLimitBN,
          maxFeePerGas: maxFeePerGasBN,
          ethValue: ethValueWei
        });

        // Prepare transaction options
        const txOptions = {
          value: ethValueWei
        };

        // Call the contract function
        const tx = await l1QueryContract.queryNFTAndSendBack(
          contractAddress.value,
          tokenIdBN,
          l2ContractAddress,
          maxSubmissionCostBN,
          gasLimitBN,
          maxFeePerGasBN,
          txOptions
        );

        console.log('Transaction submitted:', tx.hash);
        setBridgeStatus(`Transaction submitted: ${tx.hash}`);
        
        // Wait for transaction confirmation
        const receipt = await tx.wait();
        console.log('Transaction confirmed:', receipt);
        
        // Find the OwnerQueried event from the receipt
        const ownerQueriedEvent = receipt.logs.find(
          (log: any) => log.fragment?.name === 'OwnerQueried'
        );
        
        if (ownerQueriedEvent) {
          const args = ownerQueriedEvent.args;
          const owner = args[0];
          const ticketId = args[1];
          
          console.log('OwnerQueried event found:', { owner, ticketId });
          setBridgeStatus(`NFT owner query submitted. Awaiting L2 response for ticket: ${ticketId}`);
          
          // Start listening for result on L2
          setIsListening(true);
        } else {
          console.log('No OwnerQueried event found in the receipt');
          setBridgeStatus('Transaction confirmed, but no OwnerQueried event found');
        }
      } catch (error: any) {
        console.error("Error creating retryable ticket:", error);
        setBridgeStatus(`Error: ${error instanceof Error ? error.message : String(error)}`);
      }
    } catch (error) {
      console.error("Error creating retryable ticket:", error);
      setBridgeStatus(`Error: ${error instanceof Error ? error.message : String(error)}`);
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
      
      {/* Direct L1 NFT Query Section */}
      <div className="l1-query-section">
        <h3>Direct L1 Query ({environment === 'testnet' ? 'Sepolia' : 'Ethereum Mainnet'})</h3>
        <div className="info-message">
          This queries the NFT ownership directly on L1 without going through the cross-chain bridge process.
        </div>
        
        <div className="l1-query-form">
          <div className="input-group">
            <label>NFT Contract Address:</label>
            <input 
              type="text" 
              id="l1NftContract"
              defaultValue={environment === 'testnet' ? '0x3cF3dada5C03F32F0b77AAE7Ae19F61Ab89dbD06' : ''}
              placeholder="0x..."
            />
          </div>
          
          <div className="input-group">
            <label>Token ID:</label>
            <input 
              type="text" 
              id="l1TokenId"
              defaultValue={environment === 'testnet' ? '1' : ''}
              placeholder="1"
            />
          </div>
          
          <div className="input-group">
            <label>ETH Value (for cross-chain fees):</label>
            <input 
              type="text" 
              id="l1EthValue"
              defaultValue="0.01"
              placeholder="0.01"
            />
            <div className="field-help">
              Required for creating a retryable ticket. Recommended: 0.01 ETH or more to cover cross-chain fees, gas costs, and L2 execution fees. Insufficient value is the most common cause of failures.
            </div>
          </div>
          
          <details className="advanced-options">
            <summary>Advanced Retryable Ticket Options</summary>
            <div className="advanced-fields">
              <div className="input-group">
                <label>Max Submission Cost (wei):</label>
                <input 
                  type="text" 
                  id="maxSubmissionCost"
                  defaultValue="1000000"
                  placeholder="1000000"
                />
                <div className="field-help">
                  Cost of storing the retryable ticket on L2 (in wei). Default: 1000000 (0.001 ETH)
                </div>
              </div>
              
              <div className="input-group">
                <label>Gas Limit for L2 Execution:</label>
                <input 
                  type="text" 
                  id="l2GasLimit"
                  defaultValue="100000"
                  placeholder="100000"
                />
                <div className="field-help">
                  Gas limit for executing the callback on L2 (in wei). Default: 100000 (0.0001 ETH)
                </div>
              </div>
              
              <div className="input-group">
                <label>Max Fee Per Gas (wei):</label>
                <input 
                  type="text" 
                  id="maxFeePerGas"
                  defaultValue="1000000000"
                  placeholder="1000000000"
                />
                <div className="field-help">
                  Maximum gas price for L2 execution (in wei). Default: 1 gwei (0.000001 ETH)
                </div>
              </div>
            </div>
          </details>
          
          <div className="action-buttons">
            <button 
              className="l1-query-button"
              onClick={queryNFTOnL1}
            >
              Query Directly on L1
            </button>
            <button 
              className="l1-create-ticket-button"
              onClick={createRetryableTicket}
            >
              Create Retryable Ticket to L2
            </button>
          </div>
        </div>
      </div>
      
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
      
      <div className="status-box">
        <h3>Status</h3>
        <pre>{bridgeStatus || 'No status updates yet. Actions will be displayed here.'}</pre>
      </div>
    </div>
  );
};

export default BridgeTest; 