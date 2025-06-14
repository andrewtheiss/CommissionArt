// gasEstimator.ts
import { NodeInterface__factory } from '@arbitrum/sdk/dist/lib/abi/factories/NodeInterface__factory';
import { NODE_INTERFACE_ADDRESS } from '@arbitrum/sdk/dist/lib/dataEntities/constants';
import { formatEther } from 'ethers';
import { Provider } from '@ethersproject/providers';

export async function estimateGasForChain(
  chainId: number,
  provider: Provider,
  transactionDetails: any,
  nodeInterfaceAddress?: string
): Promise<bigint> {
  if (chainId === 1 || chainId === 11155111) { // Ethereum mainnet or Sepolia
    const gasEstimate = await provider.estimateGas(transactionDetails);
    return BigInt(gasEstimate.toString());
  } else if (chainId === 42161 || chainId === 421614) { // Arbitrum One or Sepolia
    const nodeInterface = NodeInterface__factory.connect(NODE_INTERFACE_ADDRESS, provider);
    const gasEstimateComponents = await nodeInterface.callStatic.gasEstimateComponents(
      transactionDetails.to,
      false,
      transactionDetails.data,
      { blockTag: 'latest' }
    );
    return BigInt(gasEstimateComponents.gasEstimate.toString());
  } else if (chainId === 421613) { // Example Orbit chain ID
    const orbitNodeInterface = NodeInterface__factory.connect(nodeInterfaceAddress || '', provider);
    const gasEstimateComponents = await orbitNodeInterface.callStatic.gasEstimateComponents(
      transactionDetails.to,
      false,
      transactionDetails.data,
      { blockTag: 'latest' }
    );
    return BigInt(gasEstimateComponents.gasEstimate.toString());
  } else {
    throw new Error(`Unsupported chain ID: ${chainId}`);
  }
}

export async function estimateTotalGasForMultiChain(
  l1Provider: Provider,
  l2Provider: Provider,
  l3Provider: Provider,
  l1ToL2Transaction: any,
  l2ToL3Transaction: any
): Promise<string> {
  const l1GasEstimate = await estimateGasForChain(1, l1Provider, l1ToL2Transaction);
  const l1GasPrice = await l1Provider.getFeeData();
  const l1GasCost = l1GasEstimate * BigInt(l1GasPrice.gasPrice?.toString() || '0');

  const l2GasEstimate = await estimateGasForChain(42161, l2Provider, l2ToL3Transaction);
  const l2GasPrice = await l2Provider.getFeeData();
  const l2GasCost = l2GasEstimate * BigInt(l2GasPrice.gasPrice?.toString() || '0');

  const l1NodeInterface = NodeInterface__factory.connect(NODE_INTERFACE_ADDRESS, l1Provider);
  const l1GasComponents = await l1NodeInterface.callStatic.gasEstimateComponents(
    l1ToL2Transaction.to,
    false,
    l1ToL2Transaction.data,
    { blockTag: 'latest' }
  );
  const maxSubmissionCost = BigInt(l1GasComponents.gasEstimateForL1.toString()) * BigInt(l1GasComponents.l1BaseFeeEstimate.toString());

  const totalEthNeeded = l1GasCost + maxSubmissionCost + l2GasCost;
  return formatEther(totalEthNeeded);
}