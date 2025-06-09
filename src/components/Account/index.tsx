import React, { useState, useEffect } from 'react';
import { useBlockchain } from '../../utils/BlockchainContext';
import profileService from '../../utils/profile-service';
import { ethers } from 'ethers';
import ArtDisplay from '../ArtDisplay';
import { safeRevokeUrl, createImageDataUrl } from '../../utils/TokenURIDecoder';
import ArtPieceDebugInfo from './ArtPieceDebugInfo';
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

  // For wallet connection
  const isTrulyConnected = isConnected && !!walletAddress;

  // Add debug mode toggle
  const [debugMode, setDebugMode] = useState<boolean>(getInitialDebugMode());

  // Toggle debug mode function
  const toggleDebugMode = () => {
    const newMode = !debugMode;
    setDebugMode(newMode);
    localStorage.setItem(DEBUG_MODE_KEY, String(newMode));
  };

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
        
        const imageData = await profile.profileImage();
        if (imageData && imageData.length > 0) {
          // Convert bytes to data URL
          const blob = new Blob([imageData], { type: 'image/avif' });
          const imageUrl = URL.createObjectURL(blob);
          setProfileImage(imageUrl);
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
  
  const loadRecentCommissions = async (profileContract: ethers.Contract) => {
    try {
      setLoadingCommissions(true);
      // Get recent commissions (page 0, 5 items per page)
      const commissions = await profileContract.getRecentCommissions(0, 5);
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
      
      // Get the most recent 5 art pieces
      const recentPieces = await profileContract.getLatestArtPieces();
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
            console.log(`Art piece ${address.substring(0, 6)}... format: ${format}`);
          } catch (formatErr) {
            console.log(`No direct format data for art piece ${address.substring(0, 6)}...`);
            // Format will be detected later from the image data
          }
          
          // Try to get tokenURIData first
          try {
            tokenURIData = await contract.getTokenURIData();
            console.log(`Got tokenURIData for art piece ${address.substring(0, 6)}..., length: ${tokenURIData ? tokenURIData.length : 0} bytes`);
            
            // Log the first few bytes to help with debugging
            if (tokenURIData && tokenURIData.length > 0) {
              const firstBytes = Array.from(tokenURIData.slice(0, 16))
                .map((b: unknown) => (b as number).toString(16).padStart(2, '0'))
                .join(' ');
              console.log(`First bytes: ${firstBytes}`);
            }
          } catch (err) {
            console.log(`No tokenURIData for art piece ${address.substring(0, 6)}...`);
          }
          
          // If that fails, try legacy getImageData
          if (!tokenURIData) {
            try {
              imageData = await contract.getImageData();
              console.log(`Got imageData for art piece ${address.substring(0, 6)}..., length: ${imageData ? imageData.length : 0} bytes`);
              
              // Log the first few bytes to help with debugging
              if (imageData && imageData.length > 0) {
                const firstBytes = Array.from(imageData.slice(0, 16))
                  .map((b: unknown) => (b as number).toString(16).padStart(2, '0'))
                  .join(' ');
                console.log(`First bytes: ${firstBytes}`);
              }
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
              console.log(`Detected format based on magic numbers: ${format}`);
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
    } catch (err) {
      console.error("Error loading art pieces:", err);
      setError("Failed to load art pieces. Please try again.");
    } finally {
      setLoadingArtPieces(false);
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
                      <div key={index} className="art-piece-item">
                        {details.tokenURIData ? (
                          <>
                            <ArtDisplay
                              imageData={details.tokenURIData}
                              title={details.title}
                              contractAddress={address}
                              className="art-piece-display"
                              showDebug={debugMode}
                            />
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
                            <ArtDisplay
                              imageData={details.imageData}
                              title={details.title}
                              contractAddress={address}
                              className="art-piece-display"
                              showDebug={debugMode}
                            />
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
                        <a 
                          href={`#/art/${address}`} 
                          className="view-art-piece-link"
                        >
                          View Details
                        </a>
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
    </div>
  );
};

export default Account;
