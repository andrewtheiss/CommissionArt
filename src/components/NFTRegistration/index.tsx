import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useBlockchain } from '../../utils/BlockchainContext';
import { compressImage, getImageOrientation, revokePreviewUrl, CompressionResult, FormatType } from '../../utils/ImageCompressorUtil';
import './NFTRegistration.css';
import { ethers } from 'ethers';
import contractConfig from '../../assets/contract_config.json';
import abiLoader from '../../utils/abiLoader';
import ethersService from '../../utils/ethers-service';
import profileService from '../../utils/profile-service';

// Define ArtistForm as a separate component with onBack prop
const ArtistForm: React.FC<{
  artworkTitle: string;
  setArtworkTitle: (title: string) => void;
  artworkDescription: string;
  setArtworkDescription: (desc: string) => void;
  descriptionBytes: number;
  selectedImage: File | null;
  setSelectedImage: (file: File | null) => void;
  originalPreviewUrl: string | null;
  setOriginalPreviewUrl: (url: string | null) => void;
  compressedResult: CompressionResult | null;
  setCompressedResult: (result: CompressionResult | null) => void;
  isCompressing: boolean;
  setIsCompressing: (compressing: boolean) => void;
  imageOrientation: 'portrait' | 'landscape' | 'square' | null;
  setImageOrientation: (orientation: 'portrait' | 'landscape' | 'square' | null) => void;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  isTrulyConnected: boolean;
  connectWallet: () => void;
  walletAddress: string | null;
  networkType: string;
  switchToLayer: (layer: 'l1' | 'l2' | 'l3', environment: 'testnet' | 'mainnet') => void;
  hasProfile: boolean;
  onBack: () => void;
}> = ({
  artworkTitle,
  setArtworkTitle,
  artworkDescription,
  setArtworkDescription,
  descriptionBytes,
  selectedImage,
  setSelectedImage,
  originalPreviewUrl,
  setOriginalPreviewUrl,
  compressedResult,
  setCompressedResult,
  isCompressing,
  setIsCompressing,
  imageOrientation,
  setImageOrientation,
  fileInputRef,
  isTrulyConnected,
  connectWallet,
  walletAddress,
  networkType,
  switchToLayer,
  hasProfile,
  onBack,
}) => {
  const handleTitleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setArtworkTitle(e.target.value);
  }, [setArtworkTitle]);

  const handleDescriptionChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value;
    const bytes = new TextEncoder().encode(text).length;
    if (bytes <= 200) {
      setArtworkDescription(text);
    }
  }, [setArtworkDescription]);

  const handleImageSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (originalPreviewUrl) revokePreviewUrl(originalPreviewUrl);
    if (compressedResult?.preview) revokePreviewUrl(compressedResult.preview);

    setSelectedImage(file);
    const previewUrl = URL.createObjectURL(file);
    setOriginalPreviewUrl(previewUrl);

    const img = new Image();
    img.onload = () => {
      const orientation = getImageOrientation(img.width, img.height);
      setImageOrientation(orientation);
      compressImageFile(file);
    };
    img.src = previewUrl;
  };

  const compressImageFile = async (file: File) => {
    setIsCompressing(true);
    try {
      const result = await compressImage(file, 'image/avif');
      setCompressedResult(result);
    } catch (error) {
      console.error('Error compressing image:', error);
    } finally {
      setIsCompressing(false);
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleRegisterArtwork = async () => {
    if (!isTrulyConnected) {
      alert("Please connect your wallet to register your artwork");
      connectWallet();
      return;
    }
    if (!selectedImage || !compressedResult || isCompressing) {
      alert("Please upload an image for your artwork");
      return;
    }
    if (!artworkTitle.trim()) {
      alert("Please enter a title for your artwork");
      return;
    }

    try {
      // Show loading state first
      setIsCompressing(true); // Reuse the compressing state to show loading

      // First, make sure we're on the AnimeChain L3 network
      if (networkType !== 'animechain') {
        await switchToLayer('l3', 'mainnet');
      }

      // Get the signer for transaction
      const signer = await ethersService.getSigner();
      if (!signer) {
        throw new Error("Failed to get signer");
      }

      // Convert the image to bytes
      if (!compressedResult.blob) {
        throw new Error("Compressed image blob is not available");
      }
      
      // Convert the image to bytes
      const imageData = new Uint8Array(await compressedResult.blob.arrayBuffer());
      const titleStr = artworkTitle.trim();
      const descriptionBytes = new TextEncoder().encode(artworkDescription);

      // Get the commissionHub address from the config
      const commissionHubAddress = contractConfig.networks.mainnet.commissionHub.address || ethers.ZeroAddress;

      if (hasProfile) {
        // Register artwork via profile
        console.log("Registering artwork via Profile...");
        
        // Get the profile contract
        const profileContract = await profileService.getMyProfile();
        if (!profileContract) {
          throw new Error("Failed to get profile contract");
        }
        
        // Use the ArtPiece address as the factory address (temporary solution)
        const artPieceAddress = contractConfig.networks.mainnet.artPiece.address;
        if (!artPieceAddress) {
          throw new Error("ArtPiece address not configured");
        }
        
        // Call the profile's createArtPiece function
        const tx = await profileContract.createArtPiece(
          artPieceAddress,
          imageData,
          titleStr,
          descriptionBytes,
          true, // is artist
          ethers.ZeroAddress, // no other party
          commissionHubAddress,
          false // not AI generated
        );
        
        // Wait for the transaction to be mined
        const receipt = await tx.wait();
        
        // Note: You'll need to determine how to extract the art piece address from the receipt
        // This depends on the event data structure from your contract
        
        setIsCompressing(false);
        alert(`Artwork registered successfully via Profile!`);
      } else {
        // Direct ArtPiece creation flow for users without a profile
        console.log("Deploying ArtPiece contract directly...");

        // Get the ArtPiece contract factory from the ABI
        const artPieceAbi = abiLoader.loadABI('ArtPiece');
        console.log("ArtPiece ABI loaded:", artPieceAbi ? "Success" : "Failed");
        
        if (artPieceAbi) {
          // Debug the ABI methods
          const methods = artPieceAbi
            .filter((item: any) => item.type === 'function')
            .map((item: any) => item.name);
          console.log("Available ABI methods:", methods);
          console.log("Has aiGenerated method:", methods.includes('aiGenerated'));
          console.log("Has getAIGenerated method:", methods.includes('getAIGenerated'));
        }
        
        if (!artPieceAbi) {
          throw new Error("Failed to load ArtPiece ABI");
        }
        
        try {
          // There are two options:
          // 1. Create a profile and then register the artwork through the profile
          // 2. Use a direct contract deployment 
          
          // For simplicity and better user experience, let's create a profile for them
          // and register the artwork at the same time
          
          // Get the ProfileHub contract
          const profileHubAddress = contractConfig.networks.mainnet.profileHub.address;
          const profileHubAbi = abiLoader.loadABI('ProfileHub');
          
          if (!profileHubAddress || !profileHubAbi) {
            throw new Error("ProfileHub configuration not found");
          }
          
          const profileHub = new ethers.Contract(profileHubAddress, profileHubAbi, signer);
          
          // Get the template ArtPiece address
          const artPieceTemplateAddress = contractConfig.networks.mainnet.artPiece.address;
          if (!artPieceTemplateAddress) {
            throw new Error("ArtPiece template address not configured");
          }
          
          console.log("Creating profile and registering artwork in one transaction...");
          
          // Create profile and register artwork
          const tx = await profileHub.createNewCommissionAndRegisterProfile(
            artPieceTemplateAddress,
            imageData,
            titleStr,
            descriptionBytes,
            true, // is artist
            ethers.ZeroAddress, // no other party
            commissionHubAddress,
            false // not AI generated
          );
          
          console.log("Transaction sent:", tx.hash);
          
          // Wait for the transaction to be mined
          const receipt = await tx.wait();
          console.log("Transaction confirmed:", receipt);
          
          // Extract profile and art piece addresses from the event logs
          let profileAddress = null;
          let artPieceAddress = null;
          
          for (const log of receipt.logs) {
            try {
              const parsedLog = profileHub.interface.parseLog(log);
              if (parsedLog && parsedLog.name === "ProfileCreated") {
                profileAddress = parsedLog.args.profile;
              } else if (parsedLog && parsedLog.name === "ArtPieceCreated") {
                artPieceAddress = parsedLog.args.art_piece;
              }
            } catch (error) {
              // Skip logs that can't be parsed
              continue;
            }
          }
          
          if (!profileAddress || !artPieceAddress) {
            throw new Error("Failed to extract profile or artwork addresses from receipt");
          }
          
          setIsCompressing(false);
          alert(`Profile created and artwork registered successfully!\nProfile: ${profileAddress}\nArtwork: ${artPieceAddress}`);
          console.log("Registration successful:", {
            profileAddress,
            artPieceAddress,
            artist: walletAddress,
            owner: walletAddress,
            artworkTitle: titleStr,
            imageSize: compressedResult.compressedSize,
            imageFormat: compressedResult.format,
            dimensions: compressedResult.dimensions,
          });
          
        } catch (error) {
          console.error("Error deploying ArtPiece contract:", error);
          setIsCompressing(false);
          
          if (String(error).includes("execution reverted")) {
            alert(`Error: Your transaction was reverted. This could be because the contract already exists or there was an issue with the parameters.`);
          } else {
            alert(`Error deploying artwork contract: ${error instanceof Error ? error.message : String(error)}`);
          }
        }
      }
    } catch (error) {
      setIsCompressing(false);
      console.error("Error registering artwork:", error);
      alert(`Error registering artwork: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  return (
    <div className="registration-form">
      <h3>Artist Registration</h3>
      <div className="form-instructions">
        <p>As an artist, you'll be able to create and register your artwork on-chain.</p>
        {!isTrulyConnected && (
          <p className="connect-reminder">
            <span className="highlight">You can fill out the form now</span>, and connect your wallet when you're ready to register.
          </p>
        )}
        {isTrulyConnected && hasProfile && (
          <p className="profile-info highlight-box">
            <span className="highlight">Your profile was detected!</span> Your artwork will be registered through your profile.
          </p>
        )}
      </div>
      <div className={`artist-form-container ${imageOrientation || ''}`}>
        {imageOrientation === 'landscape' && compressedResult && compressedResult.preview ? (
          <div className="artwork-banner">
            <div className="artwork-preview landscape">
              <img src={compressedResult.preview} alt="Artwork Preview" className="preview-image" />
              <div className="preview-overlay">
                <div className="preview-actions">
                  <button onClick={handleUploadClick} className="change-image-btn">
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
              <div className="upload-placeholder" onClick={handleUploadClick}>
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
                <img src={compressedResult.preview} alt="Artwork Preview" className="preview-image" />
                <div className="preview-overlay">
                  <div className="preview-actions">
                    <button onClick={handleUploadClick} className="change-image-btn">
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
        <form>
          <div className="form-content">
            <div className="form-group">
              <label htmlFor="artwork-title">
                Artwork Title <span className="required">*</span>
              </label>
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
              <button
                type="button"
                className={`submit-button ${hasProfile ? 'profile-button' : ''}`}
                disabled={!compressedResult || isCompressing}
                onClick={handleRegisterArtwork}
              >
                {hasProfile ? 'Register Artwork in Profile' : 'Register Artwork'}
              </button>
            </div>
          </div>
          <div className="form-footer">
            <button type="button" className="form-back-button" onClick={onBack}>
              Back
            </button>
            <button
              type="button"
              className={`submit-button ${hasProfile ? 'profile-button' : ''}`}
              disabled={!compressedResult || isCompressing}
              onClick={handleRegisterArtwork}
            >
              {hasProfile ? 'Register Artwork in Profile' : 'Register Artwork'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const NFTRegistration: React.FC = () => {
  const [userType, setUserType] = useState<'none' | 'artist' | 'commissioner'>('none');
  const { isConnected, connectWallet, walletAddress, networkType, switchToLayer } = useBlockchain();

  const [artworkTitle, setArtworkTitle] = useState<string>('');
  const [artworkDescription, setArtworkDescription] = useState<string>('');
  const [descriptionBytes, setDescriptionBytes] = useState<number>(0);
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [originalPreviewUrl, setOriginalPreviewUrl] = useState<string | null>(null);
  const [compressedResult, setCompressedResult] = useState<CompressionResult | null>(null);
  const [isCompressing, setIsCompressing] = useState(false);
  const [imageOrientation, setImageOrientation] = useState<'portrait' | 'landscape' | 'square' | null>(null);
  const [hasProfile, setHasProfile] = useState(false);
  const [checkingProfile, setCheckingProfile] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const isTrulyConnected = isConnected && !!walletAddress;

  // Check if user has a profile when they connect
  useEffect(() => {
    const checkForProfile = async () => {
      if (isTrulyConnected) {
        setCheckingProfile(true);
        try {
          const profileExists = await profileService.hasProfile();
          setHasProfile(profileExists);
          console.log("Profile check:", profileExists ? "User has a profile" : "User has no profile");
        } catch (error) {
          console.error("Error checking for profile:", error);
          setHasProfile(false);
        } finally {
          setCheckingProfile(false);
        }
      } else {
        setHasProfile(false);
      }
    };
    
    checkForProfile();
  }, [isTrulyConnected, walletAddress]);

  useEffect(() => {
    const bytes = new TextEncoder().encode(artworkDescription).length;
    setDescriptionBytes(bytes);
  }, [artworkDescription]);

  // Updated useEffect to only revoke URLs without resetting userType
  useEffect(() => {
    return () => {
      if (originalPreviewUrl) revokePreviewUrl(originalPreviewUrl);
      if (compressedResult?.preview) revokePreviewUrl(compressedResult.preview);
    };
  }, [originalPreviewUrl, compressedResult]);

  const handleUserTypeSelection = (type: 'artist' | 'commissioner') => {
    setUserType(type);
  };

  const handleDisconnect = () => {
    if (window.ethereum && window.ethereum.removeAllListeners) {
      try {
        window.ethereum.removeAllListeners();
      } catch (err) {
        console.error("Failed to remove ethereum listeners:", err);
      }
    }
    localStorage.setItem('active_tab', 'registration');
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

  const CommissionerForm = () => (
    <div className="registration-form">
      <h3>Commissioner Registration</h3>
      <div className="form-instructions">
        <p>As a commissioner, you can request and fund new commissioned artworks.</p>
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

  return (
    <div className="nft-registration-container">
      <h2>Commission Art</h2>
      <ConnectionBar />
      {userType === 'none' ? (
        <div className="user-type-selection">
          <p className="selection-prompt">I'm a:</p>
          <div className="selection-buttons">
            <button className="selection-button artist-button" onClick={() => handleUserTypeSelection('artist')}>
              Artist
            </button>
            <button className="selection-button commissioner-button" onClick={() => handleUserTypeSelection('commissioner')}>
              Commissioner
            </button>
          </div>
        </div>
      ) : userType === 'artist' ? (
        <ArtistForm
          artworkTitle={artworkTitle}
          setArtworkTitle={setArtworkTitle}
          artworkDescription={artworkDescription}
          setArtworkDescription={setArtworkDescription}
          descriptionBytes={descriptionBytes}
          selectedImage={selectedImage}
          setSelectedImage={setSelectedImage}
          originalPreviewUrl={originalPreviewUrl}
          setOriginalPreviewUrl={setOriginalPreviewUrl}
          compressedResult={compressedResult}
          setCompressedResult={setCompressedResult}
          isCompressing={isCompressing}
          setIsCompressing={setIsCompressing}
          imageOrientation={imageOrientation}
          setImageOrientation={setImageOrientation}
          fileInputRef={fileInputRef}
          isTrulyConnected={isTrulyConnected}
          connectWallet={connectWallet}
          walletAddress={walletAddress}
          networkType={networkType}
          switchToLayer={switchToLayer}
          hasProfile={hasProfile}
          onBack={() => setUserType('none')}
        />
      ) : (
        <CommissionerForm />
      )}
    </div>
  );
};

export default NFTRegistration;