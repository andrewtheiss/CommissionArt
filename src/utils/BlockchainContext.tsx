import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import ethersService from './ethers-service';
import profileService from './profile-service';
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
  switchNetwork: (network: NetworkType) => Promise<void>;
  switchToLayer: (layer: 'l1' | 'l2' | 'l3', environment: 'testnet' | 'mainnet') => Promise<void>;
  connectWallet: () => Promise<void>;
  walletAddress: string | null;
  provider: ethers.BrowserProvider | null;
  hasProfile: boolean;
  checkUserProfile: () => Promise<void>;
}

const BlockchainContext = createContext<BlockchainContextType | undefined>(undefined);

export const BlockchainProvider = ({ children }: { children: ReactNode }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [networkType, setNetworkType] = useState<NetworkType>(config.defaultNetwork as NetworkType);
  const [network, setNetwork] = useState<NetworkConfig>(ethersService.getNetwork());
  const [walletAddress, setWalletAddress] = useState<string | null>(null);
  const [provider, setProvider] = useState<ethers.BrowserProvider | null>(null);
  const [hasProfile, setHasProfile] = useState<boolean>(false);

  useEffect(() => {
    const init = async () => {
      const browserProvider = ethersService.getBrowserProvider();
      if (browserProvider) {
        setProvider(browserProvider);
        const accounts = await browserProvider.listAccounts();
        if (accounts.length > 0) {
          const signer = await browserProvider.getSigner();
          const address = await signer.getAddress();
          setWalletAddress(address);
          setIsConnected(true);
          await checkUserProfile(address, browserProvider);
        }
      }
      setIsLoading(false);
    };
    init();
  }, []);

  const checkUserProfile = async (address?: string, p?: ethers.BrowserProvider) => {
    const checkAddress = address || walletAddress;
    const checkProvider = p || provider;
    if (!checkAddress || !checkProvider) {
      setHasProfile(false);
      return;
    }
    
    try {
      // Use the profile service to check if user has a profile
      const profileExists = await profileService.hasProfile();
      setHasProfile(profileExists);
      console.log(`Profile check for ${checkAddress}: ${profileExists ? 'Found' : 'Not found'}`);
    } catch (error) {
      console.error("Error checking profile:", error);
      setHasProfile(false);
    }
  };

  const switchNetwork = async (newNetworkType: NetworkType) => {
    try {
      console.log(`[BlockchainContext] Starting switch to network: ${newNetworkType}`);
      
      // Switch the network in ethersService and request wallet network switch
      const newNetwork = ethersService.switchNetwork(newNetworkType);
      console.log(`[BlockchainContext] EthersService switched, now requesting wallet switch...`);
      
      // Request wallet to switch networks (this is async)
      const switchSuccess = await ethersService.requestWalletNetworkSwitch(newNetworkType);
      console.log(`[BlockchainContext] Wallet switch result: ${switchSuccess}`);
      
      if (switchSuccess) {
        setNetworkType(newNetworkType);
        setNetwork(newNetwork);
        
        // Check connection after switching
        const connected = await ethersService.isConnected();
        setIsConnected(connected);
        
        console.log(`[BlockchainContext] Successfully switched to network: ${newNetworkType}`);
      } else {
        throw new Error(`Failed to switch to network: ${newNetworkType}`);
      }
    } catch (error) {
      console.error('[BlockchainContext] Error switching network:', error);
      throw error; // Re-throw so the caller can handle it
    }
  };

  const switchToLayer = async (layer: 'l1' | 'l2' | 'l3', environment: 'testnet' | 'mainnet') => {
    const targetNetwork = mapLayerToNetwork(layer, environment);
    console.log(`Switching to layer ${layer} (${environment}) => network ${targetNetwork}`);
    await switchNetwork(targetNetwork);
  };

  const connectWallet = async () => {
    try {
      const browserProvider = ethersService.getBrowserProvider();
      if (!browserProvider) {
        throw new Error("No browser wallet detected.");
      }
      setProvider(browserProvider);
      await browserProvider.send("eth_requestAccounts", []);
      const signer = await browserProvider.getSigner();
      const address = await signer.getAddress();
      setWalletAddress(address);
      setIsConnected(true);
      await checkUserProfile(address, browserProvider);
    } catch (error) {
      console.error('Failed to connect wallet:', error);
      setWalletAddress(null);
      setIsConnected(false);
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
    walletAddress,
    hasProfile,
    checkUserProfile,
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