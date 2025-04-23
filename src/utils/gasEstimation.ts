// gasEstimator.ts
import { NodeInterface__factory } from '@arbitrum/sdk/dist/lib/abi/factories/NodeInterface__factory';
import { NODE_INTERFACE_ADDRESS } from '@arbitrum/sdk/dist/lib/dataEntities/constants';

export async function estimateGasForChain(
  chainId: number,
  provider: ,
  transactionDetails: any,
  nodeInterfaceAddress?: string
): Promise<string> {
  if (chainId === 1 || chainId === 11155111) { // Ethereum mainnet or Sepolia
    return await provider.estimateGas(transactionDetails);
  } else if (chainId === 42161 || chainId === 421614) { // Arbitrum One or Sepolia
    const nodeInterface = NodeInterface__factory.connect(NODE_INTERFACE_ADDRESS, provider);
    const gasEstimateComponents = await nodeInterface.callStatic.gasEstimateComponents(
      transactionDetails.to,
      false,
      transactionDetails.data,
      { blockTag: 'latest' }
    );
    return gasEstimateComponents.gasEstimate.toString();
  } else if (chainId === 421613) { // Example Orbit chain ID
    const orbitNodeInterface = NodeInterface__factory.connect(nodeInterfaceAddress || '', provider);
    const gasEstimateComponents = await orbitNodeInterface.callStatic.gasEstimateComponents(
      transactionDetails.to,
      false,
      transactionDetails.data,
      { blockTag: 'latest' }
    );
    return gasEstimateComponents.gasEstimate.toString();
  } else {
    throw new Error(`Unsupported chain ID: ${chainId}`);
  }
}

export async function estimateTotalGasForMultiChain(
  l1Provider: 
  l2Provider: 
  l3Provider: 
  l1ToL2Transaction: any,
  l2ToL3Transaction: any
): Promise<string> {
  const l1GasEstimate = await estimateGasForChain(1, l1Provider, l1ToL2Transaction);
  const l1GasCost = utils.parseUnits(l1GasEstimate, 'wei').mul(await l1Provider.getGasPrice());

  const l2GasEstimate = await estimateGasForChain(42161, l2Provider, l2ToL3Transaction);
  const l2GasCost = utils.parseUnits(l2GasEstimate, 'wei').mul(await l2Provider.getGasPrice());

  const l1NodeInterface = NodeInterface__factory.connect(NODE_INTERFACE_ADDRESS, l1Provider);
  const l1GasComponents = await l1NodeInterface.callStatic.gasEstimateComponents(
    l1ToL2Transaction.to,
    false,
    l1ToL2Transaction.data,
    { blockTag: 'latest' }
  );
  const maxSubmissionCost = l1GasComponents.gasEstimateForL1.mul(l1GasComponents.l1BaseFeeEstimate);

  const totalEthNeeded = l1GasCost.add(maxSubmissionCost).add(l2GasCost);
  return utils.formatEther(totalEthNeeded);
}