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
  artCommissionHub: ContractInfo;
  artPiece: ContractInfo;
  profileTemplate: ContractInfo;
  profileFactoryAndRegistry: ContractInfo;
  profileSocialTemplate: ContractInfo;
  artEdition1155Template: ContractInfo;
  artSales1155Template: ContractInfo;
}

interface ContractConfig {
  networks: {
    testnet: NetworkContracts;
    mainnet: Partial<NetworkContracts>; // mainnet might not have all contracts
  };
  lastUpdated: string;
}

export type ContractType = keyof NetworkContracts;

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
    networkType === 'dev' || networkType === 'arbitrum_testnet' || networkType === 'animechain' ? 'testnet' :
    networkType === 'prod' || networkType === 'arbitrum_mainnet' ? 'mainnet' : 'testnet';

  // Determine layer based on network type
  const layer =
    networkType === 'dev' || networkType === 'prod' ? 'l1' :
    networkType === 'arbitrum_testnet' || networkType === 'arbitrum_mainnet' ? 'l2' : 'l3';

  // Simulate loading on mount and networkType change
  useEffect(() => {
    setLoading(true);
    // Since config is statically imported, loading is instantaneous
    // We keep the loading state for consistency with async patterns
    setLoading(false);
  }, [networkType]);

  // Get current contract address based on active environment and layer
  const getCurrentContract = useCallback((): ContractInfo | undefined => {
    const layerKey = layer as ContractType;
    return config.networks[environment][layerKey];
  }, [config, environment, layer]);

  // Get specific contract by environment and contract type
  const getContract = useCallback((env: 'testnet' | 'mainnet', contractType: ContractType): ContractInfo | undefined => {
    return config.networks[env][contractType];
  }, [config]);

  // Get contract address by type for current environment
  const getContractAddress = useCallback((contractType: ContractType): string | undefined => {
    const contract = config.networks[environment][contractType];
    return contract?.address;
  }, [config, environment]);

  // Get all contracts for current environment
  const getAllContracts = useCallback((): Partial<NetworkContracts> => {
    return config.networks[environment];
  }, [config, environment]);

  return {
    loading,
    config,
    environment,
    layer,
    getCurrentContract,
    getContract,
    getContractAddress,
    getAllContracts,
  };
}

export default useContractConfig;