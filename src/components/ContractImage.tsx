import React, { useState, useEffect } from 'react';
import { ethers } from 'ethers';
import { contracts, defaultNetwork, defaultContract } from '../utils/contracts';
import './ContractImage.css';

const ContractImage: React.FC = () => {
  const [imageData, setImageData] = useState<string | null>(null);
  const [imageHex, setImageHex] = useState<string | null>(null);
  const [owner, setOwner] = useState<string | null>(null);
  const [artist, setArtist] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [imageType, setImageType] = useState<string>('image/jpeg'); // Default to JPEG

  useEffect(() => {
    const fetchContractData = async () => {
      try {
        setLoading(true);
        
        // Connect to the specified network
        const provider = new ethers.JsonRpcProvider(defaultNetwork.rpcUrl);
        
        // Create contract instance
        const contract = new ethers.Contract(
          defaultContract.address,
          contracts.CommissionedArt.abi,
          provider
        );
        
        // Fetch image data
        const rawImageData = await contract.get_image_data();
        console.log("Raw image data fetched:", rawImageData);
        
        // Convert the bytes to a displayable image
        if (rawImageData) {
          // Convert to hex string for display
          // Remove '0x' prefix if present
          const cleanHex = rawImageData.startsWith('0x') ? rawImageData.slice(2) : rawImageData;
          const hexString = `0x${cleanHex}`;
          setImageHex(hexString);
          
          // Convert the hex string to binary for image display
          // Convert hex to binary
          const byteArray = new Uint8Array(cleanHex.match(/.{1,2}/g)!.map((byte: string) => parseInt(byte, 16)));
          
          // Detect image type from the first few bytes of the image
          const detectedType = detectImageType(cleanHex);
          if (detectedType) {
            setImageType(detectedType);
          }
          
          // Create a blob and convert to data URL
          const blob = new Blob([byteArray], { type: imageType });
          const imageUrl = URL.createObjectURL(blob);
          setImageData(imageUrl);
        }
        
        // Fetch owner and artist
        const ownerAddress = await contract.get_owner();
        setOwner(ownerAddress);
        
        const artistAddress = await contract.get_artist();
        setArtist(artistAddress);
        
        setLoading(false);
      } catch (err) {
        console.error("Error fetching contract data:", err);
        setError(err instanceof Error ? err.message : "Unknown error occurred");
        setLoading(false);
      }
    };
    
    fetchContractData();
  }, [imageType]);

  // Helper function to detect image type from hex data
  const detectImageType = (hexData: string): string | null => {
    // Check for common image file signatures
    const firstBytes = hexData.substring(0, 8).toLowerCase();
    
    if (firstBytes.startsWith('89504e47')) {
      return 'image/png';
    } else if (firstBytes.startsWith('ffd8ffe0') || 
               firstBytes.startsWith('ffd8ffe1') || 
               firstBytes.startsWith('ffd8ffee') || 
               firstBytes.startsWith('ffd8ffdb')) {
      return 'image/jpeg';
    } else if (firstBytes.startsWith('47494638')) {
      return 'image/gif';
    } else if (firstBytes.startsWith('52494646') && hexData.substring(16, 24).toLowerCase() === '57454250') {
      return 'image/webp';
    } else if (firstBytes.startsWith('424d')) {
      return 'image/bmp';
    }
    
    // Default to JPEG if unable to detect
    return 'image/jpeg';
  };

  if (loading) {
    return <div className="contract-image-container loading">Loading image from blockchain...</div>;
  }
  
  if (error) {
    return <div className="contract-image-container error">Error: {error}</div>;
  }

  return (
    <div className="contract-image-container">
      <h2>Commissioned Artwork from Blockchain</h2>
      
      {imageData ? (
        <div className="image-display">
          <img src={imageData} alt="Artwork from blockchain" />
          <div className="image-info">
            <span className="image-format">Format: {imageType.split('/')[1].toUpperCase()}</span>
          </div>
        </div>
      ) : (
        <div className="no-image">No image data found in contract</div>
      )}
      
      <div className="contract-info">
        <div className="info-row">
          <span className="info-label">Network:</span>
          <span className="info-value">{defaultNetwork.name} (Chain ID: {defaultNetwork.chainId})</span>
        </div>
        
        <div className="info-row">
          <span className="info-label">Contract Address:</span>
          <span className="info-value">{defaultContract.address}</span>
        </div>
        
        {owner && (
          <div className="info-row">
            <span className="info-label">Owner:</span>
            <span className="info-value">{owner}</span>
          </div>
        )}
        
        {artist && (
          <div className="info-row">
            <span className="info-label">Artist:</span>
            <span className="info-value">{artist}</span>
          </div>
        )}
        
        {imageHex && (
          <div className="image-hex">
            <h3>Image Hex Data</h3>
            <div className="hex-data">{imageHex}</div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ContractImage; 