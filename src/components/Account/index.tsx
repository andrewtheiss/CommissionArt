import React, { useState, useEffect } from 'react';
import { useBlockchain } from '../../utils/BlockchainContext';
import profileService from '../../utils/profile-service';
import { ethers } from 'ethers';
import './Account.css';

// Address displayed format
const formatAddress = (address: string | null) => {
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
  const [artPieceDetails, setArtPieceDetails] = useState<{[address: string]: {title: string, imageUrl: string | null}}>({});
  
  // Profile image
  const [profileImage, setProfileImage] = useState<string | null>(null);
  
  // Create profile
  const [creatingProfile, setCreatingProfile] = useState<boolean>(false);
  const [configError, setConfigError] = useState<string | null>(null);

  // For wallet connection
  const isTrulyConnected = isConnected && !!walletAddress;

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

  const ConnectionBar = () => (
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
                  {networkType === 'arbitrum_testnet' ? 'L3 (Arbitrum Sepolia)' : networkType}
                </span>
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
        if (err.message?.includes("ProfileHub address not configured")) {
          setConfigError("ProfileHub contract is not properly configured for this network. Please contact the administrator.");
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
  }, [isConnected, walletAddress, network]);
  
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
      
      // Revoke art piece image URLs
      Object.values(artPieceDetails).forEach(details => {
        if (details.imageUrl) URL.revokeObjectURL(details.imageUrl);
      });
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
    try {
      setLoadingArtPieces(true);
      
      console.log("Loading art pieces from profile contract:", profileContract.target);
      
      // Get the total count of art pieces
      const artCount = await profileContract.myArtCount();
      setTotalArtPieces(Number(artCount));
      console.log("Total art pieces:", Number(artCount));
      
      // Instead of using paging, let's use the getLatestArtPieces method which returns the 5 most recent
      const artPieces = await profileContract.getLatestArtPieces();
      console.log("Latest art pieces:", artPieces);
      
      setRecentArtPieces(artPieces);
      
      // Load details for each art piece
      const artPieceAbi = await profileService.getArtPieceAbi();
      if (artPieceAbi) {
        const details: {[address: string]: {title: string, imageUrl: string | null}} = {};
        const provider = profileService.getProvider();
        
        if (provider) {
          for (const address of artPieces) {
            if (!address) continue; // Skip empty addresses
            
            try {
              console.log("Loading details for art piece:", address);
              const artPieceContract = new ethers.Contract(address, artPieceAbi, provider);
              const title = await artPieceContract.title();
              
              // Get image data
              let imageUrl = null;
              try {
                const imageData = await artPieceContract.imageData();
                if (imageData && imageData.length > 0) {
                  const blob = new Blob([imageData], { type: 'image/avif' });
                  imageUrl = URL.createObjectURL(blob);
                }
              } catch (err) {
                console.error(`Error loading image for art piece ${address}:`, err);
              }
              
              details[address] = { title, imageUrl };
            } catch (err) {
              console.error(`Error loading details for art piece ${address}:`, err);
              details[address] = { title: 'Unknown Art Piece', imageUrl: null };
            }
          }
          
          setArtPieceDetails(details);
        } else {
          console.error("Provider not available");
        }
      }
    } catch (err) {
      console.error("Error loading art pieces:", err);
    } finally {
      setLoadingArtPieces(false);
    }
  };
  
  const handleCreateProfile = async () => {
    if (!isConnected) {
      connectWallet();
      return;
    }
    
    try {
      setCreatingProfile(true);
      setError(null);
      
      // Create profile via the ProfileHub
      const newProfileAddress = await profileService.createProfile();
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
      if (err.message?.includes("ProfileHub address not configured")) {
        setConfigError("ProfileHub contract is not properly configured for this network. Please contact the administrator.");
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
      // Call the contract method
      const tx = await profile.setIsArtist(status);
      // Wait for transaction to be mined
      await tx.wait();
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
                    const details = artPieceDetails[address] || { title: 'Loading...', imageUrl: null };
                    return (
                      <div key={index} className="art-piece-item">
                        <div className="art-piece-image-container">
                          {details.imageUrl ? (
                            <img src={details.imageUrl} alt={details.title} className="art-piece-image" />
                          ) : (
                            <div className="art-piece-image-placeholder">Art</div>
                          )}
                        </div>
                        <div className="art-piece-info">
                          <h4 className="art-piece-title">{details.title}</h4>
                          <div className="art-piece-address">{formatAddress(address)}</div>
                          <a 
                            href={`#/art/${address}`} 
                            className="view-art-piece-link"
                          >
                            View Details
                          </a>
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
    </div>
  );
};

export default Account;
