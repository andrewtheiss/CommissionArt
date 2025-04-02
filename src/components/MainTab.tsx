import React, { useState, useEffect } from 'react';
import { ethers } from 'ethers';
import './MainTab.css';

// ABI fragments for Registry contract functions we need
const REGISTRY_ABI = [
  'function imageDataContracts(uint256) view returns (address)',
  'function owner() view returns (address)'
];

// ABI fragments for CommissionedArt functions
const COMMISSIONED_ART_ABI = [
  'function get_image_data() view returns (bytes)',
  'function get_owner() view returns (address)',
  'function get_artist() view returns (address)'
];

interface ImageContract {
  id: number;
  address: string;
  owner: string;
  artist: string;
  imageUrl: string;
}

const MainTab: React.FC = () => {
  // Hardcoded Registry contract address
  const registryAddress = '0x5174f3e6F83CF2283b7677829356C8Bc6fCe578f';
  const [registryOwner, setRegistryOwner] = useState<string>('');
  const [imageContracts, setImageContracts] = useState<ImageContract[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Helper function to detect image type from hex data
  const detectImageType = (hexData: string): string => {
    // Check for AVIF signature (ftyp+avif or ftyp+avis)
    // This is a simplified check, AVIF detection can be more complex
    const hexLower = hexData.toLowerCase();
    if (hexLower.includes('66747970617669') || hexLower.includes('6674797061766973')) {
      return 'image/avif';
    }
    
    // Check for other common image formats as fallback
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
    }
    
    // Default to AVIF since we're looking for AVIF images
    return 'image/avif';
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // Connect to AnimeChain
        const provider = new ethers.JsonRpcProvider('https://rpc-animechain-39xf6m45e3.t.conduit.xyz');
        
        // Create Registry contract instance
        const registryContract = new ethers.Contract(
          registryAddress,
          REGISTRY_ABI,
          provider
        );
        
        // Get registry owner
        const owner = await registryContract.owner();
        setRegistryOwner(owner);
        
        // Fetch the first 5 image contracts
        const imageContractsData: ImageContract[] = [];
        
        for (let i = 0; i < 5; i++) {
          try {
            // Get image contract address from registry
            const contractAddress = await registryContract.imageDataContracts(i);
            
            if (contractAddress && contractAddress !== ethers.ZeroAddress) {
              // Create contract instance for the image contract
              const imageContract = new ethers.Contract(
                contractAddress,
                COMMISSIONED_ART_ABI,
                provider
              );
              
              // Get image data, owner, and artist
              const imageData = await imageContract.get_image_data();
              const imageOwner = await imageContract.get_owner();
              const imageArtist = await imageContract.get_artist();
              
              // Convert the hex string to binary for image display
              const hexString = imageData.startsWith('0x') ? imageData.slice(2) : imageData;
              const byteArray = new Uint8Array(hexString.match(/.{1,2}/g)!.map((byte: string) => parseInt(byte, 16)));
              
              // Detect image type
              const imageType = detectImageType(hexString);
              
              // Create a blob and convert to data URL
              const blob = new Blob([byteArray], { type: imageType });
              const imageUrl = URL.createObjectURL(blob);
              
              // Add to our list
              imageContractsData.push({
                id: i,
                address: contractAddress,
                owner: imageOwner,
                artist: imageArtist,
                imageUrl: imageUrl
              });
            }
          } catch (err) {
            console.error(`Error fetching image contract ${i}:`, err);
            // Continue to the next one if there's an error with this one
          }
        }
        
        setImageContracts(imageContractsData);
        setLoading(false);
      } catch (err) {
        console.error("Error fetching registry data:", err);
        setError(err instanceof Error ? err.message : "Unknown error occurred");
        setLoading(false);
      }
    };
    
    fetchData();
    
    // Cleanup function to revoke object URLs on unmount
    return () => {
      imageContracts.forEach(contract => {
        URL.revokeObjectURL(contract.imageUrl);
      });
    };
  }, []);

  if (loading) {
    return <div className="main-tab-container loading">Loading registry and image contracts...</div>;
  }
  
  if (error) {
    return <div className="main-tab-container error">Error: {error}</div>;
  }

  return (
    <div className="main-tab-container">
      <div className="registry-info">
        <h2>Registry Contract</h2>
        <div className="info-row">
          <span className="info-label">Address:</span>
          <span className="info-value">{registryAddress}</span>
        </div>
        {registryOwner && (
          <div className="info-row">
            <span className="info-label">Owner:</span>
            <span className="info-value">{registryOwner}</span>
          </div>
        )}
      </div>
      
      <h2>AVIF Image Contracts</h2>
      {imageContracts.length > 0 ? (
        <div className="image-contracts-grid">
          {imageContracts.map(contract => (
            <div key={contract.id} className="image-contract-card">
              <h3>Azuki ID: {contract.id}</h3>
              <div className="image-display">
                <img src={contract.imageUrl} alt={`Azuki #${contract.id}`} />
              </div>
              <div className="contract-details">
                <div className="info-row">
                  <span className="info-label">Contract:</span>
                  <span className="info-value">{contract.address.substring(0, 10)}...{contract.address.substring(32)}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Owner:</span>
                  <span className="info-value">{contract.owner.substring(0, 10)}...{contract.owner.substring(32)}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Artist:</span>
                  <span className="info-value">{contract.artist.substring(0, 10)}...{contract.artist.substring(32)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="no-contracts">No image contracts found</div>
      )}
    </div>
  );
};

export default MainTab; 