export interface NetworkConfig {
  chainId: number;
  name: string;
  rpcUrl: string;
  currency?: string;
}

export interface AppConfig {
  networks: {
    animechain: NetworkConfig;
    dev: NetworkConfig;
    prod: NetworkConfig;
    local: NetworkConfig;
    arbitrum_testnet: NetworkConfig;
    arbitrum_mainnet: NetworkConfig;
  };
  defaultNetwork: 'animechain' | 'dev' | 'prod' | 'local' | 'arbitrum_testnet' | 'arbitrum_mainnet';
  alchemyApiKey: string;
}

// Load environment variables or use defaults
const ALCHEMY_API_KEY = import.meta.env.VITE_ALCHEMY_API_KEY || 'demo';

// Utility function to generate Alchemy URL with API key
const getAlchemyUrl = (network: string) => {
  return `https://eth-${network}.g.alchemy.com/v2/${ALCHEMY_API_KEY}`;
};

const config: AppConfig = {
  networks: {
    animechain: {
      chainId: 69000, // AnimeChain L3
      name: 'AnimeChain',
      rpcUrl: 'https://rpc-animechain-39xf6m45e3.t.conduit.xyz',
      currency: 'anime'
    },
    dev: {
      chainId: 11155111, // Sepolia testnet
      name: 'Sepolia',
      // Public Sepolia endpoints to avoid CORS issues
      rpcUrl: 'https://rpc.sepolia.org',
    },
    prod: {
      chainId: 1, // Ethereum mainnet
      name: 'Ethereum',
      // Public Ethereum endpoints to avoid CORS issues
      rpcUrl: 'https://ethereum.publicnode.com',
    },
    local: {
      chainId: 1337, // Local instance
      name: 'Local',
      rpcUrl: 'http://127.0.0.1:8545',
    },
    arbitrum_testnet: {
      chainId: 421614, // Arbitrum Sepolia
      name: 'Arbitrum Sepolia',
      rpcUrl: 'https://sepolia-rollup.arbitrum.io/rpc',
    },
    arbitrum_mainnet: {
      chainId: 42161, // Arbitrum One
      name: 'Arbitrum One',
      rpcUrl: 'https://arb1.arbitrum.io/rpc',
    },
  },
  defaultNetwork: 'animechain',
  alchemyApiKey: ALCHEMY_API_KEY,
};

export default config; 