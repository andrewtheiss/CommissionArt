import React, { useState, useEffect } from 'react';
import { ethers } from 'ethers';
import { useBlockchain } from '../utils/BlockchainContext';
import contractConfigJson from '../assets/contract_config.json';

// ABI for the L2Relay contract functions we need
const L2RelayABI = [
  "function receiveNFTOwnerFromCrossChainMessage(uint256 _chain_id, address _nft_contract, uint256 _token_id, address _owner)",
  "function relayToL3(uint256 _chain_id, address _nft_contract, uint256 _token_id, address _owner) payable"
];

// Get contract addresses from configuration
const CONTRACT_ADDRESSES = {
  mainnet: {
    l2Relay: contractConfigJson.networks.mainnet.l2.address
  },
  testnet: {
    l2Relay: contractConfigJson.networks.testnet.l2.address
  }
};

// Default placeholder values for testing
const DEFAULT_NFT_CONTRACT = "0xed5af388653567af2f388e6224dc7c4b3241c544";
const DEFAULT_NFT_ID = "1337";
const DEFAULT_OWNER_ADDRESS = "0xB9d4DA3aee7C5987C3B841F37808f00A2fc3866f";

type NetworkType = 'mainnet' | 'testnet';

const L2RelayTester: React.FC = () => {
  const { isConnected, walletAddress, connectWallet } = useBlockchain();
  
  // Network selection
  const [network, setNetwork] = useState<NetworkType>('testnet');
  
  // Default values for testing
  const [chainId, setChainId] = useState<string>("1"); // Default to Ethereum mainnet
  const [nftContract, setNftContract] = useState<string>(DEFAULT_NFT_CONTRACT);
  const [tokenId, setTokenId] = useState<string>(DEFAULT_NFT_ID);
  const [ownerAddress, setOwnerAddress] = useState<string>(DEFAULT_OWNER_ADDRESS);
  const [relayContractAddress, setRelayContractAddress] = useState<string>(CONTRACT_ADDRESSES.testnet.l2Relay);
  const [txStatus, setTxStatus] = useState<string>("");
  const [txHash, setTxHash] = useState<string>("");
  const [ethValue, setEthValue] = useState<string>("0.01"); // Default ETH value for relayToL3
  const [activeTab, setActiveTab] = useState<'receive' | 'relay'>('receive');

  // Update owner address when wallet connects
  useEffect(() => {
    if (walletAddress) {
      setOwnerAddress(walletAddress);
    }
  }, [walletAddress]);

  // Update relay contract address when network changes
  useEffect(() => {
    setRelayContractAddress(CONTRACT_ADDRESSES[network].l2Relay);
  }, [network]);

  const handleNetworkChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setNetwork(e.target.value as NetworkType);
  };

  const handleSendReceive = async () => {
    if (!isConnected) {
      setTxStatus("Please connect your wallet first");
      return;
    }

    try {
      setTxStatus("Preparing transaction...");
      
      // Get the provider and signer
      const provider = new ethers.BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();
      
      // Create contract instance
      const relayContract = new ethers.Contract(
        relayContractAddress,
        L2RelayABI,
        signer
      );

      // Convert inputs to appropriate types
      const chainIdBN = BigInt(chainId);
      const tokenIdBN = BigInt(tokenId);
      
      // Send transaction
      setTxStatus("Sending transaction...");
      const tx = await relayContract.receiveNFTOwnerFromCrossChainMessage(
        chainIdBN,
        nftContract,
        tokenIdBN,
        ownerAddress
      );

      setTxStatus("Transaction sent! Waiting for confirmation...");
      setTxHash(tx.hash);
      
      // Wait for transaction to be mined
      const receipt = await tx.wait();
      
      if (receipt.status === 1) {
        setTxStatus("Transaction confirmed successfully!");
      } else {
        setTxStatus("Transaction failed!");
      }
    } catch (error: any) {
      console.error("Error sending relay:", error);
      setTxStatus(`Error: ${error.message || "Unknown error"}`);
    }
  };

  const handleSendRelay = async () => {
    if (!isConnected) {
      setTxStatus("Please connect your wallet first");
      return;
    }

    try {
      setTxStatus("Preparing transaction...");
      
      // Get the provider and signer
      const provider = new ethers.BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();
      
      // Create contract instance
      const relayContract = new ethers.Contract(
        relayContractAddress,
        L2RelayABI,
        signer
      );

      // Convert inputs to appropriate types
      const chainIdBN = BigInt(chainId);
      const tokenIdBN = BigInt(tokenId);
      const ethValueWei = ethers.parseEther(ethValue);
      
      // Send transaction with ETH value
      setTxStatus("Sending transaction...");
      const tx = await relayContract.relayToL3(
        chainIdBN,
        nftContract,
        tokenIdBN,
        ownerAddress,
        { value: ethValueWei }
      );

      setTxStatus("Transaction sent! Waiting for confirmation...");
      setTxHash(tx.hash);
      
      // Wait for transaction to be mined
      const receipt = await tx.wait();
      
      if (receipt.status === 1) {
        setTxStatus("Transaction confirmed successfully!");
      } else {
        setTxStatus("Transaction failed!");
      }
    } catch (error: any) {
      console.error("Error sending relay:", error);
      setTxStatus(`Error: ${error.message || "Unknown error"}`);
    }
  };

  // Format transaction parameters for preview
  const formatTransactionPreview = () => {
    const method = activeTab === 'receive' ? 'receiveNFTOwnerFromCrossChainMessage' : 'relayToL3';
    
    return {
      contract: relayContractAddress,
      method: method,
      network: network,
      parameters: {
        chain_id: chainId,
        nft_contract: nftContract,
        token_id: tokenId,
        owner: ownerAddress,
        ...(activeTab === 'relay' ? { value: `${ethValue} ETH` } : {})
      }
    };
  };

  // Generate explorer URL based on network
  const getExplorerUrl = (hash: string) => {
    if (network === 'mainnet') {
      return `https://arbiscan.io/tx/${hash}`;
    } else {
      return `https://goerli.arbiscan.io/tx/${hash}`;
    }
  };

  return (
    <div className="relay-tester-container">
      <h2>L2 to L3 Relay Tester</h2>
      <p>Test the L2Relay contract by sending NFT ownership data to L3</p>
      
      <div className="network-toggle">
        <label className="radio-label">
          <input
            type="radio"
            name="network"
            value="testnet"
            checked={network === 'testnet'}
            onChange={handleNetworkChange}
          />
          Testnet
        </label>
        <label className="radio-label">
          <input
            type="radio"
            name="network"
            value="mainnet"
            checked={network === 'mainnet'}
            onChange={handleNetworkChange}
          />
          Mainnet
        </label>
      </div>
      
      <div className="tab-navigation">
        <button 
          className={`tab-button ${activeTab === 'receive' ? 'active' : ''}`}
          onClick={() => setActiveTab('receive')}
        >
          receiveNFTOwnerFromCrossChainMessage
        </button>
        <button 
          className={`tab-button ${activeTab === 'relay' ? 'active' : ''}`}
          onClick={() => setActiveTab('relay')}
        >
          relayToL3
        </button>
      </div>
      
      <div className="form-group">
        <label>L2Relay Contract Address:</label>
        <input 
          type="text" 
          value={relayContractAddress} 
          onChange={(e) => setRelayContractAddress(e.target.value)}
          placeholder="0x..."
        />
      </div>
      
      <div className="form-group">
        <label>Chain ID:</label>
        <input 
          type="text" 
          value={chainId} 
          onChange={(e) => setChainId(e.target.value)}
          placeholder="1"
        />
      </div>
      
      <div className="form-group">
        <label>NFT Contract Address:</label>
        <input 
          type="text" 
          value={nftContract} 
          onChange={(e) => setNftContract(e.target.value)}
          placeholder={DEFAULT_NFT_CONTRACT}
        />
      </div>
      
      <div className="form-group">
        <label>Token ID:</label>
        <input 
          type="text" 
          value={tokenId} 
          onChange={(e) => setTokenId(e.target.value)}
          placeholder={DEFAULT_NFT_ID}
        />
      </div>
      
      <div className="form-group">
        <label>Owner Address:</label>
        <input 
          type="text" 
          value={ownerAddress} 
          onChange={(e) => setOwnerAddress(e.target.value)}
          placeholder={DEFAULT_OWNER_ADDRESS}
        />
      </div>
      
      {activeTab === 'relay' && (
        <div className="form-group">
          <label>ETH Value (for gas fees):</label>
          <input 
            type="text" 
            value={ethValue} 
            onChange={(e) => setEthValue(e.target.value)}
            placeholder="0.01"
          />
          <small className="helper-text">Amount of ETH to send for L3 gas fees</small>
        </div>
      )}
      
      <div className="transaction-preview">
        <h3>Transaction Preview</h3>
        <div className="preview-content">
          <div className="preview-row">
            <span className="preview-label">Network:</span>
            <span className="preview-value">{network === 'mainnet' ? 'Mainnet' : 'Testnet'}</span>
          </div>
          <div className="preview-row">
            <span className="preview-label">Contract:</span>
            <span className="preview-value">{relayContractAddress}</span>
          </div>
          <div className="preview-row">
            <span className="preview-label">Method:</span>
            <span className="preview-value">{activeTab === 'receive' ? 'receiveNFTOwnerFromCrossChainMessage' : 'relayToL3'}</span>
          </div>
          <div className="preview-row">
            <span className="preview-label">Chain ID:</span>
            <span className="preview-value">{chainId}</span>
          </div>
          <div className="preview-row">
            <span className="preview-label">NFT Contract:</span>
            <span className="preview-value">{nftContract}</span>
          </div>
          <div className="preview-row">
            <span className="preview-label">Token ID:</span>
            <span className="preview-value">{tokenId}</span>
          </div>
          <div className="preview-row">
            <span className="preview-label">Owner:</span>
            <span className="preview-value">{ownerAddress}</span>
          </div>
          {activeTab === 'relay' && (
            <div className="preview-row">
              <span className="preview-label">Value:</span>
              <span className="preview-value">{ethValue} ETH</span>
            </div>
          )}
        </div>
      </div>
      
      <div className="action-container">
        {!isConnected ? (
          <button className="connect-button" onClick={connectWallet}>Connect Wallet</button>
        ) : (
          <button 
            className="create-button" 
            onClick={activeTab === 'receive' ? handleSendReceive : handleSendRelay}
          >
            {activeTab === 'receive' ? 'Send Receive Message' : 'Send Relay Message'}
          </button>
        )}
      </div>
      
      {txStatus && (
        <div className="status-container">
          <h3>Transaction Status</h3>
          <p>{txStatus}</p>
          {txHash && (
            <p>
              Transaction Hash: <a href={getExplorerUrl(txHash)} target="_blank" rel="noopener noreferrer">{txHash}</a>
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default L2RelayTester; 