import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useBlockchain } from '../../utils/BlockchainContext';
import { compressImage, getImageOrientation, revokePreviewUrl, CompressionResult, FormatType } from '../../utils/ImageCompressorUtil';
import './NFTRegistration.css';
import { ethers } from 'ethers';
import contractConfig from '../../assets/contract_config.json';
import abiLoader from '../../utils/abiLoader';
import ethersService from '../../utils/ethers-service';

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
  fileInputRef: React.RefObject<HTMLInputElement>;
  isTrulyConnected: boolean;
  connectWallet: () => void;
  walletAddress: string | null;
  networkType: string;
  switchToLayer: (layer: 'l1' | 'l2' | 'l3', environment: 'testnet' | 'mainnet') => void;
  onBack: () => void; // Added onBack prop
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
  onBack, // Destructure onBack
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

      // Get the ArtPiece contract factory from the ABI
      const artPieceAbi = abiLoader.loadABI('ArtPiece');
      if (!artPieceAbi) {
        throw new Error("Failed to load ArtPiece ABI");
      }
      
      // Get the bytes representation of the image and description
      if (!compressedResult.blob) {
        throw new Error("Compressed image blob is not available");
      }
      
      // Convert the image to bytes
      const imageData = new Uint8Array(await compressedResult.blob.arrayBuffer());
      const titleStr = artworkTitle.trim();
      const descriptionBytes = new TextEncoder().encode(artworkDescription);

      // Get the commissionHub address from the config
      const commissionHubAddress = contractConfig.networks.mainnet.commissionHub.address;
      
      console.log("Deploying contract with:", {
        imageDataSize: imageData.length,
        title: titleStr,
        description: artworkDescription,
        owner: walletAddress,
        artist: walletAddress,
        commissionHub: commissionHubAddress,
      });

      // Create the factory for deploying the contract
      const factory = new ethers.ContractFactory(artPieceAbi, '', signer);
      
      // Deploy the contract with the artwork data
      const contract = await factory.deploy(
        imageData,
        titleStr,
        descriptionBytes,
        walletAddress,  // owner
        walletAddress,  // artist (same as owner for now)
        commissionHubAddress || ethers.ZeroAddress,
        false  // not AI generated
      );

      // Wait for the deployment transaction to be mined
      const receipt = await contract.waitForDeployment();
      const contractAddress = await contract.getAddress();
      
      setIsCompressing(false);
      alert(`Artwork registered successfully! Contract address: ${contractAddress}`);
      console.log("Artwork registered successfully:", {
        artist: walletAddress,
        owner: walletAddress,
        artworkTitle: titleStr,
        contractAddress: contractAddress,
        imageSize: compressedResult.compressedSize,
        imageFormat: compressedResult.format,
        dimensions: compressedResult.dimensions,
      });
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
                className="submit-button"
                disabled={!compressedResult || isCompressing}
                onClick={handleRegisterArtwork}
              >
                Register Artwork
              </button>
            </div>
          </div>
          <div className="form-footer">
            <button type="button" className="form-back-button" onClick={onBack}>
              Back
            </button>
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
  const fileInputRef = useRef<HTMLInputElement>(null);
  const isTrulyConnected = isConnected && !!walletAddress;

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
          onBack={() => setUserType('none')} // Pass onBack prop
        />
      ) : (
        <CommissionerForm />
      )}
    </div>
  );
};

export default NFTRegistration;