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
   * @param isArtist Whether to create the profile as an artist
   * @returns Promise<string> Address of the created profile
   */
  public async createProfile(isArtist: boolean = false): Promise<string> {
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
      
      // Call createProfile with no parameters (defaults to msg.sender)
      // Use the specific function signature to avoid ambiguity
      const tx = await hubContract['createProfile()']();
      await tx.wait();

      // Get the newly created profile address
      const userAddress = await signer.getAddress();
      const profileAddress = await hubContract.getProfile(userAddress);
      
      // If the user wants to be an artist, set that status
      if (isArtist && profileAddress !== ethers.ZeroAddress) {
        try {
          const profileContract = await this.getMyProfile();
          if (profileContract) {
            const artistTx = await profileContract.setIsArtist(true);
            await artistTx.wait();
            console.log("Artist status set successfully");
          }
        } catch (artistError) {
          console.warn("Profile created but failed to set artist status:", artistError);
          // Don't throw here, profile creation was successful
        }
      }
      
      return profileAddress;
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
    
    // Determine environment based on network configuration
    // Testnet: Arbitrum Sepolia (421614) or Ethereum Sepolia (11155111)
    // Mainnet: AnimeChain (69000) or Ethereum Mainnet (1) 
    let environment: "testnet" | "mainnet";
    
    if (network.chainId === 421614 || network.chainId === 11155111) {
      // Arbitrum Sepolia or Ethereum Sepolia
      environment = "testnet";
    } else if (network.chainId === 69000 || network.chainId === 1) {
      // AnimeChain or Ethereum Mainnet
      environment = "mainnet";
    } else {
      // Default fallback - determine by network name
      environment = network.name === "Sepolia" || network.name === "Arbitrum Sepolia" ? "testnet" : "mainnet";
    }
    
    // Use the standard profileFactoryAndRegistry address
    try {
      const address = contractConfig.networks[environment].profileFactoryAndRegistry.address;
      
      if (!address) {
        console.warn(`ProfileFactoryAndRegistry address for ${environment} is not configured in contract_config.json`);
        return "";
      }
      
      console.log(`Using ProfileFactoryAndRegistry at: ${address} (${environment}) for network ${network.name} (${network.chainId})`);
      return address;
    } catch (error) {
      console.error("Error getting ProfileFactoryAndRegistry address:", error);
      return "";
    }
  }

  /**
   * Toggle artist status for the current user's profile
   * @param isArtist Whether the user should be an artist
   * @returns Promise<void>
   */
  public async setArtistStatus(isArtist: boolean): Promise<void> {
    try {
      const profileContract = await this.getMyProfile();
      if (!profileContract) {
        throw new Error("Profile not found");
      }

      const tx = await profileContract.setIsArtist(isArtist);
      await tx.wait();
      console.log(`Artist status ${isArtist ? 'enabled' : 'disabled'} successfully`);
    } catch (error) {
      console.error("Error setting artist status:", error);
      throw error;
    }
  }
}

// Create a singleton instance
const profileService = new ProfileService();
export default profileService; 