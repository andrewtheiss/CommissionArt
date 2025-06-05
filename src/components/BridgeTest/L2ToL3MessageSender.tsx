import React, { useState, useEffect } from 'react';
import { ethers } from 'ethers';
import { useBlockchain } from '../../utils/BlockchainContext';
import { toast } from 'react-hot-toast';
import './BridgeTest.css';

// Extend Window interface
declare global {
  interface Window {
    ethereum?: any;
  }
}

interface L2ToL3MessageSenderProps {
  setBridgeStatus: (status: string | ((prev: string) => string)) => void;
}

const L2ToL3MessageSender: React.FC<L2ToL3MessageSenderProps> = ({ setBridgeStatus }) => {
  const { isConnected, walletAddress, networkType, switchNetwork, switchToLayer, connectWallet } = useBlockchain();

  // Contract address - deployed on L2 (Arbitrum)
  const L2_TO_L3_CONTRACT = "0xa46E204B8cD37959c0e4C3082c8830eFa160dc14";
  const ANIME_TOKEN_ADDRESS = "0x37a645648dF29205C6261289983FB04ECD70b4B3";
  const DEFAULT_L3_TARGET = "0xed9d942cb93cece584b3898be216c366d81d9e84";

  // State variables for form inputs
  const [l3Receiver, setL3Receiver] = useState<string>(DEFAULT_L3_TARGET);
  const [userInputAddress, setUserInputAddress] = useState<string>("");
  const [l3CallValue, setL3CallValue] = useState<string>("1");
  const [maxSubmissionCost, setMaxSubmissionCost] = useState<string>("0.0093");
  const [gasLimit, setGasLimit] = useState<string>("300000");
  const [maxFeePerGas, setMaxFeePerGas] = useState<string>("36000000");
  const [ethValue, setEthValue] = useState<string>("1.0048");

  // State for loading states
  const [isApproving, setIsApproving] = useState<boolean>(false);
  const [isSending, setIsSending] = useState<boolean>(false);
  const [environment, setEnvironment] = useState<'testnet' | 'mainnet'>('testnet');

  // Set environment based on network type
  useEffect(() => {
    const currentEnv = networkType.includes('mainnet') ? 'mainnet' : 'testnet';
    setEnvironment(currentEnv);
  }, [networkType]);

  // Set default user input address to wallet address when connected
  useEffect(() => {
    if (isConnected && walletAddress && !userInputAddress) {
      setUserInputAddress(walletAddress);
    }
  }, [isConnected, walletAddress, userInputAddress]);

  // Contract ABI for the L2 to L3 Message Sender
  const L2_TO_L3_ABI = [
    "function approveMaxAnimeForMessaging() external",
    "function sendMessageToL3(address _l3_receiver, address _user_input_address, uint256 _l3_call_value, uint256 _max_submission_cost, uint256 _gas_limit, uint256 _max_fee_per_gas) external payable",
    "event AnimeApprovedForMessaging(address indexed user, uint256 amount)",
    "event L2ToL3MessageSent(address indexed l3_receiver, address indexed user_input_address, address sender, uint256 ticket_id)"
  ];

  // ANIME Token ABI for checking balance and allowance
  const ANIME_TOKEN_ABI = [
    "function balanceOf(address account) external view returns (uint256)",
    "function allowance(address owner, address spender) external view returns (uint256)",
    "function approve(address spender, uint256 amount) external returns (bool)"
  ];

  // Function to check ANIME token status
  const checkAnimeTokenStatus = async () => {
    if (!isConnected || !walletAddress) {
      setBridgeStatus('Please connect your wallet to check ANIME token status');
      return;
    }

    // Ensure we're on L2 (Arbitrum)
    if (!networkType.includes('arbitrum')) {
      setBridgeStatus('Please switch to Arbitrum network (L2) to check ANIME tokens');
      return;
    }

    try {
      if (typeof window === 'undefined' || !window.ethereum) {
        throw new Error('MetaMask is not installed or not accessible');
      }

      const provider = new ethers.BrowserProvider(window.ethereum);
      
      // Confirm we're on the right network first
      const network = await provider.getNetwork();
      const isArbitrum = network.chainId === 42161n || network.chainId === 421614n; // Arbitrum One or Sepolia
      
      if (!isArbitrum) {
        setBridgeStatus('Error: Please make sure your wallet is connected to Arbitrum network');
        return;
      }

      setBridgeStatus('Checking ANIME token status...');
      
      const animeContract = new ethers.Contract(ANIME_TOKEN_ADDRESS, ANIME_TOKEN_ABI, provider);
      
      // Check balance and allowance
      const [balance, allowance] = await Promise.all([
        animeContract.balanceOf(walletAddress),
        animeContract.allowance(walletAddress, L2_TO_L3_CONTRACT)
      ]);
      
      const requiredAmount = ethers.parseEther("1.0014");
      const balanceSufficient = balance >= requiredAmount;
      const allowanceSufficient = allowance >= requiredAmount;
      
      setBridgeStatus(`ANIME Token Status Check:
- Your ANIME Balance: ${ethers.formatEther(balance)} ANIME
- Contract Allowance: ${ethers.formatEther(allowance)} ANIME
- Required for Transaction: ~1.0014 ANIME
- Balance Sufficient: ${balanceSufficient ? "✅ YES" : "❌ NO"}
- Allowance Sufficient: ${allowanceSufficient ? "✅ YES" : "❌ NO"}
- Network: ${network.chainId === 42161n ? 'Arbitrum One' : 'Arbitrum Sepolia'}

${!balanceSufficient ? "\n⚠️ You need more ANIME tokens in your wallet." : ""}
${!allowanceSufficient ? "\n⚠️ You need to approve ANIME tokens for this contract." : ""}
${balanceSufficient && allowanceSufficient ? "\n🎉 All checks passed! You can proceed with the transaction." : ""}`);
      
    } catch (error: any) {
      console.error('Error checking ANIME token status:', error);
      setBridgeStatus(`Error checking ANIME token status: ${error.message || String(error)}
      
Please ensure:
- You're connected to Arbitrum network
- MetaMask is unlocked and accessible
- The ANIME token contract is accessible`);
    }
  };

  // Function to approve maximum ANIME tokens for messaging
  const handleApproveAnime = async () => {
    if (!isConnected) {
      setBridgeStatus('Please connect your wallet to continue');
      return;
    }

    // Ensure we're on L2 (Arbitrum)
    if (!networkType.includes('arbitrum')) {
      setBridgeStatus('Please switch to Arbitrum network (L2) to approve ANIME tokens');
      switchToLayer('l2', environment);
      return;
    }

    try {
      setIsApproving(true);
      setBridgeStatus('Approving maximum ANIME tokens for L2→L3 messaging...');

      if (typeof window === 'undefined' || !window.ethereum) {
        throw new Error('MetaMask is not installed or not accessible');
      }

      const provider = new ethers.BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();
      
      // Confirm we're on the right network
      const network = await provider.getNetwork();
      const isArbitrum = network.chainId === 42161n || network.chainId === 421614n; // Arbitrum One or Sepolia
      
      if (!isArbitrum) {
        setBridgeStatus('Error: Please make sure your wallet is connected to Arbitrum');
        return;
      }

      // Create contract instance
      const contract = new ethers.Contract(L2_TO_L3_CONTRACT, L2_TO_L3_ABI, signer);
      
      // Call the approve function
      const tx = await contract.approveMaxAnimeForMessaging();
      
      setBridgeStatus(prev => `${prev}\n\nApproval transaction submitted: ${tx.hash}`);
      
      // Wait for transaction confirmation
      const receipt = await tx.wait();
      
      setBridgeStatus(prev => `${prev}\n\nANIME token approval confirmed! Transaction hash: ${tx.hash}`);
      
      toast.success('ANIME tokens approved for L2→L3 messaging');
      
    } catch (error: any) {
      console.error('Error approving ANIME tokens:', error);
      setBridgeStatus(prev => `${prev}\n\nError approving ANIME: ${error.message || String(error)}`);
      toast.error('Failed to approve ANIME tokens');
    } finally {
      setIsApproving(false);
    }
  };

  // Function to send L2→L3 message
  const handleSendMessage = async () => {
    if (!isConnected) {
      setBridgeStatus('Please connect your wallet to continue');
      return;
    }

    // Ensure we're on L2 (Arbitrum)
    if (!networkType.includes('arbitrum')) {
      setBridgeStatus('Please switch to Arbitrum network (L2) to send L2→L3 messages');
      switchToLayer('l2', environment);
      return;
    }

    // Validate inputs
    if (!ethers.isAddress(l3Receiver)) {
      setBridgeStatus('Error: Invalid L3 receiver address');
      return;
    }

    if (!ethers.isAddress(userInputAddress)) {
      setBridgeStatus('Error: Invalid user input address');
      return;
    }

    try {
      setIsSending(true);
      setBridgeStatus('Sending L2→L3 message...');

      if (typeof window === 'undefined' || !window.ethereum) {
        throw new Error('MetaMask is not installed or not accessible');
      }

      const provider = new ethers.BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();
      
      // Confirm we're on the right network
      const network = await provider.getNetwork();
      const isArbitrum = network.chainId === 42161n || network.chainId === 421614n; // Arbitrum One or Sepolia
      
      if (!isArbitrum) {
        setBridgeStatus('Error: Please make sure your wallet is connected to Arbitrum');
        return;
      }

      setBridgeStatus(`Sending L2→L3 message with parameters:
- L3 Receiver: ${l3Receiver}
- User Input Address: ${userInputAddress}
- L3 Call Value: ${l3CallValue} ETH
- Max Submission Cost: ${maxSubmissionCost} ETH
- Gas Limit: ${gasLimit}
- Max Fee Per Gas: ${ethers.formatUnits(maxFeePerGas, "gwei")} gwei
- Total ETH Value: ${ethValue} ETH`);

      // Create contract instance
      const contract = new ethers.Contract(L2_TO_L3_CONTRACT, L2_TO_L3_ABI, signer);
      
      // Convert values to appropriate formats
      const l3CallValueWei = ethers.parseEther(l3CallValue);
      const maxSubmissionCostWei = ethers.parseEther(maxSubmissionCost);
      const ethValueWei = ethers.parseEther(ethValue);
      
      // Call the sendMessageToL3 function
      const tx = await contract.sendMessageToL3(
        l3Receiver,
        userInputAddress,
        l3CallValueWei,
        maxSubmissionCostWei,
        gasLimit,
        maxFeePerGas,
        { value: ethValueWei }
      );
      
      setBridgeStatus(prev => `${prev}\n\nL2→L3 message transaction submitted: ${tx.hash}`);
      
      // Wait for transaction confirmation
      const receipt = await tx.wait();
      
      setBridgeStatus(prev => `${prev}\n\nL2→L3 message confirmed! Transaction hash: ${tx.hash}`);
      
      // Find the L2ToL3MessageSent event
      const messageSentEvents = receipt.logs
        .filter((log: any) => log.fragment?.name === 'L2ToL3MessageSent');
      
      if (messageSentEvents.length > 0) {
        const event = messageSentEvents[0];
        const ticketId = event.args[3]; // Get the ticket ID from the event
        
        setBridgeStatus(prev => `${prev}\n\nSuccess! L2→L3 message sent.
Ticket ID: ${ticketId}
L3 Receiver: ${event.args[0]}
User Input Address: ${event.args[1]}
Sender: ${event.args[2]}`);
      } else {
        setBridgeStatus(prev => `${prev}\n\nTransaction succeeded but no L2ToL3MessageSent event was found.`);
      }
      
      toast.success('L2→L3 message sent successfully!');
      
    } catch (error: any) {
      console.error('Error sending L2→L3 message:', error);
      setBridgeStatus(prev => `${prev}\n\nError sending message: ${error.message || String(error)}`);
      toast.error('Failed to send L2→L3 message');
    } finally {
      setIsSending(false);
    }
  };

  // Function to use preset values for quick testing
  const usePresetValues = () => {
    setL3Receiver(DEFAULT_L3_TARGET);
    setUserInputAddress(walletAddress || "");
    setL3CallValue("1");
    setMaxSubmissionCost("0.0093");
    setGasLimit("300000");
    setMaxFeePerGas("36000000");
    setEthValue("1.0048");
    setBridgeStatus('Loaded preset values for testing');
  };

  // Function to use optimized mainnet values
  const useMainnetValues = () => {
    setL3Receiver(DEFAULT_L3_TARGET);
    setUserInputAddress(walletAddress || "");
    setL3CallValue("1");
    setMaxSubmissionCost("0.0095");
    setGasLimit("300000");
    setMaxFeePerGas("36000000");
    setEthValue("1.0048");
    setBridgeStatus('Loaded optimized mainnet values');
  };

  // Function to use ETH-only values (no ANIME tokens required)
  const useEthOnlyValues = () => {
    setL3Receiver(DEFAULT_L3_TARGET);
    setUserInputAddress(walletAddress || "");
    setL3CallValue("0");
    setMaxSubmissionCost("0.01");
    setGasLimit("300000");
    setMaxFeePerGas("2000000000");
    setEthValue("0.012");
    setBridgeStatus('Loaded ETH-only values (no ANIME tokens required)');
  };

  // Function to try the original L3 contract address
  const useOriginalL3Target = () => {
    const originalL3Target = "0x08Fa26D7C129Ea51CCFf87109C382a532605E120";
    setL3Receiver(originalL3Target);
    setUserInputAddress(walletAddress || "");
    setL3CallValue("1");
    setMaxSubmissionCost("0.0093");
    setGasLimit("300000");
    setMaxFeePerGas("36000000");
    setEthValue("1.0048");
    setBridgeStatus(`Loaded values with original L3 target: ${originalL3Target}`);
  };

  return (
    <div className="l2-to-l3-message-sender">
      <div className="contract-info">
        <h4>L2→L3 Message Sender</h4>
        <p className="contract-address">
          Contract: <code>{L2_TO_L3_CONTRACT}</code>
        </p>
        <p className="network-requirement">
          Network: Arbitrum {environment === 'testnet' ? 'Sepolia' : 'One'} (L2)
        </p>
      </div>

      <div className="sender-controls">
        <div className="approval-section">
          <h5>Step 1: Approve ANIME Tokens (Optional)</h5>
          <p className="info-text">
            Approve this contract to spend your ANIME tokens for L3 gas fees (optional for ETH-only transactions)
          </p>
          <div className="approval-buttons">
            <button 
              onClick={checkAnimeTokenStatus}
              disabled={!isConnected}
              className="check-button"
            >
              Check ANIME Status
            </button>
            <button 
              onClick={handleApproveAnime}
              disabled={!isConnected || isApproving}
              className="approve-button"
            >
              {isApproving ? 'Approving...' : 'Approve Max ANIME'}
            </button>
          </div>
        </div>

        <div className="message-section">
          <h5>Step 2: Send L2→L3 Message</h5>
          
          <div className="preset-buttons">
            <button onClick={usePresetValues} className="preset-button">
              Use Test Values
            </button>
            <button onClick={useMainnetValues} className="preset-button">
              Use Mainnet Values
            </button>
            <button onClick={useEthOnlyValues} className="preset-button">
              Use ETH-only Values
            </button>
            <button onClick={useOriginalL3Target} className="preset-button">
              Use Original L3 Target
            </button>
          </div>

          <div className="form-grid">
            <div className="form-row">
              <label>L3 Receiver Address:</label>
              <input
                type="text"
                value={l3Receiver}
                onChange={(e) => setL3Receiver(e.target.value)}
                placeholder="L3 contract address (0xed9d942cb93cece584b3898be216c366d81d9e84)"
                className="address-input"
              />
              <small>L3 contract that will receive the message</small>
            </div>

            <div className="form-row">
              <label>User Input Address:</label>
              <input
                type="text"
                value={userInputAddress}
                onChange={(e) => setUserInputAddress(e.target.value)}
                placeholder="Address parameter for crossChainUpdate"
                className="address-input"
              />
              <small>Address parameter to pass to L3 contract</small>
            </div>

            <div className="form-row">
              <label>L3 Call Value (ETH):</label>
              <input
                type="text"
                value={l3CallValue}
                onChange={(e) => setL3CallValue(e.target.value)}
                placeholder="1"
              />
              <small>ETH to send with L3 call (1 ETH based on transaction data)</small>
            </div>

            <div className="form-row">
              <label>Max Submission Cost (ETH):</label>
              <input
                type="text"
                value={maxSubmissionCost}
                onChange={(e) => setMaxSubmissionCost(e.target.value)}
                placeholder="0.0093"
              />
              <small>Cost to submit retryable ticket (0.0093 ETH based on transaction data)</small>
            </div>

            <div className="form-row">
              <label>Gas Limit:</label>
              <input
                type="text"
                value={gasLimit}
                onChange={(e) => setGasLimit(e.target.value)}
                placeholder="300000"
              />
              <small>Gas limit for L3 execution (e.g., 300,000)</small>
            </div>

            <div className="form-row">
              <label>Max Fee Per Gas (wei):</label>
              <input
                type="text"
                value={maxFeePerGas}
                onChange={(e) => setMaxFeePerGas(e.target.value)}
                placeholder="36000000"
              />
              <small>Max fee per gas (36,000,000 wei = 0.036 gwei based on transaction data)</small>
            </div>

            <div className="form-row">
              <label>Total ETH Value:</label>
              <input
                type="text"
                value={ethValue}
                onChange={(e) => setEthValue(e.target.value)}
                placeholder="1.0048"
              />
              <small>Total ETH to send (1.0048 ETH based on transaction data)</small>
            </div>
          </div>

          <button 
            onClick={handleSendMessage}
            disabled={!isConnected || isSending || !l3Receiver || !userInputAddress}
            className="send-button"
          >
            {isSending ? 'Sending Message...' : 'Send L2→L3 Message'}
          </button>
        </div>

        <div className="raw-data-section">
          <h5>Raw Transaction Data</h5>
          <div className="raw-data">
            <pre>{JSON.stringify({
              contract: L2_TO_L3_CONTRACT,
              function: 'sendMessageToL3',
              parameters: {
                _l3_receiver: l3Receiver,
                _user_input_address: userInputAddress,
                _l3_call_value: l3CallValue + ' ETH',
                _max_submission_cost: maxSubmissionCost + ' ETH',
                _gas_limit: gasLimit,
                _max_fee_per_gas: maxFeePerGas + ' wei'
              },
              value: ethValue + ' ETH'
            }, null, 2)}</pre>
          </div>
        </div>
      </div>
    </div>
  );
};

export default L2ToL3MessageSender; 