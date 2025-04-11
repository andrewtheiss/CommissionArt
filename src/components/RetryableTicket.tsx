import { useState, useEffect } from 'react';
import { ethers } from 'ethers';
import { useBlockchain } from '../utils/BlockchainContext';

/**
 * RetryableTicket Component
 * 
 * This component allows triggering a retryable ticket with specific parameters
 * directly from the frontend.
 */
const RetryableTicket = () => {
  const { isConnected, walletAddress, connectWallet } = useBlockchain();
  const [status, setStatus] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [txHash, setTxHash] = useState<string | null>(null);
  const [connectingWallet, setConnectingWallet] = useState<boolean>(false);

  // Fixed parameters from the request
  const destinationAddress = '0xef02F150156e45806aaF17A60B5541D079FE13e6';
  const ethValue = '0.0001';
  const l2CallValue = '0';
  const maxSubmissionCost = '1000000';
  const gasLimit = '1000000';
  const maxFeePerGas = '10000000';

  // Check for wallet on component mount
  useEffect(() => {
    if (isConnected && !walletAddress) {
      handleConnectWallet();
    }
  }, [isConnected, walletAddress]);

  const handleConnectWallet = async () => {
    try {
      setConnectingWallet(true);
      setStatus('Connecting wallet...');
      await connectWallet();
      setStatus('Wallet connected.');
    } catch (error) {
      console.error('Error connecting wallet:', error);
      setStatus('Failed to connect wallet. Please try again.');
    } finally {
      setConnectingWallet(false);
    }
  };

  const createRetryableTicket = async () => {
    // Clear previous status
    setStatus('');
    
    if (!isConnected) {
      setStatus('Please connect your wallet first');
      return;
    }
    
    // Try to connect wallet if address isn't available
    if (!walletAddress) {
      try {
        await handleConnectWallet();
        // If still no wallet address, stop
        if (!walletAddress) {
          setStatus('Wallet address still not available. Please try manually connecting through MetaMask.');
          return;
        }
      } catch (error) {
        setStatus('Failed to connect wallet. Please try again.');
        return;
      }
    }

    try {
      setIsLoading(true);
      setStatus('Creating retryable ticket...');

      // Get inbox address for Sepolia (from the deploy script)
      const inboxAddress = '0xaAe29B0366299461418F5324a79Afc425BE5ae21';

      // Convert parameters to appropriate formats
      const ethValueWei = ethers.parseEther(ethValue);
      const l2CallValueBN = BigInt(l2CallValue);
      const maxSubmissionCostBN = BigInt(maxSubmissionCost);
      const gasLimitBN = BigInt(gasLimit);
      const maxFeePerGasBN = BigInt(maxFeePerGas);

      // Create empty calldata (no specific function call)
      const emptyCalldata = '0x';

      // Get the provider and signer
      if (!window.ethereum) {
        setStatus('MetaMask is not installed');
        setIsLoading(false);
        return;
      }

      const provider = new ethers.BrowserProvider(window.ethereum);
      
      // Request account access if needed
      await provider.send('eth_requestAccounts', []);
      
      const signer = await provider.getSigner();
      const signerAddress = await signer.getAddress();

      console.log('Signer address:', signerAddress);
      
      // Create contract instance for the Inbox
      const inboxContract = new ethers.Contract(
        inboxAddress,
        [
          "function createRetryableTicket(address to, uint256 l2CallValue, uint256 maxSubmissionCost, address excessFeeRefundAddress, address callValueRefundAddress, uint256 gasLimit, uint256 maxFeePerGas, uint256 tokenTotalFee, bytes calldata data) external payable returns (uint256)"
        ],
        signer
      );

      console.log('Sending transaction with params:', {
        to: destinationAddress,
        l2CallValue: l2CallValueBN,
        maxSubmissionCost: maxSubmissionCostBN,
        excessFeeRefundAddress: signerAddress,
        callValueRefundAddress: signerAddress,
        gasLimit: gasLimitBN,
        maxFeePerGas: maxFeePerGasBN,
        ethValue: ethValueWei
      });

      // Send transaction
      const tx = await inboxContract.createRetryableTicket(
        destinationAddress,        // to address
        l2CallValueBN,             // l2CallValue
        maxSubmissionCostBN,       // maxSubmissionCost
        signerAddress,             // excessFeeRefundAddress - use signer address directly
        signerAddress,             // callValueRefundAddress - use signer address directly
        gasLimitBN,                // gasLimit
        maxFeePerGasBN,            // maxFeePerGas
        ethValueWei,               // tokenTotalFeeAmount (sending the full ETH value)
        emptyCalldata,             // data
        { value: ethValueWei }     // ETH value to send with the transaction
      );

      setTxHash(tx.hash);
      setStatus(`Transaction submitted: ${tx.hash}`);
      
      // Wait for transaction confirmation
      const receipt = await tx.wait();
      console.log('Transaction confirmed:', receipt);
      
      setStatus(`Retryable ticket created successfully! Transaction hash: ${tx.hash}`);
    } catch (error: any) {
      console.error('Error creating retryable ticket:', error);
      setStatus(`Error: ${error.message || String(error)}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="retryable-ticket-container">
      <h2>Create Retryable Ticket</h2>
      
      <div className="wallet-status">
        <h3>Wallet Status</h3>
        <p>
          {isConnected 
            ? walletAddress 
              ? `Connected: ${walletAddress.substring(0, 6)}...${walletAddress.substring(walletAddress.length - 4)}` 
              : 'Connected but address not available'
            : 'Not connected'
          }
        </p>
        {(!isConnected || !walletAddress) && (
          <button 
            onClick={handleConnectWallet}
            disabled={connectingWallet}
            className="connect-button"
          >
            {connectingWallet ? 'Connecting...' : 'Connect Wallet'}
          </button>
        )}
      </div>
      
      <div className="parameters-display">
        <h3>Parameters</h3>
        <table>
          <tbody>
            <tr>
              <td>ETH Value:</td>
              <td>{ethValue} ETH</td>
            </tr>
            <tr>
              <td>Destination Address:</td>
              <td>{destinationAddress}</td>
            </tr>
            <tr>
              <td>L2 Call Value:</td>
              <td>{l2CallValue}</td>
            </tr>
            <tr>
              <td>Max Submission Cost:</td>
              <td>{maxSubmissionCost}</td>
            </tr>
            <tr>
              <td>Gas Limit:</td>
              <td>{gasLimit}</td>
            </tr>
            <tr>
              <td>Max Fee Per Gas:</td>
              <td>{maxFeePerGas}</td>
            </tr>
          </tbody>
        </table>
      </div>
      
      <div className="action-container">
        <button 
          onClick={createRetryableTicket} 
          disabled={isLoading || (!isConnected && !walletAddress)}
          className="create-button"
        >
          {isLoading ? 'Processing...' : 'Create Retryable Ticket'}
        </button>
      </div>
      
      {status && (
        <div className="status-container">
          <h3>Status</h3>
          <p>{status}</p>
          {txHash && (
            <p>
              <a 
                href={`https://sepolia.etherscan.io/tx/${txHash}`} 
                target="_blank" 
                rel="noopener noreferrer"
              >
                View on Etherscan
              </a>
              {' | '}
              <a 
                href={`https://retryable-dashboard.arbitrum.io/tx/${txHash}`} 
                target="_blank" 
                rel="noopener noreferrer"
              >
                View on Retryable Dashboard
              </a>
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default RetryableTicket; 