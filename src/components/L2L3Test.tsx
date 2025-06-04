import React, { useState, useEffect } from 'react';
import { ethers } from 'ethers';
import { useBlockchain } from '../utils/BlockchainContext';
import { toast } from 'react-hot-toast';
import './BridgeTest/BridgeTest.css';

// Extend Window interface
declare global {
  interface Window {
    ethereum?: any;
  }
}

const L2L3Test: React.FC = () => {
  const { isConnected, walletAddress, networkType, switchNetwork, switchToLayer, connectWallet } = useBlockchain();

  // Contract address - L2 Inbox contract for retryable tickets
  const L2_TO_L3_CONTRACT = "0xA203252940839c8482dD4b938b4178f842E343D7";
  const ANIME_TOKEN_ADDRESS = "0x37a645648dF29205C6261289983FB04ECD70b4B3";
  const DEFAULT_L3_TARGET = "0xed9d942cb93cece584b3898be216c366d81d9e84";
  const L3ReceiveMessageContractAddress = "0x8B6Bc7Ce0D266b11375d265F7fcb2BAB57D0e728";

  // State variables for form inputs - updated to match working example
  const [toAddress, setToAddress] = useState<string>(L2_TO_L3_CONTRACT);
  const [userInputAddress, setUserInputAddress] = useState<string>("");
  const [l2CallValue, setL2CallValue] = useState<string>("1");
  const [maxSubmissionCost, setMaxSubmissionCost] = useState<string>("0.0006");
  const [excessFeeRefundAddress, setExcessFeeRefundAddress] = useState<string>("");
  const [callValueRefundAddress, setCallValueRefundAddress] = useState<string>("");
  const [gasLimit, setGasLimit] = useState<string>("300000");
  const [maxFeePerGas, setMaxFeePerGas] = useState<string>("36000000");
  const [tokenTotalFeeAmount, setTokenTotalFeeAmount] = useState<string>("1.0007");

  // State for loading states
  const [isApproving, setIsApproving] = useState<boolean>(false);
  const [isSending, setIsSending] = useState<boolean>(false);
  const [bridgeStatus, setBridgeStatus] = useState<string>('Welcome to L2→L3 Test! This component defaults to Arbitrum mainnet. It will create a retryable ticket that calls crossChainUpdate(address) on the L3ReceiveMessage contract.');

  // Auto-switch to Arbitrum mainnet when component mounts
  useEffect(() => {
    if (networkType !== 'arbitrum_mainnet') {
      console.log('L2L3Test: Auto-switching to Arbitrum mainnet (L2)');
      switchToLayer('l2', 'mainnet');
      setBridgeStatus('Switching to Arbitrum mainnet (L2) for optimal testing...');
    }
  }, [networkType, switchToLayer]);

  // Set default addresses to wallet address when connected
  useEffect(() => {
    if (isConnected && walletAddress) {
      // Don't override toAddress if it's already set to inbox contract
      if (!toAddress || toAddress === "") {
        setToAddress(L2_TO_L3_CONTRACT);
      }
      if (!userInputAddress) {
        setUserInputAddress(walletAddress);
      }
      if (!excessFeeRefundAddress) {
        setExcessFeeRefundAddress(walletAddress);
      }
      if (!callValueRefundAddress) {
        setCallValueRefundAddress(walletAddress);
      }
    }
  }, [isConnected, walletAddress, userInputAddress, excessFeeRefundAddress, callValueRefundAddress]);

  // Contract ABI for createRetryableTicket - updated to match working example
  const L2_TO_L3_ABI = [
    "function createRetryableTicket(address to, uint256 l2CallValue, uint256 maxSubmissionCost, address excessFeeRefundAddress, address callValueRefundAddress, uint256 gasLimit, uint256 maxFeePerGas, uint256 tokenTotalFeeAmount, bytes calldata data) external returns (uint256)",
    "event RetryableTicketCreated(uint256 indexed ticketId)"
  ];

  // ANIME Token ABI for checking balance and allowance
  const ANIME_TOKEN_ABI = [
    "function balanceOf(address account) external view returns (uint256)",
    "function allowance(address owner, address spender) external view returns (uint256)",
    "function approve(address spender, uint256 amount) external returns (bool)"
  ];

  // L3ReceiveMessage contract ABI
  const L3_RECEIVE_MESSAGE_ABI = [
    "function crossChainUpdate(address _user_input_address) external"
  ];

  // Helper function for safe checksum
  const safeChecksum = (address: string): string => {
    return ethers.getAddress(address);
  };

  // Helper function to calculate L2 to L3 address alias
  const calculateL2ToL3Alias = (l2Address: string): string => {
    if (!ethers.isAddress(l2Address)) {
      return 'Invalid address';
    }
    
    // Convert address to BigInt for calculation
    const addressBigInt = BigInt(l2Address);
    const offset = BigInt('0x1111000000000000000000000000000000001111');
    
    // Add the offset
    const aliasBigInt = addressBigInt + offset;
    
    // Convert back to hex address (ensure it's 40 chars + 0x)
    const aliasHex = '0x' + aliasBigInt.toString(16).padStart(40, '0');
    
    return ethers.getAddress(aliasHex);
  };

  // Helper function to create calldata for crossChainUpdate
  const createCrossChainUpdateCalldata = (userAddress: string): string => {
    if (!ethers.isAddress(userAddress)) {
      throw new Error('Invalid user address for crossChainUpdate');
    }
    
    // Create function selector - first 4 bytes of keccak256("crossChainUpdate(address)")
    const functionSignature = "crossChainUpdate(address)";
    const functionHash = ethers.keccak256(ethers.toUtf8Bytes(functionSignature));
    const functionSelector = functionHash.slice(0, 10); // 0x + 8 hex chars = 4 bytes
    
    // Convert address to bytes32 (pad with zeros)
    const addressBytes32 = ethers.zeroPadValue(userAddress, 32);
    
    // Concatenate function selector + address parameter
    const calldata = functionSelector + addressBytes32.slice(2); // Remove 0x from address bytes
    
    console.log('Created calldata for crossChainUpdate:', {
      functionSignature,
      functionHash,
      functionSelector,
      userAddress,
      addressBytes32,
      calldata
    });
    
    return calldata;
  };

  // Function to check ANIME token status with enhanced balance checking
  const checkAnimeTokenStatus = async () => {
    try {
      setBridgeStatus('Starting ANIME token status check...');
      console.log('L2L3Test: Starting ANIME token status check');
      
      if (typeof window === 'undefined' || !window.ethereum) {
        throw new Error('MetaMask is not installed or not accessible');
      }

      const provider = new ethers.BrowserProvider(window.ethereum);
      console.log('L2L3Test: Provider created');
      
      // Get accounts directly from provider to bypass context state issues
      let currentWalletAddress;
      try {
        const accounts = await provider.listAccounts();
        console.log('L2L3Test: Accounts from provider:', accounts);
        if (accounts && accounts.length > 0) {
          currentWalletAddress = accounts[0].address;
          console.log('L2L3Test: Using wallet address from provider:', currentWalletAddress);
        } else {
          // Try to get signer address
          const signer = await provider.getSigner();
          currentWalletAddress = await signer.getAddress();
          console.log('L2L3Test: Using wallet address from signer:', currentWalletAddress);
        }
      } catch (walletError) {
        console.error('L2L3Test: Error getting wallet address:', walletError);
        setBridgeStatus('Please connect your wallet to check ANIME token status. Make sure MetaMask is unlocked and connected.');
        return;
      }

      if (!currentWalletAddress) {
        setBridgeStatus('No wallet address found. Please connect your wallet to MetaMask.');
        return;
      }

      // Ensure we're on L2 (Arbitrum)
      if (!networkType.includes('arbitrum')) {
        setBridgeStatus('Please switch to Arbitrum network (L2) to check ANIME tokens');
        return;
      }
      
      // Confirm we're on the right network
      const network = await provider.getNetwork();
      console.log('L2L3Test: Network info:', {
        chainId: network.chainId.toString(),
        name: network.name
      });
      
      const isArbitrum = network.chainId === 42161n || network.chainId === 421614n; // Arbitrum One or Sepolia
      
      if (!isArbitrum) {
        setBridgeStatus(`Error: Please make sure your wallet is connected to Arbitrum network. Current network: ${network.name} (Chain ID: ${network.chainId.toString()})`);
        return;
      }

      setBridgeStatus('Connected to Arbitrum. Checking ANIME token status...');
      
      // Thorough token balance check using raw call (like working example)
      const checksummedAddress = safeChecksum(currentWalletAddress);
      const addressWithoutPrefix = checksummedAddress.substring(2).toLowerCase();
      const balanceCallData = `0x70a08231${'0'.repeat(24)}${addressWithoutPrefix}`;
      
      const rawBalanceResult = await provider.call({
        to: ANIME_TOKEN_ADDRESS,
        data: balanceCallData
      });
      
      const userBalance = BigInt(rawBalanceResult);
      const requiredAmount = ethers.parseEther(tokenTotalFeeAmount);
      const formattedBalance = ethers.formatEther(userBalance);
      
      console.log('Balance check:', {
        userBalance: formattedBalance,
        requiredAmount: tokenTotalFeeAmount,
        hasSufficientBalance: userBalance >= requiredAmount
      });
      
      // Check allowance
      const animeContract = new ethers.Contract(ANIME_TOKEN_ADDRESS, ANIME_TOKEN_ABI, provider);
      const allowance = await animeContract.allowance(currentWalletAddress, L2_TO_L3_CONTRACT);
      
      const balanceSufficient = userBalance >= requiredAmount;
      const allowanceSufficient = allowance >= requiredAmount;
      
      setBridgeStatus(`ANIME Token Status Check:
- Wallet Address: ${currentWalletAddress}
- Your ANIME Balance: ${formattedBalance} ANIME
- Contract Allowance: ${ethers.formatEther(allowance)} ANIME
- Required for Transaction: ${tokenTotalFeeAmount} ANIME
- Balance Sufficient: ${balanceSufficient ? "✅ YES" : "❌ NO"}
- Allowance Sufficient: ${allowanceSufficient ? "✅ YES" : "❌ NO"}
- Network: ${network.chainId === 42161n ? 'Arbitrum One' : 'Arbitrum Sepolia'}

${!balanceSufficient ? "\n⚠️ You need more ANIME tokens in your wallet." : ""}
${!allowanceSufficient ? "\n⚠️ You need to approve ANIME tokens for this contract." : ""}
${balanceSufficient && allowanceSufficient ? "\n🎉 All checks passed! You can proceed with the transaction." : ""}`);
      
    } catch (error: any) {
      console.error('L2L3Test: Error in checkAnimeTokenStatus:', error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      setBridgeStatus(`Error checking ANIME token status: ${errorMessage}

Debug Information:
- Network Type: ${networkType}
- Context isConnected: ${isConnected}
- Context walletAddress: ${walletAddress}
- ANIME Token Address: ${ANIME_TOKEN_ADDRESS}
- L2→L3 Contract: ${L2_TO_L3_CONTRACT}

Please ensure:
- You're connected to Arbitrum network
- MetaMask is unlocked and accessible
- The ANIME token contract is accessible on this network`);
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
      switchToLayer('l2', 'mainnet');
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
      const walletAddr = await signer.getAddress();
      console.log('L2L3Test: Approve - Using wallet address:', walletAddr);
      
      // Confirm we're on the right network
      const network = await provider.getNetwork();
      const isArbitrum = network.chainId === 42161n || network.chainId === 421614n; // Arbitrum One or Sepolia
      
      if (!isArbitrum) {
        setBridgeStatus('Error: Please make sure your wallet is connected to Arbitrum');
        return;
      }

      console.log('L2L3Test: Approve - Network confirmed:', network.chainId.toString());

      // Direct ANIME token approval
      const animeContract = new ethers.Contract(ANIME_TOKEN_ADDRESS, ANIME_TOKEN_ABI, signer);
      const maxApproval = ethers.MaxUint256; // Maximum possible approval
      
      console.log('L2L3Test: Approve - Approving ANIME tokens for max amount...');
      setBridgeStatus(prev => `${prev}\n\nSubmitting ANIME token approval transaction...`);
      
      const approveTx = await animeContract.approve(L2_TO_L3_CONTRACT, maxApproval);
      console.log('L2L3Test: Approval transaction submitted:', approveTx.hash);
      
      setBridgeStatus(prev => `${prev}\n\nApproval transaction submitted: ${approveTx.hash}\nWaiting for confirmation...`);
      
      const approveReceipt = await approveTx.wait();
      console.log('L2L3Test: Approval confirmed:', approveReceipt);
      
      setBridgeStatus(prev => `${prev}\n\nTransaction confirmed! Block: ${approveReceipt.blockNumber}`);
      
      // Verify the approval worked
      setBridgeStatus(prev => `${prev}\n\nVerifying approval...`);
      const finalAllowance = await animeContract.allowance(walletAddr, L2_TO_L3_CONTRACT);
      console.log('L2L3Test: Final allowance after approval:', ethers.formatEther(finalAllowance));
      
      setBridgeStatus(prev => `${prev}\n\n✅ ANIME approval successful!\nNew allowance: ${ethers.formatEther(finalAllowance)} ANIME\nTransaction hash: ${approveTx.hash}`);
      toast.success('ANIME tokens approved for L2→L3 messaging');
      
    } catch (error: any) {
      console.error('L2L3Test: Error in handleApproveAnime:', error);
      setBridgeStatus(prev => `${prev}\n\n❌ Error approving ANIME: ${error.message || String(error)}`);
      toast.error('Failed to approve ANIME tokens');
    } finally {
      setIsApproving(false);
    }
  };

  // Function to send L2→L3 message using createRetryableTicket
  const handleSendMessage = async () => {
    try {
      setIsSending(true);
      setBridgeStatus('Starting L2→L3 retryable ticket creation...');

      if (typeof window === 'undefined' || !window.ethereum) {
        throw new Error('MetaMask is not installed or not accessible');
      }

      const provider = new ethers.BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();
      const account = await signer.getAddress();
      
      // Confirm we're on the right network
      const network = await provider.getNetwork();
      const isArbitrum = network.chainId === 42161n || network.chainId === 421614n; // Arbitrum One or Sepolia
      
      if (!isArbitrum) {
        setBridgeStatus('Error: Please make sure your wallet is connected to Arbitrum');
        return;
      }

      // Validate inputs
      if (!ethers.isAddress(toAddress)) {
        setBridgeStatus('Error: Invalid destination address');
        return;
      }

      if (!ethers.isAddress(userInputAddress)) {
        setBridgeStatus('Error: Invalid user input address for crossChainUpdate');
        return;
      }

      if (!ethers.isAddress(excessFeeRefundAddress)) {
        setBridgeStatus('Error: Invalid excess fee refund address');
        return;
      }

      if (!ethers.isAddress(callValueRefundAddress)) {
        setBridgeStatus('Error: Invalid call value refund address');
        return;
      }

      // Thorough token balance check using raw call
      const checksummedAddress = safeChecksum(account);
      const addressWithoutPrefix = checksummedAddress.substring(2).toLowerCase();
      const balanceCallData = `0x70a08231${'0'.repeat(24)}${addressWithoutPrefix}`;
      
      const rawBalanceResult = await provider.call({
        to: ANIME_TOKEN_ADDRESS,
        data: balanceCallData
      });
      
      const userBalance = BigInt(rawBalanceResult);
      const requiredAmount = ethers.parseEther(tokenTotalFeeAmount);
      const formattedBalance = ethers.formatEther(userBalance);
      
      console.log('Balance check:', {
        userBalance: formattedBalance,
        requiredAmount: tokenTotalFeeAmount,
        hasSufficientBalance: userBalance >= requiredAmount
      });
      
      if (userBalance < requiredAmount) {
        const deficit = parseFloat(tokenTotalFeeAmount) - parseFloat(formattedBalance);
        
        setBridgeStatus(`❌ INSUFFICIENT BALANCE WARNING ❌

Current balance: ${parseFloat(formattedBalance).toFixed(4)} ANIME
Required amount: ${tokenTotalFeeAmount} ANIME
Deficit: ${deficit.toFixed(4)} ANIME

This transaction will likely fail.`);
        
        if (!window.confirm(
          `⚠️ INSUFFICIENT BALANCE WARNING ⚠️\n\n` +
          `Current balance: ${parseFloat(formattedBalance).toFixed(4)} ANIME\n` +
          `Required amount: ${tokenTotalFeeAmount} ANIME\n` +
          `Deficit: ${deficit.toFixed(4)} ANIME\n\n` +
          `This transaction will likely fail. Do you still want to try?\n` +
          `(Not recommended)`
        )) {
          setIsSending(false);
          return;
        }
      } else {
        setBridgeStatus(prev => `${prev}\n\n✅ Balance is sufficient for this transaction`);
      }

      setBridgeStatus(prev => `${prev}\n\nCreating retryable ticket with parameters:
- L2 Inbox Contract: ${toAddress}
- L3 Target Contract: ${L3ReceiveMessageContractAddress}
- User Input Address: ${userInputAddress}
- L2 Call Value: ${l2CallValue} ETH
- Max Submission Cost: ${maxSubmissionCost} ETH
- Excess Fee Refund Address: ${excessFeeRefundAddress}
- Call Value Refund Address: ${callValueRefundAddress}
- Gas Limit: ${gasLimit}
- Max Fee Per Gas: ${maxFeePerGas} wei
- Token Total Fee Amount: ${tokenTotalFeeAmount} ANIME
- Method: crossChainUpdate(address)`);

      // Create contract instance
      const bridgeContract = new ethers.Contract(L2_TO_L3_CONTRACT, L2_TO_L3_ABI, signer);
      
      // Create calldata for crossChainUpdate method
      const calldata = createCrossChainUpdateCalldata(userInputAddress);
      
      setBridgeStatus(prev => `${prev}\n\nGenerated calldata: ${calldata}`);
      
      // Execute bridge transaction using createRetryableTicket
      const tx = await bridgeContract.createRetryableTicket(
        L3ReceiveMessageContractAddress,                    // to address (L3 contract)
        ethers.parseEther(l2CallValue),                     // l2CallValue
        ethers.parseEther(maxSubmissionCost),               // maxSubmissionCost
        excessFeeRefundAddress,                             // excessFeeRefundAddress
        callValueRefundAddress,                             // callValueRefundAddress
        gasLimit,                                           // gasLimit
        maxFeePerGas,                                       // maxFeePerGas
        ethers.parseEther(tokenTotalFeeAmount),             // tokenTotalFeeAmount
        calldata                                            // data
      );
      
      setBridgeStatus(prev => `${prev}\n\nRetryable ticket transaction submitted: ${tx.hash}`);
      console.log('L2L3Test: Transaction submitted:', tx.hash);
      
      // Wait for confirmation
      const receipt = await tx.wait();
      console.log('L2L3Test: Transaction confirmed:', receipt);
      
      setBridgeStatus(prev => `${prev}\n\n✅ Retryable ticket created successfully!
Transaction Hash: ${tx.hash}
Block: ${receipt.blockNumber}
L2 Inbox Contract: ${toAddress}
L3 Contract: ${L3ReceiveMessageContractAddress}
Method: crossChainUpdate(${userInputAddress})
ETH Amount: ${l2CallValue} ETH
Token Fee: ${tokenTotalFeeAmount} ANIME
Calldata: ${calldata}

The crossChainUpdate method will be called on AnimeChain soon.`);
      
      toast.success('L2→L3 retryable ticket created successfully!');
      
    } catch (error: any) {
      console.error('L2L3Test: Error in handleSendMessage:', error);
      
      // Enhanced error debugging
      const errorInfo = {
        error: error.message,
        code: error.code,
        reason: error.reason || "Unknown reason",
        transaction: {
          to: toAddress,
          l2CallValue: l2CallValue,
          tokenTotalFeeAmount: tokenTotalFeeAmount,
          tokenAddress: ANIME_TOKEN_ADDRESS,
          bridgeAddress: L2_TO_L3_CONTRACT
        }
      };
      
      // Provide more specific guidance based on error codes
      if (error.code === 'UNPREDICTABLE_GAS_LIMIT') {
        errorInfo.reason = "The transaction cannot be simulated. This usually happens with insufficient token balance.";
      } else if (error.code === 'INSUFFICIENT_FUNDS') {
        errorInfo.reason = "You don't have enough ETH to pay for transaction gas fees.";
      } else if (error.code === 'CALL_EXCEPTION') {
        errorInfo.reason = "The transaction was reverted by the contract. Check your token balance and approvals.";
      }
      
      setBridgeStatus(prev => `${prev}\n\n❌ Error creating retryable ticket: ${error.message || String(error)}\n\nDebug Info: ${JSON.stringify(errorInfo, null, 2)}`);
      toast.error('Failed to create L2→L3 retryable ticket');
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="main-container">
      <div className="bridge-container">
        <h2>L2→L3 Test</h2>
        <p className="description">
          Test L2 to L3 retryable ticket creation functionality. This creates a retryable ticket that calls <strong>crossChainUpdate(address)</strong> on the L3ReceiveMessage contract. This page automatically switches to <strong>Arbitrum Mainnet</strong> for optimal testing.
        </p>

        {isConnected && walletAddress && (
          <div className="wallet-alias-section">
            <h4>🔗 Connected Wallet & L3 Alias</h4>
            <div className="wallet-grid">
              <div>
                <strong>L2 Address (Your Wallet):</strong>
                <div className="wallet-address-display">
                  {walletAddress}
                </div>
              </div>
              <div>
                <strong>L3 Alias (How L3 sees you):</strong>
                <div className="wallet-alias-display">
                  {calculateL2ToL3Alias(walletAddress)}
                </div>
              </div>
            </div>
            <div className="wallet-info-note">
              <strong>💡 Aliasing Info:</strong> Your L2 address gets "aliased" on L3 by adding <code>0x1111000000000000000000000000000000001111</code>. This prevents cross-chain exploits by ensuring contracts can distinguish between parent-chain and child-chain calls.
            </div>
          </div>
        )}

        {!isConnected && (
          <div className="wallet-connection-prompt">
            <strong>⚠️ Connect your wallet to see your L3 alias address</strong>
          </div>
        )}
        
        <div className="l2-to-l3-message-sender">
          <div className="contract-info">
            <h4>L2→L3 Retryable Ticket Creator</h4>
            <p className="contract-address">
              Contract: <code>{L2_TO_L3_CONTRACT}</code>
            </p>
            <p className="network-requirement">
              Network: Arbitrum One (L2) - Mainnet
            </p>
            {isConnected && walletAddress && (
              <>
                <p className="wallet-info">
                  Connected Wallet: <code>{walletAddress}</code>
                </p>
                <p className="wallet-alias">
                  Connected Wallet L3 Alias: <code>{calculateL2ToL3Alias(walletAddress)}</code>
                </p>
              </>
            )}
          </div>

          <div className="sender-controls">
            <div className="approval-section">
              <h5>Step 1: Approve ANIME Tokens</h5>
              <p className="info-text">
                Approve this contract to spend your ANIME tokens for L3 gas fees
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
              <h5>Step 2: Create Retryable Ticket</h5>
              
              <div className="calldata-subform">
                <h6>Cross-Chain Message Details</h6>
                <div className="calldata-info compact">
                  <div className="form-row compact">
                    <label>L3 Target Contract:</label>
                    <input
                      type="text"
                      value={L3ReceiveMessageContractAddress}
                      readOnly
                      className="readonly-input"
                    />
                    <small>L3ReceiveMessage contract where the message will be delivered</small>
                  </div>
                  
                  <div className="form-row compact">
                    <label>Function to Call:</label>
                    <input
                      type="text"
                      value="crossChainUpdate(address)"
                      readOnly
                      className="readonly-input"
                    />
                    <small>Method signature that will be called on L3</small>
                  </div>
                  
                  <div className="form-row compact">
                    <label>Function Parameter (address):</label>
                    <input
                      type="text"
                      value={userInputAddress}
                      onChange={(e) => setUserInputAddress(e.target.value)}
                      placeholder="Address parameter for crossChainUpdate method"
                      className="address-input"
                    />
                    <small>Address parameter to pass to crossChainUpdate method (usually your wallet address)</small>
                  </div>
                  
                  {userInputAddress && ethers.isAddress(userInputAddress) && (
                    <div className="calldata-preview">
                      <h6>Generated Calldata (Byte Encoding)</h6>
                      <div className="calldata-breakdown">
                        <div className="calldata-part">
                          <label>Function Selector:</label>
                          <code>{ethers.keccak256(ethers.toUtf8Bytes("crossChainUpdate(address)")).slice(0, 10)}</code>
                          <small>First 4 bytes of keccak256("crossChainUpdate(address)")</small>
                        </div>
                        <div className="calldata-part">
                          <label>Address Parameter (bytes32):</label>
                          <code>{ethers.zeroPadValue(userInputAddress, 32)}</code>
                          <small>Address padded to 32 bytes</small>
                        </div>
                        <div className="calldata-part">
                          <label>Complete Calldata:</label>
                          <code>{createCrossChainUpdateCalldata(userInputAddress)}</code>
                          <small>Function selector + parameters concatenated</small>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="form-grid compact">
                <div className="form-row compact">
                  <label>L2 Inbox Contract (Pre-populated, Editable):</label>
                  <input
                    type="text"
                    value={toAddress}
                    onChange={(e) => setToAddress(e.target.value)}
                    placeholder="L2 Inbox contract address"
                    className="address-input"
                  />
                  <small>L2 Inbox contract that will create the retryable ticket</small>
                </div>

                <div className="form-row compact">
                  <label>L2 Call Value (ETH):</label>
                  <input
                    type="text"
                    value={l2CallValue}
                    onChange={(e) => setL2CallValue(e.target.value)}
                    placeholder="1"
                  />
                  <small>Amount of ETH to send to your L3 wallet</small>
                </div>

                <div className="form-row compact">
                  <label>Max Submission Cost (ETH):</label>
                  <input
                    type="text"
                    value={maxSubmissionCost}
                    onChange={(e) => setMaxSubmissionCost(e.target.value)}
                    placeholder="0.0006"
                  />
                  <small>Cost to submit retryable ticket (~0.0006 ETH current estimate)</small>
                </div>

                <div className="form-row compact">
                  <label>Excess Fee Refund Address:</label>
                  <input
                    type="text"
                    value={excessFeeRefundAddress}
                    onChange={(e) => setExcessFeeRefundAddress(e.target.value)}
                    placeholder="Address to refund excess fees"
                    className="address-input"
                  />
                  <small>Address to receive refund of excess fees (usually your wallet)</small>
                </div>

                <div className="form-row compact">
                  <label>Call Value Refund Address:</label>
                  <input
                    type="text"
                    value={callValueRefundAddress}
                    onChange={(e) => setCallValueRefundAddress(e.target.value)}
                    placeholder="Address to refund call value"
                    className="address-input"
                  />
                  <small>Address to receive refund of call value on failure (usually your wallet)</small>
                </div>

                <div className="form-row compact">
                  <label>Gas Limit:</label>
                  <input
                    type="text"
                    value={gasLimit}
                    onChange={(e) => setGasLimit(e.target.value)}
                    placeholder="300000"
                  />
                  <small>Gas limit for L3 execution (300,000 is typical)</small>
                </div>

                <div className="form-row compact">
                  <label>Max Fee Per Gas (wei):</label>
                  <input
                    type="text"
                    value={maxFeePerGas}
                    onChange={(e) => setMaxFeePerGas(e.target.value)}
                    placeholder="36000000"
                  />
                  <small>Max fee per gas for L3 execution (36M wei = 0.036 gwei)</small>
                </div>

                <div className="form-row compact">
                  <label>Token Total Fee Amount (ANIME):</label>
                  <input
                    type="text"
                    value={tokenTotalFeeAmount}
                    onChange={(e) => setTokenTotalFeeAmount(e.target.value)}
                    placeholder="1.0007"
                  />
                  <small>Total ANIME tokens to pay for fees (L2 Call Value + Protocol Fees)</small>
                </div>
              </div>

              <button 
                onClick={handleSendMessage}
                disabled={!isConnected || isSending || !toAddress || !userInputAddress || !excessFeeRefundAddress || !callValueRefundAddress}
                className="send-button"
              >
                {isSending ? 'Creating Retryable Ticket...' : 'Create Retryable Ticket'}
              </button>
            </div>

            <div className="raw-data-section">
              <h5>Raw Transaction Data</h5>
              <div className="raw-data">
                <pre>{JSON.stringify({
                  l2InboxContract: L2_TO_L3_CONTRACT,
                  function: 'createRetryableTicket',
                  parameters: {
                    to: L3ReceiveMessageContractAddress + ' (L3ReceiveMessage Contract)',
                    l2CallValue: l2CallValue + ' ETH',
                    maxSubmissionCost: maxSubmissionCost + ' ETH',
                    excessFeeRefundAddress: excessFeeRefundAddress,
                    callValueRefundAddress: callValueRefundAddress,
                    gasLimit: gasLimit,
                    maxFeePerGas: maxFeePerGas + ' wei',
                    tokenTotalFeeAmount: tokenTotalFeeAmount + ' ANIME',
                    data: userInputAddress ? createCrossChainUpdateCalldata(userInputAddress) : '0x'
                  },
                  calldataBreakdown: userInputAddress && ethers.isAddress(userInputAddress) ? {
                    functionSignature: 'crossChainUpdate(address)',
                    functionSelector: ethers.keccak256(ethers.toUtf8Bytes("crossChainUpdate(address)")).slice(0, 10),
                    addressParameter: ethers.zeroPadValue(userInputAddress, 32),
                    completeCalldata: createCrossChainUpdateCalldata(userInputAddress)
                  } : null
                }, null, 2)}</pre>
              </div>
            </div>
          </div>
        </div>

        <div className="status-section">
          <h4>Status</h4>
          <div className="status-display">
            <pre className="status-text">{bridgeStatus}</pre>
          </div>
        </div>
      </div>
    </div>
  );
};

export default L2L3Test; 