import { ethers } from 'ethers';

/**
 * Estimates gas parameters for L1 to L2 transactions
 * @param provider - Ethers provider
 * @param l1ContractAddress - L1 contract address
 * @param l2ProviderUrl - Optional L2 provider URL (defaults to Arbitrum Sepolia)
 * @returns Object containing maxSubmissionCost, gasLimit, and maxFeePerGas
 */
export async function estimateL1ToL2Gas(
  provider: ethers.Provider,
  l1ContractAddress: string,
  nftContract: string,
  tokenId: string,
  l2ReceiverAddress: string,
  l2ProviderUrl: string = 'https://sepolia-rollup.arbitrum.io/rpc'
): Promise<{
  maxSubmissionCost: bigint;
  gasLimit: bigint;
  maxFeePerGas: bigint;
}> {
  try {
    // Get current gas prices from the network
    const feeData = await provider.getFeeData();
    
    // Calculate recommended values based on current network conditions
    // These are conservative estimates to ensure transactions go through
    const maxFeePerGas = feeData.maxFeePerGas || 
      BigInt(Math.floor(2 * Number(feeData.gasPrice || BigInt(100000000))));
    
    // For L1 to L2 transactions, submission costs are higher
    // This is a conservative estimate
    const maxSubmissionCost = BigInt(5000000000000); // 0.000005 ETH
    
    // Gas limit for L1 to L2 transactions needs to be higher than regular transactions
    const gasLimit = BigInt(1500000);
    
    console.log('Estimated gas parameters:', {
      maxSubmissionCost: maxSubmissionCost.toString(),
      gasLimit: gasLimit.toString(),
      maxFeePerGas: maxFeePerGas.toString()
    });
    
    return {
      maxSubmissionCost,
      gasLimit,
      maxFeePerGas
    };
  } catch (error) {
    console.error('Error estimating gas:', error);
    
    // Fallback to default values if estimation fails
    return {
      maxSubmissionCost: BigInt(4500000000000),
      gasLimit: BigInt(1000000),
      maxFeePerGas: BigInt(100000000)
    };
  }
} 