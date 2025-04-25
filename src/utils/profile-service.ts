import { ethers } from 'ethers';
import ethersService from './ethers-service';
import contractConfig from '../assets/contract_config.json';
import abiLoader from './abiLoader';

class ProfileService {
  /**
   * Check if the current wallet has a profile
   * @returns Promise<boolean> True if the user has a profile
   */
  public async hasProfile(): Promise<boolean> {
    try {
      const signer = await ethersService.getSigner();
      if (!signer) {
        throw new Error("Wallet not connected");
      }

      const userAddress = await signer.getAddress();
      const hubAddress = this.getProfileHubAddress();
      const hubAbi = abiLoader.loadABI('ProfileHub');
      
      if (!hubAddress || !hubAbi) {
        console.error("ProfileHub address or ABI not found");
        return false;
      }

      const hubContract = new ethers.Contract(hubAddress, hubAbi, signer);
      return await hubContract.hasProfile(userAddress);
    } catch (error) {
      console.error("Error checking profile:", error);
      return false;
    }
  }

  /**
   * Create a new profile for the current wallet
   * @returns Promise<string> Address of the created profile
   */
  public async createProfile(): Promise<string> {
    try {
      const signer = await ethersService.getSigner();
      if (!signer) {
        throw new Error("Wallet not connected");
      }

      const hubAddress = this.getProfileHubAddress();
      const hubAbi = abiLoader.loadABI('ProfileHub');
      
      if (!hubAddress || !hubAbi) {
        throw new Error("ProfileHub address or ABI not found");
      }

      const hubContract = new ethers.Contract(hubAddress, hubAbi, signer);
      const tx = await hubContract.createProfile();
      await tx.wait();

      // Get the newly created profile address
      const userAddress = await signer.getAddress();
      return await hubContract.getProfile(userAddress);
    } catch (error) {
      console.error("Error creating profile:", error);
      throw error;
    }
  }

  /**
   * Get the profile address for the current wallet
   * @returns Promise<string> Address of the user's profile, or null if not found
   */
  public async getMyProfileAddress(): Promise<string | null> {
    try {
      const signer = await ethersService.getSigner();
      if (!signer) {
        throw new Error("Wallet not connected");
      }

      const userAddress = await signer.getAddress();
      return await this.getProfileAddress(userAddress);
    } catch (error) {
      console.error("Error getting profile address:", error);
      return null;
    }
  }

  /**
   * Get the profile address for a specific user
   * @param userAddress Address of the user to lookup
   * @returns Promise<string> Address of the user's profile, or null if not found
   */
  public async getProfileAddress(userAddress: string): Promise<string | null> {
    try {
      const hubAddress = this.getProfileHubAddress();
      const hubAbi = abiLoader.loadABI('ProfileHub');
      
      if (!hubAddress || !hubAbi) {
        console.error("ProfileHub address or ABI not found");
        return null;
      }

      const provider = ethersService.getProvider();
      if (!provider) {
        throw new Error("Provider not connected");
      }
      
      const hubContract = new ethers.Contract(hubAddress, hubAbi, provider);
      const profileAddress = await hubContract.getProfile(userAddress);
      
      // Check if address is empty (profile doesn't exist)
      if (profileAddress === ethers.ZeroAddress) {
        return null;
      }
      
      return profileAddress;
    } catch (error) {
      console.error("Error getting profile address:", error);
      return null;
    }
  }

  /**
   * Get the profile contract for the current wallet
   * @returns Promise<ethers.Contract> The profile contract, or null if not found
   */
  public async getMyProfile(): Promise<ethers.Contract | null> {
    try {
      const signer = await ethersService.getSigner();
      if (!signer) {
        throw new Error("Wallet not connected");
      }

      const profileAddress = await this.getMyProfileAddress();
      if (!profileAddress) {
        return null;
      }

      const profileAbi = abiLoader.loadABI('Profile');
      if (!profileAbi) {
        throw new Error("Profile ABI not found");
      }

      return new ethers.Contract(profileAddress, profileAbi, signer);
    } catch (error) {
      console.error("Error getting profile contract:", error);
      return null;
    }
  }

  /**
   * Get the ProfileHub contract address from config
   * @returns string The ProfileHub contract address
   */
  private getProfileHubAddress(): string {
    // Use mainnet for now, consider adding networkType parameter
    const networkType = ethersService.getNetwork().name === "Sepolia" ? "testnet" : "mainnet";
    return contractConfig.networks[networkType].profileHub.address;
  }
}

// Create a singleton instance
const profileService = new ProfileService();
export default profileService; 