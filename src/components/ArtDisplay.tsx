import React, { useState, useEffect } from 'react';
import { DecodedTokenURI, processArtworkData, safeRevokeUrl } from '../utils/TokenURIDecoder';
import './ArtDisplay.css';

interface ArtDisplayProps {
  imageData: Uint8Array | string;
  title?: string;
  contractAddress?: string;
  className?: string;
}

/**
 * Component for displaying artwork that can handle both raw image data
 * and tokenURI formatted data
 */
const ArtDisplay: React.FC<ArtDisplayProps> = ({ 
  imageData, 
  title,
  contractAddress,
  className = '' 
}) => {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [decodedData, setDecodedData] = useState<DecodedTokenURI | null>(null);
  const [isTokenURIFormat, setIsTokenURIFormat] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [hasError, setHasError] = useState<boolean>(false);

  useEffect(() => {
    setIsLoading(true);
    setHasError(false);
    
    try {
      // Process the artwork data to get various formats
      const { imageUrl: url, decodedTokenURI, isTokenURIFormat: isTokenURI } = processArtworkData(imageData);
      
      setImageUrl(url);
      setDecodedData(decodedTokenURI);
      setIsTokenURIFormat(isTokenURI);
    } catch (error) {
      console.error('Error processing artwork:', error);
      setHasError(true);
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

  if (isLoading) {
    return (
      <div className={`art-display loading ${className}`}>
        <div className="loading-spinner"></div>
      </div>
    );
  }

  if (hasError || !imageUrl) {
    return (
      <div className={`art-display error ${className}`}>
        <div className="error-message">
          Unable to display artwork
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
    </div>
  );
};

export default ArtDisplay; 