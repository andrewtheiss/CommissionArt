import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useBlockchain } from '../../utils/BlockchainContext';
import { compressImage, getImageInfo, CompressionResult } from '../../utils/imageCompression';
import { shouldRecommendArWeave, uploadToArWeave, ArWeaveUploadResult } from '../../utils/arweave';
import { 
  formatOpenSeaMetadataAsJSON, 
  createAttribute, 
  createFileProperty, 
  getMimeTypeFromFile,
  OpenSeaAttribute,
  OpenSeaFileProperty,
  MetadataInput 
} from '../../utils/openSeaMetadataFormatter';
import AddMultimedia from '../AddMultimedia/AddMultimedia';
import { ethers } from 'ethers';
import contractConfig from '../../assets/contract_config.json';
import ProfileFactoryABI from '../../assets/abis/ProfileFactoryAndRegistry.json';
import './ComprehensiveUpload.css';

interface ArtworkFormData {
  title: string;
  description: string;
  imageData?: Uint8Array;
  imageFormat?: string;
  originalImageUrl?: string;
}

// Using OpenSea types from the formatter
type NFTAttribute = OpenSeaAttribute;
type NFTFile = OpenSeaFileProperty;

interface NFTProperties {
  files: NFTFile[];
  category?: string;
}

interface SpecialProperties {
  image?: string;
  animation_url?: string;
  external_url?: string;
  audio_url?: string;
  background_color?: string;
  youtube_url?: string;
}

const ComprehensiveUpload: React.FC = () => {
  const { isConnected, walletAddress, hasProfile, checkUserProfile, provider } = useBlockchain();

  // Basic artwork form data
  const [formData, setFormData] = useState<ArtworkFormData>({
    title: '',
    description: '',
  });

  // Image handling states
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [originalPreview, setOriginalPreview] = useState<string | null>(null);
  const [originalInfo, setOriginalInfo] = useState<{ size: number; dimensions: { width: number; height: number }; format: string } | null>(null);
  const [compressedImage, setCompressedImage] = useState<CompressionResult | null>(null);
  const [isCompressing, setIsCompressing] = useState(false);
  
  // ArWeave states
  const [useArWeave, setUseArWeave] = useState<boolean>(false);
  const [arWeaveUploading, setArWeaveUploading] = useState<boolean>(false);
  const [arWeaveResult, setArWeaveResult] = useState<ArWeaveUploadResult | null>(null);
  const [showArWeaveOption, setShowArWeaveOption] = useState<boolean>(false);

  // NFT metadata states
  const [attributes, setAttributes] = useState<NFTAttribute[]>([]);
  const [properties, setProperties] = useState<NFTProperties>({ files: [] });
  const [specialProperties, setSpecialProperties] = useState<SpecialProperties>({});

  // Multimedia toggles and URLs
  const [enableAudio, setEnableAudio] = useState(false);
  const [enableVideo, setEnableVideo] = useState(false);
  const [audioUrl, setAudioUrl] = useState('');
  const [videoUrl, setVideoUrl] = useState('');

  // Form states
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [txHash, setTxHash] = useState<string | null>(null);
  const [newArtPieceAddress, setNewArtPieceAddress] = useState<string | null>(null);
  const [aiGenerated, setAiGenerated] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isConnected) {
      checkUserProfile();
    }
  }, [isConnected, checkUserProfile]);

  // Image handling functions
  const handleFileSelect = async (file: File) => {
    if (!file.type.startsWith('image/')) {
      setError('Please select a valid image file');
      return;
    }
    
    setError(null);
    setSelectedFile(file);
    setCompressedImage(null);
    
    try {
      const info = await getImageInfo(file);
      setOriginalPreview(info.dataUrl);
      const fileInfo = {
        size: info.sizeKB,
        dimensions: info.dimensions,
        format: info.format
      };
      setOriginalInfo(fileInfo);
      await compressImageFile(file, fileInfo);
    } catch (err) {
      console.error('Error processing image:', err);
      setError('Failed to process image');
    }
  };

  const compressImageFile = async (file: File, originalFileInfo: { size: number; dimensions: { width: number; height: number }; format: string }) => {
    setIsCompressing(true);
    setError(null);
    
    try {
      const result = await compressImage(file, {
        format: 'webp',
        quality: 0.8,
        maxWidth: null,
        maxHeight: null,
        targetSizeKB: 42, 
        autoOptimize: true
      });
      
      setCompressedImage(result);
      
      setFormData(prev => ({
        ...prev,
        imageData: result.byteArray,
        imageFormat: result.format
      }));

      if (shouldRecommendArWeave(originalFileInfo.size, result.sizeKB)) {
        setShowArWeaveOption(true);
      } else {
        setShowArWeaveOption(false);
        setUseArWeave(false);
      }
      
    } catch (err) {
      setError(`Compression failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setIsCompressing(false);
    }
  };

  // Drag and drop handlers
  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
      e.dataTransfer.clearData();
    }
  }, []);

  const handleDropzoneClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelect(e.target.files[0]);
    }
  };

  // ArWeave handlers
  const handleArWeaveChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setUseArWeave(e.target.checked);
    if (!e.target.checked) {
      setArWeaveResult(null);
    }
  };

  const handleArWeaveUpload = async () => {
    if (!selectedFile) {
      setError('No file selected for ArWeave upload');
      return;
    }

    setArWeaveUploading(true);
    setError(null);

    try {
      const tags = [
        { name: 'App-Name', value: 'CommissionArt' },
        { name: 'Content-Type', value: selectedFile.type },
        { name: 'Title', value: formData.title || 'Untitled' },
      ];
      const result = await uploadToArWeave(selectedFile, tags);
      setArWeaveResult(result);
      
      if (result.success && result.url) {
        setFormData(prev => ({ ...prev, originalImageUrl: result.url }));
        // Update special properties with image URL
        setSpecialProperties(prev => ({ ...prev, image: result.url }));
      } else {
        setError(result.error || 'ArWeave upload failed');
      }
    } catch (err) {
      setError(`ArWeave upload failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setArWeaveUploading(false);
    }
  };

  // Input change handlers
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // Attribute management
  const addAttribute = () => {
    setAttributes(prev => [...prev, { trait_type: '', value: '', display_type: 'string' }]);
  };

  const updateAttribute = (index: number, field: keyof NFTAttribute, value: string | number) => {
    setAttributes(prev => prev.map((attr, i) => 
      i === index ? { ...attr, [field]: value } : attr
    ));
  };

  const removeAttribute = (index: number) => {
    setAttributes(prev => prev.filter((_, i) => i !== index));
  };

  // Multimedia handlers
  const handleAudioToggle = (enabled: boolean) => {
    setEnableAudio(enabled);
    if (!enabled) {
      setAudioUrl('');
      // Remove audio from properties and special properties
      setProperties(prev => ({
        ...prev,
        files: prev.files.filter(file => !file.type.startsWith('audio/'))
      }));
      setSpecialProperties(prev => {
        const { audio_url, ...rest } = prev;
        return rest;
      });
    }
  };

  const handleVideoToggle = (enabled: boolean) => {
    setEnableVideo(enabled);
    if (!enabled) {
      setVideoUrl('');
      // Remove video from properties and special properties
      setProperties(prev => ({
        ...prev,
        files: prev.files.filter(file => !file.type.startsWith('video/'))
      }));
      setSpecialProperties(prev => {
        const { animation_url, ...rest } = prev;
        return rest;
      });
    }
  };

  const handleAudioUrlChange = (url: string) => {
    setAudioUrl(url);
    if (url.trim()) {
      // Add to properties.files using OpenSea helper
      const mimeType = getMimeTypeFromFile(url);
      const fileProperty = createFileProperty(url, mimeType.startsWith('audio/') ? mimeType : 'audio/mp3', url);
      
      setProperties(prev => ({
        ...prev,
        files: [
          ...prev.files.filter(file => !file.type.startsWith('audio/')),
          fileProperty
        ]
      }));
      // Add to special properties
      setSpecialProperties(prev => ({ ...prev, audio_url: url }));
    }
  };

  const handleVideoUrlChange = (url: string) => {
    setVideoUrl(url);
    if (url.trim()) {
      // Add to properties.files using OpenSea helper
      const mimeType = getMimeTypeFromFile(url);
      const fileProperty = createFileProperty(url, mimeType.startsWith('video/') ? mimeType : 'video/mp4', url);
      
      setProperties(prev => ({
        ...prev,
        files: [
          ...prev.files.filter(file => !file.type.startsWith('video/')),
          fileProperty
        ]
      }));
      // Add to special properties
      setSpecialProperties(prev => ({ ...prev, animation_url: url }));
    }
  };

  // Form submission
  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    
    if (!formData.title.trim() || !formData.imageData || !isConnected || !walletAddress) {
      setError('Please complete the required fields and connect your wallet.');
      return;
    }
    
    setIsSaving(true);
    setError(null);
    
    try {
      if (!provider) {
        throw new Error("Provider not found");
      }

      // Prepare final metadata using OpenSea formatter
      const metadataInput: MetadataInput = {
        name: formData.title,
        description: formData.description,
        image: formData.originalImageUrl || 'embedded',
        attributes: attributes,
        files: properties.files,
        category: properties.category,
        animationUrl: specialProperties.animation_url,
        externalUrl: specialProperties.external_url,
        audioUrl: specialProperties.audio_url,
        backgroundColor: specialProperties.background_color,
        youtubeUrl: specialProperties.youtube_url
      };

      const metadataJSON = formatOpenSeaMetadataAsJSON(metadataInput);

      const finalImageData = useArWeave && arWeaveResult?.url ? 
        new TextEncoder().encode(arWeaveResult.url) :
        formData.imageData;

      const finalFormat = useArWeave && arWeaveResult?.url ? 'arweave' : formData.imageFormat || 'webp';
      
      const signer = await provider.getSigner();
      let tx;
      
      const artPieceTemplateAddress = (contractConfig.networks.mainnet.artPiece as any).address;
      const artCommissionHubAddress = (contractConfig.networks.mainnet.artCommissionHub as any).address;

      if (hasProfile) {
        const profileAddress = await new ethers.Contract((contractConfig.networks.mainnet.profileFactoryAndRegistry as any).address, ProfileFactoryABI, signer).getProfile(walletAddress);
        const profileContract = new ethers.Contract(profileAddress, ProfileFactoryABI, signer);
        
        if (!profileContract) throw new Error("Profile contract not found");

        tx = await profileContract.createArtPiece(
          artPieceTemplateAddress,
          finalImageData,
          finalFormat,
          formData.title,
          metadataJSON,
          true,
          ethers.ZeroAddress,
          artCommissionHubAddress,
          aiGenerated
        );
      } else {
        const profileHubContract = new ethers.Contract((contractConfig.networks.mainnet.profileFactoryAndRegistry as any).address, ProfileFactoryABI, signer);
        tx = await profileHubContract.createProfileAndArtPiece(
          artPieceTemplateAddress,
          finalImageData,
          finalFormat,
          formData.title,
          metadataJSON,
          true,
          ethers.ZeroAddress,
          artCommissionHubAddress,
          aiGenerated
        );
      }
      
      setTxHash(tx.hash);
      const receipt = await tx.wait();

      if (receipt?.logs) {
        const ProfileFactoryInterface = new ethers.Interface(ProfileFactoryABI);
        const createdEvent = receipt.logs.map((log: any) => {
          try { return ProfileFactoryInterface.parseLog(log) } catch { return null }
        }).find((parsedLog: ethers.LogDescription | null) => parsedLog?.name === "ArtPieceCreated");

        if (createdEvent) {
          const artPieceAddress = createdEvent.args[1];
          setNewArtPieceAddress(artPieceAddress);
        }
      }
      
      setSaveSuccess(true);

    } catch (err) {
      setError(`Failed to save artwork: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setIsSaving(false);
    }
  };

  const isFormValid = formData.title.trim() !== '' && (!!formData.imageData || (useArWeave && !!arWeaveResult?.success)) && isConnected;

  return (
    <div className="comprehensive-upload-page">
      <div className="comprehensive-upload-container">
        <div className="upload-header">
          <h1>Create Comprehensive NFT Artwork</h1>
          <p>Upload your artwork with full metadata support including multimedia content</p>
          {!isConnected && <div className="wallet-warning">Please connect your wallet.</div>}
          {isConnected && hasProfile && <div className="profile-info success">Your artwork will be added to your profile.</div>}
          {isConnected && !hasProfile && <div className="profile-info warning">A profile will be created for you when you submit.</div>}
        </div>
        
        <form onSubmit={handleSubmit} className="comprehensive-upload-form">
          {/* Main Image Section */}
          <section className="main-image-section">
            <h2>Main Artwork Image *</h2>
            <div
              className={`image-dropzone ${isDragging ? 'active' : ''}`}
              onClick={handleDropzoneClick}
              onDragEnter={handleDragEnter}
              onDragLeave={handleDragLeave}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
            >
              {originalPreview ? (
                <img src={compressedImage?.dataUrl || originalPreview} alt="Preview" className="preview-image" />
              ) : (
                <>
                  <div className="icon">📷</div>
                  <p>Drop main artwork image here or click to browse</p>
                  <p className="required-note">This image is required for your NFT</p>
                </>
              )}
              <input 
                ref={fileInputRef} 
                type="file" 
                accept="image/*" 
                onChange={handleFileInputChange} 
                style={{ display: 'none' }} 
              />
            </div>
            
            {isCompressing && <div className="compression-status">Optimizing image...</div>}
            
            {compressedImage && !isCompressing && (
              <div className="compression-info">
                <p>Original: {originalInfo?.size.toFixed(2)} KB</p>
                <p>Compressed: {compressedImage.sizeKB.toFixed(2)} KB ({compressedImage.byteArray.length} bytes)</p>
                <p>Format: {compressedImage.format.toUpperCase()}</p>
                <p>Dimensions: {compressedImage.width} × {compressedImage.height}</p>
              </div>
            )}

            {showArWeaveOption && (
              <div className="arweave-option">
                <label>
                  <input type="checkbox" checked={useArWeave} onChange={handleArWeaveChange} />
                  Upload original high-quality image to ArWeave for permanent storage
                </label>
                
                {useArWeave && (
                  <div className="arweave-upload-section">
                    {!arWeaveResult && !arWeaveUploading && (
                      <button type="button" onClick={handleArWeaveUpload} className="arweave-upload-button">
                        Upload Original to ArWeave
                      </button>
                    )}
                    {arWeaveUploading && <div className="arweave-status uploading">Uploading...</div>}
                    {arWeaveResult?.success && <div className="arweave-status success">✓ Uploaded! <a href={arWeaveResult.url} target="_blank" rel="noopener noreferrer">View</a></div>}
                    {arWeaveResult?.error && <div className="arweave-status error">✗ {arWeaveResult.error}</div>}
                  </div>
                )}
              </div>
            )}
          </section>

          {/* Basic Information */}
          <section className="basic-info-section">
            <h2>Basic Information</h2>
            <div className="form-group">
              <label htmlFor="title">Artwork Title *</label>
              <input 
                type="text" 
                id="title" 
                name="title" 
                value={formData.title} 
                onChange={handleInputChange} 
                required 
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="description">Description</label>
              <textarea 
                id="description" 
                name="description" 
                value={formData.description} 
                onChange={handleInputChange} 
                rows={5} 
                placeholder="Describe your artwork..."
              />
            </div>
            
            <div className="form-group checkbox-group">
              <label>
                <input 
                  type="checkbox" 
                  checked={aiGenerated} 
                  onChange={(e) => setAiGenerated(e.target.checked)} 
                />
                AI Generated Artwork
              </label>
            </div>
          </section>

          {/* Multimedia Section */}
          <section className="multimedia-section">
            <h2>Additional Multimedia Content</h2>
            <p className="section-description">Add video or audio content to enhance your NFT</p>
            
            <div className="multimedia-toggles">
              <div className="multimedia-toggle">
                <label>
                  <input 
                    type="checkbox" 
                    checked={enableVideo} 
                    onChange={(e) => handleVideoToggle(e.target.checked)} 
                  />
                  Include Video Content
                </label>
                {enableVideo && (
                  <div className="multimedia-url-input">
                    <input
                      type="url"
                      placeholder="Video URL (ArWeave, IPFS, or direct link)"
                      value={videoUrl}
                      onChange={(e) => handleVideoUrlChange(e.target.value)}
                    />
                  </div>
                )}
              </div>

              <div className="multimedia-toggle">
                <label>
                  <input 
                    type="checkbox" 
                    checked={enableAudio} 
                    onChange={(e) => handleAudioToggle(e.target.checked)} 
                  />
                  Include Audio Content
                </label>
                {enableAudio && (
                  <div className="multimedia-url-input">
                    <input
                      type="url"
                      placeholder="Audio URL (ArWeave, IPFS, or direct link)"
                      value={audioUrl}
                      onChange={(e) => handleAudioUrlChange(e.target.value)}
                    />
                  </div>
                )}
              </div>
            </div>

            {/* Multimedia Upload Component */}
            <div className="multimedia-upload-wrapper">
              <h3>Or Upload Multimedia Files</h3>
              <AddMultimedia
                onFileSelect={(data) => {
                  console.log('Multimedia file selected:', data);
                }}
                onUploadComplete={(result, data) => {
                  console.log('Multimedia upload complete:', result, data);
                  if (result.success && result.url) {
                    // Create file property for OpenSea format
                    const mimeType = data.file ? getMimeTypeFromFile(data.file.name) : 'application/octet-stream';
                    const fileProperty = createFileProperty(result.url, mimeType);
                    
                    // Add to properties.files array
                    setProperties(prev => ({
                      ...prev,
                      files: [...prev.files.filter(f => f.uri !== result.url), fileProperty]
                    }));
                    
                    // Also set specific URL fields and enable toggles
                    if (data.mediaType === 'video') {
                      handleVideoUrlChange(result.url);
                      setEnableVideo(true);
                      setSpecialProperties(prev => ({ ...prev, animation_url: result.url }));
                    } else if (data.mediaType === 'audio') {
                      handleAudioUrlChange(result.url);
                      setEnableAudio(true);
                      setSpecialProperties(prev => ({ ...prev, audio_url: result.url }));
                    }
                  }
                }}
                onError={(error) => {
                  console.error('Multimedia upload error:', error);
                  setError(error);
                }}
                maxSizeMB={750}
                showArweaveOption={true}
              />
            </div>
          </section>

          {/* Attributes Section */}
          <section className="attributes-section">
            <h2>NFT Attributes</h2>
            <p className="section-description">Add traits and properties to your NFT</p>
            
            <div className="attributes-list">
              {attributes.map((attr, index) => (
                <div key={index} className="attribute-item">
                  <div className="attribute-inputs">
                    <input
                      type="text"
                      placeholder="Trait Type (e.g., Artist, Rarity)"
                      value={attr.trait_type}
                      onChange={(e) => updateAttribute(index, 'trait_type', e.target.value)}
                    />
                    <input
                      type="text"
                      placeholder="Value"
                      value={attr.value}
                      onChange={(e) => updateAttribute(index, 'value', e.target.value)}
                    />
                    <select
                      value={attr.display_type || 'string'}
                      onChange={(e) => updateAttribute(index, 'display_type', e.target.value as any)}
                    >
                      <option value="string">Text</option>
                      <option value="number">Number</option>
                      <option value="boost_percentage">Boost %</option>
                      <option value="boost_number">Boost Number</option>
                      <option value="date">Date</option>
                    </select>
                  </div>
                  <button type="button" onClick={() => removeAttribute(index)} className="remove-button">
                    Remove
                  </button>
                </div>
              ))}
            </div>
            
            <button type="button" onClick={addAttribute} className="add-attribute-button">
              Add Attribute
            </button>
          </section>

          {/* Special Properties Section */}
          <section className="special-properties-section">
            <h2>Special Properties</h2>
            <p className="section-description">Additional URLs and external links</p>
            
            <div className="special-properties-grid">
              <div className="form-group">
                <label htmlFor="external_url">External URL</label>
                <input
                  type="url"
                  id="external_url"
                  placeholder="https://yourproject.com/token/123"
                  value={specialProperties.external_url || ''}
                  onChange={(e) => setSpecialProperties(prev => ({ ...prev, external_url: e.target.value }))}
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="youtube_url">YouTube URL</label>
                <input
                  type="url"
                  id="youtube_url"
                  placeholder="https://youtube.com/watch?v=..."
                  value={specialProperties.youtube_url || ''}
                  onChange={(e) => setSpecialProperties(prev => ({ ...prev, youtube_url: e.target.value }))}
                />
              </div>
            </div>
          </section>

          {/* Error and Success Messages */}
          {error && <div className="error-message">{error}</div>}
          {saveSuccess && (
            <div className="success-message">
              Comprehensive NFT created successfully! 
              <br/>
              Tx: <a href={`https://sepolia.arbiscan.io/tx/${txHash}`} target="_blank" rel="noopener noreferrer">{txHash?.slice(0,10)}...</a>
              <br/>
              Contract: <span className="contract-address">{newArtPieceAddress?.slice(0,10)}...</span>
            </div>
          )}

          {/* Submit Actions */}
          <div className="form-actions">
            <button type="button" className="back-button" onClick={() => window.history.back()}>
              Cancel
            </button>
            <button 
              type="submit" 
              className="submit-button" 
              disabled={!isFormValid || isCompressing || isSaving}
            >
              {isSaving ? 'Creating NFT...' : 'Create Comprehensive NFT'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ComprehensiveUpload; 