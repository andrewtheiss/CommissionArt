import React, { useState, useEffect, useRef } from 'react';
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
  tokenURIString?: string;
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
  hashesMatch,
  tokenURIString
}) => {
  const [imageError, setImageError] = useState(false);
  const [isImageLoaded, setIsImageLoaded] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [imageDetails, setImageDetails] = useState<{width: number, height: number, format: string} | null>(null);
  const [showRawData, setShowRawData] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);
  
  // Reset state when modal is closed or opened
  useEffect(() => {
    if (show) {
      setImageError(false);
      setIsImageLoaded(false);
      setIsProcessing(false);
      setShowRawData(false);
      
      // Debug log for image URL
      if (imageDataUrl) {
        console.log("Modal image URL available, starting with:", 
          imageDataUrl.substring(0, 50) + "...");
          
        // Check if it's a WebP, AVIF, or JPEG data URL
        const formatMatch = imageDataUrl.match(/^data:image\/(webp|avif|jpeg|png);base64,/i);
        if (formatMatch) {
          console.log(`Image appears to be ${formatMatch[1].toUpperCase()} format`);
        } else {
          console.warn("Image format not detected in data URL");
        }
        
        // Check if the data URL is long enough to be valid
        const base64Data = imageDataUrl.split(',')[1];
        if (base64Data) {
          console.log(`Base64 data length: ${base64Data.length} chars`);
          if (base64Data.length < 100) {
            console.warn("Base64 data appears too short - may be corrupted");
          }
        }
      } else {
        console.warn("Modal image URL is null or undefined");
      }
    }
  }, [show, imageDataUrl]);
  
  // Check if image is already loaded when component mounts
  useEffect(() => {
    // If the image element exists and is already complete, mark it as loaded
    if (imgRef.current && imgRef.current.complete && !imageError) {
      console.log("Image was already loaded when checked");
      if (imgRef.current.naturalWidth > 0) {
        setImageDetails({
          width: imgRef.current.naturalWidth,
          height: imgRef.current.naturalHeight,
          format: imageDataUrl?.match(/^data:image\/([\w-]+);/)?.[1]?.toUpperCase() || 'Unknown'
        });
        setIsImageLoaded(true);
      } else {
        console.warn("Image loaded but has zero width - may be corrupted");
        setImageError(true);
      }
    }
    
    // Set a fallback timeout to force the image to be considered loaded
    // This helps in browsers where the onLoad event might not fire correctly
    const fallbackTimer = setTimeout(() => {
      if (!isImageLoaded && imgRef.current) {
        console.log("Forcing image loaded state after timeout");
        if (imgRef.current.naturalWidth > 0) {
          setImageDetails({
            width: imgRef.current.naturalWidth,
            height: imgRef.current.naturalHeight,
            format: imageDataUrl?.match(/^data:image\/([\w-]+);/)?.[1]?.toUpperCase() || 'Unknown'
          });
          setIsImageLoaded(true);
        } else {
          console.warn("Fallback timeout: Image has zero width - marking as error");
          setImageError(true);
        }
      }
    }, 2000); // 2 second fallback
    
    return () => clearTimeout(fallbackTimer);
  }, [imageError, show, isImageLoaded, imageDataUrl]);
  
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

  const toggleRawData = () => {
    setShowRawData(!showRawData);
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
              <>
                <img 
                  ref={imgRef}
                  src={imageDataUrl} 
                  alt="NFT Preview" 
                  className={`nft-preview-image ${isImageLoaded ? 'loaded' : 'loading'}`}
                  onLoad={(e) => {
                    console.log("Image loaded successfully in modal");
                    const target = e.target as HTMLImageElement;
                    setImageDetails({
                      width: target.naturalWidth,
                      height: target.naturalHeight,
                      format: imageDataUrl.match(/^data:image\/([\w-]+);/)?.[1]?.toUpperCase() || 'Unknown'
                    });
                    setIsImageLoaded(true);
                  }}
                  onError={(e) => {
                    console.error('Image failed to load:', imageDataUrl?.substring(0, 50) + '...');
                    console.error('Image error details:', e);
                    setImageError(true);
                    setIsImageLoaded(false);
                  }}
                />
                {!isImageLoaded && (
                  <div className="image-loading-indicator">
                    <div className="spinner"></div>
                    <span>Loading image...</span>
                  </div>
                )}
              </>
            ) : (
              <div className="nft-preview-image-error">
                {imageError ? 'Image failed to load' : 'No preview available'}
                <div className="error-details">
                  The image data may be corrupted or in an unsupported format.
                  {imageError && imageDataUrl && (
                    <button 
                      className="retry-image-btn"
                      onClick={() => {
                        console.log("Retrying image load");
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
          </div>
          <div className="nft-preview-details">
            <h4 className="nft-preview-title">{title || 'Untitled'}</h4>
            <p className="nft-preview-description">{description || 'No description'}</p>
            
            <div className="nft-preview-metadata">
              {imageDetails && isImageLoaded && (
                <div className="nft-preview-image-details">
                  <h5>Image Details</h5>
                  <div className="image-details-row">
                    <span>Dimensions: {imageDetails.width} × {imageDetails.height}</span>
                  </div>
                  <div className="image-details-row">
                    <span>Format: {imageDetails.format}</span>
                  </div>
                  <button 
                    className="debug-button"
                    onClick={toggleRawData}
                  >
                    {showRawData ? 'Hide Raw Data' : 'Show Raw Data'}
                  </button>
                </div>
              )}
              
              {showRawData && imageDataUrl && (
                <div className="raw-data-container">
                  <h5>Image Data URL (first 100 chars)</h5>
                  <div className="raw-data-content original-data">
                    {imageDataUrl?.substring(0, 100) || 'No image data'}...
                  </div>
                  <div className="raw-data-info">
                    <span>Full length: {imageDataUrl?.length || 0} chars</span>
                    <span>Base64 section: {imageDataUrl?.split(',')[1]?.length || 0} chars</span>
                  </div>
                  
                  {tokenURIString && (
                    <>
                      <h5 className="token-uri-title">TokenURI (first 100 chars)</h5>
                      <div className="raw-data-content token-uri-content">
                        {tokenURIString.substring(0, 100)}...
                      </div>
                      <div className="raw-data-info">
                        <span>Full length: {tokenURIString.length} chars</span>
                        <span>Base64 section: {tokenURIString.split(',')[1]?.length || 0} chars</span>
                      </div>
                      
                      {/* Extract and display image data from tokenURI */}
                      {(() => {
                        try {
                          const base64Json = tokenURIString.split('base64,')[1];
                          if (base64Json) {
                            const jsonString = atob(base64Json);
                            const metadata = JSON.parse(jsonString);
                            if (metadata.image) {
                              return (
                                <>
                                  <h5 className="extracted-image-title">Image Data from TokenURI (first 100 chars)</h5>
                                  <div className="raw-data-content extracted-image-content">
                                    {metadata.image.substring(0, 100)}...
                                  </div>
                                  <div className="raw-data-info">
                                    <span>Format: {metadata.image.match(/^data:image\/([^;]+);/)?.[1]?.toUpperCase() || 'Unknown'}</span>
                                    <span>Base64 section: {metadata.image.split(',')[1]?.length || 0} chars</span>
                                  </div>
                                </>
                              );
                            }
                          }
                        } catch (error) {
                          return <div className="debug-error">Error extracting image from tokenURI: {String(error)}</div>;
                        }
                        return null;
                      })()}
                    </>
                  )}
                </div>
              )}
              
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