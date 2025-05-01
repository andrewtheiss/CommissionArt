import React from 'react';
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
  onProceed
}) => {
  if (!show) return null;

  const hashesMatch = tokenURIHash === originalHash;

  return (
    <div className="nft-preview-modal-overlay">
      <div className="nft-preview-modal">
        <div className="nft-preview-header">
          <h3>NFT Preview</h3>
          <button className="nft-preview-close-btn" onClick={onClose}>×</button>
        </div>
        <div className="nft-preview-content">
          <div className="nft-preview-image-container">
            {imageDataUrl ? (
              <img 
                src={imageDataUrl} 
                alt="NFT Preview" 
                className="nft-preview-image" 
                onError={(e) => {
                  (e.target as HTMLImageElement).src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2YwZjBmMCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwsIHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTQiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZpbGw9IiM5OTkiIGR5PSIuM2VtIj5JbWFnZSBMb2FkIEVycm9yPC90ZXh0Pjwvc3ZnPg==';
                }}
              />
            ) : (
              <div className="nft-preview-image-error">
                Unable to preview image
              </div>
            )}
          </div>
          <div className="nft-preview-details">
            <h4 className="nft-preview-title">{title || 'Untitled'}</h4>
            <p className="nft-preview-description">{description || 'No description'}</p>
            
            <div className="nft-preview-metadata">
              <div className="nft-preview-hash-verification">
                <h5>Verification</h5>
                <div className={`hash-status ${hashesMatch ? 'match' : 'mismatch'}`}>
                  <span className="hash-indicator"></span>
                  {hashesMatch ? 'Data Integrity Verified' : 'Data Integrity Warning'}
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
          <button className="nft-preview-cancel-btn" onClick={onClose}>Cancel</button>
          <button 
            className={`nft-preview-confirm-btn ${(!hashesMatch || compressedSize > 45) ? 'warning' : ''}`}
            onClick={onProceed || onClose}
          >
            Proceed to Register
          </button>
        </div>
      </div>
    </div>
  );
};

export default NFTPreviewModal; 