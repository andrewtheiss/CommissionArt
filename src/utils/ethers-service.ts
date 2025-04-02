import { ethers } from 'ethers';
import config, { NetworkConfig } from './config';

type NetworkType = 'animechain' | 'dev' | 'prod' | 'local';

/**
 * Service for interacting with Ethereum blockchain via ethers.js
 */
class EthersService {
  private provider: ethers.JsonRpcProvider | null = null;
  private network: NetworkConfig;

  constructor(networkType: NetworkType = config.defaultNetwork) {
    this.network = config.networks[networkType];
    this.connectProvider();
  }

  /**
   * Connect to the chosen network
   */
  private connectProvider() {
    try {
      this.provider = new ethers.JsonRpcProvider(this.network.rpcUrl);
    } catch (error) {
      console.error('Failed to connect to provider:', error);
      this.provider = null;
    }
  }

  /**
   * Change the network connection
   */
  public switchNetwork(networkType: NetworkType) {
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
      return false;
    }
  }

  /**
   * Get signer if connected via browser wallet
   */
  public async getSigner() {
    if (window.ethereum) {
      const provider = new ethers.BrowserProvider(window.ethereum);
      return await provider.getSigner();
    }
    return null;
  }
}

// Create a singleton instance
const ethersService = new EthersService();
export default ethersService; 