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
 * Validates the configuration object to ensure it has all required fields
 * @param config Configuration object to validate
 * @returns Validated configuration or throws an error
 */
const validateConfig = (config: any): ContractConfig => {
  // Check if config exists and is an object
  if (!config || typeof config !== 'object') {
    throw new Error('Invalid contract configuration format');
  }

  // Ensure networks object exists
  if (!config.networks || typeof config.networks !== 'object') {
    throw new Error('Missing networks in contract configuration');
  }

  // Validate each network
  const networks = ['testnet', 'mainnet'];
  const layers = ['l1', 'l2', 'l3'];
  
  for (const network of networks) {
    if (!config.networks[network] || typeof config.networks[network] !== 'object') {
      throw new Error(`Missing ${network} network in contract configuration`);
    }
    
    for (const layer of layers) {
      if (!config.networks[network][layer] || typeof config.networks[network][layer] !== 'object') {
        throw new Error(`Missing ${layer} in ${network} network configuration`);
      }
      
      // Ensure ContractInfo fields exist - allow empty strings for both address and contract
      if (typeof config.networks[network][layer].address !== 'string' ||
          typeof config.networks[network][layer].contract !== 'string') {
        throw new Error(`Invalid contract info for ${layer} in ${network} configuration`);
      }
    }
  }
  
  return config as ContractConfig;
};

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
      
      // Use the imported JSON directly
      console.log('Loading contract config from contract_config.json');
      
      // Validate the config and ensure it has all required fields
      const validatedConfig = validateConfig(contractConfigJson);
      setConfig(validatedConfig);
      
      console.log('Loaded and validated contract config');
      setError(null);
    } catch (err) {
      console.error('Error loading contract configuration:', err);
      setError(err instanceof Error ? err : new Error(String(err)));
      setConfig(null);
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