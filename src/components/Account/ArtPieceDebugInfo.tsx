import React, { useState } from 'react';
import { decodeTokenURI } from '../../utils/TokenURIDecoder';
import './Account.css';

interface ArtPieceDebugInfoProps {
  tokenURIData: string | null;
  contractAddress: string;
}

/**
 * Component for displaying debug information about an art piece's tokenURI
 */
const ArtPieceDebugInfo: React.FC<ArtPieceDebugInfoProps> = ({ tokenURIData, contractAddress }) => {
  const [expanded, setExpanded] = useState(false);
  
  // No tokenURI data available
  if (!tokenURIData) {
    return (
      <div className="art-piece-debug">
        <p className="debug-info-error">No tokenURI data available</p>
      </div>
    );
  }
  
  // Try to decode the tokenURI
  const decodedData = decodeTokenURI(tokenURIData);
  
  if (!decodedData) {
    return (
      <div className="art-piece-debug">
        <p className="debug-info-error">Unable to decode tokenURI</p>
        <pre className="debug-raw-data">{tokenURIData.substring(0, 100)}...</pre>
      </div>
    );
  }
  
  const toggleExpanded = () => {
    setExpanded(!expanded);
  };
  
  // Extract first 50 chars of image data
  const imagePreview = decodedData.image ? decodedData.image.substring(0, 50) + '...' : 'No image data';
  
  return (
    <div className={`art-piece-debug ${expanded ? 'expanded' : ''}`}>
      <button className="debug-toggle" onClick={toggleExpanded}>
        {expanded ? 'Hide Debug Info' : 'Show Debug Info'}
      </button>
      
      {expanded && (
        <>
          <div className="debug-section">
            <h4>TokenURI Data</h4>
            <div className="debug-json">
              <pre>{JSON.stringify({
                name: decodedData.name,
                description: decodedData.description,
              }, null, 2)}</pre>
            </div>
          </div>
          
          <div className="debug-section">
            <h4>Image Data (first 50 chars)</h4>
            <pre className="debug-image-data">{imagePreview}</pre>
          </div>
          
          <div className="debug-section">
            <h4>Contract</h4>
            <p className="debug-contract">{contractAddress}</p>
          </div>
        </>
      )}
    </div>
  );
};

export default ArtPieceDebugInfo; 