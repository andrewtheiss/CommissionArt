import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useBlockchain } from '../../utils/BlockchainContext';
import { getImageOrientation, revokePreviewUrl, compressImage } from '../../utils/ImageCompressorUtil';
import type { FormatType, CompressionResult as UtilCompressionResult } from '../../utils/ImageCompressorUtil';
import { formatTokenURI, reduceTokenURISize, hashString, extractImageFromTokenURI, createComparisonHashes } from '../../utils/TokenURIFormatter';
import './NFTRegistration.css';
import { ethers } from 'ethers';
import contractConfig from '../../assets/contract_config.json';
import abiLoader from '../../utils/abiLoader';
import ethersService from '../../utils/ethers-service';
import profileService from '../../utils/profile-service';

// Add interfaces for our new compression code:
interface DisplayResult {
  preview: string | null;
  compressedSize: number;
  originalSize: number;
  dimensions: { width: number; height: number };
  format: string;
  blob: Blob | null;
}

// Define ArtistForm as a separate component with onBack prop
const ArtistForm: React.FC<{
  artworkTitle: string;
  setArtworkTitle: (title: string) => void;
  artworkDescription: string;
  setArtworkDescription: (desc: string) => void;
  selectedImage: File | null;
  setSelectedImage: (file: File | null) => void;
  originalPreviewUrl: string | null;
  setOriginalPreviewUrl: (url: string | null) => void;
  compressedResult: DisplayResult | null;
  setCompressedResult: (result: DisplayResult | null) => void;
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
  preferredFormat: FormatType;
  setPreferredFormat: (format: FormatType) => void;
  onBack: () => void;
}> = ({
  artworkTitle,
  setArtworkTitle,
  artworkDescription,
  setArtworkDescription,
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
  preferredFormat,
  setPreferredFormat,
  onBack,
}) => {
  const handleTitleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setArtworkTitle(e.target.value);
  }, [setArtworkTitle]);

  const handleDescriptionChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value;
    if (text.length <= 200) {
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
      URL.revokeObjectURL(previewUrl); // Clean up object URL after loading image
    };
    img.src = previewUrl;
  };

  const compressImageFile = async (file: File) => {
    if (!file) return;
    
    setIsCompressing(true);
    
    try {
      const result: UtilCompressionResult = await compressImage(file, preferredFormat, 1000, 43.5);

      if (result.success && result.blob && result.preview) {
        setCompressedResult({
          preview: result.preview,
          compressedSize: result.compressedSize,
          originalSize: result.originalSize,
          dimensions: result.dimensions,
          format: result.format,
          blob: result.blob,
        });
        
        console.log(`Compression successful:
          - Original size: ${result.originalSize.toFixed(2)} KB
          - Compressed size: ${result.compressedSize.toFixed(2)} KB (${result.blob.size} bytes)
          - Dimensions: ${result.dimensions.width}x${result.dimensions.height}
          - Format: ${result.format}
          - Target reached: ${result.targetReached}
        `);

        const orientation = getImageOrientation(result.dimensions.width, result.dimensions.height);
        setImageOrientation(orientation);

      } else {
        throw new Error(result.error || 'Compression failed with unknown error');
      }
    } catch (error) {
      console.error('Error compressing image:', error);
      alert(`Failed to compress image: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsCompressing(false);
    }
  };

  const handleUploadClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const proceedWithRegistration = async (
    titleStr: string,
    descriptionStr: string,
    imageDataArray: Uint8Array,
    mimeType: string
  ) => {
    if (!isTrulyConnected) {
      alert("Please connect your wallet to register your artwork");
      connectWallet();
      return;
    }
    
    try {
      if (networkType !== 'animechain') {
        await switchToLayer('l3', 'mainnet');
      }

      const signer = await ethersService.getSigner();
      if (!signer) {
        throw new Error("Failed to get signer");
      }
      
      const artCommissionHubAddress = contractConfig.networks.mainnet.artCommissionHub.address || ethers.ZeroAddress;

      if (hasProfile) {
        const profileContract = await profileService.getMyProfile();
        if (!profileContract) {
          throw new Error("Failed to get profile contract");
        }
        
        const artPieceAddress = contractConfig.networks.mainnet.artPiece.address;
        if (!artPieceAddress) {
          throw new Error("ArtPiece address not configured");
        }
        
        const bytesData = ethers.hexlify(ethers.concat([imageDataArray]));

        const dataSize = imageDataArray.length;
        if (dataSize > 45000) {
          throw new Error(`Image size (${dataSize} bytes) exceeds the contract limit of 45000 bytes. Please use a smaller image.`);
        }

        const tx = await profileContract.createArtPiece(
          artPieceAddress,
          bytesData, 
          mimeType,
          titleStr,      
          descriptionStr,
          true,
          ethers.ZeroAddress,
          artCommissionHubAddress,
          false
        );
        
        await tx.wait();
        alert(`Artwork registered successfully via Profile!`);

      } else {
        const artPieceAbi = abiLoader.loadABI('ArtPiece');
        if (!artPieceAbi) {
          throw new Error("Failed to load ArtPiece ABI");
        }
        
        const profileFactoryAndRegistryAddress = contractConfig.networks.mainnet.profileFactoryAndRegistry.address;
        const profileFactoryAndRegistryAbi = abiLoader.loadABI('ProfileFactoryAndRegistry');
        
        if (!profileFactoryAndRegistryAddress || !profileFactoryAndRegistryAbi) {
          throw new Error("ProfileFactoryAndRegistry configuration not found");
        }
        
        const profileFactoryAndRegistry = new ethers.Contract(profileFactoryAndRegistryAddress, profileFactoryAndRegistryAbi, signer);
        
        const artPieceTemplateAddress = contractConfig.networks.mainnet.artPiece.address;
        if (!artPieceTemplateAddress) {
          throw new Error("ArtPiece template address not configured");
        }
        
        const bytesData2 = ethers.hexlify(ethers.concat([imageDataArray]));
        const dataSize2 = imageDataArray.length;
        if (dataSize2 > 45000) {
          throw new Error(`Image size (${dataSize2} bytes) exceeds the contract limit of 45000 bytes. Please use a smaller image.`);
        }

        const tx = await profileFactoryAndRegistry.createNewArtPieceAndRegisterProfileAndAttachToHub(
          artPieceTemplateAddress,
          bytesData2,
          mimeType,
          titleStr,      
          descriptionStr,
          true, 
          ethers.ZeroAddress,
          artCommissionHubAddress,
          false
        );
        
        const receipt = await tx.wait();
        let profileAddress = null;
        let artPieceAddress = null;
        
        for (const log of receipt.logs) {
          try {
            const parsedLog = profileFactoryAndRegistry.interface.parseLog(log);
            if (parsedLog && parsedLog.name === "ProfileCreated") {
              profileAddress = parsedLog.args.profile;
            } else if (parsedLog && parsedLog.name === "ArtPieceCreated") {
              artPieceAddress = parsedLog.args.art_piece;
            }
          } catch (error) {
            continue;
          }
        }
        
        if (!profileAddress || !artPieceAddress) {
          throw new Error("Failed to extract profile or artwork addresses from receipt");
        }
        
        alert(`Profile created and artwork registered successfully!\nProfile: ${profileAddress}\nArtwork: ${artPieceAddress}`);
      }
    } catch (error) {
      console.error("Error registering artwork:", error);
      alert(`Error registering artwork: ${error instanceof Error ? error.message : String(error)}`);
      throw error;
    }
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
      setIsCompressing(true);

      if (!compressedResult.blob) {
        throw new Error("Compressed image blob is not available");
      }
      
      const titleStr = artworkTitle.trim();
      const descriptionStr = artworkDescription.trim();
      
      const imageDataArray = new Uint8Array(await compressedResult.blob.arrayBuffer());
      const formatStr = compressedResult.format.toLowerCase();

      await proceedWithRegistration(
        titleStr,
        descriptionStr,
        imageDataArray,
        formatStr
      );
    } catch (error) {
      // Error is alerted within proceedWithRegistration
    } finally {
      setIsCompressing(false);
    }
  };

  const handleLogByteArray = async () => {
    if (!compressedResult?.blob) return;
    const byteArray = new Uint8Array(await compressedResult.blob.arrayBuffer());
    console.log('Compressed Image Byte Array:', byteArray);
    alert('The byte array has been logged to the browser console.');
  };

  return (
    <div className="artist-form-wrapper">
      <div className={`artist-form-container ${imageOrientation || ''}`}>
        <div className="artwork-upload-section">
          {!selectedImage && !isCompressing && (
            <div
              className={`upload-placeholder ${imageOrientation || ''}`}
              onClick={handleUploadClick}
            >
              <div className="placeholder-content">
                <div className="upload-icon">📷</div>
                <div className="upload-text">Upload Artwork</div>
                <div className="upload-subtext">Max 43.5KB (AVIF/WebP recommended)</div>
              </div>
            </div>
          )}
          {isCompressing && (
            <div className={`compressing-indicator ${imageOrientation || ''}`}>
              <div className="spinner"></div>
              <span>Compressing...</span>
            </div>
          )}
          {originalPreviewUrl && !isCompressing && (
            <div className={`artwork-preview ${imageOrientation || ''}`}>
              <img
                src={originalPreviewUrl}
                alt="Artwork Preview"
                className="preview-image"
              />
              <div className="preview-overlay">
                <div className="preview-info">
                  {selectedImage && <p>Original: {(selectedImage.size / 1024).toFixed(2)} KB</p>}
                </div>
                <div className="preview-actions">
                  <button type="button" className="change-image-btn" onClick={handleUploadClick}>
                    Change Image
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
        <div className="compressed-preview-section">
          {compressedResult && !isCompressing && (
            <div className="artwork-preview compressed">
              <img
                src={compressedResult.preview || ''}
                alt="Compressed Artwork Preview"
                className="preview-image"
              />
              <div className="preview-overlay">
                <div className="preview-info compressed-info">
                  <p>
                    <strong>{compressedResult.format}</strong>
                  </p>
                  <p>{compressedResult.dimensions.width} x {compressedResult.dimensions.height}</p>
                  <p>
                    Size: {compressedResult.compressedSize.toFixed(2)} KB
                  </p>
                </div>
              </div>
            </div>
          )}
           {compressedResult?.blob && (
            <div className="image-info-details" style={{marginTop: '10px'}}>
              <p>
                <strong>Storage Size: {compressedResult.blob.size} bytes</strong>
                <br />
                <small>This is the raw data size for on-chain storage.</small>
              </p>
              <p>
                <strong>Base64 Size: ~{Math.round(compressedResult.blob.size * 4 / 3)} bytes</strong>
                <br />
                <small>Base64 is ~33% larger and not ideal for contracts.</small>
              </p>
               <button onClick={handleLogByteArray} className="download-button" style={{ backgroundColor: '#117a8b', marginTop: '10px' }}>
                  Log Byte Array
                </button>
            </div>
          )}
          {!compressedResult && !isCompressing && selectedImage && (
            <div className="compressed-placeholder">
              <p>Awaiting compression...</p>
            </div>
          )}
        </div>
        <div className="format-selector">
          <label htmlFor="format-select">Preferred Format:</label>
          <select
            id="format-select"
            value={preferredFormat}
            onChange={(e) => setPreferredFormat(e.target.value as FormatType)}
            className="format-select-dropdown"
          >
            <option value="image/avif">AVIF (Best Quality)</option>
            <option value="image/webp">WebP (Good Quality)</option>
            <option value="image/jpeg">JPEG (Compatible)</option>
          </select>
        </div>
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
                Description <span className="byte-counter">{artworkDescription.length}/200 characters</span>
              </label>
              <textarea
                id="artwork-description"
                value={artworkDescription}
                onChange={handleDescriptionChange}
                placeholder="Enter a description for your artwork"
                className="form-control"
              />
            </div>
            <div className="form-actions">
              <button
                type="button"
                className="form-back-button"
                onClick={onBack}
              >
                Back
              </button>
              <button
                type="button"
                className={`submit-button ${hasProfile ? 'profile-button' : ''}`}
                disabled={!compressedResult || isCompressing}
                onClick={handleRegisterArtwork}
              >
                {isCompressing ? 'Processing...' : (hasProfile ? 'Register Artwork in Profile' : 'Register Artwork')}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

const NFTRegistration: React.FC = () => {
  const [userType, setUserType] = useState<'artist' | 'commissioner' | null>(null);
  const { isConnected, connectWallet, walletAddress, networkType, switchToLayer } = useBlockchain();

  const [artworkTitle, setArtworkTitle] = useState<string>('');
  const [artworkDescription, setArtworkDescription] = useState<string>('');
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [originalPreviewUrl, setOriginalPreviewUrl] = useState<string | null>(null);
  const [compressedResult, setCompressedResult] = useState<DisplayResult | null>(null);
  const [isCompressing, setIsCompressing] = useState<boolean>(false);
  const [imageOrientation, setImageOrientation] = useState<'portrait' | 'landscape' | 'square' | null>(null);
  const [hasProfile, setHasProfile] = useState<boolean>(false);
  const [checkingProfile, setCheckingProfile] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const isTrulyConnected = isConnected && !!walletAddress;
  const [preferredFormat, setPreferredFormat] = useState<FormatType>('image/avif');

  useEffect(() => {
    if (isTrulyConnected) {
      checkForProfile();
    }
  }, [isTrulyConnected, walletAddress]);

  const checkForProfile = async () => {
    setCheckingProfile(true);
    try {
      const profileExists = await profileService.hasProfile();
      setHasProfile(profileExists);
    } catch (error) {
      console.error("Error checking for profile:", error);
      setHasProfile(false);
    } finally {
      setCheckingProfile(false);
    }
  };

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
      <div className={`connection-status ${isTrulyConnected ? 'connected' : 'disconnected'}`}>
        <span className="status-icon"></span>
        <div className="connection-details">
          {isTrulyConnected ? (
            <>
              <span className="status-text">
                Connected <span className="network-name">{networkType}</span>
              </span>
              <span className="wallet-address">{walletAddress}</span>
            </>
          ) : (
            <span className="status-text">Not Connected</span>
          )}
        </div>
      </div>
      {isTrulyConnected ? (
        <button className="disconnect-wallet-button" onClick={handleDisconnect}>
          Disconnect
        </button>
      ) : (
        <button className="connect-wallet-button" onClick={() => connectWallet()}>
          Connect Wallet
        </button>
      )}
      {isTrulyConnected && networkType !== 'animechain' && (
        <div className="connection-error-message">
          <p><strong>Wrong Network!</strong> Please switch to AnimeChain to register artwork.</p>
        </div>
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
          <button type="button" className="form-back-button" onClick={() => setUserType(null)}>
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

  const renderContent = () => {
    if (userType === null) {
      return (
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
      );
    } else if (userType === 'artist') {
      return (
        <ArtistForm
          artworkTitle={artworkTitle}
          setArtworkTitle={setArtworkTitle}
          artworkDescription={artworkDescription}
          setArtworkDescription={setArtworkDescription}
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
          preferredFormat={preferredFormat}
          setPreferredFormat={setPreferredFormat}
          onBack={() => setUserType(null)}
        />
      );
    } else {
      return <CommissionerForm />;
    }
  };

  return (
    <div className="nft-registration-container">
      <h2>Commission Art</h2>
      <ConnectionBar />
      {renderContent()}
    </div>
  );
};

export default NFTRegistration;