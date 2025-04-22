import { useState, useEffect, useCallback } from 'react';
import { useBlockchain } from './BlockchainContext';
import contractConfigJson from '../assets/contract_config.json';

// Define the contract config structure
interface ContractInfo {
  address: string;
  contract: string;
}

interface NetworkContracts {
  l1: ContractInfo;
  l2: ContractInfo;
  l3: ContractInfo;
}

interface ContractConfig {
  networks: {
    testnet: NetworkContracts;
    mainnet: NetworkContracts;
  };
  lastUpdated: string;
}

/**
 * Hook to access contract configuration
 * @returns Contract configuration based on current network
 */
export function useContractConfig() {
  const { networkType } = useBlockchain();
  const [config] = useState<ContractConfig>(contractConfigJson);
  const [loading, setLoading] = useState(true);

  // Determine environment (testnet/mainnet) based on network type
  const environment =
    networkType === 'dev' || networkType === 'arbitrum_testnet' ? 'testnet' :
    networkType === 'prod' || networkType === 'arbitrum_mainnet' ? 'mainnet' : 'testnet';

  // Determine layer based on network type
  const layer =
    networkType === 'dev' || networkType === 'prod' ? 'l1' :
    networkType === 'arbitrum_testnet' || networkType === 'arbitrum_mainnet' ? 'l2' : 'l1';

  // Simulate loading on mount and networkType change
  useEffect(() => {
    setLoading(true);
    // Since config is statically imported, loading is instantaneous
    // We keep the loading state for consistency with async patterns
    setLoading(false);
  }, [networkType]);

  // Get current contract address based on active environment and layer
  const getCurrentContract = useCallback((): ContractInfo => {
    return config.networks[environment][layer];
  }, [config, environment, layer]);

  // Get specific contract by environment and layer
  const getContract = useCallback((env: 'testnet' | 'mainnet', l: 'l1' | 'l2' | 'l3'): ContractInfo => {
    return config.networks[env][l];
  }, [config]);

  return {
    loading,
    config,
    environment,
    layer,
    getCurrentContract,
    getContract,
  };
}

export default useContractConfig;