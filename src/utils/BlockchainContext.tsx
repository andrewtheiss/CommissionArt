import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import ethersService from './ethers-service';
import { NetworkConfig } from './config';

interface BlockchainContextType {
  isConnected: boolean;
  isLoading: boolean;
  networkType: 'dev' | 'prod' | 'local';
  network: NetworkConfig;
  switchNetwork: (network: 'dev' | 'prod' | 'local') => void;
  connectWallet: () => Promise<void>;
  walletAddress: string | null;
}

const BlockchainContext = createContext<BlockchainContextType | undefined>(undefined);

export const BlockchainProvider = ({ children }: { children: ReactNode }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [networkType, setNetworkType] = useState<'dev' | 'prod' | 'local'>('dev');
  const [network, setNetwork] = useState<NetworkConfig>(ethersService.getNetwork());
  const [walletAddress, setWalletAddress] = useState<string | null>(null);

  useEffect(() => {
    // Check connection status on mount
    const checkConnection = async () => {
      const connected = await ethersService.isConnected();
      setIsConnected(connected);
      setIsLoading(false);
    };
    
    checkConnection();
  }, []);

  const switchNetwork = (newNetworkType: 'dev' | 'prod' | 'local') => {
    const newNetwork = ethersService.switchNetwork(newNetworkType);
    setNetworkType(newNetworkType);
    setNetwork(newNetwork);
    
    // Check connection after switching
    ethersService.isConnected().then(connected => {
      setIsConnected(connected);
    });
  };

  const connectWallet = async () => {
    try {
      const signer = await ethersService.getSigner();
      if (signer) {
        const address = await signer.getAddress();
        setWalletAddress(address);
        return;
      }
      throw new Error('No wallet connected');
    } catch (error) {
      console.error('Failed to connect wallet:', error);
      setWalletAddress(null);
    }
  };

  const value = {
    isConnected,
    isLoading,
    networkType,
    network,
    switchNetwork,
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