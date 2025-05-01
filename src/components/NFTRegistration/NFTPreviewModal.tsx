import React, { useState, useEffect } from 'react';
import './NFTRegistration.css';

interface NFTPreviewModalProps {
  show: boolean;
  onClose: () => void;
  imageDataUrl: string | null;
  title: string;
  description: string;
  tokenURIHash: string;
  originalHash: string;
  compressedSize: number;
  onProceed?: () => void;
  hashesMatch?: boolean;
}

const NFTPreviewModal: React.FC<NFTPreviewModalProps> = ({
  show,
  onClose,
  imageDataUrl,
  title,
  description,
  tokenURIHash,
  originalHash,
  compressedSize,
  onProceed,
  hashesMatch
}) => {
  const [imageError, setImageError] = useState(false);
  const [isImageLoaded, setIsImageLoaded] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  
  // Reset state when modal is closed or opened
  useEffect(() => {
    if (show) {
      setImageError(false);
      setIsImageLoaded(false);
      setIsProcessing(false);
    }
  }, [show]);
  
  // Return null if the modal shouldn't be shown
  if (!show) return null;

  // Use directly provided hashesMatch if available, otherwise compare hashes
  const doHashesMatch = hashesMatch !== undefined ? hashesMatch : tokenURIHash === originalHash;

  // Handle proceed action with loading state
  const handleProceed = async () => {
    if (!onProceed || isProcessing) return;
    
    setIsProcessing(true);
    try {
      await onProceed();
    } catch (error) {
      console.error("Error during registration process:", error);
      // Error is handled by the parent component
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="nft-preview-modal-overlay">
      <div className="nft-preview-modal">
        <div className="nft-preview-header">
          <h3>NFT Preview</h3>
          <button 
            className="nft-preview-close-btn" 
            onClick={onClose}
            disabled={isProcessing}
          >×</button>
        </div>
        <div className="nft-preview-content">
          <div className="nft-preview-image-container">
            {imageDataUrl && !imageError ? (
              <img 
                src={imageDataUrl} 
                alt="NFT Preview" 
                className={`nft-preview-image ${isImageLoaded ? 'loaded' : 'loading'}`}
                onLoad={() => setIsImageLoaded(true)}
                onError={(e) => {
                  console.error('Image failed to load:', imageDataUrl?.substring(0, 50) + '...');
                  setImageError(true);
                  setIsImageLoaded(false);
                }}
              />
            ) : (
              <div className="nft-preview-image-error">
                {imageError ? 'Image failed to load' : 'No preview available'}
                <div className="error-details">
                  The image data may be corrupted or in an unsupported format.
                  {imageError && imageDataUrl && (
                    <button 
                      className="retry-image-btn"
                      onClick={() => {
                        setImageError(false); 
                        setIsImageLoaded(false);
                      }}
                    >
                      Retry
                    </button>
                  )}
                </div>
              </div>
            )}
            {imageDataUrl && !imageError && !isImageLoaded && (
              <div className="image-loading-indicator">
                <div className="spinner"></div>
                <span>Loading image...</span>
              </div>
            )}
          </div>
          <div className="nft-preview-details">
            <h4 className="nft-preview-title">{title || 'Untitled'}</h4>
            <p className="nft-preview-description">{description || 'No description'}</p>
            
            <div className="nft-preview-metadata">
              <div className="nft-preview-hash-verification">
                <h5>Verification</h5>
                <div className={`hash-status ${doHashesMatch ? 'match' : 'mismatch'}`}>
                  <span className="hash-indicator"></span>
                  {doHashesMatch ? 'Data Integrity Verified' : 'Data Integrity Warning'}
                </div>
                <div className="hash-details">
                  <div className="hash-row">
                    <span className="hash-label">Original Hash:</span>
                    <span className="hash-value">{originalHash.substring(0, 10)}...{originalHash.substring(originalHash.length - 6)}</span>
                  </div>
                  <div className="hash-row">
                    <span className="hash-label">Final Hash:</span>
                    <span className="hash-value">{tokenURIHash.substring(0, 10)}...{tokenURIHash.substring(tokenURIHash.length - 6)}</span>
                  </div>
                </div>
                {!doHashesMatch && (
                  <div className="hash-mismatch-warning">
                    Data may be corrupted during tokenURI formation. Registration can continue, but image quality may be affected.
                  </div>
                )}
              </div>
              
              <div className="nft-preview-size">
                <span className="size-label">Data Size:</span>
                <span className="size-value">{compressedSize.toFixed(2)} KB</span>
                <span className={`size-status ${compressedSize <= 45 ? 'valid' : 'invalid'}`}>
                  {compressedSize <= 45 ? '✓ Within limit' : '⚠️ Exceeds 45KB limit'}
                </span>
              </div>
            </div>
          </div>
        </div>
        <div className="nft-preview-actions">
          <button 
            className="nft-preview-cancel-btn" 
            onClick={onClose}
            disabled={isProcessing}
          >
            Cancel
          </button>
          <button 
            className={`nft-preview-confirm-btn ${(!doHashesMatch || compressedSize > 45 || imageError) ? 'warning' : ''}`}
            onClick={handleProceed}
            disabled={isProcessing}
          >
            {isProcessing ? (
              <>
                <span className="button-spinner"></span>
                Processing...
              </>
            ) : (
              (!doHashesMatch || compressedSize > 45 || imageError) 
                ? 'Proceed with Caution' 
                : 'Proceed to Register'
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default NFTPreviewModal; 