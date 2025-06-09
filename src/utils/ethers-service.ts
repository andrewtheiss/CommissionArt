import { ethers } from 'ethers';
import config, { NetworkConfig } from './config';

type NetworkType = 'animechain' | 'dev' | 'prod' | 'local' | 'arbitrum_testnet' | 'arbitrum_mainnet';

/**
 * Service for interacting with Ethereum blockchain via ethers.js
 */
class EthersService {
  private provider: ethers.JsonRpcProvider | null = null;
  private network: NetworkConfig;
  private fallbackProviders: {[key in NetworkType]?: string[]} = {
    dev: [
      'https://rpc.sepolia.org',
      'https://eth-sepolia.public.blastapi.io',
      'https://rpc.sepolia.dev',
      'https://ethereum-sepolia-rpc.publicnode.com',
      'https://endpoints.omniatech.io/v1/eth/sepolia/public'
    ],
    prod: [
      'https://ethereum.publicnode.com',
      'https://eth.llamarpc.com',
      'https://rpc.ankr.com/eth'
    ],
    arbitrum_testnet: [
      'https://sepolia-rollup.arbitrum.io/rpc',
      'https://arbitrum-sepolia-rpc.publicnode.com'
    ],
    arbitrum_mainnet: [
      'https://arb1.arbitrum.io/rpc',
      'https://arbitrum-one.public.blastapi.io',
      'https://arbitrum.llamarpc.com'
    ]
  };
  private currentProviderIndex: number = 0;

  constructor(networkType: NetworkType = config.defaultNetwork) {
    this.network = config.networks[networkType];
    this.connectProvider();
  }

  /**
   * Connect to the chosen network
   */
  private connectProvider() {
    try {
      // Create provider with specific options to handle CORS issues
      this.provider = new ethers.JsonRpcProvider(this.network.rpcUrl, 
        undefined, // Auto-detect the network
        {
          batchMaxCount: 1, // Disable batching for compatibility
          polling: true,    // Force polling for compatibility
          staticNetwork: true, // Prevent network detection issues
          cacheTimeout: -1  // Disable cache for testing
        }
      );
      
      // Set a timeout to check the connection
      setTimeout(() => {
        this.checkConnection();
      }, 2000);
    } catch (error) {
      console.error('Failed to connect to provider:', error);
      this.provider = null;
    }
  }

  /**
   * Attempt to validate the connection and switch to fallback if needed
   */
  private async checkConnection() {
    if (!this.provider) return;
    
    try {
      await this.provider.getBlockNumber();
      // Connection successful
    } catch (error) {
      console.warn('Connection failed, trying fallback provider...');
      this.tryFallbackProvider();
    }
  }

  /**
   * Try to connect using a fallback provider
   */
  private tryFallbackProvider() {
    const networkType = Object.keys(config.networks).find(
      key => config.networks[key as NetworkType].chainId === this.network.chainId
    ) as NetworkType;
    
    const fallbacks = this.fallbackProviders[networkType];
    
    if (!fallbacks || fallbacks.length === 0) {
      console.error('No fallback providers available for network:', networkType);
      return;
    }
    
    // Increment index and wrap around if needed
    this.currentProviderIndex = (this.currentProviderIndex + 1) % fallbacks.length;
    const fallbackUrl = fallbacks[this.currentProviderIndex];
    
    console.log(`Trying fallback provider: ${fallbackUrl}`);
    
    try {
      this.provider = new ethers.JsonRpcProvider(fallbackUrl);
    } catch (error) {
      console.error('Failed to connect to fallback provider:', error);
      this.provider = null;
    }
  }

  /**
   * Change the network connection
   */
  public switchNetwork(networkType: NetworkType) {
    // Reset provider index when switching networks
    this.currentProviderIndex = 0;
    this.network = config.networks[networkType];
    this.connectProvider();
    
    return this.network;
  }

  /**
   * Check if a browser wallet is available
   */
  public hasBrowserWallet(): boolean {
    return typeof window !== 'undefined' && !!window.ethereum;
  }

  /**
   * Request the wallet to switch to the specified network
   */
  public async requestWalletNetworkSwitch(networkType: NetworkType) {
    console.log(`[EthersService] requestWalletNetworkSwitch called for: ${networkType}`);
    
    if (!this.hasBrowserWallet()) {
      console.warn('[EthersService] No wallet detected for network switching');
      return false;
    }
    
    const targetNetwork = config.networks[networkType];
    console.log(`[EthersService] Target network config:`, targetNetwork);
    
    try {
      // Format chain ID as hexadecimal string required by MetaMask
      const chainIdHex = `0x${targetNetwork.chainId.toString(16)}`;
      console.log(`[EthersService] Requesting switch to chainId: ${chainIdHex} (${targetNetwork.chainId})`);
      
      // Request network switch
      try {
        console.log(`[EthersService] Calling wallet_switchEthereumChain...`);
        await window.ethereum.request({
          method: 'wallet_switchEthereumChain',
          params: [{ chainId: chainIdHex }],
        });
        
        console.log(`[EthersService] Successfully switched to network: ${targetNetwork.name}`);
        return true;
      } catch (switchError: any) {
        console.log(`[EthersService] Switch error:`, switchError);
        
        // This error code indicates the chain has not been added to MetaMask
        if (switchError.code === 4902) {
          console.log(`[EthersService] Network not found in wallet, attempting to add...`);
          try {
            const addParams = {
                  chainId: chainIdHex,
                  chainName: targetNetwork.name,
                  rpcUrls: [targetNetwork.rpcUrl],
                  nativeCurrency: {
                    name: targetNetwork.currency || 'ETH',
                    symbol: targetNetwork.currency || 'ETH',
                    decimals: 18,
                  },
            };
            console.log(`[EthersService] Adding network with params:`, addParams);
            
            await window.ethereum.request({
              method: 'wallet_addEthereumChain',
              params: [addParams],
            });
            console.log(`[EthersService] Successfully added and switched to network: ${targetNetwork.name}`);
            return true;
          } catch (addError) {
            console.error('[EthersService] Error adding network to wallet:', addError);
            return false;
          }
        } else {
          console.error('[EthersService] Error switching network in wallet:', switchError);
          return false;
        }
      }
    } catch (error) {
      console.error('[EthersService] Error requesting network switch:', error);
      return false;
    }
  }

  /**
   * Get current provider
   */
  public getProvider() {
    return this.provider;
  }

  /**
   * Get current network config
   */
  public getNetwork() {
    return this.network;
  }

  /**
   * Check connection status
   */
  public async isConnected(): Promise<boolean> {
    if (!this.provider) return false;
    
    try {
      await this.provider.getBlockNumber();
      return true;
    } catch (error) {
      // Try fallback provider before returning false
      this.tryFallbackProvider();
      
      // Try again with the fallback provider
      if (this.provider) {
        try {
          await this.provider.getBlockNumber();
          return true;
        } catch (e) {
          return false;
        }
      }
      
      return false;
    }
  }

  /**
   * Get browser wallet provider if available
   */
  public getBrowserProvider(): ethers.BrowserProvider | null {
    if (this.hasBrowserWallet()) {
      try {
        return new ethers.BrowserProvider(window.ethereum);
      } catch (error) {
        console.error('Error creating browser provider:', error);
        return null;
      }
    }
    return null;
  }

  /**
   * Get signer if connected via browser wallet
   */
  public async getSigner() {
    const browserProvider = this.getBrowserProvider();
    if (browserProvider) {
      try {
        await this.requestWalletNetworkSwitch(
          Object.keys(config.networks).find(
            key => config.networks[key as NetworkType].chainId === this.network.chainId
          ) as NetworkType
        );
        return await browserProvider.getSigner();
      } catch (error) {
        console.error('Error getting signer:', error);
        return null;
      }
    }
    return null;
  }
}

// Create a singleton instance
const ethersService = new EthersService();
export default ethersService; 