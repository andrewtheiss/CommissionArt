import React, { useState, useEffect } from 'react';
import { useBlockchain } from '../../utils/BlockchainContext';
import useContractConfig from '../../utils/useContractConfig';
import abiLoader from '../../utils/abiLoader';
import NFTOwnershipQuery from './NFTOwnershipQuery';
import L3OwnerLookup from './L3OwnerLookup';
import L1OwnerUpdateRequest from './L1OwnerUpdateRequest';
import L2RelayManager from './L2RelayManager';
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
  l3: {
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
    l3: string;
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
      "https://rpc.sepolia.dev",
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

const BridgeTestContainer: React.FC = () => {
  // Add error state
  const [blockchainError, setBlockchainError] = useState<string | null>(null);
  
  // Try-catch for blockchain context
  let blockchainContext;
  try {
    blockchainContext = useBlockchain();
  } catch (error) {
    console.error("Error accessing blockchain context:", error);
    setBlockchainError("Failed to access blockchain services. Make sure MetaMask is installed and accessible.");
    // Return a fallback UI
    return (
      <div className="bridge-test-container error">
        <h2>CommissionArt NFT Bridge Testing</h2>
        <div className="error-message">
          <h3>Blockchain Connection Error</h3>
          <p>{blockchainError}</p>
          <p>Please ensure that:</p>
          <ul>
            <li>MetaMask extension is installed and enabled</li>
            <li>You are logged in to MetaMask</li>
            <li>Your browser allows access to the MetaMask extension</li>
          </ul>
          <button onClick={() => window.location.reload()}>Retry Connection</button>
        </div>
      </div>
    );
  }
  
  // Destructure blockchain context values
  const { 
    networkType, 
    switchNetwork, 
    switchToLayer, 
    connectWallet, 
    walletAddress, 
    isConnected 
  } = blockchainContext;
  
  // Try-catch for contract config
  let configContext;
  try {
    configContext = useContractConfig();
  } catch (error) {
    console.error("Error accessing contract configuration:", error);
    // Return a fallback UI
    return (
      <div className="bridge-test-container error">
        <h2>CommissionArt NFT Bridge Testing</h2>
        <div className="error-message">
          <h3>Contract Configuration Error</h3>
          <p>Failed to load contract configuration. This may be due to missing or malformed configuration files.</p>
          <button onClick={() => window.location.reload()}>Retry</button>
        </div>
      </div>
    );
  }
  
  // Destructure contract config values
  const { 
    loading: configLoading, 
    config: contractsConfig, 
    getContract, 
    reloadConfig 
  } = configContext;
  
  // State for network selection
  const [layer, setLayer] = useState<'l1' | 'l2'>('l1');
  const [environment, setEnvironment] = useState<'testnet' | 'mainnet'>('testnet');
  
  // State for showing/hiding MetaMask actions dropdown
  const [showMetaMaskActions, setShowMetaMaskActions] = useState(false);
  
  // State for showing/hiding NFT Query
  const [showNFTQuery, setShowNFTQuery] = useState(false);
  
  // State to track listening for events
  const [isListening, setIsListening] = useState(false);
  
  // Ensure contractsConfig is safely accessed by creating a safe version with extra null checks
  const safeContractsConfig = {
    networks: {
      testnet: {
        l1: {
          address: contractsConfig?.networks?.testnet?.l1?.address || '',
          contract: contractsConfig?.networks?.testnet?.l1?.contract || 'L1QueryOwner'
        },
        l2: {
          address: contractsConfig?.networks?.testnet?.l2?.address || '',
          contract: contractsConfig?.networks?.testnet?.l2?.contract || 'L2Relay'
        },
        l3: {
          address: contractsConfig?.networks?.testnet?.l3?.address || '',
          contract: contractsConfig?.networks?.testnet?.l3?.contract || 'L3QueryOwner'
        }
      },
      mainnet: {
        l1: {
          address: contractsConfig?.networks?.mainnet?.l1?.address || '',
          contract: contractsConfig?.networks?.mainnet?.l1?.contract || 'L1QueryOwner'
        },
        l2: {
          address: contractsConfig?.networks?.mainnet?.l2?.address || '',
          contract: contractsConfig?.networks?.mainnet?.l2?.contract || 'L2Relay'
        },
        l3: {
          address: contractsConfig?.networks?.mainnet?.l3?.address || '',
          contract: contractsConfig?.networks?.mainnet?.l3?.contract || 'L3QueryOwner'
        }
      }
    }
  };
  
  // Use our safeguard function to ensure valid configuration
  const verifiedConfig = safeContractsConfig;
  
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
    
    // Initialize with empty addresses and default ABI names
    return {
      addresses: {
        l1: { testnet: '', mainnet: '' },
        l2: { testnet: '', mainnet: '' },
        l3: { testnet: '', mainnet: '' }
      },
      abiFiles: {
        l1: 'L1QueryOwner',
        l2: 'L2Relay',
        l3: 'L3QueryOwner'
      }
    };
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
  
  // State for gas estimation
  const [gasEstimation, setGasEstimation] = useState<{
    estimating: boolean;
    estimationComplete: boolean;
    maxSubmissionCost: string;
    gasLimit: string;
    maxFeePerGas: string;
    totalEstimatedCost: string;
  }>({
    estimating: false,
    estimationComplete: false,
    maxSubmissionCost: "4491126164080", // Higher default value
    gasLimit: "1000000",
    maxFeePerGas: "100000000",
    totalEstimatedCost: "0",
  });
  
  // Save config to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(contractConfig));
  }, [contractConfig]);
  
  // Load contract addresses from configuration when it's available
  useEffect(() => {
    if (contractsConfig && !configLoading) {
      try {
        // Load the deployed contract addresses from the configuration using our safe version
        const newAddresses = {
          l1: {
            testnet: safeContractsConfig.networks.testnet.l1.address || '',
            mainnet: safeContractsConfig.networks.mainnet.l1.address || '',
          },
          l2: {
            testnet: safeContractsConfig.networks.testnet.l2.address || '',
            mainnet: safeContractsConfig.networks.mainnet.l2.address || '',
          },
          l3: {
            testnet: safeContractsConfig.networks.testnet.l3.address || '',
            mainnet: safeContractsConfig.networks.mainnet.l3.address || '',
          }
        };
        
        // Update contract ABIs based on configuration
        const newAbiFiles = {
          l1: safeContractsConfig.networks.testnet.l1.contract || 'L1QueryOwner',
          l2: safeContractsConfig.networks.testnet.l2.contract || 'L2Relay',
          l3: safeContractsConfig.networks.testnet.l3.contract || 'L3QueryOwner'
        };
        
        // Update the contract configuration if any address has changed
        if (
          newAddresses.l1.testnet !== contractConfig.addresses.l1.testnet ||
          newAddresses.l1.mainnet !== contractConfig.addresses.l1.mainnet ||
          newAddresses.l2.testnet !== contractConfig.addresses.l2.testnet ||
          newAddresses.l2.mainnet !== contractConfig.addresses.l2.mainnet ||
          newAddresses.l3.testnet !== contractConfig.addresses.l3.testnet ||
          newAddresses.l3.mainnet !== contractConfig.addresses.l3.mainnet ||
          newAbiFiles.l1 !== contractConfig.abiFiles.l1 ||
          newAbiFiles.l2 !== contractConfig.abiFiles.l2 ||
          newAbiFiles.l3 !== contractConfig.abiFiles.l3
        ) {
          setContractConfig({
            addresses: newAddresses,
            abiFiles: newAbiFiles
          });
          
          setBridgeStatus(prev => {
            return `${prev ? prev + '\n\n' : ''}Loaded contract addresses from configuration.`;
          });
        }
      } catch (error) {
        console.error("Error updating contract configuration:", error);
        // Don't update the configuration if there's an error
      }
    }
  }, [contractsConfig, configLoading]);
  
  // Handle layer selection change
  const handleLayerChange = (newLayer: 'l1' | 'l2') => {
    setLayer(newLayer);
    
    // Automatically switch to the appropriate network when layer is changed
    switchToLayer(newLayer, environment);
    
    setBridgeStatus(`Switched to ${newLayer === 'l1' ? 'Ethereum' : 'Arbitrum'} ${environment === 'testnet' ? 'testnet' : 'mainnet'}`);
  };
  
  // Handle environment selection change
  const handleEnvironmentChange = (newEnvironment: 'testnet' | 'mainnet') => {
    setEnvironment(newEnvironment);
    
    // Automatically switch to the appropriate network when environment is changed
    switchToLayer(layer, newEnvironment);
    
    setBridgeStatus(`Switched to ${layer === 'l1' ? 'Ethereum' : 'Arbitrum'} ${newEnvironment === 'testnet' ? 'testnet' : 'mainnet'}`);
  };
  
  // Update selected ABI when layer or ABI file changes
  useEffect(() => {
    try {
      // Safely access the ABI file name with fallbacks
      const abiFileName = contractConfig?.abiFiles?.[layer] || 'L1QueryOwner';
      
      console.log(`Loading ABI for ${layer}: ${abiFileName}`);
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
    } catch (error) {
      console.error("Error loading ABI:", error);
      setBridgeStatus(prev => {
        if (prev.includes('Connected to')) {
          return `${prev}\n\nError loading ABI: ${error instanceof Error ? error.message : String(error)}`;
        }
        return `Error loading ABI: ${error instanceof Error ? error.message : String(error)}`;
      });
    }
  }, [layer, contractConfig.abiFiles]);
  
  // Handle contract address changes
  const handleAddressChange = (layer: 'l1' | 'l2' | 'l3', env: 'testnet' | 'mainnet', value: string) => {
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
  const handleABIChange = (layer: 'l1' | 'l2' | 'l3', value: string) => {
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
      setContractConfig({
        addresses: {
          l1: { testnet: '', mainnet: '' },
          l2: { testnet: '', mainnet: '' },
          l3: { testnet: '', mainnet: '' }
        },
        abiFiles: {
          l1: 'L1QueryOwner',
          l2: 'L2Relay',
          l3: 'L3QueryOwner'
        }
      });
      setBridgeStatus('Configuration reset to defaults');
    }
  };
  
  // Load from contract config file
  const handleLoadFromConfig = () => {
    if (configLoading) {
      setBridgeStatus('Contract configuration is still loading...');
      return;
    }
    
    if (window.confirm('Load contract addresses from the application configuration file?')) {
      try {
        // Load the deployed contract addresses from the configuration using our safe version
        const newAddresses = {
          l1: {
            testnet: safeContractsConfig.networks.testnet.l1.address || '',
            mainnet: safeContractsConfig.networks.mainnet.l1.address || '',
          },
          l2: {
            testnet: safeContractsConfig.networks.testnet.l2.address || '',
            mainnet: safeContractsConfig.networks.mainnet.l2.address || '',
          },
          l3: {
            testnet: safeContractsConfig.networks.testnet.l3.address || '',
            mainnet: safeContractsConfig.networks.mainnet.l3.address || '',
          }
        };
        
        // Update contract ABIs based on configuration
        const newAbiFiles = {
          l1: safeContractsConfig.networks.testnet.l1.contract || 'L1QueryOwner',
          l2: safeContractsConfig.networks.testnet.l2.contract || 'L2Relay',
          l3: safeContractsConfig.networks.testnet.l3.contract || 'L3QueryOwner'
        };
        
        setContractConfig({
          addresses: newAddresses,
          abiFiles: newAbiFiles
        });
        
        setBridgeStatus('Contract addresses loaded from configuration file.');
      } catch (error) {
        console.error("Error loading from config:", error);
        setBridgeStatus('Error loading contract addresses from configuration file.');
      }
    }
  };
  
  // Functions to add networks to MetaMask
  const addNetworkToMetaMask = async (network: 'sepolia' | 'arbitrumSepolia') => {
    if (typeof window === 'undefined' || !window.ethereum) {
      alert('MetaMask is not installed. Please install it to use this feature.');
      return;
    }
    
    try {
      const params = NETWORK_CONFIG[network];
      await (window as any).ethereum.request({
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
  
  // Function to switch networks in MetaMask - updated to use switchToLayer
  const switchNetworkInMetaMask = async (network: 'sepolia' | 'arbitrumSepolia') => {
    if (typeof window === 'undefined' || !window.ethereum) {
      alert('MetaMask is not installed. Please install it to use this feature.');
      return;
    }
    
    // Use our switchToLayer functionality for network switching
    if (network === 'sepolia') {
      switchToLayer('l1', 'testnet');
      setBridgeStatus(prev => `${prev ? prev + '\n\n' : ''}Requested switch to Sepolia testnet.`);
    } else if (network === 'arbitrumSepolia') {
      switchToLayer('l2', 'testnet');
      setBridgeStatus(prev => `${prev ? prev + '\n\n' : ''}Requested switch to Arbitrum Sepolia testnet.`);
    }
  };

  // Function to estimate gas for the retryable ticket
  const estimateRetryableTicketGas = async () => {
    if (!isConnected) {
      setBridgeStatus('Please connect your wallet to continue');
      return;
    }

    try {
      setGasEstimation(prev => ({ ...prev, estimating: true, estimationComplete: false }));
      setBridgeStatus('Estimating gas for retryable ticket...');

      // Check if window.ethereum exists
      if (typeof window === 'undefined' || !window.ethereum) {
        throw new Error('MetaMask is not installed or not accessible');
      }

      // Get form values or use defaults
      const nftContractElement = document.getElementById('nftContract') as HTMLInputElement;
      const tokenIdElement = document.getElementById('tokenId') as HTMLInputElement;
      const l2ReceiverElement = document.getElementById('l2Receiver') as HTMLInputElement;

      // Use the form values or fallback to defaults
      const nftContract = nftContractElement?.value || '0x3cF3dada5C03F32F0b77AAE7Ae19F61Ab89dbD06';
      const tokenId = tokenIdElement?.value || '0';
      const l2Receiver = l2ReceiverElement?.value || '0xef02F150156e45806aaF17A60B5541D079FE13e6';
      
      // The deployed contract address on Sepolia
      const contractAddress = '0xbd25dC4bDe33A14AE54c4BEeDE14297E4235a4e2';

      // Get L1 provider
      const l1Provider = new ethers.BrowserProvider((window as any).ethereum);
      
      // Create a mock L2 provider for Arbitrum Sepolia
      const l2Provider = new ethers.JsonRpcProvider("https://sepolia-rollup.arbitrum.io/rpc");

      // Get the current L1 gas price
      const l1FeeData = await l1Provider.getFeeData();
      const l1GasPrice = l1FeeData.gasPrice || ethers.parseUnits("20", "gwei"); // Fallback

      // Get the current L2 gas price (typically much lower than L1)
      const l2FeeData = await l2Provider.getFeeData();
      const l2GasPrice = l2FeeData.gasPrice || ethers.parseUnits("0.1", "gwei"); // Fallback
      
      setBridgeStatus(prev => `${prev}\n\nCurrent Gas Prices:
- L1 (Sepolia): ${ethers.formatUnits(l1GasPrice, "gwei")} gwei
- L2 (Arbitrum Sepolia): ${ethers.formatUnits(l2GasPrice, "gwei")} gwei`);

      // Estimate L2 gas for the operation (calling receiveResultFromL1)
      // We'll create a rough calldata simulation to estimate
      const functionSig = "0x7b8a9b7a"; // receiveResultFromL1(address)
      const mockOwner = "0x" + "0".repeat(64); // Mock owner parameter (will be replaced)
      const l2Calldata = functionSig + mockOwner;
      
      // L2 gas estimation
      let l2GasEstimate;
      try {
        l2GasEstimate = await l2Provider.estimateGas({
          to: l2Receiver,
          data: l2Calldata,
        });
        // Add a safety buffer (30%)
        l2GasEstimate = l2GasEstimate * BigInt(11130) / BigInt(100);
      } catch (error) {
        console.warn("L2 gas estimation failed, using default:", error);
        l2GasEstimate = BigInt(500000); // Use a conservative default
      }
      
      // Estimate the L1 calldata cost:
      // This is a simplified estimation - in a production app, you would use 
      // the Arbitrum SDK's L1ToL2MessageGasEstimator
      
      // Calculate a reasonable maxSubmissionCost based on L1 gas price
      // Higher L1 gas price means higher submission cost
      const callDataSizeEstimate = BigInt(300); // bytes
      const callDataGasCostPerByte = BigInt(16); // Approximation
      // maxSubmissionCost should scale with L1 gas price
      const estimatedMaxSubmissionCost = (callDataSizeEstimate * callDataGasCostPerByte * l1GasPrice) / BigInt(1e9);
      // Add a 50% buffer to be safe
      const maxSubmissionCost = estimatedMaxSubmissionCost * BigInt(150) / BigInt(100);
      
      // L2 gas price is typically much lower than L1, we'll use the current L2 gas price with a buffer
      const maxFeePerGas = l2GasPrice * BigInt(120) / BigInt(100); // 20% buffer
      
      // Calculate a reasonable total cost:
      // L1 cost (submission) + L2 cost (execution)
      const l2ExecutionCost = l2GasEstimate * maxFeePerGas;
      // Include some ETH for the auto-redeem attempt (l2CallValue is 0 in this case)
      const totalEstimatedCost = maxSubmissionCost + l2ExecutionCost;
      
      // Format values for display
      const maxSubmissionCostFormatted = ethers.formatEther(maxSubmissionCost);
      const gasLimitFormatted = l2GasEstimate.toString();
      const maxFeePerGasFormatted = maxFeePerGas.toString();
      const totalEstimatedCostFormatted = ethers.formatEther(totalEstimatedCost);
      
      // Add a buffer to the total recommended ETH value (25%)
      const recommendedEthValue = ethers.formatEther(totalEstimatedCost * BigInt(125) / BigInt(100));
      
      setBridgeStatus(prev => `${prev}\n\nGas Estimation Results:
- Max Submission Cost: ${maxSubmissionCostFormatted} ETH
- Gas Limit: ${gasLimitFormatted}
- Max Fee Per Gas: ${ethers.formatUnits(maxFeePerGas, "gwei")} gwei
- Total Estimated Cost: ${totalEstimatedCostFormatted} ETH
- Recommended ETH Value: ${recommendedEthValue} ETH (includes 25% buffer)`);

      // Update state with estimates
      setGasEstimation({
        estimating: false,
        estimationComplete: true,
        maxSubmissionCost: maxSubmissionCost.toString(),
        gasLimit: gasLimitFormatted,
        maxFeePerGas: maxFeePerGasFormatted,
        totalEstimatedCost: totalEstimatedCostFormatted,
      });
      
      // Update the ETH input field with the recommended value
      const ethValueElement = document.getElementById('ethValue') as HTMLInputElement;
      if (ethValueElement) {
        ethValueElement.value = recommendedEthValue;
      }
      
    } catch (error: any) {
      console.error('Error estimating gas:', error);
      setBridgeStatus(prev => `${prev}\n\nError estimating gas: ${error.message || String(error)}`);
      setGasEstimation(prev => ({ 
        ...prev, 
        estimating: false, 
        estimationComplete: false 
      }));
    }
  };

  // Function to call queryNFTAndSendBack with default parameters
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

      // Check if window.ethereum exists
      if (typeof window === 'undefined' || !window.ethereum) {
        throw new Error('MetaMask is not installed or not accessible');
      }

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
      
      // Default high values to ensure transaction success
      const maxSubmissionCost = "4500000000000";  // Very high value due to fluctuations
      const gasLimit = "1000000";                 // Keep at 1M gas
      const maxFeePerGas = "100000000";           // Keep at 0.1 gwei
      
      setBridgeStatus(`Calling queryNFTAndSendBack on contract ${contractAddress} with parameters:
- NFT Contract: ${nftContract}
- Token ID: ${tokenId}
- L2 Receiver: ${l2Receiver}
- ETH Value: ${ethValue} ETH
- Max Submission Cost: ${ethers.formatEther(maxSubmissionCost)} ETH
- Gas Limit: ${gasLimit}
- Max Fee Per Gas: ${ethers.formatUnits(maxFeePerGas, "gwei")} gwei`);

      // Create contract instance
      const provider = new ethers.BrowserProvider((window as any).ethereum);
      const signer = await provider.getSigner();
      
      // Confirm we're on the right network
      const network = await provider.getNetwork();
      const isSepoliaChainId = network.chainId === 11155111n; // Sepolia
      
      if (!isSepoliaChainId) {
        setBridgeStatus(prev => `${prev}\n\nError: Please make sure your wallet is connected to Sepolia`);
        return;
      }

      // L1QueryOwner contract ABI with all parameters 
      const l1QueryOwnerABI = [
        "function queryNFTAndSendBack(address nftContract, uint256 tokenId, address l2Receiver, uint256 maxSubmissionCost, uint256 gasLimit, uint256 maxFeePerGas) external payable",
        "event OwnerQueried(address indexed nftContract, uint256 indexed tokenId, address owner, uint256 ticketId)"
      ];
      
      // Create contract instance
      const contract = new ethers.Contract(contractAddress, l1QueryOwnerABI, signer);
      
      // Convert ETH value to wei
      const ethValueWei = parseEther(ethValue);
      
      // Call the contract function with all 6 parameters
      const tx = await contract.queryNFTAndSendBack(
        nftContract,
        tokenId,
        l2Receiver,
        maxSubmissionCost,
        gasLimit,
        maxFeePerGas,
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

  // Call queryNFTAndSendBack with optimized gas parameters
  const callQueryNFTAndSendBackOptimized = async () => {
    if (!isConnected) {
      setBridgeStatus('Please connect your wallet to continue');
      return;
    }

    // If we haven't estimated gas yet, run the estimation first
    if (!gasEstimation.estimationComplete) {
      setBridgeStatus('Please estimate gas first by clicking the "Estimate Gas" button');
      return;
    }

    // Ensure we're on L1 testnet
    if (layer !== 'l1' || environment !== 'testnet') {
      setLayer('l1');
      setEnvironment('testnet');
      setBridgeStatus('Switching to L1 (Sepolia) network...');
      setTimeout(() => callQueryNFTAndSendBackOptimized(), 1000); // Try again after network change
      return;
    }

    try {
      setBridgeStatus('Preparing to query NFT ownership with optimized gas parameters...');

      // Check if window.ethereum exists
      if (typeof window === 'undefined' || !window.ethereum) {
        throw new Error('MetaMask is not installed or not accessible');
      }

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
      
      setBridgeStatus(`Calling queryNFTAndSendBack with optimized gas parameters:
- NFT Contract: ${nftContract}
- Token ID: ${tokenId}
- L2 Receiver: ${l2Receiver}
- ETH Value: ${ethValue} ETH
- Max Submission Cost: ${ethers.formatEther(gasEstimation.maxSubmissionCost)} ETH
- Gas Limit: ${gasEstimation.gasLimit}
- Max Fee Per Gas: ${ethers.formatUnits(gasEstimation.maxFeePerGas, "gwei")} gwei`);

      // Create contract instance
      const provider = new ethers.BrowserProvider((window as any).ethereum);
      const signer = await provider.getSigner();
      
      // Confirm we're on the right network
      const network = await provider.getNetwork();
      const isSepoliaChainId = network.chainId === 11155111n; // Sepolia
      
      if (!isSepoliaChainId) {
        setBridgeStatus(prev => `${prev}\n\nError: Please make sure your wallet is connected to Sepolia`);
        return;
      }

      // L1QueryOwner contract ABI with the full function signature including all parameters
      const l1QueryOwnerABI = [
        "function queryNFTAndSendBack(address nftContract, uint256 tokenId, address l2Receiver, uint256 maxSubmissionCost, uint256 gasLimit, uint256 maxFeePerGas) external payable",
        "event OwnerQueried(address indexed nftContract, uint256 indexed tokenId, address owner, uint256 ticketId)"
      ];
      
      // Create contract instance
      const contract = new ethers.Contract(contractAddress, l1QueryOwnerABI, signer);
      
      // Convert ETH value to wei
      const ethValueWei = parseEther(ethValue);
      
      // Call the contract function with all parameters
      const tx = await contract.queryNFTAndSendBack(
        nftContract,
        tokenId,
        l2Receiver,
        gasEstimation.maxSubmissionCost,
        gasEstimation.gasLimit,
        gasEstimation.maxFeePerGas,
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
        
        setBridgeStatus(prev => `${prev}\n\nSuccess! NFT ownership query sent to Arbitrum with optimized gas parameters.
Ticket ID: ${ticketId}
You can monitor the status at: https://sepolia-retryable-tx-dashboard.arbitrum.io/tx/${tx.hash}`);
      } else {
        setBridgeStatus(prev => `${prev}\n\nTransaction succeeded but no OwnerQueried event was found.`);
      }
      
    } catch (error: any) {
      console.error('Error calling queryNFTAndSendBack with optimized parameters:', error);
      setBridgeStatus(prev => `${prev}\n\nError: ${error.message || String(error)}`);
    }
  };

  return (
    <div className="bridge-test-container">
      <h2>CommissionArt NFT Bridge Testing</h2>
      
      {configLoading ? (
        <div className="loading">Loading configuration...</div>
      ) : (
        <>
          <div className="network-selection">
            <div className="network-info">
              <h3>Current Network</h3>
              <p className={`network-type ${networkType.replace('_', '-')}`}>
                {networkType === 'arbitrum_mainnet' ? 'Arbitrum One' :
                 networkType === 'arbitrum_testnet' ? 'Arbitrum Sepolia' :
                 networkType === 'prod' ? 'Ethereum Mainnet' :
                 networkType === 'dev' || networkType === 'local' ? 'Sepolia Testnet' : 
                 'Unknown Network'}
              </p>
              <p className="wallet-info">
                {isConnected ? (
                  <>
                    <span className="wallet-address">
                      {walletAddress && `${walletAddress.substring(0, 6)}...${walletAddress.substring(walletAddress.length - 4)}`}
                    </span>
                    <span className="connection-status connected">Connected</span>
                  </>
                ) : (
                  <button onClick={connectWallet} className="connect-wallet-button">
                    Connect Wallet
                  </button>
                )}
              </p>
            </div>
            <div className="network-controls">
              <h3>Switch Networks</h3>
              <div className="network-buttons">
                <button 
                  className={`network-button ${layer === 'l1' ? 'active' : ''}`} 
                  onClick={() => handleLayerChange('l1')}
                >
                  Layer 1 ({environment === 'testnet' ? 'Sepolia' : 'Ethereum'})
                </button>
                <button 
                  className={`network-button ${layer === 'l2' ? 'active' : ''}`} 
                  onClick={() => handleLayerChange('l2')}
                >
                  Layer 2 ({environment === 'testnet' ? 'Arbitrum Sepolia' : 'Arbitrum One'})
                </button>
              </div>
              <div className="environment-buttons">
                <button 
                  className={`environment-button ${environment === 'testnet' ? 'active' : ''}`} 
                  onClick={() => handleEnvironmentChange('testnet')}
                >
                  Testnet
                </button>
                <button 
                  className={`environment-button ${environment === 'mainnet' ? 'active' : ''}`} 
                  onClick={() => handleEnvironmentChange('mainnet')}
                >
                  Mainnet
                </button>
              </div>
            </div>
          </div>
          
          <div className="bridge-components">
            {/* L3 Owner Lookup Component - Always visible */}
            <div className="component-section">
              <h3>L3 Ownership Lookup (Arbitrum)</h3>
              <L3OwnerLookup 
                environment={environment} 
                contractConfig={contractConfig} 
                setBridgeStatus={setBridgeStatus}
              />
            </div>
            
            {/* L1 Owner Request Component - Always visible */}
            <div className="component-section">
              <h3>L1 NFT Owner Request (Sepolia)</h3>
              <L1OwnerUpdateRequest />
            </div>
            
            {/* L2 Relay Manager Component - Now always visible */}
            <div className="component-section">
              <h3>L2 Relay Manager (Arbitrum Sepolia)</h3>
              <L2RelayManager />
            </div>
            
            {/* NFT Query Toggle */}
            <div className="component-section">
              <div className="component-header" onClick={() => setShowNFTQuery(!showNFTQuery)}>
                <h3>Advanced: Generic NFT Ownership Query</h3>
                <span className="toggle-icon">{showNFTQuery ? '▼' : '►'}</span>
              </div>
              {showNFTQuery && <NFTOwnershipQuery 
                layer={layer}
                environment={environment}
                contractConfig={contractConfig}
                setBridgeStatus={setBridgeStatus}
                isListening={isListening}
                setIsListening={setIsListening}
                setLayer={setLayer}
              />}
            </div>
            
            {/* Contract Config Toggle */}
            <div className="component-section">
              <div className="component-header" onClick={() => setShowContractConfig(!showContractConfig)}>
                <h3>Contract Configuration</h3>
                <span className="toggle-icon">{showContractConfig ? '▼' : '►'}</span>
              </div>
              {showContractConfig && (
                <div className="contract-config">
                  <h4>Contract Addresses</h4>
                  
                  {/* L1 Contract Address */}
                  <div className="config-row">
                    <label>L1 Contract (Sepolia):</label>
                    <input 
                      type="text" 
                      value={contractConfig.addresses.l1.testnet} 
                      onChange={(e) => handleAddressChange('l1', 'testnet', e.target.value)}
                      placeholder="L1 Contract Address (Sepolia)"
                    />
                  </div>
                  
                  <div className="config-row">
                    <label>L1 Contract (Mainnet):</label>
                    <input 
                      type="text" 
                      value={contractConfig.addresses.l1.mainnet} 
                      onChange={(e) => handleAddressChange('l1', 'mainnet', e.target.value)}
                      placeholder="L1 Contract Address (Mainnet)"
                    />
                  </div>
                  
                  {/* L2 Contract Address */}
                  <div className="config-row">
                    <label>L2 Contract (Arbitrum Sepolia):</label>
                    <input 
                      type="text" 
                      value={contractConfig.addresses.l2.testnet} 
                      onChange={(e) => handleAddressChange('l2', 'testnet', e.target.value)}
                      placeholder="L2 Contract Address (Arbitrum Sepolia)"
                    />
                  </div>
                  
                  <div className="config-row">
                    <label>L2 Contract (Arbitrum One):</label>
                    <input 
                      type="text" 
                      value={contractConfig.addresses.l2.mainnet} 
                      onChange={(e) => handleAddressChange('l2', 'mainnet', e.target.value)}
                      placeholder="L2 Contract Address (Arbitrum One)"
                    />
                  </div>
                  
                  {/* L3 Contract Address */}
                  <div className="config-row">
                    <label>L3 Contract (Arbitrum Sepolia):</label>
                    <input 
                      type="text" 
                      value={contractConfig.addresses.l3.testnet} 
                      onChange={(e) => handleAddressChange('l3', 'testnet', e.target.value)}
                      placeholder="L3 Contract Address (Arbitrum Sepolia)"
                    />
                  </div>
                  
                  <div className="config-row">
                    <label>L3 Contract (Arbitrum One):</label>
                    <input 
                      type="text" 
                      value={contractConfig.addresses.l3.mainnet} 
                      onChange={(e) => handleAddressChange('l3', 'mainnet', e.target.value)}
                      placeholder="L3 Contract Address (Arbitrum One)"
                    />
                  </div>
                  
                  <h4>Contract ABIs</h4>
                  
                  {/* L1 Contract ABI */}
                  <div className="config-row">
                    <label>L1 Contract ABI:</label>
                    <select 
                      value={contractConfig.abiFiles.l1} 
                      onChange={(e) => handleABIChange('l1', e.target.value)}
                    >
                      {availableAbis.map(abi => (
                        <option key={abi} value={abi}>{abi}</option>
                      ))}
                    </select>
                  </div>
                  
                  {/* L2 Contract ABI */}
                  <div className="config-row">
                    <label>L2 Contract ABI:</label>
                    <select 
                      value={contractConfig.abiFiles.l2} 
                      onChange={(e) => handleABIChange('l2', e.target.value)}
                    >
                      {availableAbis.map(abi => (
                        <option key={abi} value={abi}>{abi}</option>
                      ))}
                    </select>
                  </div>
                  
                  {/* L3 Contract ABI */}
                  <div className="config-row">
                    <label>L3 Contract ABI:</label>
                    <select 
                      value={contractConfig.abiFiles.l3} 
                      onChange={(e) => handleABIChange('l3', e.target.value)}
                    >
                      {availableAbis.map(abi => (
                        <option key={abi} value={abi}>{abi}</option>
                      ))}
                    </select>
                  </div>
                  
                  <div className="config-buttons">
                    <button onClick={handleLoadFromConfig}>Load from Contract Config</button>
                    <button onClick={handleResetConfig} className="reset-button">Reset</button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Bridge Status Section */}
          <div className="bridge-status">
            <h3>Bridge Status</h3>
            <pre>{bridgeStatus}</pre>
          </div>
        </>
      )}
    </div>
  );
};

export default BridgeTestContainer; 