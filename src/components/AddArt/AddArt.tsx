import React, { useState, useRef, useCallback, useEffect } from 'react';
import { compressImage, getImageInfo, CompressionResult } from '../../utils/imageCompression';
import { useBlockchain } from '../../utils/BlockchainContext';
import { ethers } from 'ethers';
import { 
  shouldRecommendArWeave, 
  uploadToArWeave,
  ArWeaveUploadResult 
} from '../../utils/arweave';
// Note: These are placeholder imports. You will need to create these services.
// import profileService from '../../utils/profileService';
import ethersService from '../../utils/ethers-service';
import contractConfig from '../../assets/contract_config.json';
import ProfileFactoryABI from '../../assets/abis/ProfileFactoryAndRegistry.json';
import ArtPieceABI from '../../assets/abis/ArtPiece.json';
import AddMultimedia from '../AddMultimedia/AddMultimedia';
import './AddArt.css';
import '../AddMultimedia/AddMultimedia.css';

interface ArtFormData {
  title: string;
  description: string;
  imageData?: Uint8Array;
  format?: string;
  arweaveUrl?: string;
}

const AddArt: React.FC = () => {
  const { isConnected, walletAddress, hasProfile, checkUserProfile, provider } = useBlockchain();

  const [formData, setFormData] = useState<ArtFormData>({
    title: '',
    description: '',
    arweaveUrl: '',
  });

  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [originalPreview, setOriginalPreview] = useState<string | null>(null);
  const [originalInfo, setOriginalInfo] = useState<{ size: number; dimensions: { width: number; height: number }; format: string } | null>(null);
  const [compressedImage, setCompressedImage] = useState<CompressionResult | null>(null);
  const [isCompressing, setIsCompressing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [txHash, setTxHash] = useState<string | null>(null);
  const [newArtPieceAddress, setNewArtPieceAddress] = useState<string | null>(null);
  const [aiGenerated, setAiGenerated] = useState<boolean>(false);

  const [useArWeave, setUseArWeave] = useState<boolean>(false);
  const [arWeaveUploading, setArWeaveUploading] = useState<boolean>(false);
  const [arWeaveResult, setArWeaveResult] = useState<ArWeaveUploadResult | null>(null);
  const [showArWeaveOption, setShowArWeaveOption] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  
  useEffect(() => {
    if (isConnected) {
      checkUserProfile();
    }
  }, [isConnected, checkUserProfile]);
  
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
        format: result.format
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
  
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };
  
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
  
  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    
    if (!formData.title.trim() || !formData.imageData || !isConnected || !walletAddress) {
      setError('Please complete the form and connect your wallet.');
      return;
    }
    
    setIsSaving(true);
    setError(null);
    
    try {
        if(!provider) {
            throw new Error("Provider not found");
        }
      const finalImageData = useArWeave && arWeaveResult?.url ? 
        new TextEncoder().encode(arWeaveResult.url) :
        formData.imageData;

      const finalFormat = useArWeave && arWeaveResult?.url ? 'arweave' : formData.format || 'webp';
      
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
      
      console.log(`[AddArt] Network: ${currentNetwork.name} (${currentNetwork.chainId}) => Environment: ${environment}`);
      
      const artPieceTemplateAddress = contractConfig.networks[environment].artPiece.address;
      const artCommissionHubAddress = contractConfig.networks[environment].artCommissionHub.address;

      if (hasProfile) {
        const profileFactoryContract = new ethers.Contract(contractConfig.networks[environment].profileFactoryAndRegistry.address, ProfileFactoryABI, signer);
        const profileAddress = await profileFactoryContract.getProfile(walletAddress);
        const ProfileABI = await import('../../assets/abis/Profile.json');
        const profileContract = new ethers.Contract(profileAddress, ProfileABI.default, signer);
        
        if (!profileContract) throw new Error("Profile contract not found");

        tx = await profileContract['createArtPiece(address,bytes,string,string,string,bool,address,bool,address,bool,string)'](
          artPieceTemplateAddress,      // _art_piece_template
          finalImageData,               // _token_uri_data
          finalFormat,                  // _token_uri_data_format
          formData.title,               // _title
          formData.description || '',   // _description
          true,                         // _as_artist
          walletAddress,                // _other_party (user's own address for personal art)
          aiGenerated,                  // _ai_generated
          artCommissionHubAddress,      // _art_commission_hub
          false,                        // _is_profile_art
          ''                            // _token_uri_json (empty for simple art pieces)
        );
      } else {
        const profileHubContract = new ethers.Contract(contractConfig.networks[environment].profileFactoryAndRegistry.address, ProfileFactoryABI, signer);
        tx = await profileHubContract.createNewArtPieceAndRegisterProfileAndAttachToHub(
          artPieceTemplateAddress,      // _art_piece_template
          finalImageData,               // _token_uri_data
          finalFormat,                  // _token_uri_data_format
          formData.title,               // _title
          formData.description || '',   // _description
          true,                         // _is_artist
          walletAddress,                // _other_party (user's own address for personal art)
          artCommissionHubAddress,      // _commission_hub
          aiGenerated,                  // _ai_generated
          1,                            // _linked_to_art_commission_hub_chain_id (generic)
          ethers.ZeroAddress,           // _linked_to_art_commission_hub_address (empty for no hub)
          0,                            // _linked_to_art_commission_hub_token_id_or_generic_hub_account
          ''                            // _token_uri_json (empty for simple art pieces)
        );
      }
      
      setTxHash(tx.hash);
      const receipt = await tx.wait();

      if(receipt?.logs) {
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
      if (!result.success) setError(result.error || 'ArWeave upload failed');
    } catch (err) {
      setError(`ArWeave upload failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setArWeaveUploading(false);
    }
  };

  return (
    <div className="add-art-page">
      <div className="add-art-container">
        <div className="add-art-header">
          <h2>Add Artwork</h2>
          {!isConnected && <div className="wallet-warning">Please connect your wallet.</div>}
          {isConnected && hasProfile && <div className="profile-info success">Your artwork will be added to your profile.</div>}
          {isConnected && !hasProfile && <div className="profile-info warning">A profile will be created for you when you submit.</div>}
        </div>
        
        <form onSubmit={handleSubmit} className="add-art-form">
          <div className="art-image-section">
            <div
              className={`dropzone ${isDragging ? 'active' : ''}`}
              onClick={handleDropzoneClick}
              onDragEnter={handleDragEnter} onDragLeave={handleDragLeave}
              onDragOver={handleDragOver} onDrop={handleDrop}
            >
              {originalPreview ? (
                <img src={compressedImage?.dataUrl || originalPreview} alt="Preview" className="preview-image" />
              ) : (
                <>
                  <div className="icon">📷</div>
                  <p>Drop image here or click to browse</p>
                </>
              )}
              <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFileInputChange} style={{ display: 'none' }} />
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
                  Upload original file to ArWeave for high-quality storage
                </label>
                
                {useArWeave && (
                  <div className="arweave-upload-section">
                    {!arWeaveResult && !arWeaveUploading && (
                      <button type="button" onClick={handleArWeaveUpload} className="arweave-upload-button">
                        Upload to Arweave
                      </button>
                    )}
                    {arWeaveUploading && <div className="arweave-status uploading">Uploading...</div>}
                    {arWeaveResult?.success && <div className="arweave-status success">✓ Uploaded! <a href={arWeaveResult.url} target="_blank" rel="noopener noreferrer">View</a></div>}
                    {arWeaveResult?.error && <div className="arweave-status error">✗ {arWeaveResult.error}</div>}
                  </div>
                )}
              </div>
            )}
            
            {error && <div className="error-message">{error}</div>}
            {saveSuccess && (
              <div className="success-message">
                Artwork saved! Tx: <a href={`https://sepolia.arbiscan.io/tx/${txHash}`} target="_blank" rel="noopener noreferrer">{txHash?.slice(0,10)}...</a>
                <br/>
                Contract: <span className="contract-address">{newArtPieceAddress?.slice(0,10)}...</span>
              </div>
            )}
          </div>
          
          <div className="art-info-section">
            <div className="form-group">
              <label htmlFor="title">Title *</label>
              <input type="text" id="title" name="title" value={formData.title} onChange={handleInputChange} required />
            </div>
            
            <div className="form-group">
              <label htmlFor="description">Description</label>
              <textarea id="description" name="description" value={formData.description} onChange={handleInputChange} rows={5} />
            </div>
            
            <div className="form-group checkbox-group">
              <label>
                <input type="checkbox" checked={aiGenerated} onChange={(e) => setAiGenerated(e.target.checked)} />
                AI Generated Artwork
              </label>
            </div>
            
            <div className="form-actions">
                              <button type="button" className="back-link" onClick={() => window.history.back()}>Cancel</button>
              <button type="submit" className="submit-button" disabled={!isFormValid || isCompressing || isSaving}>
                {isSaving ? 'Saving...' : 'Save Artwork'}
              </button>
            </div>
          </div>
        </form>

        {/* Multimedia Upload Section */}
        <div className="multimedia-section">
          <AddMultimedia
            onFileSelect={(data) => {
              console.log('Multimedia file selected:', data);
            }}
            onUploadComplete={(result, data) => {
              console.log('Multimedia upload complete:', result, data);
            }}
            onError={(error) => {
              console.error('Multimedia upload error:', error);
            }}
            maxSizeMB={750}
            showArweaveOption={true}
          />
        </div>
      </div>
    </div>
  );
};

export default AddArt; 