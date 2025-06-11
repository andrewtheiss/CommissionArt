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

// Sale Types (matching contract constants)
enum SaleType {
  FOREVER = 0,      // No deadline, mint forever
  CAPPED = 1,       // Stop after maxSupply reached
  QUANTITY_PHASES = 2,  // Price increases based on quantity sold
  TIME_PHASES = 3   // Price increases based on time
}

interface PhaseConfig {
  threshold: string; // Quantity for QUANTITY_PHASES, timestamp for TIME_PHASES
  price: string;     // Price in base currency
}

interface EditionFormData {
  name: string;
  symbol: string;
  mintPrice: string;
  maxSupply: string;
  royaltyPercent: string;
  paymentCurrency: string;
  saleType: SaleType;
  enableTimePhases: boolean;
  enableQuantityPhases: boolean;
  timePhases: PhaseConfig[];
  quantityPhases: PhaseConfig[];
}

// ERC20 Token Info Interface
interface TokenInfo {
  symbol: string;
  name: string;
  decimals: number;
  isERC20: boolean;
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
    mintPrice: '',
    maxSupply: '',
    royaltyPercent: '',
    paymentCurrency: '',
    saleType: SaleType.CAPPED,
    enableTimePhases: false,
    enableQuantityPhases: false,
    timePhases: [],
    quantityPhases: []
  });
  
  const [isCreating, setIsCreating] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [hasExistingEdition, setHasExistingEdition] = useState<boolean>(false);
  const [checkingExistingEdition, setCheckingExistingEdition] = useState<boolean>(false);
  
  // Add token info state
  const [tokenInfo, setTokenInfo] = useState<TokenInfo>({
    symbol: 'ETH',
    name: 'Ethereum',
    decimals: 18,
    isERC20: false
  });
  const [isLoadingTokenInfo, setIsLoadingTokenInfo] = useState<boolean>(false);

  // Format address for display
  const formatAddress = (address: string): string => {
    return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
  };

  // Fetch token information for ERC20 tokens
  const fetchTokenInfo = async (tokenAddress: string): Promise<TokenInfo> => {
    if (!tokenAddress || tokenAddress === ethers.ZeroAddress) {
      return {
        symbol: 'ETH',
        name: 'Ethereum',
        decimals: 18,
        isERC20: false
      };
    }

    try {
      setIsLoadingTokenInfo(true);
      const provider = new ethers.BrowserProvider(window.ethereum);
      
      // ERC20 ABI for symbol, name, and decimals
      const erc20Abi = [
        'function symbol() view returns (string)',
        'function name() view returns (string)',
        'function decimals() view returns (uint8)'
      ];
      
      const tokenContract = new ethers.Contract(tokenAddress, erc20Abi, provider);
      
      const [symbol, name, decimals] = await Promise.all([
        tokenContract.symbol(),
        tokenContract.name(),
        tokenContract.decimals()
      ]);
      
      return {
        symbol,
        name,
        decimals: Number(decimals),
        isERC20: true
      };
    } catch (error) {
      console.error('Error fetching token info:', error);
      // Fallback for invalid token addresses
      return {
        symbol: 'TOKEN',
        name: 'Unknown Token',
        decimals: 18,
        isERC20: true
      };
    } finally {
      setIsLoadingTokenInfo(false);
    }
  };

  // Update token info when payment currency changes
  useEffect(() => {
    const updateTokenInfo = async () => {
      const info = await fetchTokenInfo(formData.paymentCurrency);
      setTokenInfo(info);
    };
    
    updateTokenInfo();
  }, [formData.paymentCurrency]);

  // Convert price to correct decimal format
  const convertPriceToTokenUnits = (price: string): bigint => {
    if (!price || isNaN(Number(price))) {
      return BigInt(0);
    }
    
    if (tokenInfo.isERC20) {
      // For ERC20 tokens, use the token's decimals
      return ethers.parseUnits(price, tokenInfo.decimals);
    } else {
      // For native ETH, use 18 decimals
      return ethers.parseEther(price);
    }
  };

  // Initialize form data when art piece changes
  useEffect(() => {
    if (artPieceDetails && selectedArtPiece) {
      setFormData({
        name: `${artPieceDetails.title} Edition`,
        symbol: 'ART',
        mintPrice: '0.01',
        maxSupply: '100',
        royaltyPercent: '2.5',
        paymentCurrency: '',
        saleType: SaleType.CAPPED,
        enableTimePhases: false,
        enableQuantityPhases: false,
        timePhases: [],
        quantityPhases: []
      });
      checkForExistingEdition();
    }
  }, [artPieceDetails, selectedArtPiece]);

  // Update sale type based on phase selections
  useEffect(() => {
    if (formData.enableTimePhases && !formData.enableQuantityPhases) {
      setFormData(prev => ({ ...prev, saleType: SaleType.TIME_PHASES }));
    } else if (formData.enableQuantityPhases && !formData.enableTimePhases) {
      setFormData(prev => ({ ...prev, saleType: SaleType.QUANTITY_PHASES }));
    } else if (!formData.enableTimePhases && !formData.enableQuantityPhases) {
      // If max supply is set to a very high number, default to FOREVER, otherwise CAPPED
      const maxSupply = parseInt(formData.maxSupply) || 100;
      setFormData(prev => ({ 
        ...prev, 
        saleType: maxSupply >= 1000000 ? SaleType.FOREVER : SaleType.CAPPED 
      }));
    }
  }, [formData.enableTimePhases, formData.enableQuantityPhases, formData.maxSupply]);

  // Check if art piece already has an edition
  const checkForExistingEdition = async () => {
    if (!profileContract || !selectedArtPiece) return;

    try {
      setCheckingExistingEdition(true);
      const hasEditions = await profileContract.artPieceHasEditions(selectedArtPiece);
      setHasExistingEdition(hasEditions);
    } catch (error) {
      console.error('Error checking for existing edition:', error);
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
      mintPrice: '',
      maxSupply: '',
      royaltyPercent: '',
      paymentCurrency: '',
      saleType: SaleType.CAPPED,
      enableTimePhases: false,
      enableQuantityPhases: false,
      timePhases: [],
      quantityPhases: []
    });
    setFormError(null);
    setIsCreating(false);
    setHasExistingEdition(false);
    setTokenInfo({
      symbol: 'ETH',
      name: 'Ethereum',
      decimals: 18,
      isERC20: false
    });
    onClose();
  };

  // Handle form input changes
  const handleInputChange = (field: keyof EditionFormData, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: field === 'symbol' ? value.toUpperCase() : value
    }));
    
    if (formError) {
      setFormError(null);
    }
  };

  // Handle phase changes
  const handlePhaseChange = (type: 'time' | 'quantity', index: number, field: 'threshold' | 'price', value: string) => {
    const phaseField = type === 'time' ? 'timePhases' : 'quantityPhases';
    setFormData(prev => ({
      ...prev,
      [phaseField]: prev[phaseField].map((phase, i) => 
        i === index ? { ...phase, [field]: value } : phase
      )
    }));
  };

  // Add new phase
  const addPhase = (type: 'time' | 'quantity') => {
    const phaseField = type === 'time' ? 'timePhases' : 'quantityPhases';
    setFormData(prev => ({
      ...prev,
      [phaseField]: [...prev[phaseField], { threshold: '', price: '' }]
    }));
  };

  // Remove phase
  const removePhase = (type: 'time' | 'quantity', index: number) => {
    const phaseField = type === 'time' ? 'timePhases' : 'quantityPhases';
    setFormData(prev => ({
      ...prev,
      [phaseField]: prev[phaseField].filter((_, i) => i !== index)
    }));
  };

  // Convert timestamp string to Unix timestamp
  const convertToTimestamp = (dateTimeString: string): number => {
    return Math.floor(new Date(dateTimeString).getTime() / 1000);
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
    if (Number(formData.royaltyPercent) > 100) {
      return 'Royalty percent cannot exceed 100%';
    }

    // Validate phases if enabled
    if (formData.enableTimePhases) {
      if (formData.timePhases.length === 0) {
        return 'At least one time phase is required when time-based pricing is enabled';
      }
      for (let i = 0; i < formData.timePhases.length; i++) {
        const phase = formData.timePhases[i];
        if (!phase.threshold || !phase.price) {
          return `Time phase ${i + 1} is incomplete`;
        }
        if (isNaN(Number(phase.price)) || Number(phase.price) < 0) {
          return `Invalid price in time phase ${i + 1}`;
        }
        // Validate that it's a valid datetime
        if (isNaN(convertToTimestamp(phase.threshold))) {
          return `Invalid date/time in time phase ${i + 1}`;
        }
      }
    }

    if (formData.enableQuantityPhases) {
      if (formData.quantityPhases.length === 0) {
        return 'At least one quantity phase is required when quantity-based pricing is enabled';
      }
      for (let i = 0; i < formData.quantityPhases.length; i++) {
        const phase = formData.quantityPhases[i];
        if (!phase.threshold || !phase.price) {
          return `Quantity phase ${i + 1} is incomplete`;
        }
        if (isNaN(Number(phase.price)) || Number(phase.price) < 0) {
          return `Invalid price in quantity phase ${i + 1}`;
        }
        if (isNaN(Number(phase.threshold)) || Number(phase.threshold) < 1) {
          return `Invalid quantity threshold in phase ${i + 1}`;
        }
      }
    }

    if (formData.enableTimePhases && formData.enableQuantityPhases) {
      return 'Cannot enable both time-based and quantity-based pricing simultaneously';
    }

    return null;
  };

  // Create the art edition
  const handleCreateEdition = async () => {
    if (!selectedArtPiece || !profileContract || !isArtist) {
      setFormError('Missing required data or insufficient permissions');
      return;
    }

    const validationError = validateForm();
    if (validationError) {
      setFormError(validationError);
      return;
    }

    try {
      setIsCreating(true);
      setFormError(null);

      // Convert form values to contract parameters using correct decimals
      const mintPriceTokenUnits = convertPriceToTokenUnits(formData.mintPrice);
      const maxSupply = parseInt(formData.maxSupply);
      const royaltyBasisPoints = Math.floor(parseFloat(formData.royaltyPercent) * 100);

      // Prepare phases array with correct decimal conversions
      let phases: Array<{threshold: bigint, price: bigint}> = [];
      
      if (formData.saleType === SaleType.TIME_PHASES && formData.timePhases.length > 0) {
        phases = formData.timePhases.map(phase => ({
          threshold: BigInt(convertToTimestamp(phase.threshold)),
          price: convertPriceToTokenUnits(phase.price)
        }));
      } else if (formData.saleType === SaleType.QUANTITY_PHASES && formData.quantityPhases.length > 0) {
        phases = formData.quantityPhases.map(phase => ({
          threshold: BigInt(parseInt(phase.threshold)),
          price: convertPriceToTokenUnits(phase.price)
        }));
      }

      console.log('Creating art edition with parameters:', {
        artPiece: selectedArtPiece,
        name: formData.name,
        symbol: formData.symbol,
        mintPrice: formData.mintPrice,
        mintPriceTokenUnits: mintPriceTokenUnits.toString(),
        maxSupply,
        royaltyPercent: formData.royaltyPercent,
        royaltyBasisPoints,
        paymentCurrency: formData.paymentCurrency || 'Native ETH',
        tokenInfo,
        saleType: formData.saleType,
        phases: phases.length
      });

      // Call the createArtEdition method on the profile contract
      const tx = await profileContract['createArtEdition(address,string,string,uint256,uint256,uint256,address,uint256,(uint256,uint256)[])'](
        selectedArtPiece,
        formData.name,
        formData.symbol,
        mintPriceTokenUnits,
        maxSupply,
        royaltyBasisPoints,
        formData.paymentCurrency || ethers.ZeroAddress,
        formData.saleType,
        phases
      );

      console.log('Transaction submitted:', tx.hash);
      const receipt = await tx.wait();
      console.log('Transaction confirmed:', receipt);

      // Extract edition address from logs
      let editionAddress = '';
      if (receipt.logs && receipt.logs.length > 0) {
        for (const log of receipt.logs) {
          try {
            if (log.topics && log.topics.length > 0) {
              editionAddress = 'created';
            }
          } catch (error) {
            console.log('Could not parse log:', error);
          }
        }
      }

      onSuccess(editionAddress || 'created');
      handleClose();

    } catch (error: any) {
      console.error('Error creating art edition:', error);
      
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

          {!isArtist && (
            <div className="warning-message">
              Only artists can create editions. Please activate artist mode first.
            </div>
          )}

          {/* Edition creation form */}
          <form className="edition-form" onSubmit={(e) => e.preventDefault()}>
            {/* Basic Info */}
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

            {/* Pricing and Supply */}
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="mint-price">
                  Starting Price ({tokenInfo.symbol}) *
                  {isLoadingTokenInfo && <span className="loading-indicator">🔄</span>}
                </label>
                <input
                  id="mint-price"
                  type="number"
                  step="0.001"
                  min="0"
                  value={formData.mintPrice}
                  onChange={(e) => handleInputChange('mintPrice', e.target.value)}
                  placeholder={tokenInfo.isERC20 ? "100" : "0.01"}
                  disabled={isCreating || !isArtist}
                  required
                />
                <small className="form-help">
                  Starting price per token in {tokenInfo.symbol}
                  {tokenInfo.isERC20 && ` (${tokenInfo.name})`}
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
                  {formData.saleType === SaleType.FOREVER 
                    ? 'Set high for unlimited minting (e.g., 999999999)'
                    : 'Maximum tokens that can be minted'
                  }
                </small>
              </div>
            </div>

            {/* Royalty and Payment */}
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="royalty-percent">Royalty (%) *</label>
                <input
                  id="royalty-percent"
                  type="number"
                  step="0.1"
                  min="0"
                  max="100"
                  value={formData.royaltyPercent}
                  onChange={(e) => handleInputChange('royaltyPercent', e.target.value)}
                  placeholder="2.5"
                  disabled={isCreating || !isArtist}
                  required
                />
                <small className="form-help">
                  Royalty percentage (0-100%)
                </small>
              </div>
              <div className="form-group">
                <label htmlFor="payment-currency">Payment Currency</label>
                <input
                  id="payment-currency"
                  type="text"
                  value={formData.paymentCurrency}
                  onChange={(e) => handleInputChange('paymentCurrency', e.target.value)}
                  placeholder="0x... (leave empty for native ETH)"
                  disabled={isCreating || !isArtist}
                />
                <small className="form-help">
                  ERC20 token address. Leave empty for native ETH.
                  {tokenInfo.isERC20 && ` Current: ${tokenInfo.name} (${tokenInfo.symbol})`}
                </small>
              </div>
            </div>

            {/* Sale Type Configuration */}
            <div className="form-section">
              <h4>Sale Configuration</h4>
              
              {/* Sale Type Display */}
              <div className="sale-type-info">
                <strong>Sale Type: </strong>
                <span className="sale-type-label">
                  {formData.saleType === SaleType.FOREVER && 'Unlimited Minting'}
                  {formData.saleType === SaleType.CAPPED && 'Limited Supply'}
                  {formData.saleType === SaleType.TIME_PHASES && 'Time-Based Pricing'}
                  {formData.saleType === SaleType.QUANTITY_PHASES && 'Quantity-Based Pricing'}
                </span>
              </div>

              {/* Dynamic Pricing Options */}
              <div className="pricing-options">
                <div className="checkbox-group">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={formData.enableTimePhases}
                      onChange={(e) => {
                        handleInputChange('enableTimePhases', e.target.checked);
                        if (e.target.checked) {
                          handleInputChange('enableQuantityPhases', false);
                        }
                      }}
                      disabled={isCreating || !isArtist}
                    />
                    <span>Price adjusts by time</span>
                  </label>
                  <small className="form-help">
                    Price increases at specific timestamps
                  </small>
                </div>

                <div className="checkbox-group">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={formData.enableQuantityPhases}
                      onChange={(e) => {
                        handleInputChange('enableQuantityPhases', e.target.checked);
                        if (e.target.checked) {
                          handleInputChange('enableTimePhases', false);
                        }
                      }}
                      disabled={isCreating || !isArtist}
                    />
                    <span>Price adjusts by sales</span>
                  </label>
                  <small className="form-help">
                    Price increases after certain quantities sold
                  </small>
                </div>
              </div>

              {/* Time-Based Phases */}
              {formData.enableTimePhases && (
                <div className="phases-section">
                  <div className="phases-header">
                    <h5>Time-Based Price Phases</h5>
                    <button
                      type="button"
                      className="add-phase-btn"
                      onClick={() => addPhase('time')}
                      disabled={formData.timePhases.length >= 5 || isCreating || !isArtist}
                    >
                      + Add Phase
                    </button>
                  </div>
                  {formData.timePhases.map((phase, index) => (
                    <div key={index} className="phase-config">
                      <div className="phase-inputs">
                        <div className="form-group">
                          <label>Activation Date/Time</label>
                          <input
                            type="datetime-local"
                            value={phase.threshold}
                            onChange={(e) => handlePhaseChange('time', index, 'threshold', e.target.value)}
                            disabled={isCreating || !isArtist}
                          />
                        </div>
                        <div className="form-group">
                          <label>Price ({tokenInfo.symbol})</label>
                          <input
                            type="number"
                            step="0.001"
                            min="0"
                            value={phase.price}
                            onChange={(e) => handlePhaseChange('time', index, 'price', e.target.value)}
                            placeholder={tokenInfo.isERC20 ? "200" : "0.02"}
                            disabled={isCreating || !isArtist}
                          />
                        </div>
                        <button
                          type="button"
                          className="remove-phase-btn"
                          onClick={() => removePhase('time', index)}
                          disabled={isCreating || !isArtist}
                        >
                          ×
                        </button>
                      </div>
                    </div>
                  ))}
                  {formData.timePhases.length === 0 && (
                    <p className="phase-help">Add time phases to increase price at specific dates/times</p>
                  )}
                </div>
              )}

              {/* Quantity-Based Phases */}
              {formData.enableQuantityPhases && (
                <div className="phases-section">
                  <div className="phases-header">
                    <h5>Quantity-Based Price Phases</h5>
                    <button
                      type="button"
                      className="add-phase-btn"
                      onClick={() => addPhase('quantity')}
                      disabled={formData.quantityPhases.length >= 5 || isCreating || !isArtist}
                    >
                      + Add Phase
                    </button>
                  </div>
                  {formData.quantityPhases.map((phase, index) => (
                    <div key={index} className="phase-config">
                      <div className="phase-inputs">
                        <div className="form-group">
                          <label>Sold Quantity Threshold</label>
                          <input
                            type="number"
                            min="1"
                            value={phase.threshold}
                            onChange={(e) => handlePhaseChange('quantity', index, 'threshold', e.target.value)}
                            placeholder="50"
                            disabled={isCreating || !isArtist}
                          />
                        </div>
                        <div className="form-group">
                          <label>Price ({tokenInfo.symbol})</label>
                          <input
                            type="number"
                            step="0.001"
                            min="0"
                            value={phase.price}
                            onChange={(e) => handlePhaseChange('quantity', index, 'price', e.target.value)}
                            placeholder={tokenInfo.isERC20 ? "200" : "0.02"}
                            disabled={isCreating || !isArtist}
                          />
                        </div>
                        <button
                          type="button"
                          className="remove-phase-btn"
                          onClick={() => removePhase('quantity', index)}
                          disabled={isCreating || !isArtist}
                        >
                          ×
                        </button>
                      </div>
                    </div>
                  ))}
                  {formData.quantityPhases.length === 0 && (
                    <p className="phase-help">Add quantity phases to increase price after certain amounts are sold</p>
                  )}
                </div>
              )}
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