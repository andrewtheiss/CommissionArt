import React, { useState, useEffect } from 'react';
import { ethers } from 'ethers';
import ArtDisplay from '../ArtDisplay';
import './CreateArtEdition.css';

interface ArtPieceDetails {
  title: string;
  tokenURIData: string | null;
  imageData: Uint8Array | null;
  format: string | null;
}

interface CreateArtEditionProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (editionAddress: string) => void;
  onError: (error: string) => void;
  selectedArtPiece: string | null;
  artPieceDetails: ArtPieceDetails | null;
  profileContract: ethers.Contract | null;
  isArtist: boolean;
}

interface EditionFormData {
  name: string;
  symbol: string;
  baseUri: string;
  mintPrice: string;
  maxSupply: string;
  royaltyPercent: string;
}

const CreateArtEdition: React.FC<CreateArtEditionProps> = ({
  isOpen,
  onClose,
  onSuccess,
  onError,
  selectedArtPiece,
  artPieceDetails,
  profileContract,
  isArtist
}) => {
  const [formData, setFormData] = useState<EditionFormData>({
    name: '',
    symbol: '',
    baseUri: '',
    mintPrice: '',
    maxSupply: '',
    royaltyPercent: ''
  });
  
  const [isCreating, setIsCreating] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [hasExistingEdition, setHasExistingEdition] = useState<boolean>(false);
  const [checkingExistingEdition, setCheckingExistingEdition] = useState<boolean>(false);

  // Format address for display
  const formatAddress = (address: string): string => {
    return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
  };

  // Initialize form data when art piece changes
  useEffect(() => {
    if (artPieceDetails && selectedArtPiece) {
      setFormData({
        name: `${artPieceDetails.title} Edition`,
        symbol: 'ART',
        baseUri: 'https://api.example.com/metadata/',
        mintPrice: '0.01',
        maxSupply: '100',
        royaltyPercent: '2.5'
      });
      checkForExistingEdition();
    }
  }, [artPieceDetails, selectedArtPiece]);

  // Check if art piece already has an edition
  const checkForExistingEdition = async () => {
    if (!profileContract || !selectedArtPiece) return;

    try {
      setCheckingExistingEdition(true);
      const hasEditions = await profileContract.artPieceHasEditions(selectedArtPiece);
      setHasExistingEdition(hasEditions);
    } catch (error) {
      console.error('Error checking for existing edition:', error);
      // Don't show error for this check, just assume no existing edition
      setHasExistingEdition(false);
    } finally {
      setCheckingExistingEdition(false);
    }
  };

  // Reset form and close modal
  const handleClose = () => {
    setFormData({
      name: '',
      symbol: '',
      baseUri: '',
      mintPrice: '',
      maxSupply: '',
      royaltyPercent: ''
    });
    setFormError(null);
    setIsCreating(false);
    setHasExistingEdition(false);
    onClose();
  };

  // Handle form input changes
  const handleInputChange = (field: keyof EditionFormData, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: field === 'symbol' ? value.toUpperCase() : value
    }));
    
    // Clear error when user starts typing
    if (formError) {
      setFormError(null);
    }
  };

  // Validate form data
  const validateForm = (): string | null => {
    if (!formData.name.trim()) {
      return 'Edition name is required';
    }
    if (!formData.symbol.trim()) {
      return 'Edition symbol is required';
    }
    if (formData.symbol.length > 10) {
      return 'Symbol must be 10 characters or less';
    }
    if (!formData.mintPrice || isNaN(Number(formData.mintPrice)) || Number(formData.mintPrice) < 0) {
      return 'Valid mint price is required';
    }
    if (!formData.maxSupply || isNaN(Number(formData.maxSupply)) || Number(formData.maxSupply) < 1) {
      return 'Valid max supply is required (minimum 1)';
    }
    if (!formData.royaltyPercent || isNaN(Number(formData.royaltyPercent)) || Number(formData.royaltyPercent) < 0) {
      return 'Valid royalty percent is required';
    }
    if (Number(formData.royaltyPercent) > 10) {
      return 'Royalty percent cannot exceed 10%';
    }
    
    return null;
  };

  // Create the art edition
  const handleCreateEdition = async () => {
    if (!selectedArtPiece || !profileContract || !isArtist) {
      setFormError('Missing required data or insufficient permissions');
      return;
    }

    // Validate form
    const validationError = validateForm();
    if (validationError) {
      setFormError(validationError);
      return;
    }

    try {
      setIsCreating(true);
      setFormError(null);

      // Convert form values to contract parameters
      const mintPriceWei = ethers.parseEther(formData.mintPrice);
      const maxSupply = parseInt(formData.maxSupply);
      const royaltyBasisPoints = Math.floor(parseFloat(formData.royaltyPercent) * 100); // Convert percent to basis points

      console.log('Creating art edition with parameters:', {
        artPiece: selectedArtPiece,
        name: formData.name,
        symbol: formData.symbol,
        baseUri: formData.baseUri,
        mintPrice: formData.mintPrice,
        mintPriceWei: mintPriceWei.toString(),
        maxSupply,
        royaltyPercent: formData.royaltyPercent,
        royaltyBasisPoints
      });

      // Call the createArtEdition method on the profile contract
      const tx = await profileContract.createArtEdition(
        selectedArtPiece,
        formData.name,
        formData.symbol,
        formData.baseUri,
        mintPriceWei,
        maxSupply,
        royaltyBasisPoints
      );

      console.log('Transaction submitted:', tx.hash);

      // Wait for transaction confirmation
      const receipt = await tx.wait();
      console.log('Transaction confirmed:', receipt);

      // Extract the edition address from transaction logs or return value
      let editionAddress = '';
      if (receipt.logs && receipt.logs.length > 0) {
        // Try to find the edition address in the logs
        for (const log of receipt.logs) {
          try {
            // This is a simplified approach - in a real implementation,
            // you might want to parse the logs more carefully
            if (log.topics && log.topics.length > 0) {
              // The actual edition address would be in the transaction return value
              // For now, we'll use a placeholder that indicates success
              editionAddress = 'created'; // This will be replaced with actual address parsing
            }
          } catch (error) {
            console.log('Could not parse log:', error);
          }
        }
      }

      // Call success callback
      onSuccess(editionAddress || 'created');
      
      // Close the modal
      handleClose();

    } catch (error: any) {
      console.error('Error creating art edition:', error);
      
      // Extract meaningful error message
      let errorMessage = 'Failed to create art edition';
      if (error.message) {
        if (error.message.includes('user rejected')) {
          errorMessage = 'Transaction was cancelled by user';
        } else if (error.message.includes('insufficient funds')) {
          errorMessage = 'Insufficient funds for transaction';
        } else if (error.message.includes('Art piece already has an edition')) {
          errorMessage = 'This art piece already has an edition';
        } else if (error.message.includes('Must be the artist')) {
          errorMessage = 'Only the artist can create editions for this art piece';
        } else if (error.message.includes('Art piece not in profile')) {
          errorMessage = 'Art piece not found in your profile';
        } else {
          errorMessage = error.message;
        }
      }
      
      setFormError(errorMessage);
      onError(errorMessage);
    } finally {
      setIsCreating(false);
    }
  };

  // Don't render if not open
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="create-edition-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Create Art Edition</h3>
          <button className="modal-close" onClick={handleClose} disabled={isCreating}>
            ×
          </button>
        </div>

        <div className="modal-content">
          {/* Art piece preview */}
          {selectedArtPiece && artPieceDetails && (
            <div className="selected-art-preview">
              <div className="preview-image">
                {artPieceDetails.tokenURIData ? (
                  <ArtDisplay
                    imageData={artPieceDetails.tokenURIData}
                    title={artPieceDetails.title}
                    contractAddress={selectedArtPiece}
                    className="modal-art-display"
                    showDebug={false}
                  />
                ) : (
                  <div className="art-piece-placeholder">
                    <div className="art-piece-image-placeholder">Art</div>
                  </div>
                )}
              </div>
              <div className="preview-info">
                <h4>{artPieceDetails.title}</h4>
                <p className="art-address">{formatAddress(selectedArtPiece)}</p>
                {checkingExistingEdition && (
                  <p className="checking-status">Checking for existing editions...</p>
                )}
                {hasExistingEdition && (
                  <p className="warning-message">⚠️ This art piece already has an edition</p>
                )}
              </div>
            </div>
          )}

          {/* Error display */}
          {formError && (
            <div className="error-message">{formError}</div>
          )}

          {/* Disable form if not artist */}
          {!isArtist && (
            <div className="warning-message">
              Only artists can create editions. Please activate artist mode first.
            </div>
          )}

          {/* Edition creation form */}
          <form className="edition-form" onSubmit={(e) => e.preventDefault()}>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="edition-name">Edition Name *</label>
                <input
                  id="edition-name"
                  type="text"
                  value={formData.name}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                  placeholder="My Art Edition"
                  disabled={isCreating || !isArtist}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="edition-symbol">Symbol *</label>
                <input
                  id="edition-symbol"
                  type="text"
                  value={formData.symbol}
                  onChange={(e) => handleInputChange('symbol', e.target.value)}
                  placeholder="ART"
                  maxLength={10}
                  disabled={isCreating || !isArtist}
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="base-uri">Base URI</label>
              <input
                id="base-uri"
                type="url"
                value={formData.baseUri}
                onChange={(e) => handleInputChange('baseUri', e.target.value)}
                placeholder="https://api.example.com/metadata/"
                disabled={isCreating || !isArtist}
              />
              <small className="form-help">
                Optional: URL for token metadata. Can be updated later.
              </small>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="mint-price">Mint Price (ETH) *</label>
                <input
                  id="mint-price"
                  type="number"
                  step="0.001"
                  min="0"
                  value={formData.mintPrice}
                  onChange={(e) => handleInputChange('mintPrice', e.target.value)}
                  placeholder="0.01"
                  disabled={isCreating || !isArtist}
                  required
                />
                <small className="form-help">
                  Price per token in ETH
                </small>
              </div>
              <div className="form-group">
                <label htmlFor="max-supply">Max Supply *</label>
                <input
                  id="max-supply"
                  type="number"
                  min="1"
                  value={formData.maxSupply}
                  onChange={(e) => handleInputChange('maxSupply', e.target.value)}
                  placeholder="100"
                  disabled={isCreating || !isArtist}
                  required
                />
                <small className="form-help">
                  Maximum number of tokens that can be minted
                </small>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="royalty-percent">Royalty Percentage *</label>
              <input
                id="royalty-percent"
                type="number"
                step="0.1"
                min="0"
                max="10"
                value={formData.royaltyPercent}
                onChange={(e) => handleInputChange('royaltyPercent', e.target.value)}
                placeholder="2.5"
                disabled={isCreating || !isArtist}
                required
              />
              <small className="form-help">
                Royalty on secondary sales (0-10%). Example: 2.5 = 2.5%
              </small>
            </div>
          </form>
        </div>

        <div className="modal-footer">
          <button 
            className="modal-button secondary"
            onClick={handleClose}
            disabled={isCreating}
          >
            Cancel
          </button>
          <button 
            className="modal-button primary"
            onClick={handleCreateEdition}
            disabled={isCreating || !isArtist || hasExistingEdition || checkingExistingEdition}
          >
            {isCreating ? (
              <>
                <span>Creating Edition...</span>
                <div className="button-spinner"></div>
              </>
            ) : hasExistingEdition ? (
              'Edition Already Exists'
            ) : checkingExistingEdition ? (
              'Checking...'
            ) : (
              'Create Edition'
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default CreateArtEdition; 