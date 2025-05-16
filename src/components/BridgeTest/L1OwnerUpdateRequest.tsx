import React, { useState, useEffect, useRef } from 'react';
import { ethers } from 'ethers';
import { useBlockchain } from '../../utils/BlockchainContext';
import './BridgeTest.css';
import l1QueryOwnerABI from '../../assets/abis/L1QueryOwnership.json';
import { NodeInterface__factory } from '@arbitrum/sdk/dist/lib/abi/factories/NodeInterface__factory';
import { NODE_INTERFACE_ADDRESS } from '@arbitrum/sdk/dist/lib/dataEntities/constants';
import useContractConfig from '../../utils/useContractConfig';
import abiLoader from '../../utils/abiLoader';
import { estimateL1ToL2Gas } from '../../utils/gasEstimator';

// Using the ethers LogDescription type
type ParsedLog = ethers.LogDescription;

// Alias addition constant
const ALIAS_ADDITION = "0x1111000000000000000000000000000000001111";

// Extend Window interface
declare global {
  interface Window {
    ethereum?: any;
  }
}

// Props interface for L1OwnerUpdateRequest
interface L1OwnerUpdateRequestProps {
  environment: 'testnet' | 'mainnet';
  contractConfig: {
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
  };
  setBridgeStatus: (status: string | ((prev: string) => string)) => void;
}

const L1OwnerUpdateRequest: React.FC<L1OwnerUpdateRequestProps> = ({ 
  environment, 
  contractConfig, 
  setBridgeStatus 
}) => {
  const { 
    isConnected, 
    networkType, 
    switchNetwork, 
    connectWallet, 
    walletAddress,
    switchToLayer
  } = useBlockchain();
  const { getContract, loading: configLoading } = useContractConfig();
  const [aliasedAddress, setAliasedAddress] = useState<string>("");
  const [configError, setConfigError] = useState<Error | null>(null);
  const [contractAddress, setContractAddress] = useState<string>("");

  // Form state
  const [formNftContract, setFormNftContract] = useState<string>("");
  const [formTokenId, setFormTokenId] = useState<string>("");
  const [formGasAmount, setFormGasAmount] = useState<string>("0.01");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [events, setEvents] = useState<Array<ethers.LogDescription | ethers.Log>>([]);
  const [isListening, setIsListening] = useState<boolean>(false);
  const [isEstimatingGas, setIsEstimatingGas] = useState<boolean>(false);
  const [gasEstimates, setGasEstimates] = useState<{
    maxSubmissionCost: string;
    gasLimit: string;
    maxFeePerGas: string;
  } | null>(null);
  
  // Refs for input elements
  const nftContractRef = useRef<HTMLInputElement>(null);
  const tokenIdRef = useRef<HTMLInputElement>(null);
  const l2ReceiverRef = useRef<HTMLInputElement>(null);
  const ethValueRef = useRef<HTMLInputElement>(null);
  const contractAddressRef = useRef<HTMLInputElement>(null);

  const networkMatch = networkType === (environment === 'testnet' ? 'dev' : 'prod');

  useEffect(() => {
    const loadData = async () => {
      // Reset error state at the beginning
      setConfigError(null);

      // Check for correct network
      if (!networkMatch) {
        setBridgeStatus(`Please switch to ${environment === 'testnet' ? 'Sepolia' : 'Ethereum Mainnet'} to use this feature`);
        // Clear address if network doesn't match
        if (contractAddress !== "") {
          setContractAddress("");
        }
        return;
      }

      try {
        // Get the L1 contract from configuration
        const l1Contract = getContract(environment, 'l1');
        const newAddress = l1Contract?.address;

        if (!newAddress) {
          throw new Error('L1 contract address not found in configuration');
        }

        // Only update state if the address has actually changed
        if (newAddress !== contractAddress) {
          setContractAddress(newAddress);
          setBridgeStatus(`Using L1QueryOwnership at ${newAddress}`);
        }
      } catch (error) {
        const newError = error instanceof Error ? error : new Error('Unknown error');
        console.error('Error loading contract data:', newError);
        // Only update state if the error message is different
        if (newError.message !== configError?.message) {
           setConfigError(newError);
        }
      }
    };

    loadData();
  // Ensure all dependencies used in the effect are listed.
  // Note: `getContract` stability is crucial. If it changes reference on every render, this effect will still loop.
  // Consider wrapping `getContract` with `useCallback` in `useContractConfig` if the loop persists.
  }, [environment, getContract, networkMatch, setBridgeStatus, contractAddress, configError, setConfigError, setContractAddress]);

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

  // Update aliased address when the contract address changes
  useEffect(() => {
    const updateAliasedAddress = () => {
      const currentAddress = contractAddressRef.current?.value || contractAddress;
      if (currentAddress && ethers.isAddress(currentAddress)) {
        const aliased = computeAliasedAddress(currentAddress);
        // Only update if different
        if (aliased !== aliasedAddress) {
          setAliasedAddress(aliased);
        }
      }
    };

    updateAliasedAddress();
    
    // Set up event listener for input changes
    const contractAddressInput = contractAddressRef.current;
    if (contractAddressInput) {
      contractAddressInput.addEventListener('input', updateAliasedAddress);
      return () => {
        contractAddressInput.removeEventListener('input', updateAliasedAddress);
      };
    }
  // Add aliasedAddress and setAliasedAddress to dependencies
  }, [contractAddress, aliasedAddress, setAliasedAddress]);

  // Initialize contract (assuming the wallet is connected and on Sepolia network)
  const initializeContract = async () => {
    if (!isConnected) {
      setBridgeStatus('Please connect your wallet');
      return null;
    }

    // Check network based on environment
    const targetNetwork = environment === 'testnet' ? 'dev' : 'prod';
    if (networkType !== targetNetwork) {
      setBridgeStatus(`Please switch to ${environment === 'testnet' ? 'Sepolia' : 'Ethereum Mainnet'} network`);
      return null;
    }

    try {
      // Use the window.ethereum directly to get a signer
      if (!window.ethereum) {
        setBridgeStatus('MetaMask or another web3 wallet is required');
        return null;
      }
      
      const provider = new ethers.BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();
      
      if (!signer) {
        setBridgeStatus('No signer available');
        return null;
      }

      // Use the state variable contractAddress
      const currentContractAddress = contractAddressRef.current?.value || contractAddress;
      if (!currentContractAddress || !ethers.isAddress(currentContractAddress)) {
        setBridgeStatus('Please enter or load a valid L1 contract address');
        return null;
      }

      // Use the ABI name from the config
      const abiName = contractConfig.abiFiles.l1;
      const abi = abiLoader.loadABI(abiName);
      if (!abi) {
        setBridgeStatus(`Failed to load ABI: ${abiName}`);
        return null;
      }

      return new ethers.Contract(currentContractAddress, abi, signer);
    } catch (error: any) {
      setBridgeStatus(`Error initializing contract: ${error.message}`);
      console.error('Contract initialization error:', error);
      return null;
    }
  };

  // Function to estimate gas parameters
  const estimateGasParameters = async () => {
    try {
      if (!isConnected) {
        setBridgeStatus('Please connect your wallet to estimate gas');
        return;
      }

      // Check network based on environment
      const targetNetwork = environment === 'testnet' ? 'dev' : 'prod';
      if (networkType !== targetNetwork) {
        setBridgeStatus(`Please switch to ${environment === 'testnet' ? 'Sepolia' : 'Ethereum Mainnet'} network`);
        return;
      }

      setIsEstimatingGas(true);
      setBridgeStatus('Estimating gas parameters...');

      // Get input values from refs
      const nftContract = nftContractRef.current?.value || '0xED5AF388653567Af2F388E6224dC7C4b3241C544';
      const tokenId = tokenIdRef.current?.value || '0';
      const l2Receiver = l2ReceiverRef.current?.value || contractConfig.addresses.l2[environment];
      
      // Use the window.ethereum directly to get a provider
      if (!window.ethereum) {
        setBridgeStatus('MetaMask or another web3 wallet is required');
        return;
      }
      
      const provider = new ethers.BrowserProvider(window.ethereum);
      const currentContractAddress = contractAddressRef.current?.value || contractAddress;

      // Call the gas estimator
      const estimates = await estimateL1ToL2Gas(
        provider,
        currentContractAddress,
        nftContract,
        tokenId,
        l2Receiver
      );

      // Update state with string versions of the bigint values
      setGasEstimates({
        maxSubmissionCost: estimates.maxSubmissionCost.toString(),
        gasLimit: estimates.gasLimit.toString(),
        maxFeePerGas: estimates.maxFeePerGas.toString()
      });

      setBridgeStatus('Gas estimation completed successfully');
    } catch (error: any) {
      setBridgeStatus(`Gas estimation error: ${error.message}`);
      console.error('Gas estimation error:', error);
    } finally {
      setIsEstimatingGas(false);
    }
  };

  // Use estimated gas values if available
  const callQueryNFTAndSendBackWithEstimatedGas = async () => {
    try {
      setBridgeStatus('Checking network...');
      
      const contract = await initializeContract();
      if (!contract) return;

      const nftContract = nftContractRef.current?.value || '0xED5AF388653567Af2F388E6224dC7C4b3241C544';
      const tokenId = tokenIdRef.current?.value || '0';
      const l2Receiver = l2ReceiverRef.current?.value || contractConfig.addresses.l2[environment];
      const ethValue = ethValueRef.current?.value || '0.001';
      const ethValueWei = ethers.parseEther(ethValue);

      if (!l2Receiver || !ethers.isAddress(l2Receiver)) {
        setBridgeStatus('Invalid or missing L2 receiver address from config');
        return;
      }

      // Use estimated gas values if available, otherwise use defaults
      const maxSubmissionCost = gasEstimates 
        ? BigInt(gasEstimates.maxSubmissionCost)
        : BigInt('4500000000000');
      
      const gasLimit = gasEstimates
        ? BigInt(gasEstimates.gasLimit)
        : BigInt('1000000');
      
      const maxFeePerGas = gasEstimates
        ? BigInt(gasEstimates.maxFeePerGas)
        : BigInt('100000000');

      setBridgeStatus('Sending transaction with estimated gas values...');
      setIsSubmitting(true);

      const tx = await contract.queryNFTAndSendBack(
        nftContract,
        BigInt(tokenId),
        l2Receiver,
        maxSubmissionCost,
        gasLimit,
        maxFeePerGas,
        { value: ethValueWei }
      );

      setBridgeStatus('Transaction sent, awaiting confirmation...');
      const receipt = await tx.wait();

      // Parse logs for OwnerQueried event
      const ownerQueriedEvents: ParsedLog[] = [];
      if (receipt?.logs) {
        for (const log of receipt.logs) {
          try {
            if (log.topics && log.data) {
               const parsedLog = contract.interface.parseLog(log as any);
               if (parsedLog && parsedLog.name === 'OwnerQueried') {
                  ownerQueriedEvents.push(parsedLog);
               }
            }
          } catch (error) {
            console.warn('Could not parse log:', log, error);
          }
        }
      }

      if (ownerQueriedEvents.length > 0) {
        const event = ownerQueriedEvents[0];
        const ticketId = event.args[3];
        setBridgeStatus(`Transaction confirmed! Ticket ID: ${ticketId?.toString()}`);
      } else {
        setBridgeStatus('Transaction confirmed, but no OwnerQueried event found.');
      }
    } catch (error: any) {
      setBridgeStatus(`Error: ${error.message}`);
      console.error(error);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Function to call queryNFTAndSendBack with hardcoded gas values
  const callQueryNFTAndSendBack = async () => {
    try {
      setBridgeStatus('Checking network...');
      
      // Check network and initialize
      const contract = await initializeContract();
      if (!contract) return; // initializeContract handles error messages

      // Get input values from refs
      const nftContract = nftContractRef.current?.value || '0xED5AF388653567Af2F388E6224dC7C4b3241C544';
      const tokenId = tokenIdRef.current?.value || '0';
      const l2Receiver = l2ReceiverRef.current?.value || contractConfig.addresses.l2[environment]; // Use correct env
      const ethValue = ethValueRef.current?.value || '0.001';

      // Input validation
      if (!ethers.isAddress(nftContract)) {
        setBridgeStatus('Invalid NFT contract address');
        return;
      }

      if (!l2Receiver || !ethers.isAddress(l2Receiver)) {
        setBridgeStatus('Invalid or missing L2 receiver address from config');
        return;
      }

      // Convert ETH value to wei
      const ethValueWei = ethers.parseEther(ethValue);

      // Define gas parameters as BigInt
      const maxSubmissionCost = BigInt('4500000000000');
      const gasLimit = BigInt('1000000');
      const maxFeePerGas = BigInt('100000000');

      setBridgeStatus('Sending transaction...');
      setIsSubmitting(true); // Disable button

      const tx = await contract.queryNFTAndSendBack(
        nftContract,
        BigInt(tokenId), // Ensure tokenId is BigInt
        l2Receiver,
        maxSubmissionCost,
        gasLimit,
        maxFeePerGas,
        { value: ethValueWei }
      );

      setBridgeStatus('Transaction sent, awaiting confirmation...');
      const receipt = await tx.wait();

      // Parse logs for OwnerQueried event
      const ownerQueriedEvents: ParsedLog[] = [];
      if (receipt?.logs) {
        for (const log of receipt.logs) {
          try {
            // Check if log has topic and data for parsing
            if (log.topics && log.data) {
               const parsedLog = contract.interface.parseLog(log as any); // Use 'as any' to bypass strict type checking if necessary
               if (parsedLog && parsedLog.name === 'OwnerQueried') {
                  ownerQueriedEvents.push(parsedLog);
               }
            }
          } catch (error) {
            // Skip logs that can't be parsed
            console.warn('Could not parse log:', log, error);
          }
        }
      } else {
         console.warn('No logs found in transaction receipt');
      }

      if (ownerQueriedEvents.length > 0) {
        const event = ownerQueriedEvents[0];
        // Adjust index based on ABI definition (check if indexed)
        const ticketId = event.args[3]; // Assuming ticketId is the 4th argument (index 3)
        setBridgeStatus(`Transaction confirmed! Ticket ID: ${ticketId?.toString()}`);
      } else {
        setBridgeStatus('Transaction confirmed, but no OwnerQueried event found. Check ABI or contract logic.');
      }
    } catch (error: any) {
      setBridgeStatus(`Error: ${error.message}`);
      console.error(error);
    } finally {
      setIsSubmitting(false); // Re-enable button
    }
  };

  // Function with optimized gas estimation
  const callQueryNFTAndSendBackOptimized = async () => {
    try {
      setBridgeStatus('Estimating optimal gas values... (Currently using hardcoded values)');
      
      // Placeholder for actual gas estimation logic
      const gasEstimation = {
        maxSubmissionCost: '4500000000000',
        gasLimit: '1000000',
        maxFeePerGas: '100000000'
      };
      
      const contract = await initializeContract();
      if (!contract) return;

      const nftContract = nftContractRef.current?.value || '0xED5AF388653567Af2F388E6224dC7C4b3241C544';
      const tokenId = tokenIdRef.current?.value || '0';
      const l2Receiver = l2ReceiverRef.current?.value || contractConfig.addresses.l2[environment];
      const ethValue = ethValueRef.current?.value || '0.001';
      const ethValueWei = ethers.parseEther(ethValue);

      if (!l2Receiver || !ethers.isAddress(l2Receiver)) {
        setBridgeStatus('Invalid or missing L2 receiver address from config');
        return;
      }

      setBridgeStatus('Sending optimized transaction...');
      setIsSubmitting(true);

      const tx = await contract.queryNFTAndSendBack(
        nftContract,
        BigInt(tokenId),
        l2Receiver,
        BigInt(gasEstimation.maxSubmissionCost),
        BigInt(gasEstimation.gasLimit),
        BigInt(gasEstimation.maxFeePerGas),
        { value: ethValueWei }
      );

      setBridgeStatus('Optimized transaction sent, awaiting confirmation...');
      const receipt = await tx.wait();
      setBridgeStatus(`Optimized transaction confirmed: ${receipt?.transactionHash || 'N/A'}`);
    } catch (error: any) {
      setBridgeStatus(`Error: ${error.message}`);
      console.error(error);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Function to execute a transaction with retry logic that increases gas by 10x on failure
  const callQueryNFTWithRetry = async () => {
    try {
      const contract = await initializeContract();
      if (!contract) return;
      
      const nftContract = nftContractRef.current?.value || '0xED5AF388653567Af2F388E6224dC7C4b3241C544';
      const tokenId = tokenIdRef.current?.value || '0';
      const l2Receiver = l2ReceiverRef.current?.value || contractConfig.addresses.l2[environment];
      const ethValue = ethValueRef.current?.value || '0.001';
      const ethValueWei = ethers.parseEther(ethValue);

      if (!l2Receiver || !ethers.isAddress(l2Receiver)) {
        setBridgeStatus('Invalid or missing L2 receiver address from config');
        return;
      }
      
      // Initial gas values
      let maxSubmissionCost = BigInt('4500000000000');
      let gasLimit = BigInt('1000000');
      let maxFeePerGas = BigInt('100000000');
      
      setBridgeStatus('Sending transaction (with retry logic)...');
      setIsSubmitting(true);
      
      try {
        const tx = await contract.queryNFTAndSendBack(
          nftContract,
          BigInt(tokenId), // Ensure tokenId is BigInt
          l2Receiver,
          maxSubmissionCost,
          gasLimit,
          maxFeePerGas,
          { value: ethValueWei }
        );
        
        setBridgeStatus('Transaction sent, awaiting confirmation...');
        const receipt = await tx.wait();
        setBridgeStatus(`Transaction confirmed: ${receipt?.transactionHash || 'N/A'}`);
        
      } catch (txError: any) {
        setBridgeStatus(`Transaction failed: ${txError.message}. Retrying with 10x maxSubmissionCost...`);
        
        // Increase only maxSubmissionCost by 10x
        maxSubmissionCost = maxSubmissionCost * 10n;
        
        // Retry with increased maxSubmissionCost
        const retryTx = await contract.queryNFTAndSendBack(
          nftContract,
          BigInt(tokenId),
          l2Receiver,
          maxSubmissionCost,
          gasLimit,
          maxFeePerGas,
          { value: ethValueWei }
        );
        
        setBridgeStatus('Retry transaction sent, awaiting confirmation...');
        const retryReceipt = await retryTx.wait();
        setBridgeStatus(`Retry transaction confirmed: ${retryReceipt?.transactionHash || 'N/A'}`);
      }
      
    } catch (error: any) {
      setBridgeStatus(`Error during retry logic: ${error.message}`);
      console.error(error);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle wallet connection
  const handleConnectWallet = async () => {
    try {
      setBridgeStatus('Connecting wallet...');
      await connectWallet();
      setBridgeStatus('Wallet connected');
    } catch (error: any) {
      setBridgeStatus(`Wallet connection error: ${error.message}`);
    }
  };

  // Show loading or error message if config isn't ready
  if (configLoading) {
    return <div className="bridge-test-container">Loading contract configuration...</div>;
  }

  // Don't render the main content if config error exists, show error message instead
  if (configError) {
    return (
      <div className="contract-interaction-container">
        <div className="card">
          <div className="card-content error-message">
            <h3>Configuration Error</h3>
            <p>{configError.message}</p>
            <p>Please check the L1 contract address configuration for the {environment} environment.</p>
          </div>
        </div>
      </div>
    );
  }

  // Don't render if network doesn't match, useEffect handles the status message
  if (!networkMatch) {
     return (
        <div className="contract-interaction-container">
          <div className="card">
            <div className="card-content network-mismatch">
              <h3>Network Mismatch</h3>
              <p>Please switch to {environment === 'testnet' ? 'Sepolia' : 'Ethereum Mainnet'} to use this feature.</p>
               <button 
                  onClick={() => switchToLayer('l1', environment)}
                  className="primary-button"
               >
                  Switch to {environment === 'testnet' ? 'Sepolia' : 'Ethereum Mainnet'}
               </button>
            </div>
          </div>
        </div>
     );
  }

  return (
    <div className="contract-interaction-container">
      <div className="card">
        <div className="card-content">
          {/* Title is now handled in the parent index.tsx */}
          
          <div className="explorer-links">
            {environment === 'testnet' && contractAddress && (
              <a 
                href={`https://sepolia.etherscan.io/address/${contractAddress}`} 
                target="_blank" 
                rel="noopener noreferrer"
                className="explorer-link"
              >
                View Contract on Sepolia
              </a>
            )}
            {environment === 'mainnet' && contractAddress && (
              <a 
                href={`https://etherscan.io/address/${contractAddress}`} 
                target="_blank" 
                rel="noopener noreferrer"
                className="explorer-link"
              >
                View Contract on Mainnet
              </a>
            )}
          </div>
          
          {/* Display info about current contract address */}
          <div className="info-section">
            <div className="info-item">
              <span className="info-label">L1 Contract Address:</span>
              <span className="info-value">{contractAddress || "Loading..."}</span>
            </div>
          </div>
          
          {!isConnected ? (
            <div className="connect-wallet-container">
              <p>Please connect your wallet to interact with the L1 contract.</p>
              <button 
                onClick={handleConnectWallet}
                className="primary-button"
                disabled={isSubmitting} // Disable if submitting
              >
                Connect Wallet
              </button>
            </div>
          ) : (
            <>
              <div className="wallet-info small-text">
                <p className="wallet-address">
                  Connected: {walletAddress?.slice(0, 6)}...{walletAddress?.slice(-4)}
                </p>
                <p className="network-info">
                  Network: {networkType} (Expected: {environment === 'testnet' ? 'dev' : 'prod'})
                </p>
              </div>
              
              {/* Removed contract address display from here, moved above */}
              
              <div className="form-container">
                {/* Removed contract address input, it's loaded from config */}
                {aliasedAddress && (
                  <div className="info-section small-text">
                    <div className="info-item">
                       <span className="info-label">L2 Aliased Address:</span>
                       <span className="info-value">{aliasedAddress}</span>
                    </div>
                  </div>
                )}
                
                <div className="form-group">
                  <label htmlFor="nftContract">NFT Contract Address:</label>
                  <input
                    type="text"
                    id="nftContract"
                    ref={nftContractRef}
                    defaultValue="0xED5AF388653567Af2F388E6224dC7C4b3241C544" // Example Address
                    placeholder="0x..."
                    disabled={isSubmitting}
                  />
                </div>
                
                <div className="form-group">
                  <label htmlFor="tokenId">Token ID:</label>
                  <input
                    type="text"
                    id="tokenId"
                    ref={tokenIdRef}
                    defaultValue="0"
                    placeholder="0"
                    disabled={isSubmitting}
                  />
                </div>
                
                <div className="form-group">
                  <label htmlFor="l2Receiver">L2 Receiver Address:</label>
                  <input
                    type="text"
                    id="l2Receiver"
                    ref={l2ReceiverRef}
                    defaultValue={contractConfig.addresses.l2[environment] || ''} // Default from config
                    placeholder="0x... (L2 Relay Address)"
                    disabled={isSubmitting}
                  />
                  <small>Address on L2 (e.g., L2RelayOwnership) to receive the owner info.</small>
                </div>
                
                <div className="form-group">
                  <label htmlFor="ethValue">ETH Value (for L2 Gas):</label>
                  <input
                    type="text"
                    id="ethValue"
                    ref={ethValueRef}
                    defaultValue="0.001"
                    placeholder="e.g., 0.001"
                    disabled={isSubmitting}
                  />
                  <small>Covers Arbitrum retryable ticket fees.</small>
                </div>
                
                {gasEstimates && (
                  <div className="gas-estimates-container">
                    <h4>Estimated Gas Parameters</h4>
                    <div className="info-section small-text">
                      <div className="info-item">
                        <span className="info-label">Max Submission Cost:</span>
                        <span className="info-value">{gasEstimates.maxSubmissionCost}</span>
                      </div>
                      <div className="info-item">
                        <span className="info-label">Gas Limit:</span>
                        <span className="info-value">{gasEstimates.gasLimit}</span>
                      </div>
                      <div className="info-item">
                        <span className="info-label">Max Fee Per Gas:</span>
                        <span className="info-value">{gasEstimates.maxFeePerGas}</span>
                      </div>
                    </div>
                  </div>
                )}
                
                <div className="button-group">
                  <button 
                    onClick={estimateGasParameters} 
                    className="secondary-button" 
                    disabled={isEstimatingGas || isSubmitting}
                  >
                    {isEstimatingGas ? 'Estimating...' : 'Estimate Gas'}
                  </button>
                  
                  <button 
                    onClick={callQueryNFTAndSendBackWithEstimatedGas} 
                    className="primary-button" 
                    disabled={isSubmitting || isEstimatingGas}
                  >
                    {isSubmitting ? 'Sending...' : 'Send with Estimated Gas'}
                  </button>
                  
                  <button onClick={callQueryNFTAndSendBack} className="secondary-button" disabled={isSubmitting || isEstimatingGas}>
                    {isSubmitting ? 'Sending...' : 'Send Request (Safe Gas)'}
                  </button>
                  
                  <button onClick={callQueryNFTAndSendBackOptimized} className="secondary-button" disabled={isSubmitting || isEstimatingGas}>
                    {isSubmitting ? 'Sending...' : 'Send Request (Optimized Gas)'}
                  </button>
                  
                  <button onClick={callQueryNFTWithRetry} className="secondary-button" disabled={isSubmitting || isEstimatingGas}>
                    {isSubmitting ? 'Sending...' : 'Send with Retry (10x Gas)'}
                  </button>
                </div>
              </div>
            </> // End of isConnected fragment
          )}
        </div> 
      </div> 
    </div> 
  );
};

export default L1OwnerUpdateRequest; 