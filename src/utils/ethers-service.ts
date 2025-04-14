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
      'https://arbitrum-sepolia.blockpi.network/v1/rpc/public'
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
   * Get signer if connected via browser wallet
   */
  public async getSigner() {
    if (window.ethereum) {
      try {
        const provider = new ethers.BrowserProvider(window.ethereum);
        return await provider.getSigner();
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