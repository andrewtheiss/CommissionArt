import React, { useState, useEffect } from 'react';
import { ethers } from 'ethers';
import { useBlockchain } from '../../utils/BlockchainContext';
import abiLoader from '../../utils/abiLoader';
import './NFTOwnershipQuery.css';

// NFT query form state
interface NFTQuery {
  contractAddress: string;
  tokenId: string;
  ethValue: string;
  isSubmitting: boolean;
  transactionHash: string;
  result: string;
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
  };
  abiFiles: {
    l1: string;
    l2: string;
  };
}

// Props for NFTOwnershipQuery component
interface NFTOwnershipQueryProps {
  layer: 'l1' | 'l2';
  environment: 'testnet' | 'mainnet';
  contractConfig: ContractConfig;
  setBridgeStatus: (status: string | ((prev: string) => string)) => void;
  isListening: boolean;
  setIsListening: (isListening: boolean) => void;
  setLayer: (layer: 'l1' | 'l2') => void;
}

const NFTOwnershipQuery: React.FC<NFTOwnershipQueryProps> = ({
  layer,
  environment,
  contractConfig,
  setBridgeStatus,
  isListening,
  setIsListening,
  setLayer
}) => {
  // Get blockchain context
  const { connectWallet, isConnected } = useBlockchain();
  
  // State for NFT query
  const [nftQuery, setNftQuery] = useState<NFTQuery>({
    contractAddress: environment === 'testnet' ? '0xED5AF388653567Af2F388E6224dC7C4b3241C544' : '',
    tokenId: environment === 'testnet' ? '1' : '',
    ethValue: '0.001', // Default ETH value for cross-chain messaging
    isSubmitting: false,
    transactionHash: '',
    result: ''
  });

  // Update NFT contract address when environment changes
  useEffect(() => {
    if (environment === 'testnet') {
      setNftQuery(prev => ({
        ...prev,
        contractAddress: '0xED5AF388653567Af2F388E6224dC7C4b3241C544',
        tokenId: prev.tokenId || '1'
      }));
    }
  }, [environment]);
  
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
      // Use own RPC providers to avoid CORS issues with MetaMask's provider
      let provider;
      try {
        // Try to use MetaMask's provider first
        provider = new ethers.BrowserProvider(window.ethereum);
        // Test the connection
        await provider.getBlockNumber();
        setBridgeStatus(prev => `${prev}\nUsing MetaMask provider for event listening`);
      } catch (error) {
        // If MetaMask provider fails, use a public RPC endpoint
        console.log("MetaMask provider failed, trying public RPC endpoints");
        const rpcUrl = environment === 'testnet' 
          ? "https://arb-sepolia.g.alchemy.com/v2/demo" 
          : "https://arb1.arbitrum.io/rpc";
        
        provider = new ethers.JsonRpcProvider(rpcUrl);
        setBridgeStatus(prev => `${prev}\nFallback: Using public RPC for event listening: ${rpcUrl}`);
      }
      
      // Load the L2Relay ABI
      const l2RelayABI = abiLoader.loadABI('L2Relay');
      if (!l2RelayABI) {
        setBridgeStatus('Error: Could not load L2Relay ABI');
        return;
      }
      
      // Create contract instance
      const contract = new ethers.Contract(l2Address, l2RelayABI, provider);
      
      // Clear previous listeners
      try {
        contract.removeAllListeners();
      } catch (error) {
        console.log("Failed to remove previous listeners, continuing anyway");
      }
      
      // Function to handle RequestSent events
      const handleRequestSent = (
        nftContract: string,
        tokenId: ethers.BigNumberish,
        uniqueId: ethers.BigNumberish,
        event: ethers.EventLog | ethers.Log
      ) => {
        console.log("RequestSent event received:", { 
          nftContract, 
          tokenId: tokenId.toString(), 
          uniqueId: uniqueId.toString() 
        });
        setBridgeStatus(prev => 
          `${prev}\n\nNFT Query Request Sent!\nContract: ${nftContract}\nToken ID: ${tokenId}\nRequest ID: ${uniqueId}`
        );
      };
      
      // Function to handle OwnerReceived events
      const handleOwnerReceived = (
        owner: string,
        event: ethers.EventLog | ethers.Log
      ) => {
        console.log("OwnerReceived event received:", { owner });
        setBridgeStatus(prev => 
          `${prev}\n\nOwner Received from L1!\nNFT Owner: ${owner}`
        );
        
        // Update the query result
        setNftQuery(prev => ({
          ...prev,
          isSubmitting: false,
          result: `NFT owner: ${owner}`
        }));
      };
      
      // Listen for RequestSent events
      contract.on("RequestSent", handleRequestSent);
      
      // Listen for OwnerReceived events
      contract.on("OwnerReceived", handleOwnerReceived);
      
      // Also set up polling for OwnerReceived events as a fallback
      if (environment === 'testnet') {
        setBridgeStatus(prev => `${prev}\n\nSetting up fallback polling for events (every 15 seconds)`);
        
        // Get current block number
        const currentBlock = await provider.getBlockNumber();
        console.log("Current block number:", currentBlock);
        
        // Set up polling interval
        const pollInterval = setInterval(async () => {
          try {
            // Query for OwnerReceived events
            const filter = contract.filters.OwnerReceived();
            const events = await contract.queryFilter(filter, currentBlock);
            
            if (events.length > 0) {
              console.log("Found OwnerReceived events via polling:", events);
              // Process the most recent event
              const latestEvent = events[events.length - 1];
              if (latestEvent && 'args' in latestEvent && latestEvent.args) {
                // Type assertion to handle the EventLog interface
                const eventLog = latestEvent as ethers.EventLog;
                const owner = eventLog.args[0] as string;
                handleOwnerReceived(owner, eventLog);
                
                // Clear the interval once we've found an event
                clearInterval(pollInterval);
              }
            }
          } catch (error) {
            console.error("Error polling for events:", error);
          }
        }, 15000); // Poll every 15 seconds
        
        // Clean up interval after 10 minutes (max wait time)
        setTimeout(() => {
          clearInterval(pollInterval);
          console.log("Cleared polling interval after timeout");
        }, 10 * 60 * 1000);
      }
      
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
    
    // Ensure we're on L2 - auto switch if needed
    if (layer !== 'l2') {
      setBridgeStatus('Automatically switching to L2 (Arbitrum) to query NFT ownership...');
      // This will trigger the parent component to switch to L2
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
      
      // Validate ETH value
      let ethValueWei;
      try {
        // Convert ETH value to wei
        ethValueWei = ethers.parseEther(nftQuery.ethValue || '0');
        if (ethValueWei <= 0n) {
          setBridgeStatus('Error: ETH value must be greater than 0');
          setNftQuery(prev => ({ ...prev, isSubmitting: false }));
          return;
        }
      } catch (error) {
        setBridgeStatus('Error: Invalid ETH value format');
        setNftQuery(prev => ({ ...prev, isSubmitting: false }));
        return;
      }
      
      // Call requestNFTOwner
      setBridgeStatus(`Submitting query for NFT contract ${nftQuery.contractAddress} with token ID ${tokenId}...`);
      setBridgeStatus(prev => `${prev}\nSending ${nftQuery.ethValue} ETH to pay for cross-chain message fees`);
      
      // Convert token ID to BigInt for safer handling of large numbers
      const tokenIdBigInt = BigInt(tokenId);
      
      // Call with value
      const tx = await contract.requestNFTOwner(
        nftQuery.contractAddress, 
        tokenIdBigInt,
        { value: ethValueWei }
      );
      
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

  return (
    <div className="nft-query-section">
      <h3>Query NFT Ownership from L2 (Arbitrum)</h3>
      {environment === 'testnet' && (
        <div className="info-message">
          Using default Sepolia NFT contract: <code>0xED5AF388653567Af2F388E6224dC7C4b3241C544</code>
        </div>
      )}
      
      <div className="notice-message">
        <p><strong>Cross-Chain Process:</strong> Querying NFT ownership requires sending a message from Arbitrum (L2) to Ethereum (L1) and back.</p>
        <p>This process can take 10-15 minutes to complete. The status will update automatically when the response is received.</p>
        <p>If you experience connection issues or RPC errors, the app will try alternative endpoints automatically.</p>
      </div>
      
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
        
        <div className="input-group">
          <label>ETH Value (for cross-chain fees):</label>
          <input 
            type="text" 
            value={nftQuery.ethValue} 
            onChange={(e) => handleNftQueryChange('ethValue', e.target.value)}
            placeholder="0.001"
            disabled={nftQuery.isSubmitting}
          />
          <div className="field-help">
            ETH is required to pay for the cross-chain message fees. Recommended minimum: 0.005 ETH
          </div>
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
            disabled={!nftQuery.contractAddress || !nftQuery.tokenId || !nftQuery.ethValue || nftQuery.isSubmitting}
          >
            {nftQuery.isSubmitting ? 'Processing...' : 'Query NFT Owner'}
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
          <p>
            <strong>Retryable Status:</strong>{' '}
            <a 
              href={`https://retryable-dashboard.arbitrum.io/tx/${nftQuery.transactionHash}`} 
              target="_blank" 
              rel="noopener noreferrer"
            >
              Check Status
            </a>
            <span className="field-help">
              Track cross-chain message progress through the Arbitrum bridge
            </span>
          </p>
        </div>
      )}
      
      {nftQuery.result && (
        <div className="query-result">
          <h4>Query Result</h4>
          <div className="result-container">
            <p>{nftQuery.result}</p>
            <button 
              className="copy-button" 
              onClick={() => {
                // Extract just the address from the result (format is "NFT owner: 0x...")
                const addressMatch = nftQuery.result.match(/0x[a-fA-F0-9]{40}/);
                if (addressMatch) {
                  navigator.clipboard.writeText(addressMatch[0])
                    .then(() => {
                      // Visual feedback that copy succeeded
                      const btn = document.querySelector('.copy-button') as HTMLButtonElement;
                      if (btn) {
                        const originalText = btn.textContent;
                        btn.textContent = 'Copied!';
                        setTimeout(() => {
                          btn.textContent = originalText;
                        }, 2000);
                      }
                    })
                    .catch(err => console.error('Failed to copy text: ', err));
                }
              }}
            >
              Copy Address
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default NFTOwnershipQuery; 