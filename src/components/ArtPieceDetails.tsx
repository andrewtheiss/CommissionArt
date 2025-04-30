import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { ethers } from 'ethers';
import ArtDisplay from './ArtDisplay';
import profileService from '../utils/profile-service';
import { decodeTokenURI, DecodedTokenURI } from '../utils/TokenURIDecoder';
import './ArtPieceDetails.css';

/**
 * Component for displaying detailed art piece information when given an address
 */
const ArtPieceDetails: React.FC = () => {
  const { address } = useParams<{ address: string }>();
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [artPiece, setArtPiece] = useState<{
    address: string;
    title: string;
    description: string;
    tokenURIData: string | null;
    artist: string;
    owner: string;
    isTokenUri: boolean;
    decodedData: DecodedTokenURI | null;
  } | null>(null);

  // Format address for display
  const formatAddress = (addr: string) => {
    return `${addr.substring(0, 6)}...${addr.substring(addr.length - 4)}`;
  };

  useEffect(() => {
    const loadArtPiece = async () => {
      if (!address) {
        setError("No art piece address provided");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        // Load the ABI
        const artPieceAbi = await profileService.getArtPieceAbi();
        if (!artPieceAbi) {
          throw new Error("Failed to load ArtPiece ABI");
        }

        // Get provider
        const provider = profileService.getProvider();
        if (!provider) {
          throw new Error("No provider available");
        }

        // Create contract instance
        const contract = new ethers.Contract(address, artPieceAbi, provider);

        // Initialize default values
        let title = "Untitled Artwork";
        let description = "";
        let artist = ethers.ZeroAddress;
        let owner = ethers.ZeroAddress;
        let tokenURIData: string | null = null;
        let isTokenUri = false;
        let decodedData: DecodedTokenURI | null = null;
        let descriptionText = "";

        // Load basic details safely
        try {
          // Try to get title
          if (typeof contract.title === 'function') {
            title = await contract.title();
          } else if (contract.title !== undefined) {
            title = await contract.title;
          } else if (typeof contract.getTitle === 'function') {
            title = await contract.getTitle();
          }
        } catch (titleErr) {
          console.warn(`Could not get title for art piece ${address}:`, titleErr);
        }

        try {
          // Try to get description
          if (typeof contract.getDescription === 'function') {
            description = await contract.getDescription();
          } else if (typeof contract.description === 'function') {
            description = await contract.description();
          } else if (contract.description !== undefined) {
            description = await contract.description;
          }
          
          // Get description text, handling both string and bytes formats for backward compatibility
          if (description) {
            if (typeof description === 'string') {
              // If it's already a string, use it directly
              descriptionText = description;
            } else if (description && typeof description === 'object' && 'length' in description) {
              // If it's bytes or array-like, convert to string
              try {
                descriptionText = new TextDecoder().decode(description as unknown as Uint8Array);
              } catch (decodeErr) {
                console.warn(`Error decoding description: ${decodeErr}`);
                // Fallback to string conversion
                descriptionText = String(description);
              }
            }
          }
        } catch (descErr) {
          console.warn(`Could not get description for art piece ${address}:`, descErr);
        }

        try {
          // Try to get artist
          if (typeof contract.getArtist === 'function') {
            artist = await contract.getArtist();
          } else if (typeof contract.artist === 'function') {
            artist = await contract.artist();
          } else if (contract.artist !== undefined) {
            artist = await contract.artist;
          }
        } catch (artistErr) {
          console.warn(`Could not get artist for art piece ${address}:`, artistErr);
        }

        try {
          // Try to get owner
          if (typeof contract.getOwner === 'function') {
            owner = await contract.getOwner();
          } else if (typeof contract.owner === 'function') {
            owner = await contract.owner();
          } else if (contract.owner !== undefined) {
            owner = await contract.owner;
          } else if (typeof contract.ownerOf === 'function') {
            // Try ERC721 standard method
            owner = await contract.ownerOf(1);
          }
        } catch (ownerErr) {
          console.warn(`Could not get owner for art piece ${address}:`, ownerErr);
        }

        // Try to get tokenURI data using various methods
        try {
          // First try the new tokenURI standard method
          if (typeof contract.tokenURI === 'function') {
            tokenURIData = await contract.tokenURI(1);
          } 
          // Then try the new direct property
          else if (typeof contract.tokenURI_data === 'function') {
            tokenURIData = await contract.tokenURI_data();
          } 
          // Then try the getter
          else if (typeof contract.getTokenURIData === 'function') {
            tokenURIData = await contract.getTokenURIData();
          } 
          // Fallback to legacy getter
          else if (typeof contract.getImageData === 'function') {
            tokenURIData = await contract.getImageData();
          }
          // Finally check if it's a direct property
          else if (contract.tokenURI_data !== undefined) {
            tokenURIData = await contract.tokenURI_data;
          }
          
          if (tokenURIData) {
            console.log(`Loaded tokenURI data for ${address}, type: ${typeof tokenURIData}`);
            
            // For backwards compatibility, convert from Bytes to String if needed
            if (typeof tokenURIData !== 'string') {
              try {
                // Check if it's an array-like object with a slice method
                if (tokenURIData && typeof tokenURIData === 'object' && 'slice' in tokenURIData) {
                  const dataStr = new TextDecoder().decode(tokenURIData as Uint8Array);
                  tokenURIData = dataStr;
                } else {
                  // Fallback to string conversion
                  tokenURIData = String(tokenURIData);
                }
              } catch (convErr) {
                console.warn(`Failed to convert binary data to string: ${convErr}`);
              }
            }

            // Check if it's in tokenURI format
            if (typeof tokenURIData === 'string' && tokenURIData.startsWith('data:application/json;base64,')) {
              console.log(`TokenURI data starts with: ${tokenURIData.substring(0, 50)}...`);
              isTokenUri = true;
              decodedData = decodeTokenURI(tokenURIData);
              console.log("Successfully decoded tokenURI:", decodedData ? "yes" : "no");
              
              // If we have decoded token data, use its values to fill in missing info
              if (decodedData) {
                if (title === "Untitled Artwork" && decodedData.name) {
                  title = decodedData.name;
                }
                
                if (descriptionText === "" && decodedData.description) {
                  descriptionText = decodedData.description;
                }
              }
            }
          }
        } catch (imageErr) {
          console.error(`Error loading tokenURI data for art piece ${address}:`, imageErr);
        }

        setArtPiece({
          address,
          title,
          description: descriptionText,
          tokenURIData,
          artist,
          owner,
          isTokenUri,
          decodedData
        });
      } catch (err) {
        console.error("Error loading art piece:", err);
        setError(`Failed to load art piece: ${err instanceof Error ? err.message : String(err)}`);
      } finally {
        setLoading(false);
      }
    };

    loadArtPiece();
  }, [address]);

  if (loading) {
    return (
      <div className="art-piece-details loading">
        <div className="loading-spinner"></div>
        <p>Loading art piece details...</p>
      </div>
    );
  }

  if (error || !artPiece) {
    return (
      <div className="art-piece-details error">
        <h2>Error</h2>
        <p>{error || "Failed to load art piece"}</p>
        <button onClick={() => window.history.back()} className="back-button">
          Go Back
        </button>
      </div>
    );
  }

  return (
    <div className="art-piece-details">
      <div className="details-header">
        <h2>{artPiece.title}</h2>
        <button onClick={() => window.history.back()} className="back-button">
          Go Back
        </button>
      </div>

      <div className="details-content">
        <div className="details-artwork">
          {artPiece.tokenURIData ? (
            <ArtDisplay
              imageData={artPiece.tokenURIData}
              title={artPiece.title}
              className="main-artwork-display"
            />
          ) : (
            <div className="artwork-placeholder">
              <div className="artwork-missing">Artwork not available</div>
            </div>
          )}
        </div>

        <div className="details-info">
          <div className="info-section">
            <h3>Artwork Details</h3>
            <div className="info-row">
              <span className="info-label">Title:</span>
              <span className="info-value">{artPiece.title}</span>
            </div>
            
            <div className="info-row">
              <span className="info-label">Description:</span>
              <span className="info-value description">
                {artPiece.isTokenUri && artPiece.decodedData?.description
                  ? artPiece.decodedData.description
                  : artPiece.description || "No description provided"}
              </span>
            </div>
            
            <div className="info-row">
              <span className="info-label">Data Format:</span>
              <span className="info-value">
                {artPiece.isTokenUri ? (
                  <span className="token-uri-badge">TokenURI</span>
                ) : (
                  <span className="raw-data-badge">Raw Data</span>
                )}
              </span>
            </div>
          </div>

          <div className="info-section">
            <h3>Ownership</h3>
            <div className="info-row">
              <span className="info-label">Artist:</span>
              <span className="info-value address">
                <a href={`#/profile/${artPiece.artist}`} className="address-link">
                  {formatAddress(artPiece.artist)}
                </a>
              </span>
            </div>
            
            <div className="info-row">
              <span className="info-label">Owner:</span>
              <span className="info-value address">
                <a href={`#/profile/${artPiece.owner}`} className="address-link">
                  {formatAddress(artPiece.owner)}
                </a>
              </span>
            </div>
          </div>

          <div className="info-section">
            <h3>Contract Information</h3>
            <div className="info-row">
              <span className="info-label">Contract Address:</span>
              <span className="info-value address">
                <a 
                  href={`https://arbiscan.io/address/${artPiece.address}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="contract-link"
                >
                  {formatAddress(artPiece.address)}
                </a>
              </span>
            </div>
            
            {artPiece.isTokenUri && artPiece.decodedData && (
              <div className="token-uri-data">
                <h4>TokenURI Metadata</h4>
                <pre className="metadata-json">
                  {JSON.stringify({
                    name: artPiece.decodedData.name,
                    description: artPiece.decodedData.description,
                    // Don't include full image data to avoid large rendering
                    image: artPiece.decodedData.image.substring(0, 50) + '...'
                  }, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ArtPieceDetails; 