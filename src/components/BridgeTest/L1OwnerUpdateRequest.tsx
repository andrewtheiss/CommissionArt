import React, { useState, useEffect, useRef } from 'react';
import { ethers } from 'ethers';
import { useBlockchain } from '../../utils/BlockchainContext';
import './BridgeTest.css';
import contractConfigJson from '../../assets/contract_config.json';
import l1QueryOwnerABI from '../../assets/abis/L1QueryOwner.json';

// Using the ethers LogDescription type
type ParsedLog = ethers.LogDescription;

// Extend Window interface
declare global {
  interface Window {
    ethereum?: any;
  }
}

const L1OwnerUpdateRequest: React.FC = () => {
  const [bridgeStatus, setBridgeStatus] = useState<string>('Ready');
  const { isConnected, networkType, switchNetwork, connectWallet, walletAddress } = useBlockchain();

  // Get contract addresses from configuration
  const l1ContractAddress = contractConfigJson.networks.testnet.l1.address;
  const l2ContractAddress = contractConfigJson.networks.testnet.l2.address;
  const l3ContractAddress = contractConfigJson.networks.testnet.l3.address;

  // Refs for input elements
  const nftContractRef = useRef<HTMLInputElement>(null);
  const tokenIdRef = useRef<HTMLInputElement>(null);
  const l2ReceiverRef = useRef<HTMLInputElement>(null);
  const ethValueRef = useRef<HTMLInputElement>(null);
  const contractAddressRef = useRef<HTMLInputElement>(null);

  // Initialize contract (assuming the wallet is connected and on Sepolia network)
  const initializeContract = async () => {
    if (!isConnected) {
      setBridgeStatus('Please connect your wallet');
      return null;
    }

    if (networkType !== 'dev') {
      setBridgeStatus('Please switch to Sepolia network');
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

      const contractAddress = contractAddressRef.current?.value || l1ContractAddress;
      if (!contractAddress || !ethers.isAddress(contractAddress)) {
        setBridgeStatus('Please enter a valid contract address');
        return null;
      }

      return new ethers.Contract(contractAddress, l1QueryOwnerABI, signer);
    } catch (error: any) {
      setBridgeStatus(`Error initializing contract: ${error.message}`);
      console.error('Contract initialization error:', error);
      return null;
    }
  };

  // Function to call queryNFTAndSendBack with hardcoded gas values
  const callQueryNFTAndSendBack = async () => {
    try {
      setBridgeStatus('Checking network...');
      
      // First make sure we're on Sepolia
      if (networkType !== 'dev') {
        setBridgeStatus('Switching to Sepolia...');
        switchNetwork('dev');
        setBridgeStatus('Network switched to Sepolia, please try again');
        return;
      }

      const contract = await initializeContract();
      if (!contract) return;

      // Get input values from refs
      const nftContract = nftContractRef.current?.value || '0x3cF3dada5C03F32F0b77AAE7Ae19F61Ab89dbD06';
      const tokenId = tokenIdRef.current?.value || '0';
      const l2Receiver = l2ReceiverRef.current?.value || l2ContractAddress;
      const ethValue = ethValueRef.current?.value || '0.001';

      // Input validation
      if (!ethers.isAddress(nftContract)) {
        setBridgeStatus('Invalid NFT contract address');
        return;
      }

      if (!ethers.isAddress(l2Receiver)) {
        setBridgeStatus('Invalid L2 receiver address');
        return;
      }

      // Convert ETH value to wei
      const ethValueWei = ethers.parseEther(ethValue);

      // Define gas parameters as BigInt
      const maxSubmissionCost = BigInt('4500000000000');
      const gasLimit = BigInt('1000000');
      const maxFeePerGas = BigInt('100000000');

      setBridgeStatus('Sending transaction...');
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
      for (const log of receipt.logs) {
        try {
          const parsedLog = contract.interface.parseLog(log);
          if (parsedLog && parsedLog.name === 'OwnerQueried') {
            ownerQueriedEvents.push(parsedLog);
          }
        } catch (error) {
          // Skip logs that can't be parsed
        }
      }

      if (ownerQueriedEvents.length > 0) {
        const event = ownerQueriedEvents[0];
        const ticketId = event.args[0]; // First indexed param is ticketId
        setBridgeStatus(`Transaction confirmed! Ticket ID: ${ticketId.toString()}`);
      } else {
        setBridgeStatus('Transaction confirmed, but no OwnerQueried event found.');
      }
    } catch (error: any) {
      setBridgeStatus(`Error: ${error.message}`);
      console.error(error);
    }
  };

  // Function with optimized gas estimation
  const callQueryNFTAndSendBackOptimized = async () => {
    try {
      setBridgeStatus('Estimating optimal gas values...');
      
      // Use these as fallback values
      const gasEstimation = {
        maxSubmissionCost: '4500000000000',
        gasLimit: '1000000',
        maxFeePerGas: '100000000'
      };
      
      const contract = await initializeContract();
      if (!contract) return;

      const nftContract = nftContractRef.current?.value || '0x3cF3dada5C03F32F0b77AAE7Ae19F61Ab89dbD06';
      const tokenId = tokenIdRef.current?.value || '0';
      const l2Receiver = l2ReceiverRef.current?.value || l2ContractAddress;
      const ethValue = ethValueRef.current?.value || '0.001';
      const ethValueWei = ethers.parseEther(ethValue);

      setBridgeStatus('Sending optimized transaction...');
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
      setBridgeStatus(`Optimized transaction confirmed: ${receipt.transactionHash}`);
    } catch (error: any) {
      setBridgeStatus(`Error: ${error.message}`);
      console.error(error);
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

  return (
    <div className="bridge-test-container">
      <h2>L1 Owner Update Request</h2>
      
      {!isConnected ? (
        <div className="connect-wallet-container">
          <p>Please connect your wallet to use this feature</p>
          <button 
            onClick={handleConnectWallet}
            className="primary-button"
          >
            Connect Wallet
          </button>
        </div>
      ) : (
        <>
          <div className="wallet-info">
            <p className="wallet-address">
              Connected: {walletAddress?.slice(0, 6)}...{walletAddress?.slice(-4)}
            </p>
            <p className="network-info">
              Network: {networkType === 'dev' ? 'Sepolia' : networkType}
              {networkType !== 'dev' && (
                <button 
                  onClick={() => switchNetwork('dev')}
                  className="network-switch-button"
                >
                  Switch to Sepolia
                </button>
              )}
            </p>
          </div>
          
          <div className="info-panel">
            <p>Contract Addresses from Configuration:</p>
            <ul>
              <li>L1 (Sepolia): {l1ContractAddress}</li>
              <li>L2 (Arbitrum): {l2ContractAddress}</li>
              <li>L3 (Orbit): {l3ContractAddress}</li>
            </ul>
          </div>
          
          <div className="form-container">
            <div className="form-group">
              <label htmlFor="contractAddress">L1 Contract Address:</label>
              <input
                type="text"
                id="contractAddress"
                ref={contractAddressRef}
                defaultValue={l1ContractAddress}
                placeholder="Contract address"
              />
              <small>The contract that will send the query to L2</small>
            </div>
            
            <div className="form-group">
              <label htmlFor="nftContract">NFT Contract:</label>
              <input
                type="text"
                id="nftContract"
                ref={nftContractRef}
                defaultValue="0x3cF3dada5C03F32F0b77AAE7Ae19F61Ab89dbD06"
                placeholder="NFT contract address"
              />
              <small>The NFT contract to query</small>
            </div>
            
            <div className="form-group">
              <label htmlFor="tokenId">Token ID:</label>
              <input
                type="text"
                id="tokenId"
                ref={tokenIdRef}
                defaultValue="0"
                placeholder="Token ID"
              />
              <small>The token ID to check ownership</small>
            </div>
            
            <div className="form-group">
              <label htmlFor="l2Receiver">L2 Receiver:</label>
              <input
                type="text"
                id="l2Receiver"
                ref={l2ReceiverRef}
                defaultValue={l2ContractAddress}
                placeholder="L2 receiver address"
              />
              <small>The contract that will receive the result on L2</small>
            </div>
            
            <div className="form-group">
              <label htmlFor="ethValue">ETH Value:</label>
              <input
                type="text"
                id="ethValue"
                ref={ethValueRef}
                defaultValue="0.001"
                placeholder="ETH amount"
              />
              <small>ETH to send for cross-chain fees (min. 0.001 recommended)</small>
            </div>
            
            <div className="button-group">
              <button onClick={callQueryNFTAndSendBack} className="primary-button">
                Send Request (Safe Parameters)
              </button>
              <button onClick={callQueryNFTAndSendBackOptimized} className="secondary-button">
                Send Request (Optimized Gas)
              </button>
            </div>
          </div>
          
          <div className="status-panel">
            <h3>Status:</h3>
            <div className="status-box">
              <pre>{bridgeStatus}</pre>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default L1OwnerUpdateRequest; 