import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import ethersService from './ethers-service';
import { NetworkConfig } from './config';
import config from './config';
import { ethers } from 'ethers';

type NetworkType = 'animechain' | 'dev' | 'prod' | 'local' | 'arbitrum_testnet' | 'arbitrum_mainnet';

// Map layer and environment to network type
export const mapLayerToNetwork = (layer: 'l1' | 'l2' | 'l3', environment: 'testnet' | 'mainnet'): NetworkType => {
  if (layer === 'l1') {
    return environment === 'testnet' ? 'dev' : 'prod';
  } else if (layer === 'l2') {
    return environment === 'testnet' ? 'arbitrum_testnet' : 'arbitrum_mainnet';
  } else if (layer === 'l3') {
    // L3 is Arbitrum in testnet but AnimeChain in mainnet
    return environment === 'testnet' ? 'arbitrum_testnet' : 'animechain';
  } else {
    return 'animechain';
  }
};

interface BlockchainContextType {
  isConnected: boolean;
  isLoading: boolean;
  networkType: NetworkType;
  network: NetworkConfig;
  switchNetwork: (network: NetworkType) => void;
  switchToLayer: (layer: 'l1' | 'l2' | 'l3', environment: 'testnet' | 'mainnet') => void;
  connectWallet: () => Promise<void>;
  walletAddress: string | null;
}

const BlockchainContext = createContext<BlockchainContextType | undefined>(undefined);

export const BlockchainProvider = ({ children }: { children: ReactNode }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [networkType, setNetworkType] = useState<NetworkType>(config.defaultNetwork as NetworkType);
  const [network, setNetwork] = useState<NetworkConfig>(ethersService.getNetwork());
  const [walletAddress, setWalletAddress] = useState<string | null>(null);
  const [provider, setProvider] = useState<ethers.BrowserProvider | null>(null);

  useEffect(() => {
    // Check connection status on mount
    const checkConnection = async () => {
      const connected = await ethersService.isConnected();
      setIsConnected(connected);
      setIsLoading(false);
    };
    
    checkConnection();
  }, []);

  const switchNetwork = async (newNetworkType: NetworkType) => {
    const newNetwork = ethersService.switchNetwork(newNetworkType);
    setNetworkType(newNetworkType);
    setNetwork(newNetwork);
    
    // Check connection after switching
    ethersService.isConnected().then(connected => {
      setIsConnected(connected);
    });
  };

  const switchToLayer = (layer: 'l1' | 'l2' | 'l3', environment: 'testnet' | 'mainnet') => {
    const targetNetwork = mapLayerToNetwork(layer, environment);
    console.log(`Switching to layer ${layer} (${environment}) => network ${targetNetwork}`);
    switchNetwork(targetNetwork);
  };

  const connectWallet = async () => {
    try {
      const signer = await ethersService.getSigner();
      if (signer) {
        const address = await signer.getAddress();
        setWalletAddress(address);
        setIsConnected(true);
        return;
      }
      throw new Error('No wallet connected');
    } catch (error) {
      console.error('Failed to connect wallet:', error);
      setWalletAddress(null);
    }
  };

  const value = {
    provider,
    isConnected,
    isLoading,
    networkType,
    network,
    switchNetwork,
    switchToLayer,
    connectWallet,
    walletAddress
  };

  return (
    <BlockchainContext.Provider value={value}>
      {children}
    </BlockchainContext.Provider>
  );
};

export const useBlockchain = () => {
  const context = useContext(BlockchainContext);
  if (context === undefined) {
    throw new Error('useBlockchain must be used within a BlockchainProvider');
  }
  return context;
}; 