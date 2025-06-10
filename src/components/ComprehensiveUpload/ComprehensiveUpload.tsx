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
import ethersService from '../../utils/ethers-service';

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

interface ComprehensiveUploadProps {
  onBack?: () => void;
  userType?: 'artist' | 'commissioner';
}

const ComprehensiveUpload: React.FC<ComprehensiveUploadProps> = ({ onBack, userType }) => {
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
  const [enableImage, setEnableImage] = useState(false);
  const [audioUrl, setAudioUrl] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const [imageUrl, setImageUrl] = useState('');

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
      setVideoUrl(currentVideoUrl => {
        setSpecialProperties(prev => {
          const { audio_url, ...rest } = prev;
          return {
            ...rest,
            // If audio is disabled, use video URL for animation_url if video exists
            animation_url: currentVideoUrl.trim() ? currentVideoUrl : undefined
          };
        });
        return currentVideoUrl; // Don't change videoUrl, just use it for reference
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
      setAudioUrl(currentAudioUrl => {
        setSpecialProperties(prev => {
          // If video is disabled, only keep animation_url if audio exists
          const { animation_url, ...rest } = prev;
          return {
            ...rest,
            animation_url: currentAudioUrl.trim() ? currentAudioUrl : undefined
          };
        });
        return currentAudioUrl; // Don't change audioUrl, just use it for reference
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
      // Add to special properties - audio gets priority for animation_url
      setSpecialProperties(prev => ({ ...prev, audio_url: url, animation_url: url }));
    } else {
      // If audio URL is cleared, check if we have video to use for animation_url
      setVideoUrl(currentVideoUrl => {
        setSpecialProperties(prev => {
          const { audio_url, ...rest } = prev;
          return {
            ...rest,
            animation_url: currentVideoUrl.trim() ? currentVideoUrl : undefined
          };
        });
        return currentVideoUrl; // Don't change videoUrl, just use it for reference
      });
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
      // Add to special properties - only set animation_url if no audio exists
      setAudioUrl(currentAudioUrl => {
        setSpecialProperties(prev => ({ 
          ...prev, 
          animation_url: currentAudioUrl.trim() ? prev.animation_url : url 
        }));
        return currentAudioUrl; // Don't change audioUrl, just use it for reference
      });
    } else {
      // If video URL is cleared and no audio exists, clear animation_url
      setAudioUrl(currentAudioUrl => {
        setSpecialProperties(prev => ({
          ...prev,
          animation_url: currentAudioUrl.trim() ? currentAudioUrl : undefined
        }));
        return currentAudioUrl; // Don't change audioUrl, just use it for reference
      });
    }
  };

  const handleImageToggle = (enabled: boolean) => {
    setEnableImage(enabled);
    if (!enabled) {
      setImageUrl('');
      // Remove image from properties and special properties
      setProperties(prev => ({
        ...prev,
        files: prev.files.filter(file => !file.type.startsWith('image/'))
      }));
      setSpecialProperties(prev => {
        const { image, ...rest } = prev;
        return rest;
      });
    }
  };

  const handleImageUrlChange = (url: string) => {
    setImageUrl(url);
    if (url.trim()) {
      // Add to properties.files using OpenSea helper
      const mimeType = getMimeTypeFromFile(url);
      const fileProperty = createFileProperty(url, mimeType.startsWith('image/') ? mimeType : 'image/jpeg', url);
      
      setProperties(prev => ({
        ...prev,
        files: [
          ...prev.files.filter(file => !file.type.startsWith('image/')),
          fileProperty
        ]
      }));
      // Add to special properties
      setSpecialProperties(prev => ({ ...prev, image: url }));
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
        image: specialProperties.image || formData.originalImageUrl || 'embedded',
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
      
      // Get contract addresses from config - use current network
      const currentNetwork = ethersService.getNetwork();
      
      // Determine environment based on network configuration (same logic as profile service)
      // Testnet: Arbitrum Sepolia (421614) or Ethereum Sepolia (11155111)
      // Mainnet: AnimeChain (69000) or Ethereum Mainnet (1)
      let environment: "testnet" | "mainnet";
      
      if (currentNetwork.chainId === 421614 || currentNetwork.chainId === 11155111) {
        // Arbitrum Sepolia or Ethereum Sepolia
        environment = "testnet";
      } else if (currentNetwork.chainId === 69000 || currentNetwork.chainId === 1) {
        // AnimeChain or Ethereum Mainnet
        environment = "mainnet";
      } else {
        // Default fallback - determine by network name
        environment = currentNetwork.name === "Sepolia" || currentNetwork.name === "Arbitrum Sepolia" ? "testnet" : "mainnet";
      }
      
      console.log(`[ComprehensiveUpload] Network: ${currentNetwork.name} (${currentNetwork.chainId}) => Environment: ${environment}`);
      
      const artPieceTemplateAddress = contractConfig.networks[environment].artPiece.address;
      const profileFactoryRegistryAddress = contractConfig.networks[environment].profileFactoryAndRegistry.address;
      
      if (!artPieceTemplateAddress || !profileFactoryRegistryAddress) {
        throw new Error(`Contract addresses not configured for ${environment} network`);
      }

      if (hasProfile) {
        // User has profile - get profile address and use Profile.createArtPiece
        const profileFactoryContract = new ethers.Contract(
          profileFactoryRegistryAddress, 
          ProfileFactoryABI, 
          signer
        );
        
        let profileAddress;
        try {
          profileAddress = await profileFactoryContract.getProfile(walletAddress);
          
          // Check if profile address is valid (not zero address)
          if (!profileAddress || profileAddress === ethers.ZeroAddress) {
            console.log("Profile address is zero, user doesn't actually have a profile");
            // Fall back to creating new profile and art piece
            const profileFactoryContract = new ethers.Contract(
              profileFactoryRegistryAddress, 
              ProfileFactoryABI, 
              signer
            );
            
            console.log('=== CREATING PROFILE AND ART PIECE (FALLBACK) ===');
            console.log('Profile Factory Address:', profileFactoryRegistryAddress);
            console.log('User Address:', walletAddress);
            console.log('Art Piece Template:', artPieceTemplateAddress);
            console.log('=================================================');
            
            // Use the combined method to create profile and art piece in one transaction
            tx = await profileFactoryContract['createNewArtPieceAndRegisterProfileAndAttachToHub(address,bytes,string,string,string,bool,address,address,bool,uint256,address,uint256,string)'](
              artPieceTemplateAddress,           // _art_piece_template
              finalImageData,                    // _token_uri_data
              finalFormat,                       // _token_uri_data_format
              formData.title,                    // _title
              formData.description || '',        // _description
              true,                              // _is_artist (true since they're creating personal art)
              ethers.ZeroAddress,                // _other_party (zero address for personal art)
              ethers.ZeroAddress,                // _commission_hub (empty for personal art)
              aiGenerated,                       // _ai_generated
              1,                                 // _linked_to_art_commission_hub_chain_id (generic)
              ethers.ZeroAddress,                // _linked_to_art_commission_hub_address (empty for no hub)
              0,                                 // _linked_to_art_commission_hub_token_id_or_generic_hub_account
              metadataJSON                       // _token_uri_json (full metadata JSON)
            );
          } else {
            // Profile exists, proceed with normal flow
            // Import Profile ABI
            const ProfileABI = await import('../../assets/abis/Profile.json');
            const profileContract = new ethers.Contract(profileAddress, ProfileABI.default, signer);
            
            if (!profileContract) throw new Error("Profile contract not found");

            // Log all parameters before creating art piece
            console.log('=== CREATE ART PIECE PARAMETERS ===');
            console.log('1. _art_piece_template:', artPieceTemplateAddress);
            console.log('2. _token_uri_data (length):', finalImageData.length, 'bytes');
            console.log('2. _token_uri_data (first 100 chars):', 
              finalImageData instanceof Uint8Array 
                ? new TextDecoder().decode(finalImageData.slice(0, 100)) + '...'
                : String(finalImageData).substring(0, 100) + '...'
            );
            console.log('3. _token_uri_data_format:', finalFormat);
            console.log('4. _title:', formData.title);
            console.log('5. _description (metadata JSON):');
            console.log(JSON.stringify(JSON.parse(metadataJSON), null, 2));
            console.log('6. _as_artist:', true);
            console.log('7. _other_party:', ethers.ZeroAddress);
            console.log('8. _ai_generated:', aiGenerated);
            console.log('9. _art_commission_hub:', ethers.ZeroAddress);
            console.log('10. _is_profile_art:', false);
            console.log('=====================================');

            // Use the specific createArtPiece method signature with 11 parameters to avoid ambiguity
            tx = await profileContract['createArtPiece(address,bytes,string,string,string,bool,address,bool,address,bool,string)'](
              artPieceTemplateAddress,           // _art_piece_template
              finalImageData,                    // _token_uri_data
              finalFormat,                       // _token_uri_data_format 
              formData.title,                    // _title
              formData.description || '',        // _description
              true,                              // _as_artist (true since they're creating personal art)
              walletAddress,                     // _other_party (user's own address for personal art)
              aiGenerated,                       // _ai_generated
              ethers.ZeroAddress,                // _art_commission_hub (empty for personal art)
              false,                             // _is_profile_art (false for regular art pieces)
              metadataJSON                       // _token_uri_json (full metadata JSON)
            );
          }
        } catch (error) {
          console.error("Error in profile check or art creation:", error);
          throw error;
        }
      } else {
        // User doesn't have profile - use the ProfileFactoryAndRegistry's combined creation method
        const profileFactoryContract = new ethers.Contract(
          profileFactoryRegistryAddress, 
          ProfileFactoryABI, 
          signer
        );
        
        console.log('=== CREATING PROFILE AND ART PIECE ===');
        console.log('Profile Factory Address:', profileFactoryRegistryAddress);
        console.log('User Address:', walletAddress);
        console.log('Art Piece Template:', artPieceTemplateAddress);
        console.log('==========================================');
        
        // Use the combined method to create profile and art piece in one transaction
        tx = await profileFactoryContract['createNewArtPieceAndRegisterProfileAndAttachToHub(address,bytes,string,string,string,bool,address,address,bool,uint256,address,uint256,string)'](
          artPieceTemplateAddress,           // _art_piece_template
          finalImageData,                    // _token_uri_data
          finalFormat,                       // _token_uri_data_format
          formData.title,                    // _title
          formData.description || '',        // _description
          true,                              // _is_artist (true since they're creating personal art)
          walletAddress,                     // _other_party (user's own address for personal art)
          ethers.ZeroAddress,                // _commission_hub (empty for personal art)
          aiGenerated,                       // _ai_generated
          1,                                 // _linked_to_art_commission_hub_chain_id (generic)
          ethers.ZeroAddress,                // _linked_to_art_commission_hub_address (empty for no hub)
          0,                                 // _linked_to_art_commission_hub_token_id_or_generic_hub_account
          metadataJSON                       // _token_uri_json (full metadata JSON)
        );
      }
      
      setTxHash(tx.hash);
      const receipt = await tx.wait();

      // Look for ArtPieceCreated event to get the new art piece address
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
      
      // Refresh profile status since we may have created a new profile
      await checkUserProfile();

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
          <h1>
            {userType === 'commissioner' 
              ? 'Commission Artwork Creation' 
              : 'Create Comprehensive NFT Artwork'
            }
          </h1>
          <p>
            {userType === 'commissioner'
              ? 'Upload your artwork or commission new pieces with full metadata support including multimedia content'
              : 'Upload your artwork with full metadata support including multimedia content'
            }
          </p>
          {!isConnected && <div className="wallet-warning">Please connect your wallet.</div>}
          {isConnected && hasProfile && <div className="profile-info success">Your artwork will be added to your profile.</div>}
          {isConnected && !hasProfile && <div className="profile-info warning">A profile will be created for you when you submit.</div>}
          
          {/* User type explanation */}
          <div className={`user-type-explanation ${userType}`}>
            {userType === 'commissioner' ? (
              <div>
                <h3>Creating as a Commissioner</h3>
                <p>You're uploading artwork as a commissioner. This means you can either:</p>
                <ul>
                  <li>Upload artwork you've commissioned from artists</li>
                  <li>Upload your own personal artwork collection</li>
                  <li>Create NFTs to represent commissioned work</li>
                </ul>
                <p><strong>Note:</strong> When uploading commissioned work, make sure you have permission from the artist.</p>
              </div>
            ) : (
              <div>
                <h3>Creating as an Artist</h3>
                <p>You're uploading artwork as an artist. This will:</p>
                <ul>
                  <li>Create an NFT of your original artwork</li>
                  <li>Add the artwork to your artist profile</li>
                  <li>Allow you to set up sales and editions later</li>
                </ul>
                <p><strong>Note:</strong> Only upload artwork that you created or have rights to.</p>
              </div>
            )}
          </div>
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
                {userType === 'commissioner' 
                  ? 'This artwork was created using AI tools' 
                  : 'AI Generated Artwork'
                }
              </label>
            </div>
          </section>

          {/* Multimedia Section */}
          <section className="multimedia-section">
            <h2>Additional Multimedia Content</h2>
            <p className="section-description">Add image, video or audio content to enhance your NFT</p>
            
            <div className="multimedia-toggles">
              <div className="multimedia-toggle">
                <label>
                  <input 
                    type="checkbox" 
                    checked={enableImage} 
                    onChange={(e) => handleImageToggle(e.target.checked)} 
                  />
                  Include Additional Image Content
                </label>
                {enableImage && (
                  <div className="multimedia-url-input">
                    <input
                      type="url"
                      placeholder="Image URL (ArWeave, IPFS, or direct link)"
                      value={imageUrl}
                      onChange={(e) => handleImageUrlChange(e.target.value)}
                    />
                  </div>
                )}
              </div>

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
                    if (data.mediaType === 'image') {
                      handleImageUrlChange(result.url);
                      setEnableImage(true);
                      setSpecialProperties(prev => ({ ...prev, image: result.url }));
                    } else if (data.mediaType === 'video') {
                      handleVideoUrlChange(result.url);
                      setEnableVideo(true);
                      // The handleVideoUrlChange already handles the animation_url logic correctly
                    } else if (data.mediaType === 'audio') {
                      handleAudioUrlChange(result.url);
                      setEnableAudio(true);
                      // The handleAudioUrlChange already handles the animation_url logic correctly
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
                <label htmlFor="image_url">Image URL</label>
                <input
                  type="url"
                  id="image_url"
                  placeholder="https://ipfs.io/ipfs/... or https://..."
                  value={specialProperties.image || ''}
                  onChange={(e) => {
                    const url = e.target.value;
                    setSpecialProperties(prev => ({ ...prev, image: url }));
                    // Also sync with multimedia toggle
                    setImageUrl(url);
                    setEnableImage(!!url.trim());
                    // Update properties.files if URL is provided
                    if (url.trim()) {
                      const mimeType = getMimeTypeFromFile(url);
                      const fileProperty = createFileProperty(url, mimeType.startsWith('image/') ? mimeType : 'image/jpeg', url);
                      setProperties(prev => ({
                        ...prev,
                        files: [
                          ...prev.files.filter(file => !file.type.startsWith('image/')),
                          fileProperty
                        ]
                      }));
                    } else {
                      // Remove image files if URL is cleared
                      setProperties(prev => ({
                        ...prev,
                        files: prev.files.filter(file => !file.type.startsWith('image/'))
                      }));
                    }
                  }}
                />
              </div>
              
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
            <button type="button" className="back-button" onClick={onBack || (() => window.history.back())}>
              Cancel
            </button>
            <button 
              type="submit" 
              className="submit-button" 
              disabled={!isFormValid || isCompressing || isSaving}
            >
              {isSaving 
                ? (userType === 'commissioner' ? 'Creating Commission...' : 'Creating NFT...') 
                : (userType === 'commissioner' ? 'Create Commission NFT' : 'Create Comprehensive NFT')
              }
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ComprehensiveUpload; 