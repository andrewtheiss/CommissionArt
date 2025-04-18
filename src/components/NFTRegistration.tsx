import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useBlockchain } from '../utils/BlockchainContext';
import { compressImage, getImageOrientation, revokePreviewUrl, CompressionResult, FormatType } from '../utils/ImageCompressorUtil';
import './NFTRegistration.css';

const NFTRegistration: React.FC = () => {
  const [userType, setUserType] = useState<'none' | 'artist' | 'commissioner'>('none');
  const { isConnected, connectWallet, walletAddress, networkType } = useBlockchain();
  
  // Form state
  const [artworkTitle, setArtworkTitle] = useState<string>('');
  const [artworkDescription, setArtworkDescription] = useState<string>('');
  const [descriptionBytes, setDescriptionBytes] = useState<number>(0);
  
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

  // Calculate description byte length when it changes
  useEffect(() => {
    const bytes = new TextEncoder().encode(artworkDescription).length;
    setDescriptionBytes(bytes);
  }, [artworkDescription]);

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

  // Memoized input change handlers to preserve focus
  const handleTitleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setArtworkTitle(e.target.value);
  }, []);

  const handleDescriptionChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value;
    const bytes = new TextEncoder().encode(text).length;
    if (bytes <= 200) {
      setArtworkDescription(text);
    }
  }, []);

  // Handle artwork registration
  const handleRegisterArtwork = async () => {
    // If not connected, prompt to connect wallet first
    if (!isTrulyConnected) {
      alert("Please connect your wallet to register your artwork");
      connectWallet();
      return;
    }
    
    // Validate form
    if (!selectedImage || !compressedResult || isCompressing) {
      alert("Please upload an image for your artwork");
      return;
    }
    
    if (!artworkTitle.trim()) {
      alert("Please enter a title for your artwork");
      return;
    }
    
    // Here we would implement the actual contract creation
    // For now, just log the information
    console.log("Registering artwork:", {
      artist: walletAddress, // Use wallet address as the artist
      artworkTitle,
      artworkDescription,
      descriptionBytes,
      imageSize: compressedResult.compressedSize,
      imageFormat: compressedResult.format,
      dimensions: compressedResult.dimensions
    });
    
    alert("Artwork registration initiated! This would create an ArtPiece in a real implementation.");
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

  // Artist form that's always fully functional
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
              <span className="highlight">You can fill out the form now</span>, and connect your wallet when you're ready to register.
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
          
          {/* Side image upload section for portrait/square or no image yet */}
          {(imageOrientation !== 'landscape' || !compressedResult || !compressedResult.preview) && (
            <div className="artwork-upload-section">
              <input 
                ref={fileInputRef}
                type="file" 
                id="artwork-image"
                accept="image/*"
                onChange={handleImageSelect}
                className="file-input"
                style={{ display: 'none' }}
              />
              
              {!compressedResult || !compressedResult.preview ? (
                <div 
                  className="upload-placeholder"
                  onClick={handleUploadClick}
                >
                  <div className="placeholder-content">
                    <div className="upload-icon">+</div>
                    <div className="upload-text">Upload Image</div>
                    <div className="upload-subtext">Max size: 45KB (will be automatically compressed)</div>
                  </div>
                </div>
              ) : isCompressing ? (
                <div className="compressing-indicator">
                  <div className="spinner"></div>
                  <div>Compressing image...</div>
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
          <form>
            <div className="form-content">
              <div className="form-group">
                <label htmlFor="artwork-title">Artwork Title <span className="required">*</span></label>
                <input 
                  type="text" 
                  id="artwork-title" 
                  className="form-input"
                  placeholder="Enter the title of your artwork"
                  value={artworkTitle}
                  onChange={handleTitleChange}
                  required
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="artwork-description">
                  Description <span className="byte-counter">{descriptionBytes}/200 bytes</span>
                </label>
                <textarea 
                  id="artwork-description" 
                  className="form-textarea"
                  placeholder="Describe your artwork..."
                  rows={4}
                  value={artworkDescription}
                  onChange={handleDescriptionChange}
                  maxLength={200}
                ></textarea>
              </div>
              
              <div className="form-actions">
                {/* First "Register Artwork" button */}
                <button 
                  type="button" 
                  className="submit-button"
                  disabled={!compressedResult || isCompressing}
                  onClick={handleRegisterArtwork}
                >
                  Register Artwork
                </button>
              </div>
            </div>
            
            <div className="form-footer">
              <button type="button" className="form-back-button" onClick={() => setUserType('none')}>
                Back
              </button>
              
              {/* Second identical "Register Artwork" button */}
              <button 
                type="button" 
                className="submit-button"
                disabled={!compressedResult || isCompressing}
                onClick={handleRegisterArtwork}
              >
                Register Artwork
              </button>
            </div>
          </form>
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
              <span className="highlight">You can fill out the form now</span>, and connect your wallet when you're ready to register.
            </p>
          )}
        </div>
        
        <form>
          <div className="form-content">
            <div className="form-group">
              <label>Commissioner form coming soon...</label>
              <p>Fill out your details and register when you're ready.</p>
            </div>
          </div>
          
          <div className="form-footer">
            <button type="button" className="form-back-button" onClick={() => setUserType('none')}>
              Back
            </button>
            
            <button 
              type="button" 
              className="submit-button"
              onClick={() => {
                if (!isTrulyConnected) {
                  alert("Please connect your wallet to register as a commissioner");
                  connectWallet();
                } else {
                  alert("Commissioner registration would be processed here");
                }
              }}
            >
              Register as Commissioner
            </button>
          </div>
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