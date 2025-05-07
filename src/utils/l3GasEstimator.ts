import { ethers } from 'ethers';

// Default L3 RPC URL - AnimeChain Mainnet
const L3_RPC_URL = 'https://rpc-animechain-39xf6m45e3.t.conduit.xyz';

// Interface for gas estimates
export interface L3GasEstimates {
  maxSubmissionCost: string;
  gasLimit: string;
  maxFeePerGas: string;
  baseFee: string;
  l3GasPrice: string;
  totalCost: string;
}

/**
 * Estimates gas parameters for L3 transactions
 * @param nftContract NFT contract address
 * @param tokenId NFT token ID
 * @param ownerAddress Owner address
 * @returns Gas estimates for L3
 */
export async function estimateL3Gas(
  nftContract: string,
  tokenId: string,
  ownerAddress: string
): Promise<L3GasEstimates> {
  try {
    // Connect to L3 mainnet
    const provider = new ethers.JsonRpcProvider(L3_RPC_URL);
    
    // Get current gas price on L3
    const feeData = await provider.getFeeData();
    const l3GasPrice = feeData.gasPrice || ethers.parseUnits('0.1', 'gwei');
    const baseFee = feeData.maxFeePerGas || ethers.parseUnits('0.1', 'gwei');
    
    // Calculate gas parameters for L3
    // These are conservative estimates for a cross-chain message
    const gasLimit = ethers.parseUnits('1000000', 'wei'); // 1M gas units
    const maxFeePerGas = l3GasPrice * BigInt(2); // 2x current gas price
    
    // Calculate max submission cost (this is a conservative estimate)
    // For L3, submission costs are typically lower than L2, but we're being conservative
    const maxSubmissionCost = ethers.parseUnits('0.0001', 'ether'); // 0.0001 ETH
    
    // Calculate total estimated cost
    const totalCost = (gasLimit * maxFeePerGas) / BigInt(1e9) + maxSubmissionCost;
    
    return {
      maxSubmissionCost: maxSubmissionCost.toString(),
      gasLimit: gasLimit.toString(),
      maxFeePerGas: maxFeePerGas.toString(),
      baseFee: baseFee.toString(),
      l3GasPrice: l3GasPrice.toString(),
      totalCost: totalCost.toString()
    };
  } catch (error) {
    console.error('Error estimating L3 gas:', error);
    
    // Return fallback values if estimation fails
    return {
      maxSubmissionCost: ethers.parseUnits('0.0001', 'ether').toString(),
      gasLimit: ethers.parseUnits('1000000', 'wei').toString(),
      maxFeePerGas: ethers.parseUnits('0.2', 'gwei').toString(),
      baseFee: ethers.parseUnits('0.1', 'gwei').toString(),
      l3GasPrice: ethers.parseUnits('0.1', 'gwei').toString(),
      totalCost: ethers.parseUnits('0.0003', 'ether').toString()
    };
  }
}

/**
 * Format wei value to a human-readable ETH string
 * @param wei Wei value as string
 * @returns Formatted ETH value
 */
export function formatWeiToEth(wei: string): string {
  try {
    const weiValue = BigInt(wei);
    const ethValue = ethers.formatEther(weiValue);
    
    // Format to max 6 decimal places
    const parts = ethValue.split('.');
    if (parts.length === 2 && parts[1].length > 6) {
      return `${parts[0]}.${parts[1].substring(0, 6)}`;
    }
    
    return ethValue;
  } catch (error) {
    console.error('Error formatting wei to ETH:', error);
    return '0';
  }
}

/**
 * Format wei value to a human-readable Gwei string
 * @param wei Wei value as string
 * @returns Formatted Gwei value
 */
export function formatWeiToGwei(wei: string): string {
  try {
    const weiValue = BigInt(wei);
    const gweiValue = ethers.formatUnits(weiValue, 'gwei');
    
    // Format to max 2 decimal places
    const parts = gweiValue.split('.');
    if (parts.length === 2 && parts[1].length > 2) {
      return `${parts[0]}.${parts[1].substring(0, 2)}`;
    }
    
    return gweiValue;
  } catch (error) {
    console.error('Error formatting wei to Gwei:', error);
    return '0';
  }
} 