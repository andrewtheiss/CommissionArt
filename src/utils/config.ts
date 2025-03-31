export interface NetworkConfig {
  chainId: number;
  name: string;
  rpcUrl: string;
}

export interface AppConfig {
  networks: {
    dev: NetworkConfig;
    prod: NetworkConfig;
    local: NetworkConfig;
  };
  defaultNetwork: 'dev' | 'prod' | 'local';
}

const config: AppConfig = {
  networks: {
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
  defaultNetwork: 'dev',
};

export default config; 