import React, { useState } from 'react';
import AddMultimedia, { MediaType } from '../AddMultimedia/AddMultimedia';
import { ArWeaveUploadResult } from '../../utils/arweave';

interface MultimediaData {
  file: File;
  mediaType: MediaType;
  preview?: string;
  duration?: number;
  dimensions?: { width: number; height: number };
}

const AddArtWithMultimedia: React.FC = () => {
  const [artworkTitle, setArtworkTitle] = useState('');
  const [artworkDescription, setArtworkDescription] = useState('');
  const [selectedMultimedia, setSelectedMultimedia] = useState<MultimediaData | null>(null);
  const [uploadedToArweave, setUploadedToArweave] = useState<ArWeaveUploadResult | null>(null);

  const handleMultimediaSelect = (data: MultimediaData) => {
    console.log('Multimedia selected:', data);
    setSelectedMultimedia(data);
    // Reset Arweave upload when new file is selected
    setUploadedToArweave(null);
  };

  const handleUploadComplete = (result: ArWeaveUploadResult, data: MultimediaData) => {
    console.log('Upload completed:', result);
    if (result.success) {
      setUploadedToArweave(result);
      // Here you could save the Arweave URL instead of the compressed image
      // for your artwork metadata
    }
  };

  const handleError = (error: string) => {
    console.error('Multimedia error:', error);
    // Handle error display in your UI
  };

  const handleSubmitArtwork = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!artworkTitle.trim()) {
      alert('Please enter an artwork title');
      return;
    }

    if (!selectedMultimedia) {
      alert('Please select a multimedia file');
      return;
    }

    // Here you would integrate with your existing artwork submission logic
    const artworkData = {
      title: artworkTitle,
      description: artworkDescription,
      mediaType: selectedMultimedia.mediaType,
      file: selectedMultimedia.file,
      arweaveUrl: uploadedToArweave?.url || null,
      transactionId: uploadedToArweave?.transactionId || null
    };

    console.log('Submitting artwork:', artworkData);
    
    // Your existing blockchain submission logic here...
    // Example:
    // await submitToBlockchain(artworkData);
  };

  return (
    <div className="add-art-with-multimedia">
      <div className="page-header">
        <h2>Create Artwork</h2>
        <p>Upload your multimedia content and create an NFT artwork</p>
      </div>

      <form onSubmit={handleSubmitArtwork} className="artwork-form">
        {/* Multimedia Upload Section */}
        <AddMultimedia
          onFileSelect={handleMultimediaSelect}
          onUploadComplete={handleUploadComplete}
          onError={handleError}
          acceptedTypes="image/*,video/*,audio/*"
          maxSizeMB={500} // 500MB max for large video files
          showArweaveOption={true}
        />

        {/* Artwork Details */}
        <div className="artwork-details">
          <div className="form-group">
            <label htmlFor="title">Artwork Title *</label>
            <input
              type="text"
              id="title"
              value={artworkTitle}
              onChange={(e) => setArtworkTitle(e.target.value)}
              placeholder="Enter artwork title"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="description">Description</label>
            <textarea
              id="description"
              value={artworkDescription}
              onChange={(e) => setArtworkDescription(e.target.value)}
              placeholder="Describe your artwork (optional)"
              rows={4}
            />
          </div>

          {/* Summary of selected multimedia */}
          {selectedMultimedia && (
            <div className="multimedia-summary">
              <h4>Selected Media:</h4>
              <p><strong>Type:</strong> {selectedMultimedia.mediaType.toUpperCase()}</p>
              <p><strong>File:</strong> {selectedMultimedia.file.name}</p>
              <p><strong>Size:</strong> {(selectedMultimedia.file.size / 1024 / 1024).toFixed(2)} MB</p>
              {selectedMultimedia.dimensions && (
                <p><strong>Dimensions:</strong> {selectedMultimedia.dimensions.width} × {selectedMultimedia.dimensions.height}</p>
              )}
              {selectedMultimedia.duration && (
                <p><strong>Duration:</strong> {Math.floor(selectedMultimedia.duration / 60)}:{Math.floor(selectedMultimedia.duration % 60).toString().padStart(2, '0')}</p>
              )}
              {uploadedToArweave && (
                <p><strong>Arweave URL:</strong> <a href={uploadedToArweave.url} target="_blank" rel="noopener noreferrer">View on Arweave</a></p>
              )}
            </div>
          )}

          <div className="form-actions">
            <button type="button" onClick={() => window.history.back()}>
              Cancel
            </button>
            <button 
              type="submit" 
              disabled={!artworkTitle.trim() || !selectedMultimedia}
              className="submit-button"
            >
              Create Artwork NFT
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};

export default AddArtWithMultimedia; 