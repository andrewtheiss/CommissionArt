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

// Default config to use as fallback
const DEFAULT_CONFIG: ContractConfig = {
  networks: {
    testnet: {
      l1: {
        address: "0x7312002419fd59829C0502d86bCc5fF31A0A973f",
        contract: "L1QueryOwner"
      },
      l2: {
        address: "0x81ED70eC160a03E508ef12aED22b258c1a6Eb25D", 
        contract: "L2Relay"
      },
      l3: {
        address: "0x275BB76Ffd0Be5276bca1F6C94e763E271aAC557",
        contract: "OwnerRegistry"
      }
    },
    mainnet: {
      l1: {
        address: "",
        contract: "L1QueryOwner"
      },
      l2: {
        address: "",
        contract: "L2Relay"
      },
      l3: {
        address: "",
        contract: "OwnerRegistry"
      }
    }
  },
  lastUpdated: new Date().toISOString()
};

/**
 * Validates the configuration object to ensure it has all required fields
 * @param config Configuration object to validate
 * @returns Fixed configuration with defaults for missing fields
 */
const validateConfig = (config: any): ContractConfig => {
  if (!config || typeof config !== 'object') {
    console.warn('Invalid config format, using defaults');
    return DEFAULT_CONFIG;
  }

  // Ensure networks object exists
  if (!config.networks || typeof config.networks !== 'object') {
    console.warn('Missing networks in config, using defaults');
    return DEFAULT_CONFIG;
  }

  // Validate each network
  const networks = ['testnet', 'mainnet'];
  const layers = ['l1', 'l2', 'l3'];
  
  for (const network of networks) {
    if (!config.networks[network] || typeof config.networks[network] !== 'object') {
      console.warn(`Missing ${network} network in config, using defaults`);
      return DEFAULT_CONFIG;
    }
    
    for (const layer of layers) {
      if (!config.networks[network][layer] || typeof config.networks[network][layer] !== 'object') {
        console.warn(`Missing ${layer} in ${network} network, using defaults`);
        return DEFAULT_CONFIG;
      }
      
      // Ensure ContractInfo fields exist
      if (!config.networks[network][layer].address || 
          typeof config.networks[network][layer].address !== 'string' ||
          !config.networks[network][layer].contract || 
          typeof config.networks[network][layer].contract !== 'string') {
        console.warn(`Invalid contract info for ${layer} in ${network}, using defaults`);
        return DEFAULT_CONFIG;
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
      
      // Use the imported JSON directly instead of fetching
      console.log('Loading contract config from imported file');
      
      // Validate the config and ensure it has all required fields
      const validatedConfig = validateConfig(contractConfigJson);
      setConfig(validatedConfig);
      
      console.log('Loaded and validated contract config');
      setError(null);
    } catch (err) {
      console.error('Error loading contract configuration:', err);
      setError(err instanceof Error ? err : new Error(String(err)));
      
      // Use default config as fallback
      setConfig(DEFAULT_CONFIG);
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
      // Return default if there's an error
      return DEFAULT_CONFIG.networks[environment][layer];
    }
  };
  
  // Get specific contract by environment and layer
  const getContract = (env: 'testnet' | 'mainnet', l: 'l1' | 'l2' | 'l3'): ContractInfo | undefined => {
    if (!config) return undefined;
    try {
      return config.networks[env][l];
    } catch (err) {
      console.error(`Error getting contract for ${env} ${l}:`, err);
      // Return default if there's an error
      return DEFAULT_CONFIG.networks[env][l];
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