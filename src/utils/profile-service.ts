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
      const hubAddress = this.getProfileFactoryAndRegistryAddress();
      
      if (!hubAddress) {
        console.error("ProfileFactoryAndRegistry address not configured");
        return false;
      }
      
      const hubAbi = abiLoader.loadABI('ProfileFactoryAndRegistry');
      
      if (!hubAbi) {
        console.error("ProfileFactoryAndRegistry ABI not found");
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

      const hubAddress = this.getProfileFactoryAndRegistryAddress();
      
      if (!hubAddress) {
        throw new Error("ProfileFactoryAndRegistry address not configured in contract_config.json");
      }
      
      const hubAbi = abiLoader.loadABI('ProfileFactoryAndRegistry');
      
      if (!hubAbi) {
        throw new Error("ProfileFactoryAndRegistry ABI not found");
      }

      const hubContract = new ethers.Contract(hubAddress, hubAbi, signer);
      console.log("Creating profile via ProfileFactoryAndRegistry at:", hubAddress);
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
      const hubAddress = this.getProfileFactoryAndRegistryAddress();
      
      if (!hubAddress) {
        console.error("ProfileFactoryAndRegistry address not configured");
        return null;
      }
      
      const hubAbi = abiLoader.loadABI('ProfileFactoryAndRegistry');
      
      if (!hubAbi) {
        console.error("ProfileFactoryAndRegistry ABI not found");
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
   * Get the ABI for the ArtPiece contract
   * @returns Interface The ABI for the ArtPiece contract
   */
  public async getArtPieceAbi(): Promise<any> {
    try {
      const artPieceAbi = abiLoader.loadABI('ArtPiece');
      if (!artPieceAbi) {
        throw new Error("ArtPiece ABI not found");
      }
      return artPieceAbi;
    } catch (error) {
      console.error("Error loading ArtPiece ABI:", error);
      return null;
    }
  }

  /**
   * Get the provider from ethers service
   * @returns ethers.Provider The current provider
   */
  public getProvider(): ethers.Provider | null {
    return ethersService.getProvider();
  }

  /**
   * Get the ProfileFactoryAndRegistry contract address from config
   * @returns string The ProfileFactoryAndRegistry contract address
   */
  private getProfileFactoryAndRegistryAddress(): string {
    const network = ethersService.getNetwork();
    // Use the toggle preference from localStorage to determine which layer to use
    const useL2Testnet = localStorage.getItem('profile-use-l2-testnet') === 'true';
    
    // Determine environment (testnet/mainnet)
    const environment = network.name === "Sepolia" ? "testnet" : "mainnet";
    
    // Select the contract based on the toggle setting
    // If useL2Testnet is true, we use the L2 testnet contract
    // Otherwise, we use the L3 animechain contract (default behavior)
    try {
      let address;
      if (useL2Testnet) {
        // Use L2 testnet contract for profiles
        address = contractConfig.networks[environment].l2ProfileFactoryAndRegistry.address;
        console.log(`Using L2 testnet ProfileFactoryAndRegistry at: ${address}`);
      } else {
        // Use L3 animechain contract (previous default behavior)
        address = contractConfig.networks[environment].l3ProfileFactoryAndRegistry.address;
        console.log(`Using L3 AnimeChain ProfileFactoryAndRegistry at: ${address}`);
      }
    
      if (!address) {
        console.warn(`ProfileFactoryAndRegistry address for ${environment} is not configured in contract_config.json`);
      }
      
      return address;
    } catch (error) {
      console.error("Error getting ProfileFactoryAndRegistry address:", error);
      return "";
    }
  }
}

// Create a singleton instance
const profileService = new ProfileService();
export default profileService; 