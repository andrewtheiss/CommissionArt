import React, { useState, useEffect } from 'react';
import { useBlockchain } from '../../utils/BlockchainContext';
import profileService from '../../utils/profile-service';
import { ethers } from 'ethers';
import ArtDisplay from '../ArtDisplay';
import { safeRevokeUrl, createImageDataUrl } from '../../utils/TokenURIDecoder';
import ArtPieceDebugInfo from './ArtPieceDebugInfo';
import CreateArtEdition from './CreateArtEdition';
import MintArtEdition from './MintArtEdition';
import abiLoader from '../../utils/abiLoader';
import ethersService from '../../utils/ethers-service';
import './Account.css';
import ProfileEnvironmentToggle from '../ProfileEnvironmentToggle';
import '../ProfileEnvironmentToggle.css';

// Start with debug mode off by default, user can toggle it on
const DEBUG_MODE_KEY = 'account_debug_mode';
const getInitialDebugMode = (): boolean => {
  const savedMode = localStorage.getItem(DEBUG_MODE_KEY);
  return savedMode === 'true';
};

// Address displayed format
const formatAddress = (address: string | null): string => {
  if (!address) return 'Not connected';
  return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
};

const Account: React.FC = () => {
  const { isConnected, connectWallet, walletAddress, network, networkType, switchToLayer } = useBlockchain();
  
  // Profile data and loading states
  const [profileAddress, setProfileAddress] = useState<string | null>(null);
  const [profile, setProfile] = useState<ethers.Contract | null>(null);
  const [hasProfile, setHasProfile] = useState<boolean>(false);
  const [isArtist, setIsArtist] = useState<boolean>(false);
  const [profileChecking, setProfileChecking] = useState<boolean>(true);
  const [profileDataLoading, setProfileDataLoading] = useState<boolean>(false);
  const [profileImageLoading, setProfileImageLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  
  // Commission data
  const [recentCommissions, setRecentCommissions] = useState<string[]>([]);
  const [loadingCommissions, setLoadingCommissions] = useState<boolean>(false);
  
  // Art pieces data
  const [recentArtPieces, setRecentArtPieces] = useState<string[]>([]);
  const [totalArtPieces, setTotalArtPieces] = useState<number>(0);
  const [loadingArtPieces, setLoadingArtPieces] = useState<boolean>(false);
  const [artPieceDetails, setArtPieceDetails] = useState<{
    [address: string]: {
      title: string;
      tokenURIData: string | null;
      imageData: Uint8Array | null;
      format: string | null;
    }
  }>({});
  
  // Profile image
  const [profileImage, setProfileImage] = useState<string | null>(null);
  
  // Create profile
  const [creatingProfile, setCreatingProfile] = useState<boolean>(false);
  const [configError, setConfigError] = useState<string | null>(null);
  const [createAsArtist, setCreateAsArtist] = useState<boolean>(false);

  // Art edition modal states
  const [showEditionModal, setShowEditionModal] = useState<boolean>(false);
  const [selectedArtPiece, setSelectedArtPiece] = useState<string | null>(null);

  // Mint edition modal states
  const [showMintModal, setShowMintModal] = useState<boolean>(false);
  const [selectedMintArtPiece, setSelectedMintArtPiece] = useState<string | null>(null);
  const [artEditions, setArtEditions] = useState<{[artPieceAddress: string]: string | null}>({});

  // Withdrawal states
  const [ethBalance, setEthBalance] = useState<string>('0');
  const [withdrawing, setWithdrawing] = useState<boolean>(false);
  const [tokenAddress, setTokenAddress] = useState<string>('');
  const [tokenBalance, setTokenBalance] = useState<string>('0');
  const [tokenSymbol, setTokenSymbol] = useState<string>('');
  const [tokenDecimals, setTokenDecimals] = useState<number>(18);
  const [loadingTokenInfo, setLoadingTokenInfo] = useState<boolean>(false);
  const [showWithdrawal, setShowWithdrawal] = useState<boolean>(false);

  // For wallet connection
  const isTrulyConnected = isConnected && !!walletAddress;

  // Add debug mode toggle
  const [debugMode, setDebugMode] = useState<boolean>(getInitialDebugMode());

  // Network change tracking
  const [lastNetworkType, setLastNetworkType] = useState<string>(networkType);
  const [lastWalletAddress, setLastWalletAddress] = useState<string | null>(walletAddress);

  // Toggle debug mode function
  const toggleDebugMode = () => {
    const newMode = !debugMode;
    setDebugMode(newMode);
    localStorage.setItem(DEBUG_MODE_KEY, String(newMode));
  };

  // NETWORK CHANGE HANDLER - Reset all state when network or wallet changes
  useEffect(() => {
    const networkChanged = lastNetworkType !== networkType;
    const walletChanged = lastWalletAddress !== walletAddress;
    
    if (networkChanged || walletChanged) {
      console.log(`🔄 Network/Wallet Change Detected:`);
      console.log(`  Network: ${lastNetworkType} → ${networkType}`);
      console.log(`  Wallet: ${lastWalletAddress} → ${walletAddress}`);
      console.log(`  🧹 Clearing all component state...`);
      
      // Reset ALL component state
      setProfileAddress(null);
      setProfile(null);
      setHasProfile(false);
      setIsArtist(false);
      setProfileChecking(true);
      setProfileDataLoading(false);
      setProfileImageLoading(false);
      setError(null);
      setConfigError(null);
      
      // Reset data arrays
      setRecentCommissions([]);
      setRecentArtPieces([]);
      setTotalArtPieces(0);
      setArtPieceDetails({});
      setArtEditions({});
      setProfileImage(null);
      
      // Reset loading states
      setLoadingCommissions(false);
      setLoadingArtPieces(false);
      
      // Reset modal states
      setShowEditionModal(false);
      setShowMintModal(false);
      setSelectedArtPiece(null);
      setSelectedMintArtPiece(null);
      setCreatingProfile(false);
      
      // Update tracking variables
      setLastNetworkType(networkType);
      setLastWalletAddress(walletAddress);
      
      console.log(`✅ State cleared, will re-check profile status`);
    }
  }, [networkType, walletAddress, lastNetworkType, lastWalletAddress]);

  const handleDisconnect = () => {
    if (window.ethereum && window.ethereum.removeAllListeners) {
      try {
        window.ethereum.removeAllListeners();
      } catch (err) {
        console.error("Failed to remove ethereum listeners:", err);
      }
    }
    localStorage.setItem('active_tab', 'account');
    localStorage.setItem('wallet_disconnect_requested', 'true');
    window.location.reload();
  };

  useEffect(() => {
    if (localStorage.getItem('wallet_disconnect_requested') === 'true') {
      localStorage.removeItem('wallet_disconnect_requested');
      console.log("Wallet disconnected as requested");
      if (window.ethereum) {
        try {
          if (window.ethereum._state && window.ethereum._state.accounts) {
            window.ethereum._state.accounts = [];
          }
        } catch (err) {
          console.error("Error forcing wallet disconnect:", err);
        }
      }
    }
  }, []);

  // Create a state to track profile environment changes
  const [profileEnvironment, setProfileEnvironment] = useState<string>(
    localStorage.getItem('profile-use-testnet') === 'true' ? 'Testnet' : 'Mainnet'
  );

  // Watch for changes to the profile environment setting
  useEffect(() => {
    const checkProfileEnvironment = () => {
      const useTestnet = localStorage.getItem('profile-use-testnet') === 'true';
      setProfileEnvironment(useTestnet ? 'Testnet' : 'Mainnet');
    };

    // Check initially
    checkProfileEnvironment();

    // Set up event listener for storage changes
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'profile-use-testnet') {
        checkProfileEnvironment();
      }
    };
    
    window.addEventListener('storage', handleStorageChange);
    
    // Custom event for local changes
    const handleCustomEvent = () => checkProfileEnvironment();
    window.addEventListener('profile-environment-changed', handleCustomEvent);
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('profile-environment-changed', handleCustomEvent);
    };
  }, []);

  const ConnectionBar = () => {
    // Get the profile environment preference from localStorage
    const useTestnet = localStorage.getItem('profile-use-testnet') === 'true';
    const currentEnvironment = useTestnet ? 'Testnet' : 'Mainnet';
    
    // Better network name mapping
    const getNetworkDisplayName = (networkType: string) => {
      switch (networkType) {
        case 'animechain':
          return 'AnimeChain L3';
        case 'arbitrum_testnet':
          return 'Arbitrum Sepolia (L2)';
        case 'arbitrum_mainnet':
          return 'Arbitrum One (L2)';
        case 'dev':
          return 'Sepolia (L1)';
        case 'prod':
          return 'Ethereum (L1)';
        case 'local':
          return 'Local Network';
        default:
          return networkType;
      }
    };
    
    return (
      <div className="connection-bar">
        {!isTrulyConnected ? (
          <>
            <div className="connection-status disconnected">
              <span className="status-icon"></span>
              <span className="status-text">Wallet Not Connected</span>
            </div>
            <button className="connect-wallet-button" onClick={connectWallet}>
              Connect Wallet
            </button>
            {isConnected && !walletAddress && (
              <div className="connection-error-message">
                <p>Connection detected but no wallet address available. Please try reconnecting.</p>
              </div>
            )}
          </>
        ) : (
          <>
            <div className="connection-status connected">
              <span className="status-icon"></span>
              <div className="connection-details">
                <span className="status-text">
                  Connected to: <span className="network-name">
                    {getNetworkDisplayName(networkType)}
                  </span>
                </span>
                <span className="profile-environment">
                  Environment: <span className="environment-name">{currentEnvironment}</span>
                </span>
                <span className="wallet-address">
                  {walletAddress ? `${walletAddress.substring(0, 6)}...${walletAddress.substring(walletAddress.length - 4)}` : 'Not connected'}
                </span>
              </div>
            </div>
            <button className="disconnect-wallet-button" onClick={handleDisconnect}>
              Disconnect
            </button>
          </>
        )}
      </div>
    );
  };

  // Check if user has a profile
  useEffect(() => {
    const checkProfileStatus = async () => {
      if (!isConnected || !walletAddress) {
        setProfileChecking(false);
        setHasProfile(false);
        return;
      }
      
      try {
        setProfileChecking(true);
        setError(null);
        setConfigError(null);
        
        // Check if user has a profile
        const profileExists = await profileService.hasProfile();
        setHasProfile(profileExists);
        
        if (profileExists) {
          // Get profile address
          const address = await profileService.getMyProfileAddress();
          setProfileAddress(address);
          
          // Get profile contract
          const profileContract = await profileService.getMyProfile();
          setProfile(profileContract);
          
          // Log profile address for debugging
          console.log("Connected to Profile at:", address);
        }
      } catch (err: any) {
        console.error("Error checking profile:", err);
        if (err.message?.includes("ProfileFactoryAndRegistry address not configured")) {
          setConfigError("ProfileFactoryAndRegistry contract is not properly configured for this network. Please contact the administrator.");
        } else if (err.message?.includes("ABI not found")) {
          setConfigError("Contract ABI configuration error. Please contact the administrator.");
        } else {
          setError("Failed to check profile status. Please try again.");
        }
      } finally {
        setProfileChecking(false);
      }
    };
    
    checkProfileStatus();
  }, [isConnected, walletAddress, network, profileEnvironment]);
  
  // Load profile data after we have the profile contract
  useEffect(() => {
    const loadProfileData = async () => {
      if (!profile) return;
      
      try {
        setProfileDataLoading(true);
        
        // Get artist status
        const artistStatus = await profile.isArtist();
        setIsArtist(artistStatus);
      } catch (err) {
        console.error("Error loading profile data:", err);
        setError("Failed to load profile data. Please try again.");
      } finally {
        setProfileDataLoading(false);
      }
    };
    
    loadProfileData();
  }, [profile]);
  
  // Load profile image separately
  useEffect(() => {
    const loadProfileImage = async () => {
      if (!profile) return;
      
      try {
        setProfileImageLoading(true);
        
        // profileImage() returns an address of an ArtPiece contract, not bytes data
        const profileImageAddress = await profile.profileImage();
        
        if (profileImageAddress && profileImageAddress !== ethers.ZeroAddress) {
          // Create contract instance for the profile image art piece
          const artPieceContract = new ethers.Contract(
            profileImageAddress,
            abiLoader.loadABI('ArtPiece'),
            ethersService.getProvider()
          );
          
          // Try to get the image data from the art piece
          let imageData = null;
          let format = 'avif'; // default format
          
          try {
            // Try to get tokenURIData first
            imageData = await artPieceContract.getTokenURIData();
          } catch (err) {
            // Fallback to getImageData if tokenURIData doesn't exist
            try {
              imageData = await artPieceContract.getImageData();
            } catch (err2) {
              console.log("No image data available for profile image");
            }
          }
          
          // Try to get format
          try {
            format = await artPieceContract.tokenURI_data_format();
          } catch (err) {
            // Keep default format
          }
          
          if (imageData && imageData.length > 0) {
            // Convert bytes to data URL
            const blob = new Blob([imageData], { type: `image/${format}` });
            const imageUrl = URL.createObjectURL(blob);
            setProfileImage(imageUrl);
          }
        }
      } catch (err) {
        console.error("Error loading profile image:", err);
      } finally {
        setProfileImageLoading(false);
      }
    };
    
    loadProfileImage();
    
    // Cleanup function
    return () => {
      if (profileImage) {
        URL.revokeObjectURL(profileImage);
      }
      
      // No need to revoke URLs here as the ArtDisplay component handles its own cleanup
    };
  }, [profile]);
  
  // Load commissions separately
  useEffect(() => {
    if (!profile) return;
    
    loadRecentCommissions(profile);
  }, [profile]);
  
  // Load art pieces separately
  useEffect(() => {
    if (!profile) return;
    
    loadArtPieces(profile);
  }, [profile]);

  // Load profile balances when profile changes
  useEffect(() => {
    if (!profile) return;
    
    loadProfileBalances();
  }, [profile, tokenAddress, tokenDecimals]);
  
  const loadRecentCommissions = async (profileContract: ethers.Contract) => {
    try {
      setLoadingCommissions(true);
      // Get recent commissions using the new pagination method (offset=0, count=5, reverse=true for newest first)
      const commissions = await profileContract.getCommissionsByOffset(0, 5, true);
      setRecentCommissions(commissions);
    } catch (err) {
      console.error("Error loading commissions:", err);
    } finally {
      setLoadingCommissions(false);
    }
  };
  
  const loadArtPieces = async (profileContract: ethers.Contract) => {
    if (!profileContract) return;
    
    try {
      setLoadingArtPieces(true);
      setError(null);
      
      // Get total count
      const artPieceCount = await profileContract.myArtCount();
      setTotalArtPieces(Number(artPieceCount));
      
      if (Number(artPieceCount) === 0) {
        setLoadingArtPieces(false);
        return;
      }
      
      // Get the most recent 5 art pieces using the new pagination method (offset=0, count=5, reverse=true for newest first)
      const recentPieces = await profileContract.getArtPiecesByOffset(0, 5, true);
      setRecentArtPieces(recentPieces);
      
      // For each art piece, get its details
      const artDetails: { [address: string]: { title: string; tokenURIData: string | null; imageData: Uint8Array | null; format: string | null } } = {};
      
      for (const address of recentPieces) {
        if (!address || address === ethers.ZeroAddress) continue;
        
        try {
          // Create contract instance
          const contract = new ethers.Contract(
            address,
            abiLoader.loadABI('ArtPiece'),
            ethersService.getProvider()
          );
          
          const title = await contract.getTitle();
          let tokenURIData = null;
          let imageData = null;
          let format = null;
          
          // First try to get format if available
          try {
            format = await contract.tokenURI_data_format();
          } catch (formatErr) {
            // Format will be detected later from the image data
          }
          
          // Try to get tokenURIData first
          try {
            tokenURIData = await contract.getTokenURIData();
          } catch (err) {
            // No tokenURIData available
          }
          
          // If that fails, try legacy getImageData
          if (!tokenURIData) {
            try {
              imageData = await contract.getImageData();
            } catch (err) {
              console.error(`Error getting image data for ${address}:`, err);
            }
          }
          
          // If we still don't have format, try to detect from the binary data
          if (!format && (tokenURIData || imageData)) {
            const dataToCheck = tokenURIData || imageData;
            if (dataToCheck && dataToCheck.length > 0) {
              // Check for JPEG signature: FF D8 FF
              if (dataToCheck[0] === 0xFF && dataToCheck[1] === 0xD8 && dataToCheck[2] === 0xFF) {
                format = 'jpeg';
              }
              // Check for PNG signature: 89 50 4E 47
              else if (dataToCheck[0] === 0x89 && dataToCheck[1] === 0x50 && dataToCheck[2] === 0x4E && dataToCheck[3] === 0x47) {
                format = 'png';
              }
              // Check for GIF signature: 47 49 46 38
              else if (dataToCheck[0] === 0x47 && dataToCheck[1] === 0x49 && dataToCheck[2] === 0x46 && dataToCheck[3] === 0x38) {
                format = 'gif';
              }
              // Check for WebP signature: 52 49 46 46 ... 57 45 42 50 (RIFF....WEBP)
              else if (dataToCheck[0] === 0x52 && dataToCheck[1] === 0x49 && dataToCheck[2] === 0x46 && dataToCheck[3] === 0x46 &&
                      dataToCheck.length >= 12 && dataToCheck[8] === 0x57 && dataToCheck[9] === 0x45 && dataToCheck[10] === 0x42 && dataToCheck[11] === 0x50) {
                format = 'webp';
              }
              // Default to avif if no other format detected
              else {
                format = 'avif';
              }
            }
          }
          
          // Store the art piece details
          artDetails[address] = { 
            title, 
            tokenURIData,
            imageData,
            format
          };
        } catch (err) {
          console.error(`Error loading art piece ${address}:`, err);
        }
      }
      
      setArtPieceDetails(artDetails);
      
      // After loading art pieces, check for active sales - USE LOCAL VARIABLE, NOT STATE
      console.log(`loadArtPieces: Loaded ${recentPieces.length} art pieces, now checking for editions...`);
      await checkActiveSales(recentPieces);
    } catch (err) {
      console.error("Error loading art pieces:", err);
      setError("Failed to load art pieces. Please try again.");
    } finally {
      setLoadingArtPieces(false);
    }
  };

  // Check for existing editions for art pieces (active or inactive)
  const checkActiveSales = async (artPieces: string[]) => {
    if (!profile || !isConnected) {
      console.log("checkActiveSales: Missing profile or not connected");
      return;
    }
    
    try {
      const signer = await ethersService.getSigner();
      if (!signer) {
        console.log("checkActiveSales: No signer available");
        return;
      }

      const userAddress = await signer.getAddress();
      console.log(`checkActiveSales: Checking ${artPieces.length} art pieces for user ${userAddress.substring(0, 6)}...`);
      
      // Get the user's ArtSales1155 contract address
      const artSalesAddress = await profile.artSales1155();
      console.log(`checkActiveSales: ArtSales1155 address: ${artSalesAddress}`);
      
      if (!artSalesAddress || artSalesAddress === ethers.ZeroAddress) {
        console.log("checkActiveSales: No ArtSales1155 contract found for user");
        return;
      }

      // Load ArtSales1155 ABI
      const artSalesAbi = abiLoader.loadABI('ArtSales1155');
      if (!artSalesAbi) {
        console.error("checkActiveSales: ArtSales1155 ABI not found");
        return;
      }

      const artSalesContract = new ethers.Contract(artSalesAddress, artSalesAbi, signer);
      
      // Get and log the total count of artist ERC1155s
      try {
        const erc1155Count = await artSalesContract.artistErc1155sToSellCount();
        console.log(`checkActiveSales: ArtSales1155 has ${erc1155Count} total artist ERC1155s`);
      } catch (err) {
        console.error("checkActiveSales: Error getting artistErc1155sToSellCount:", err);
      }
      
      const salesData: {[artPieceAddress: string]: string | null} = {};

      // Check each art piece for active sales
      for (const artPieceAddress of artPieces) {
        if (!artPieceAddress) continue;
        
        try {
          console.log(`checkActiveSales: Checking art piece ${artPieceAddress.substring(0, 6)}...`);
          
          // Check if this art piece has editions
          const hasEditions = await artSalesContract.hasEditions(artPieceAddress);
          console.log(`  → Has editions: ${hasEditions}`);
          
          if (!hasEditions) {
            salesData[artPieceAddress] = null;
            continue;
          }

          // Get the ERC1155 address for this art piece
          const erc1155Address = await artSalesContract.artistPieceToErc1155Map(artPieceAddress);
          console.log(`  → ERC1155 address: ${erc1155Address?.substring(0, 6)}...`);
          
          if (!erc1155Address || erc1155Address === ethers.ZeroAddress) {
            salesData[artPieceAddress] = null;
            continue;
          }

          // Check if sale is active (but we'll show button regardless)
          const isActive = await artSalesContract.isSaleActive(erc1155Address);
          console.log(`  → Sale active: ${isActive}`);
          
          // Store the ArtSales1155 address for any existing edition (active or not)
          salesData[artPieceAddress] = artSalesAddress;
          console.log(`✅ Edition found for art piece ${artPieceAddress.substring(0, 6)}... (active: ${isActive})`);
        
        } catch (err) {
          console.error(`Error checking sales for art piece ${artPieceAddress}:`, err);
          salesData[artPieceAddress] = null;
        }
      }

      console.log("checkActiveSales: Final salesData:", salesData);
      setArtEditions(salesData);
    } catch (err) {
      console.error("Error checking active sales:", err);
    }
  };
  
  // Decode tokenURI data - this function existed before but was inside loadArtPieces
  const decodeTokenFromUri = (tokenURI: string) => {
    if (!tokenURI) return null;
    
    try {
      if (tokenURI.startsWith('data:application/json;base64,')) {
        const base64Data = tokenURI.slice('data:application/json;base64,'.length);
        const decodedData = atob(base64Data);
        return JSON.parse(decodedData);
      }
    } catch (error) {
      console.error('Error decoding token URI:', error);
    }
    
    return null;
  };
  
  const handleCreateProfile = async () => {
    if (!isConnected) {
      connectWallet();
      return;
    }
    
    try {
      setCreatingProfile(true);
      setError(null);
      
      // Create profile via the ProfileFactoryAndRegistry with artist status
      const newProfileAddress = await profileService.createProfile(createAsArtist);
      console.log("Profile created at address:", newProfileAddress);
      
      // Refresh profile data
      setProfileAddress(newProfileAddress);
      setHasProfile(true);
      
      // Get the new profile contract
      const profileContract = await profileService.getMyProfile();
      setProfile(profileContract);
      
      if (profileContract) {
        setIsArtist(await profileContract.isArtist());
      }
    } catch (err: any) {
      console.error("Error creating profile:", err);
      if (err.message?.includes("ProfileFactoryAndRegistry address not configured")) {
        setConfigError("ProfileFactoryAndRegistry contract is not properly configured for this network. Please contact the administrator.");
      } else if (err.message?.includes("ABI not found")) {
        setConfigError("Contract ABI configuration error. Please contact the administrator.");
      } else {
        setError("Failed to create profile. Please try again.");
      }
    } finally {
      setCreatingProfile(false);
    }
  };
  
  const handleSetArtistStatus = async (status: boolean) => {
    if (!profile) return;
    
    try {
      setProfileDataLoading(true);
      setError(null);
      
      // Use the profile service method
      await profileService.setArtistStatus(status);
      
      // Update state
      setIsArtist(status);
    } catch (err) {
      console.error("Error setting artist status:", err);
      setError(`Failed to ${status ? 'become' : 'stop being'} an artist. Please try again.`);
    } finally {
      setProfileDataLoading(false);
    }
  };

  // Handle art piece click for edition creation
  const handleArtPieceClick = (artPieceAddress: string, event: React.MouseEvent) => {
    // Prevent triggering if clicking on the "View Details" link
    if ((event.target as HTMLElement).closest('.view-art-piece-link')) {
      return;
    }
    
    // Only allow artists to create editions
    if (!isArtist) {
      return;
    }
    
    setSelectedArtPiece(artPieceAddress);
    setShowEditionModal(true);
  };

  // Handle edition creation success
  const handleEditionSuccess = (editionAddress: string) => {
    console.log('Edition created successfully:', editionAddress);
    // Optionally refresh the art pieces list
    if (profile) {
      loadArtPieces(profile);
    }
  };

  // Handle edition creation error
  const handleEditionError = (error: string) => {
    console.error('Edition creation error:', error);
    setError(error);
  };

  // Close edition modal
  const handleEditionClose = () => {
    setShowEditionModal(false);
    setSelectedArtPiece(null);
  };

  // Handle mint button click
  const handleMintClick = (artPieceAddress: string) => {
    setSelectedMintArtPiece(artPieceAddress);
    setShowMintModal(true);
  };

  // Handle mint success
  const handleMintSuccess = (txHash: string) => {
    console.log('Mint successful:', txHash);
    // Optionally refresh the art editions data
    if (profile && recentArtPieces.length > 0) {
      checkActiveSales(recentArtPieces);
    }
  };

  // Handle mint error
  const handleMintError = (error: string) => {
    console.error('Mint error:', error);
    setError(error);
  };

  // Close mint modal
  const handleMintClose = () => {
    setShowMintModal(false);
    setSelectedMintArtPiece(null);
  };

  // Load profile balances
  const loadProfileBalances = async () => {
    if (!profile) return;
    
    try {
      // Load ETH balance
      const ethBal = await profile.getAvailableEthBalance();
      setEthBalance(ethers.formatEther(ethBal));
      
      // If we have a token address, load token balance
      if (tokenAddress && ethers.isAddress(tokenAddress)) {
        const tokenBal = await profile.getTokenBalance(tokenAddress);
        setTokenBalance(ethers.formatUnits(tokenBal, tokenDecimals));
      }
    } catch (err) {
      console.error("Error loading profile balances:", err);
    }
  };

  // Load token information
  const loadTokenInfo = async (tokenAddr: string) => {
    if (!tokenAddr || !ethers.isAddress(tokenAddr)) {
      setTokenSymbol('');
      setTokenDecimals(18);
      setTokenBalance('0');
      return;
    }

    try {
      setLoadingTokenInfo(true);
      
      // Create ERC20 contract to get token info
      const tokenContract = new ethers.Contract(
        tokenAddr,
        [
          'function symbol() view returns (string)',
          'function decimals() view returns (uint8)',
          'function balanceOf(address) view returns (uint256)'
        ],
        ethersService.getProvider()
      );

      const [symbol, decimals] = await Promise.all([
        tokenContract.symbol(),
        tokenContract.decimals()
      ]);

      setTokenSymbol(symbol);
      setTokenDecimals(Number(decimals));

      // Load balance using profile contract
      if (profile) {
        const tokenBal = await profile.getTokenBalance(tokenAddr);
        setTokenBalance(ethers.formatUnits(tokenBal, decimals));
      }
    } catch (err) {
      console.error("Error loading token info:", err);
      setTokenSymbol('UNKNOWN');
      setTokenDecimals(18);
      setTokenBalance('0');
    } finally {
      setLoadingTokenInfo(false);
    }
  };

  // Handle ETH withdrawal
  const handleWithdrawEth = async () => {
    if (!profile) return;
    
    try {
      setWithdrawing(true);
      setError(null);
      
      // Check if there's ETH to withdraw
      if (parseFloat(ethBalance) <= 0) {
        setError("No ETH available to withdraw");
        return;
      }

      console.log("Withdrawing ETH from profile...");
      const tx = await profile.withdrawEth();
      console.log("Withdrawal transaction:", tx.hash);
      
      // Wait for transaction confirmation
      await tx.wait();
      console.log("ETH withdrawal confirmed");
      
      // Refresh balance
      loadProfileBalances();
      
    } catch (err: any) {
      console.error("Error withdrawing ETH:", err);
      if (err.message?.includes("No ETH to withdraw")) {
        setError("No ETH available to withdraw");
      } else if (err.message?.includes("Only owner can withdraw")) {
        setError("Only the profile owner can withdraw funds");
      } else {
        setError("Failed to withdraw ETH. Please try again.");
      }
    } finally {
      setWithdrawing(false);
    }
  };

  // Handle ERC20 token withdrawal
  const handleWithdrawTokens = async () => {
    if (!profile || !tokenAddress || !ethers.isAddress(tokenAddress)) {
      setError("Please enter a valid token address");
      return;
    }
    
    try {
      setWithdrawing(true);
      setError(null);
      
      // Check if there are tokens to withdraw
      if (parseFloat(tokenBalance) <= 0) {
        setError(`No ${tokenSymbol} tokens available to withdraw`);
        return;
      }

      console.log(`Withdrawing ${tokenSymbol} tokens from profile...`);
      const tx = await profile.withdrawTokens(tokenAddress);
      console.log("Token withdrawal transaction:", tx.hash);
      
      // Wait for transaction confirmation
      await tx.wait();
      console.log("Token withdrawal confirmed");
      
      // Refresh balance
      loadProfileBalances();
      
    } catch (err: any) {
      console.error("Error withdrawing tokens:", err);
      if (err.message?.includes("No tokens to withdraw")) {
        setError(`No ${tokenSymbol} tokens available to withdraw`);
      } else if (err.message?.includes("Only owner can withdraw")) {
        setError("Only the profile owner can withdraw funds");
      } else if (err.message?.includes("Invalid token address")) {
        setError("Invalid token address");
      } else {
        setError("Failed to withdraw tokens. Please try again.");
      }
    } finally {
      setWithdrawing(false);
    }
  };

  // Handle token address change
  const handleTokenAddressChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const addr = e.target.value.trim();
    setTokenAddress(addr);
    
    if (addr && ethers.isAddress(addr)) {
      loadTokenInfo(addr);
    } else {
      setTokenSymbol('');
      setTokenDecimals(18);
      setTokenBalance('0');
    }
  };

  // Toggle withdrawal section visibility
  const toggleWithdrawalSection = () => {
    setShowWithdrawal(!showWithdrawal);
    
    // If opening for the first time and no token address set, pre-fill it
    if (!showWithdrawal && !tokenAddress) {
      const defaultTokenAddress = '0xdafcF0d6fc4a43cf8595f2172c07CEa7f273531D';
      setTokenAddress(defaultTokenAddress);
      loadTokenInfo(defaultTokenAddress);
    }
  };

  return (
    <div className="account-container">
      <h2>Your Account</h2>
      
      {/* Add debug mode toggle at the top */}
      <div className="debug-mode-toggle-container">
        <label className="debug-mode-toggle">
          <input 
            type="checkbox" 
            checked={debugMode} 
            onChange={toggleDebugMode} 
          />
          <span className="debug-mode-toggle-text">Debug Mode</span>
        </label>
      </div>
      
      {/* Add profile environment toggle */}
      <ProfileEnvironmentToggle />
      
      <ConnectionBar />
      
      {error && <div className="error-banner">{error}</div>}
      
      {profileChecking ? (
        <div className="loading-spinner">Checking profile...</div>
      ) : configError ? (
        <div className="account-card error-card">
          <h3>Configuration Error</h3>
          <p>{configError}</p>
          <p>Current network: {network.name}</p>
        </div>
      ) : !hasProfile && isTrulyConnected ? (
        <div className="account-card">
          <h3>No Profile Found</h3>
          <p>You don't have a profile yet. Create one to start using the platform.</p>
          <p className="wallet-info">Connected wallet: {formatAddress(walletAddress)}</p>
          
          <div className="create-profile-options">
            <label className="artist-checkbox">
              <input 
                type="checkbox" 
                checked={createAsArtist} 
                onChange={(e) => setCreateAsArtist(e.target.checked)}
                disabled={creatingProfile}
              />
              <span className="checkbox-text">Create as Artist</span>
            </label>
            <p className="artist-help-text">
              Artists can create and sell art pieces. You can change this setting later.
            </p>
          </div>
          
          <button 
            className="create-profile-button" 
            onClick={handleCreateProfile}
            disabled={creatingProfile}
          >
            {creatingProfile ? 'Creating Profile...' : 'Create Profile'}
          </button>
          {error && <div className="error-message">{error}</div>}
        </div>
      ) : isTrulyConnected ? (
        <div className="account-grid">
          <div className="account-card profile-card">
            <div className="profile-header">
              <div className="profile-image-container">
                {profileImageLoading ? (
                  <div className="profile-image-loading">
                    <div className="mini-spinner"></div>
                  </div>
                ) : profileImage ? (
                  <img src={profileImage} alt="Profile" className="profile-image" />
                ) : (
                  <div className="profile-image-placeholder">
                    {walletAddress ? walletAddress.substring(2, 4).toUpperCase() : '??'}
                  </div>
                )}
              </div>
              <div className="profile-info">
                <h3>Profile</h3>
                <p className="wallet-address">
                  Wallet: {formatAddress(walletAddress)}
                </p>
                <p className="profile-address">
                  Profile: {formatAddress(profileAddress)}
                </p>
                <div className="artist-status">
                  {profileDataLoading ? (
                    <div className="mini-spinner">Loading status...</div>
                  ) : (
                    <>
                      <span>Artist Status: {isArtist ? 'Active' : 'Inactive'}</span>
                      <button 
                        className={`artist-toggle ${isArtist ? 'deactivate' : 'activate'}`}
                        onClick={() => handleSetArtistStatus(!isArtist)}
                        disabled={profileDataLoading}
                      >
                        {isArtist ? 'Deactivate' : 'Activate'} Artist Mode
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
            
            {/* Withdrawal Section - Collapsible */}
            <div className="withdrawal-section">
              <div className="withdrawal-toggle" onClick={toggleWithdrawalSection}>
                <h4>Fund Withdrawal</h4>
                <div className="withdrawal-summary">
                  <span className="balance-summary">{parseFloat(ethBalance).toFixed(4)} ETH</span>
                  {tokenSymbol && <span className="token-summary">{parseFloat(tokenBalance).toFixed(4)} {tokenSymbol}</span>}
                  <span className={`toggle-icon ${showWithdrawal ? 'expanded' : ''}`}>▼</span>
                </div>
              </div>
              
              {showWithdrawal && (
                <div className="withdrawal-content">
                  {/* ETH Withdrawal */}
                  <div className="withdrawal-group">
                    <div className="balance-display">
                      <span className="balance-label">ETH Balance:</span>
                      <span className="balance-amount">{parseFloat(ethBalance).toFixed(6)} ETH</span>
                    </div>
                    <button 
                      className="withdrawal-button eth-withdrawal"
                      onClick={handleWithdrawEth}
                      disabled={withdrawing || parseFloat(ethBalance) <= 0}
                    >
                      {withdrawing ? 'Withdrawing...' : `Withdraw ETH`}
                    </button>
                  </div>

                  {/* ERC20 Token Withdrawal */}
                  <div className="withdrawal-group">
                    <div className="token-input-section">
                      <input
                        type="text"
                        placeholder="0xdafcF0d6fc4a43cf8595f2172c07CEa7f273531D"
                        value={tokenAddress}
                        onChange={handleTokenAddressChange}
                        className="token-address-input"
                        disabled={withdrawing}
                      />
                      {loadingTokenInfo && <div className="token-loading">Loading token info...</div>}
                    </div>
                    
                    {tokenSymbol && (
                      <div className="balance-display">
                        <span className="balance-label">{tokenSymbol} Balance:</span>
                        <span className="balance-amount">{parseFloat(tokenBalance).toFixed(6)} {tokenSymbol}</span>
                      </div>
                    )}
                    
                    <button 
                      className="withdrawal-button token-withdrawal"
                      onClick={handleWithdrawTokens}
                      disabled={withdrawing || !tokenAddress || !ethers.isAddress(tokenAddress) || parseFloat(tokenBalance) <= 0}
                    >
                      {withdrawing ? 'Withdrawing...' : `Withdraw ${tokenSymbol || 'Tokens'}`}
                    </button>
                  </div>

                  <div className="withdrawal-actions">
                    <button 
                      className="refresh-balance-button"
                      onClick={loadProfileBalances}
                      disabled={withdrawing}
                      title="Refresh balance information"
                    >
                      🔄 Refresh Balances
                    </button>
                  </div>

                  <div className="withdrawal-help">
                    <p className="help-text">
                      Withdraw funds that have accumulated in your profile from sales and commissions.
                      ETH withdrawals are instant. For ERC20 tokens, enter the token contract address.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
          
          <div className="account-card commissions-card">
            <h3>Recent Commissions</h3>
            {loadingCommissions ? (
              <div className="loading-spinner">Loading commissions...</div>
            ) : recentCommissions.length > 0 ? (
              <ul className="commission-list">
                {recentCommissions.map((address, index) => (
                  <li key={index} className="commission-item">
                    <div className="commission-address">{formatAddress(address)}</div>
                    <a 
                      href={`#/commission/${address}`} 
                      className="view-commission-link"
                    >
                      View
                    </a>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="no-commissions">No commissions found.</p>
            )}
          </div>
          
          <div className="account-card art-pieces-card">
            <h3>My Art Pieces {totalArtPieces > 0 && <span className="count-badge">{totalArtPieces}</span>}</h3>
            {isArtist && (
              <p className="art-pieces-subtitle">Click on any art piece image to create an ERC1155 edition for sale</p>
            )}
            {loadingArtPieces ? (
              <div className="loading-spinner">Loading art pieces...</div>
            ) : recentArtPieces.length > 0 ? (
              <div>
                <p className="art-count">Total: {totalArtPieces} art piece{totalArtPieces !== 1 ? 's' : ''}</p>
                <div className="art-pieces-grid">
                  {recentArtPieces.map((address, index) => {
                    if (!address) return null; // Skip empty addresses
                    const details = artPieceDetails[address] || { title: 'Loading...', tokenURIData: null };
                    
                    return (
                      <div 
                        key={index} 
                        className="art-piece-item"
                      >
                        {details.tokenURIData ? (
                          <>
                            <div 
                              className={`art-piece-image-container ${isArtist ? 'clickable' : ''}`}
                              onClick={isArtist ? (e) => handleArtPieceClick(address, e) : undefined}
                            >
                              <ArtDisplay
                                imageData={details.tokenURIData}
                                title={details.title}
                                contractAddress={address}
                                className="art-piece-display"
                                showDebug={debugMode}
                              />
                              {isArtist && (
                                <div className="art-piece-overlay">
                                  <span className="edition-hint">Click to create edition</span>
                                </div>
                              )}
                            </div>
                            {/* Add debug info component conditionally */}
                            {debugMode && (
                              <ArtPieceDebugInfo 
                                tokenURIData={details.tokenURIData} 
                                contractAddress={address}
                              />
                            )}
                          </>
                        ) : details.imageData ? (
                          // Handle raw image data format
                          <>
                            <div 
                              className={`art-piece-image-container ${isArtist ? 'clickable' : ''}`}
                              onClick={isArtist ? (e) => handleArtPieceClick(address, e) : undefined}
                            >
                              <ArtDisplay
                                imageData={details.imageData}
                                title={details.title}
                                contractAddress={address}
                                className="art-piece-display"
                                showDebug={debugMode}
                              />
                              {isArtist && (
                                <div className="art-piece-overlay">
                                  <span className="edition-hint">Click to create edition</span>
                                </div>
                              )}
                            </div>
                            {debugMode && (
                              <div className="art-debug-info small">
                                <div>Raw binary image data</div>
                                <div>Format: {details.format || 'unknown'}</div>
                                <div>Size: {(details.imageData.length / 1024).toFixed(2)} KB</div>
                              </div>
                            )}
                          </>
                        ) : (
                          <div className="art-piece-placeholder">
                            <div className="art-piece-image-placeholder">Art</div>
                            <div className="art-piece-info">
                              <h4 className="art-piece-title">{details.title}</h4>
                              <div className="art-piece-address">{formatAddress(address)}</div>
                            </div>
                          </div>
                        )}
                        <div className="art-actions">
                          <a 
                            href={`#/art/${address}`} 
                            className="view-art-piece-link"
                          >
                            View Details
                          </a>
                          {artEditions[address] && (
                            <button
                              className="mint-edition-button"
                              onClick={() => handleMintClick(address)}
                              title="View and manage edition"
                            >
                              Manage Edition
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
                {totalArtPieces > recentArtPieces.length && (
                  <div className="view-all-link-container">
                    <a href="#/art/gallery" className="view-all-link">View All Art Pieces</a>
                  </div>
                )}
              </div>
            ) : (
              <div>
                <p className="art-count">Total: {totalArtPieces} art pieces</p>
                {totalArtPieces > 0 ? (
                  <p className="loading-error">Art pieces found but couldn't be loaded. Please try again later.</p>
                ) : (
                  <p className="no-art-pieces">No art pieces found.</p>
                )}
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="account-card connect-card">
          <p>Please connect your wallet to view your profile</p>
        </div>
      )}
      
      {/* Debug information */}
      {debugMode && hasProfile && profile && (
        <div className="account-card debug-card">
          <h3>Debug Information</h3>
          <div className="debug-info">
            <p><strong>Profile Address:</strong> {profileAddress}</p>
            <p><strong>Environment:</strong> {profileEnvironment}</p>
            <p><strong>Network:</strong> {network.name}</p>
            <p><strong>Is Artist:</strong> {isArtist ? 'Yes' : 'No'}</p>
            <p><strong>Total Art Pieces:</strong> {totalArtPieces}</p>
            <p><strong>Total Commissions:</strong> {recentCommissions.length}</p>
            <div className="debug-actions">
              <button 
                className="debug-button"
                onClick={async () => {
                  try {
                    const artistStatus = await profile.isArtist();
                    const owner = await profile.owner();
                    const artCount = await profile.myArtCount();
                    console.log('Profile Debug Info:', {
                      address: profileAddress,
                      owner,
                      isArtist: artistStatus,
                      artCount: Number(artCount)
                    });
                    alert('Debug info logged to console');
                  } catch (err) {
                    console.error('Debug error:', err);
                    alert('Debug failed - check console');
                  }
                }}
              >
                Log Profile Details
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Art Edition Creation Modal */}
      <CreateArtEdition
        isOpen={showEditionModal}
        onClose={handleEditionClose}
        onSuccess={handleEditionSuccess}
        onError={handleEditionError}
        selectedArtPiece={selectedArtPiece}
        artPieceDetails={selectedArtPiece ? artPieceDetails[selectedArtPiece] || null : null}
        profileContract={profile}
        isArtist={isArtist}
      />

      {/* Mint Art Edition Modal */}
      <MintArtEdition
        isOpen={showMintModal}
        onClose={handleMintClose}
        onSuccess={handleMintSuccess}
        onError={handleMintError}
        artPieceAddress={selectedMintArtPiece}
        artSales1155Address={selectedMintArtPiece ? artEditions[selectedMintArtPiece] || null : null}
      />
    </div>
  );
};

export default Account;
