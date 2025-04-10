import { useState, useEffect } from 'react';
import { useBlockchain } from './BlockchainContext';
// Import the contract config directly
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
  const [config, setConfig] = useState<ContractConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  // Determine environment (testnet/mainnet) based on network type
  const environment = 
    networkType === 'dev' || networkType === 'arbitrum_testnet' ? 'testnet' :
    networkType === 'prod' || networkType === 'arbitrum_mainnet' ? 'mainnet' : 'testnet';

  // Determine layer based on network type
  const layer = 
    networkType === 'dev' || networkType === 'prod' ? 'l1' :
    networkType === 'arbitrum_testnet' || networkType === 'arbitrum_mainnet' ? 'l2' : 'l1';

  const loadConfig = async () => {
    try {
      setLoading(true);
      
      // Use the imported JSON directly instead of fetching
      console.log('Loading contract config from imported file');
      setConfig(contractConfigJson as ContractConfig);
      console.log('Loaded contract config:', contractConfigJson);
      setError(null);
    } catch (err) {
      console.error('Error loading contract configuration:', err);
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  };

  // Load config on initial mount
  useEffect(() => {
    loadConfig();
  }, []);
  
  // Reload config when network type changes
  useEffect(() => {
    loadConfig();
  }, [networkType]);

  // Get current contract address based on active environment and layer
  const getCurrentContract = (): ContractInfo | undefined => {
    if (!config) return undefined;
    try {
      return config.networks[environment][layer];
    } catch (err) {
      console.error('Error getting current contract:', err);
      return undefined;
    }
  };
  
  // Get specific contract by environment and layer
  const getContract = (env: 'testnet' | 'mainnet', l: 'l1' | 'l2' | 'l3'): ContractInfo | undefined => {
    if (!config) return undefined;
    try {
      return config.networks[env][l];
    } catch (err) {
      console.error(`Error getting contract for ${env} ${l}:`, err);
      return undefined;
    }
  };
  
  // Method to manually reload config
  const reloadConfig = () => {
    loadConfig();
  };
  
  return {
    loading,
    error,
    config,
    environment,
    layer,
    getCurrentContract,
    getContract,
    reloadConfig
  };
}

export default useContractConfig; 