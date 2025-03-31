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
  };
  defaultNetwork: 'animechain' | 'dev' | 'prod' | 'local';
}

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
      rpcUrl: 'https://eth-sepolia.g.alchemy.com/v2/demo',
    },
    prod: {
      chainId: 1, // Ethereum mainnet
      name: 'Ethereum',
      rpcUrl: 'https://eth-mainnet.g.alchemy.com/v2/demo',
    },
    local: {
      chainId: 1337, // Local instance
      name: 'Local',
      rpcUrl: 'http://127.0.0.1:8545',
    },
  },
  defaultNetwork: 'animechain',
};

export default config; 