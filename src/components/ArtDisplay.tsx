import React, { useState, useEffect } from 'react';
import { DecodedTokenURI, processArtworkData, safeRevokeUrl, detectImageFormat } from '../utils/TokenURIDecoder';
import './ArtDisplay.css';

interface ArtDisplayProps {
  imageData: Uint8Array | string;  // Can be either binary data or string tokenURI
  title?: string;
  contractAddress?: string;
  className?: string;
  showDebug?: boolean;
}

/**
 * Component for displaying artwork that can handle both raw image data
 * and tokenURI formatted data
 */
const ArtDisplay: React.FC<ArtDisplayProps> = ({ 
  imageData, 
  title,
  contractAddress,
  className = '',
  showDebug = false
}) => {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [decodedData, setDecodedData] = useState<DecodedTokenURI | null>(null);
  const [isTokenURIFormat, setIsTokenURIFormat] = useState<boolean>(false);
  const [mimeType, setMimeType] = useState<string>('image/avif');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [hasError, setHasError] = useState<boolean>(false);
  const [showDebugInfo, setShowDebugInfo] = useState<boolean>(showDebug);
  const [errorDetails, setErrorDetails] = useState<string | null>(null);

  useEffect(() => {
    setIsLoading(true);
    setHasError(false);
    setErrorDetails(null);
    
    try {
      // Process the artwork data to get various formats
      const { imageUrl: url, decodedTokenURI, isTokenURIFormat: isTokenURI, mimeType: detectedMimeType } = processArtworkData(imageData);
      
      setImageUrl(url);
      setDecodedData(decodedTokenURI);
      setIsTokenURIFormat(isTokenURI);
      setMimeType(detectedMimeType);
      
      console.log(`Processed artwork: MIME type=${detectedMimeType}, format=${isTokenURI ? 'tokenURI' : 'raw'}`);
      
      if (!url) {
        setHasError(true);
        setErrorDetails("Failed to generate a valid image URL from the data");
      }
    } catch (error) {
      console.error('Error processing artwork:', error);
      setHasError(true);
      setErrorDetails(error instanceof Error ? error.message : String(error));
    } finally {
      setIsLoading(false);
    }
    
    // Cleanup function to revoke URLs
    return () => {
      if (imageUrl) {
        safeRevokeUrl(imageUrl);
      }
    };
  }, [imageData]);

  const toggleDebug = () => {
    setShowDebugInfo(!showDebugInfo);
  };

  // Get image data format description for debugging
  const getImageDataDescription = (): string => {
    if (isTokenURIFormat) {
      return 'TokenURI format (base64 encoded JSON with embedded image)';
    } else {
      if (imageData instanceof Uint8Array) {
        const sizeKB = (imageData.length / 1024).toFixed(2);
        const firstBytes = Array.from(imageData.slice(0, 8))
          .map(b => b.toString(16).padStart(2, '0'))
          .join(' ');
        return `Raw binary (${sizeKB} KB, MIME: ${mimeType}, First bytes: ${firstBytes}...)`;
      } else if (typeof imageData === 'string' && imageData.startsWith('0x')) {
        // Handle hex string format
        const displayLength = Math.min(imageData.length, 20);
        return `Hex string (${imageData.slice(0, displayLength)}...)`;
      } else {
        return 'String format (possibly tokenURI or data URL)';
      }
    }
  };

  // Enhanced function to display a hex dump of the first bytes
  const getHexDump = (): string => {
    if (imageData instanceof Uint8Array) {
      const bytesToShow = Math.min(32, imageData.length);
      return Array.from(imageData.slice(0, bytesToShow))
        .map(b => b.toString(16).padStart(2, '0'))
        .join(' ');
    } else if (typeof imageData === 'string' && imageData.startsWith('0x')) {
      // Show first part of hex string
      return imageData.slice(0, Math.min(imageData.length, 66)); // Show 0x + 32 bytes
    }
    return 'N/A';
  };

  if (isLoading) {
    return (
      <div className={`art-display loading ${className}`}>
        <div className="art-loading-indicator"></div>
      </div>
    );
  }

  if (hasError || !imageUrl) {
    return (
      <div className={`art-display error ${className}`}>
        <div className="error-message">
          Unable to display artwork
          {errorDetails && <div className="error-details">{errorDetails}</div>}
          {showDebugInfo && (
            <div className="debug-error-info">
              <p>Data type: {typeof imageData === 'string' ? 'String' : 'Uint8Array'}</p>
              {imageData instanceof Uint8Array && (
                <>
                  <p>Data length: {imageData.length} bytes</p>
                  <p>First bytes: {getHexDump()}</p>
                  <p>Detected MIME: {detectImageFormat(imageData)}</p>
                </>
              )}
              {typeof imageData === 'string' && (
                <p>String starts with: {imageData.substring(0, 30)}...</p>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={`art-display ${isTokenURIFormat ? 'token-uri-format' : 'raw-format'} ${className}`}>
      <div className="art-image-container">
        <img 
          src={imageUrl} 
          alt={decodedData?.name || title || 'Artwork'} 
          className="art-image" 
          onError={(e) => {
            console.error('Image failed to load:', e);
            setHasError(true);
            setErrorDetails('Image failed to render in browser');
          }}
        />
      </div>
      
      {isTokenURIFormat && decodedData && (
        <div className="art-metadata">
          <h3 className="art-title">{decodedData.name}</h3>
          {decodedData.description && (
            <p className="art-description">{decodedData.description}</p>
          )}
          {contractAddress && (
            <div className="art-contract">
              <small>Contract: {contractAddress}</small>
            </div>
          )}
        </div>
      )}
      
      {!isTokenURIFormat && title && (
        <div className="art-metadata">
          <h3 className="art-title">{title}</h3>
          {contractAddress && (
            <div className="art-contract">
              <small>Contract: {contractAddress}</small>
            </div>
          )}
        </div>
      )}
      
      {/* Debug button */}
      <button 
        className="art-debug-toggle" 
        onClick={toggleDebug}
        style={{ display: 'block', marginTop: '5px', fontSize: '10px' }}
      >
        {showDebugInfo ? 'Hide Debug Info' : 'Show Debug Info'}
      </button>
      
      {/* Debug information section */}
      {showDebugInfo && (
        <div className="art-debug-info">
          <div className="debug-row">
            <span className="debug-label">Format:</span>
            <span className="debug-value">{getImageDataDescription()}</span>
          </div>
          <div className="debug-row">
            <span className="debug-label">MIME:</span>
            <span className="debug-value">{mimeType}</span>
          </div>
          {imageData instanceof Uint8Array && (
            <>
              <div className="debug-row">
                <span className="debug-label">Size:</span>
                <span className="debug-value">{(imageData.length / 1024).toFixed(2)} KB ({imageData.length} bytes)</span>
              </div>
              <div className="debug-row">
                <span className="debug-label">Hex:</span>
                <span className="debug-value hex-dump">{getHexDump()}</span>
              </div>
            </>
          )}
          {typeof imageData === 'string' && !isTokenURIFormat && (
            <div className="debug-row">
              <span className="debug-label">Data:</span>
              <span className="debug-value string-preview">
                {imageData.substring(0, 50)}...
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ArtDisplay; 