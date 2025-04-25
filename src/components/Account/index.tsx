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
  const { isConnected, connectWallet, walletAddress, network } = useBlockchain();
  const [profileAddress, setProfileAddress] = useState<string | null>(null);
  const [profile, setProfile] = useState<ethers.Contract | null>(null);
  const [hasProfile, setHasProfile] = useState<boolean>(false);
  const [isArtist, setIsArtist] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  
  // Commission data
  const [recentCommissions, setRecentCommissions] = useState<string[]>([]);
  const [loadingCommissions, setLoadingCommissions] = useState<boolean>(false);
  
  // Profile image
  const [profileImage, setProfileImage] = useState<string | null>(null);
  
  // Create profile
  const [creatingProfile, setCreatingProfile] = useState<boolean>(false);
  const [configError, setConfigError] = useState<string | null>(null);

  useEffect(() => {
    const checkProfileStatus = async () => {
      if (!isConnected || !walletAddress) {
        setIsLoading(false);
        setHasProfile(false);
        return;
      }
      
      try {
        setIsLoading(true);
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
          
          if (profileContract) {
            // Get artist status
            const artistStatus = await profileContract.isArtist();
            setIsArtist(artistStatus);
            
            // Get profile image
            try {
              const imageData = await profileContract.profileImage();
              if (imageData && imageData.length > 0) {
                // Convert bytes to data URL
                const blob = new Blob([imageData], { type: 'image/avif' });
                const imageUrl = URL.createObjectURL(blob);
                setProfileImage(imageUrl);
              }
            } catch (err) {
              console.error("Error loading profile image:", err);
            }
            
            // Load recent commissions
            loadRecentCommissions(profileContract);
          }
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
        setIsLoading(false);
      }
    };
    
    checkProfileStatus();
    
    // Cleanup function
    return () => {
      // Revoke any object URLs to avoid memory leaks
      if (profileImage) {
        URL.revokeObjectURL(profileImage);
      }
    };
  }, [isConnected, walletAddress, network]);
  
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
      setIsLoading(true);
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
      setIsLoading(false);
    }
  };
  
  if (!isConnected) {
    return (
      <div className="account-container">
        <h2>Your Account</h2>
        <div className="account-card connect-card">
          <p>Connect your wallet to view your profile</p>
          <button className="connect-button" onClick={connectWallet}>Connect Wallet</button>
        </div>
      </div>
    );
  }
  
  if (isLoading) {
    return (
      <div className="account-container">
        <h2>Your Account</h2>
        <div className="loading-spinner">Loading profile...</div>
      </div>
    );
  }
  
  if (configError) {
    return (
      <div className="account-container">
        <h2>Your Account</h2>
        <div className="account-card error-card">
          <h3>Configuration Error</h3>
          <p>{configError}</p>
          <p>Current network: {network.name}</p>
        </div>
      </div>
    );
  }
  
  if (!hasProfile) {
    return (
      <div className="account-container">
        <h2>Your Account</h2>
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
      </div>
    );
  }
  
  return (
    <div className="account-container">
      <h2>Your Account</h2>
      
      {error && <div className="error-banner">{error}</div>}
      
      <div className="account-grid">
        <div className="account-card profile-card">
          <div className="profile-header">
            <div className="profile-image-container">
              {profileImage ? (
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
                <span>Artist Status: {isArtist ? 'Active' : 'Inactive'}</span>
                <button 
                  className={`artist-toggle ${isArtist ? 'deactivate' : 'activate'}`}
                  onClick={() => handleSetArtistStatus(!isArtist)}
                  disabled={isLoading}
                >
                  {isArtist ? 'Deactivate' : 'Activate'} Artist Mode
                </button>
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
      </div>
    </div>
  );
};

export default Account;
