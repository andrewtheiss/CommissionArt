import React, { useState, useEffect, useRef } from 'react';
import { useBlockchain } from '../utils/BlockchainContext';
import { compressImage, getImageOrientation, revokePreviewUrl, CompressionResult, FormatType } from '../utils/ImageCompressorUtil';
import './NFTRegistration.css';

const NFTRegistration: React.FC = () => {
  const [userType, setUserType] = useState<'none' | 'artist' | 'commissioner'>('none');
  const { isConnected, connectWallet, walletAddress, networkType } = useBlockchain();
  
  // Image states for artist registration
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [originalPreviewUrl, setOriginalPreviewUrl] = useState<string | null>(null);
  const [compressedResult, setCompressedResult] = useState<CompressionResult | null>(null);
  const [isCompressing, setIsCompressing] = useState(false);
  const [imageOrientation, setImageOrientation] = useState<'portrait' | 'landscape' | 'square' | null>(null);
  
  // Refs
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Consider a wallet truly connected only when we have both isConnected flag AND a wallet address
  const isTrulyConnected = isConnected && !!walletAddress;

  // Reset form when component unmounts
  useEffect(() => {
    return () => {
      setUserType('none');
      
      // Clean up image preview URLs
      if (originalPreviewUrl) {
        revokePreviewUrl(originalPreviewUrl);
      }
      if (compressedResult?.preview) {
        revokePreviewUrl(compressedResult.preview);
      }
    };
  }, []);

  const handleUserTypeSelection = (type: 'artist' | 'commissioner') => {
    setUserType(type);
  };

  // Since we don't have a built-in disconnect method in our context,
  // we'll handle it by clearing state and forcing a reload
  const handleDisconnect = () => {
    // For future improvement: This should ideally be moved to the BlockchainContext
    if (window.ethereum && window.ethereum.removeAllListeners) {
      try {
        window.ethereum.removeAllListeners();
      } catch (err) {
        console.error("Failed to remove ethereum listeners:", err);
      }
    }
    
    // Store the current tab before refresh
    localStorage.setItem('active_tab', 'registration');
    
    // Use localStorage to indicate we want to disconnect on reload
    localStorage.setItem('wallet_disconnect_requested', 'true');
    
    // Force a proper wallet disconnect by clearing any cached provider state
    if (window.localStorage) {
      // Clear any wallet-related cached data
      const keysToRemove = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && (
            key.includes('wallet') || 
            key.includes('metamask') || 
            key.includes('ethereum') ||
            key.includes('connectedWallet') ||
            key.includes('connect') ||
            key.includes('walletconnect')
        )) {
          keysToRemove.push(key);
        }
      }
      
      // Remove the keys we found
      keysToRemove.forEach(key => {
        localStorage.removeItem(key);
      });
    }
    
    // Reload the page to clear the connection state
    window.location.reload();
  };

  // On component mount, check if we have a disconnect request in localStorage
  useEffect(() => {
    if (localStorage.getItem('wallet_disconnect_requested') === 'true') {
      // Clear the flag
      localStorage.removeItem('wallet_disconnect_requested');
      console.log("Wallet disconnected as requested");
      
      // If we're on this tab after a disconnect, let's manually disconnect from the wallet
      if (window.ethereum) {
        try {
          // Force the wallet UI to show as disconnected
          console.log("Clearing wallet connection after disconnect request");
          
          // Forcibly clear any provider and wallet state
          if (window.ethereum._state && window.ethereum._state.accounts) {
            window.ethereum._state.accounts = [];
          }
        } catch (err) {
          console.error("Error forcing wallet disconnect:", err);
        }
      }
    }
  }, []);

  // Handle file selection for artist image upload
  const handleImageSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Clean up previous URLs
    if (originalPreviewUrl) {
      revokePreviewUrl(originalPreviewUrl);
    }
    if (compressedResult?.preview) {
      revokePreviewUrl(compressedResult.preview);
    }

    // Set the selected file
    setSelectedImage(file);
    
    // Create preview URL
    const previewUrl = URL.createObjectURL(file);
    setOriginalPreviewUrl(previewUrl);
    
    // Determine orientation
    const img = new Image();
    img.onload = () => {
      const orientation = getImageOrientation(img.width, img.height);
      setImageOrientation(orientation);
      
      // Auto-compress the image
      compressImageFile(file);
    };
    img.src = previewUrl;
  };

  // Auto-compress the image when uploaded
  const compressImageFile = async (file: File) => {
    setIsCompressing(true);
    try {
      // Use AVIF as the preferred format
      const result = await compressImage(file, 'image/avif');
      setCompressedResult(result);
    } catch (error) {
      console.error('Error compressing image:', error);
    } finally {
      setIsCompressing(false);
    }
  };

  // Trigger the file input click
  const handleUploadClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  // Connection Bar Component
  const ConnectionBar = () => (
    <div className="connection-bar">
      {!isTrulyConnected ? (
        <>
          <div className="connection-status disconnected">
            <span className="status-icon"></span>
            <span className="status-text">Wallet Not Connected</span>
          </div>
          <button 
            className="connect-wallet-button" 
            onClick={connectWallet}
          >
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
              <span className="status-text">Connected to: <span className="network-name">
                {networkType === 'arbitrum_testnet' ? 'L3 (Arbitrum Sepolia)' : networkType}
              </span></span>
              <span className="wallet-address">{walletAddress ? `${walletAddress.substring(0, 6)}...${walletAddress.substring(walletAddress.length - 4)}` : 'Not connected'}</span>
            </div>
          </div>
          <button 
            className="disconnect-wallet-button" 
            onClick={handleDisconnect}
          >
            Disconnect
          </button>
        </>
      )}
    </div>
  );

  // Artist form that adapts based on connection status
  const ArtistForm = () => {
    return (
      <div className="registration-form">
        <h3>Artist Registration</h3>
        <div className="form-instructions">
          <p>
            As an artist, you'll be able to create and register your artwork on-chain.
          </p>
          {!isTrulyConnected && (
            <p className="connect-reminder">
              <span className="highlight">Please connect your wallet</span> to access the full artist registration features.
            </p>
          )}
        </div>
        
        <div className={`artist-form-container ${imageOrientation || ''}`}>
          {/* For landscape images, show preview across the top */}
          {imageOrientation === 'landscape' && compressedResult && compressedResult.preview ? (
            <div className="artwork-banner">
              <div className="artwork-preview landscape">
                <img 
                  src={compressedResult.preview} 
                  alt="Artwork Preview" 
                  className="preview-image"
                />
                <div className="preview-overlay">
                  <div className="preview-actions">
                    <button 
                      onClick={handleUploadClick}
                      className="change-image-btn"
                    >
                      Change Image
                    </button>
                  </div>
                  <div className="image-info">
                    <span>Size: {compressedResult.compressedSize.toFixed(2)} KB</span>
                    <span>Format: {compressedResult.format}</span>
                    <span>Dimensions: {compressedResult.dimensions.width}x{compressedResult.dimensions.height}</span>
                  </div>
                </div>
              </div>
            </div>
          ) : null}
          
          {/* Image Upload Section - Only show for non-landscape or when no image is selected */}
          {(imageOrientation !== 'landscape' || !compressedResult || !compressedResult.preview) && (
            <div className="artwork-upload-section">
              <input
                type="file"
                accept="image/*"
                onChange={handleImageSelect}
                ref={fileInputRef}
                style={{ display: 'none' }}
              />
              
              {!compressedResult || !compressedResult.preview ? (
                <div 
                  className="upload-placeholder"
                  onClick={handleUploadClick}
                >
                  <div className="upload-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                      <circle cx="8.5" cy="8.5" r="1.5"></circle>
                      <polyline points="21 15 16 10 5 21"></polyline>
                    </svg>
                  </div>
                  <span>Upload Artwork</span>
                  {isCompressing && <div className="compressing-indicator">Compressing...</div>}
                </div>
              ) : (
                <div className={`artwork-preview ${imageOrientation || ''}`}>
                  <img 
                    src={compressedResult.preview} 
                    alt="Artwork Preview" 
                    className="preview-image"
                  />
                  <div className="preview-overlay">
                    <div className="preview-actions">
                      <button 
                        onClick={handleUploadClick}
                        className="change-image-btn"
                      >
                        Change Image
                      </button>
                    </div>
                    <div className="image-info">
                      <span>Size: {compressedResult.compressedSize.toFixed(2)} KB</span>
                      <span>Format: {compressedResult.format}</span>
                      <span>Dimensions: {compressedResult.dimensions.width}x{compressedResult.dimensions.height}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
          
          {/* Registration Form Details */}
          <div className="registration-details">
            <form>
              {isTrulyConnected ? (
                // Connected artist form
                <div className="form-content">
                  <div className="form-group">
                    <label htmlFor="artist-name">Artist Name</label>
                    <input 
                      type="text" 
                      id="artist-name" 
                      className="form-input"
                      placeholder="Enter your artist name"
                    />
                  </div>
                  
                  <div className="form-group">
                    <label htmlFor="artwork-title">Artwork Title</label>
                    <input 
                      type="text" 
                      id="artwork-title" 
                      className="form-input"
                      placeholder="Enter the title of your artwork"
                    />
                  </div>
                  
                  <div className="form-group">
                    <label htmlFor="artwork-description">Description</label>
                    <textarea 
                      id="artwork-description" 
                      className="form-textarea"
                      placeholder="Describe your artwork..."
                      rows={4}
                    ></textarea>
                  </div>
                  
                  <div className="form-actions">
                    <button 
                      type="button" 
                      className="submit-button"
                      disabled={!compressedResult || isCompressing}
                    >
                      Register Artwork
                    </button>
                  </div>
                </div>
              ) : (
                // Not connected artist form
                <div className="form-content disabled">
                  <div className="form-group">
                    <label>Artist features will be available once connected</label>
                    <div className="placeholder-content"></div>
                  </div>
                </div>
              )}
              <button type="button" className="form-back-button" onClick={() => setUserType('none')}>
                Back
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  };

  // Commissioner form that adapts based on connection status
  const CommissionerForm = () => {
    return (
      <div className="registration-form">
        <h3>Commissioner Registration</h3>
        <div className="form-instructions">
          <p>
            As a commissioner, you can request and fund new commissioned artworks.
          </p>
          {!isTrulyConnected && (
            <p className="connect-reminder">
              <span className="highlight">Please connect your wallet</span> to access the full commissioner registration features.
            </p>
          )}
        </div>
        <form>
          {isTrulyConnected ? (
            // Connected commissioner form
            <div className="form-content">
              <div className="form-group">
                <label>Commissioner form coming soon...</label>
                <p>Your wallet is connected and you can register as a commissioner.</p>
              </div>
            </div>
          ) : (
            // Not connected commissioner form
            <div className="form-content disabled">
              <div className="form-group">
                <label>Commissioner features will be available once connected</label>
                <div className="placeholder-content"></div>
              </div>
            </div>
          )}
          <button type="button" className="form-back-button" onClick={() => setUserType('none')}>
            Back
          </button>
        </form>
      </div>
    );
  };

  return (
    <div className="nft-registration-container">
      <h2>Commission Art</h2>
      
      {/* Always show the connection bar at the top */}
      <ConnectionBar />
      
      {/* Always show the user type selection or corresponding form */}
      {userType === 'none' ? (
        <div className="user-type-selection">
          <p className="selection-prompt">I'm a:</p>
          <div className="selection-buttons">
            <button 
              className="selection-button artist-button"
              onClick={() => handleUserTypeSelection('artist')}
            >
              Artist
            </button>
            <button 
              className="selection-button commissioner-button"
              onClick={() => handleUserTypeSelection('commissioner')}
            >
              Commissioner
            </button>
          </div>
        </div>
      ) : userType === 'artist' ? (
        <ArtistForm />
      ) : (
        <CommissionerForm />
      )}
    </div>
  );
};

export default NFTRegistration; 