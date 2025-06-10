import React, { useState, useEffect } from 'react';
import { useBlockchain } from '../../utils/BlockchainContext';
import ethersService from '../../utils/ethers-service';
import abiLoader from '../../utils/abiLoader';
import { ethers } from 'ethers';
import './MintArtEdition.css';

interface MintArtEditionProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (txHash: string) => void;
  onError: (error: string) => void;
  artPieceAddress: string | null;
  artSales1155Address: string | null;
}

const MintArtEdition: React.FC<MintArtEditionProps> = ({
  isOpen,
  onClose,
  onSuccess,
  onError,
  artPieceAddress,
  artSales1155Address
}) => {
  const { isConnected, walletAddress } = useBlockchain();
  
  // Modal states
  const [loading, setLoading] = useState<boolean>(false);
  const [mintAmount, setMintAmount] = useState<number>(1);
  const [editionInfo, setEditionInfo] = useState<{
    name: string;
    symbol: string;
    mintPrice: string;
    maxSupply: number;
    currentSupply: number;
    royaltyPercent: number;
    paymentCurrency: string;
    saleActive: boolean;
    erc1155Address: string;
  } | null>(null);

      // State for sale management
    const [managingSale, setManagingSale] = useState<boolean>(false);
    const [debugInfo, setDebugInfo] = useState<any>(null);
  
  // Loading edition information
  useEffect(() => {
    if (isOpen && artSales1155Address && artPieceAddress) {
      loadEditionInfo();
    }
  }, [isOpen, artSales1155Address, artPieceAddress]);

  const loadEditionInfo = async () => {
    if (!artSales1155Address || !artPieceAddress) return;
    
    try {
      setLoading(true);
      
      const signer = await ethersService.getSigner();
      if (!signer) {
        throw new Error("Wallet not connected");
      }

      // Load ArtSales1155 ABI
      const artSalesAbi = abiLoader.loadABI('ArtSales1155');
      if (!artSalesAbi) {
        throw new Error("ArtSales1155 ABI not found");
      }

      const artSalesContract = new ethers.Contract(artSales1155Address, artSalesAbi, signer);
      
      // Check if this art piece has an edition
      const hasEditions = await artSalesContract.hasEditions(artPieceAddress);
      if (!hasEditions) {
        throw new Error("No editions found for this art piece");
      }

      // Get the ERC1155 address mapped to this art piece
      const erc1155Address = await artSalesContract.artistPieceToErc1155Map(artPieceAddress);
      if (!erc1155Address || erc1155Address === ethers.ZeroAddress) {
        throw new Error("No ERC1155 contract found for this art piece");
      }

      // Check if sale is active
      const saleActive = await artSalesContract.isSaleActive(erc1155Address);
      
      // Get sale info
      const saleInfo = await artSalesContract.getSaleInfo(erc1155Address);
      const [mintPrice, maxSupply, currentSupply, royaltyPercent, , saleType] = saleInfo;

      // Load ArtEdition1155 ABI to get edition details
      const artEditionAbi = abiLoader.loadABI('ArtEdition1155');
      if (!artEditionAbi) {
        throw new Error("ArtEdition1155 ABI not found");
      }

      const editionContract = new ethers.Contract(erc1155Address, artEditionAbi, signer);
      
      // Get edition name and symbol
      const name = await editionContract.name();
      const symbol = await editionContract.symbol();
      
      // Get payment currency (if applicable)
      let paymentCurrency = "ETH"; // Default
      try {
        const currencyAddress = await editionContract.paymentCurrency();
        if (currencyAddress && currencyAddress !== ethers.ZeroAddress) {
          // Could load ERC20 contract to get symbol, for now just show address
          paymentCurrency = currencyAddress;
        }
      } catch (err) {
        // Payment currency might not be implemented or might be ETH
        console.log("Payment currency not available or ETH");
      }

      setEditionInfo({
        name,
        symbol,
        mintPrice: ethers.formatEther(mintPrice),
        maxSupply: Number(maxSupply),
        currentSupply: Number(currentSupply),
        royaltyPercent: Number(royaltyPercent),
        paymentCurrency,
        saleActive,
        erc1155Address
      });

    } catch (err: any) {
      console.error("Error loading edition info:", err);
      onError(`Failed to load edition information: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleMint = async () => {
    if (!artSales1155Address || !editionInfo || !isConnected) return;
    
    try {
      setLoading(true);
      
      const signer = await ethersService.getSigner();
      if (!signer) {
        throw new Error("Wallet not connected");
      }

      // Load ArtEdition1155 ABI for minting
      const artEditionAbi = abiLoader.loadABI('ArtEdition1155');
      if (!artEditionAbi) {
        throw new Error("ArtEdition1155 ABI not found");
      }

      const editionContract = new ethers.Contract(editionInfo.erc1155Address, artEditionAbi, signer);
      
      // Calculate total cost
      const mintPriceWei = ethers.parseEther(editionInfo.mintPrice);
      const totalCost = mintPriceWei * BigInt(mintAmount);
      
      // Check if payment is in ETH or ERC20
      let tx;
      if (editionInfo.paymentCurrency === "ETH") {
        // Mint with ETH
        tx = await editionContract.mint(walletAddress, mintAmount, {
          value: totalCost
        });
      } else {
        // For ERC20 payments, we'd need to approve first
        // This is a simplified version - in reality you'd need to handle ERC20 approvals
        tx = await editionContract.mint(walletAddress, mintAmount);
      }
      
      // Wait for transaction
      const receipt = await tx.wait();
      console.log("Mint successful:", receipt);
      
      onSuccess(receipt.hash);
      onClose();
      
    } catch (err: any) {
      console.error("Error minting:", err);
      let errorMessage = "Failed to mint edition";
      
      if (err.message?.includes("insufficient funds")) {
        errorMessage = "Insufficient funds for minting";
      } else if (err.message?.includes("exceeds max supply")) {
        errorMessage = "Mint amount exceeds maximum supply";
      } else if (err.message?.includes("sale not active")) {
        errorMessage = "Sale is not currently active";
      } else if (err.reason) {
        errorMessage = err.reason;
      }
      
      onError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleStartSale = async () => {
    if (!artSales1155Address || !editionInfo || !isConnected) return;
    
    try {
      setManagingSale(true);
      
      const signer = await ethersService.getSigner();
      if (!signer) {
        throw new Error("Wallet not connected");
      }

      // Load ArtSales1155 ABI for sale management
      const artSalesAbi = abiLoader.loadABI('ArtSales1155');
      if (!artSalesAbi) {
        throw new Error("ArtSales1155 ABI not found");
      }

      const artSalesContract = new ethers.Contract(artSales1155Address, artSalesAbi, signer);
      
      // Start the sale
      const tx = await artSalesContract.startSaleForEdition(editionInfo.erc1155Address);
      const receipt = await tx.wait();
      
      console.log("Sale started successfully:", receipt);
      
      // Refresh edition info to show updated sale status
      await loadEditionInfo();
      
      onSuccess(receipt.hash);
      
    } catch (err: any) {
      console.error("Error starting sale:", err);
      let errorMessage = "Failed to start sale";
      
      if (err.message?.includes("Only owner can start sales")) {
        errorMessage = "Only the edition owner can start sales";
      } else if (err.reason) {
        errorMessage = err.reason;
      }
      
      onError(errorMessage);
    } finally {
      setManagingSale(false);
    }
  };

  const handleClose = () => {
    if (!loading && !managingSale) {
      setMintAmount(1);
      setEditionInfo(null);
      setManagingSale(false);
      onClose();
    }
  };

  // Debug function to check ownership
  const checkOwnership = async () => {
    try {
      console.log('[MintArtEdition] Checking ownership...');
      const provider = ethersService.getProvider();
      if (!provider) throw new Error('No provider available');

      const signer = await provider.getSigner();
      const currentAddress = await signer.getAddress();
      console.log('[MintArtEdition] Current wallet address:', currentAddress);

      if (!artSales1155Address) {
        console.log('[MintArtEdition] No ArtSales1155 address available');
        return;
      }

      const ArtSales1155ABI = (await import('../../assets/abis/ArtSales1155.json')).default;
      const salesContract = new ethers.Contract(artSales1155Address, ArtSales1155ABI, provider);

      const contractOwner = await salesContract.owner();
      const profileAddress = await salesContract.profileAddress();
      
      console.log('[MintArtEdition] ArtSales1155 contract owner:', contractOwner);
      console.log('[MintArtEdition] ArtSales1155 profile address:', profileAddress);
      console.log('[MintArtEdition] Current wallet matches owner:', currentAddress.toLowerCase() === contractOwner.toLowerCase());

      setDebugInfo({
        currentWallet: currentAddress,
        contractOwner,
        profileAddress,
        isOwner: currentAddress.toLowerCase() === contractOwner.toLowerCase(),
        artSalesAddress: artSales1155Address
      });

    } catch (error) {
      console.error('[MintArtEdition] Error checking ownership:', error);
      setDebugInfo({ error: error instanceof Error ? error.message : String(error) });
    }
  };

     // Check ownership when modal opens
   useEffect(() => {
     if (isOpen && artSales1155Address) {
       checkOwnership();
     }
   }, [isOpen, artSales1155Address]);

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content mint-edition-modal">
        <div className="modal-header">
          <h2>Manage Art Edition</h2>
          <button 
            className="modal-close-button" 
            onClick={handleClose}
            disabled={loading}
          >
            ×
          </button>
        </div>
        
        <div className="modal-body">
          {loading && !editionInfo ? (
            <div className="loading-spinner">Loading edition information...</div>
          ) : editionInfo ? (
            <div className="edition-details">
              <div className="edition-info">
                <h3>{editionInfo.name} ({editionInfo.symbol})</h3>
                <div className="info-row">
                  <span className="label">Price per mint:</span>
                  <span className="value">{editionInfo.mintPrice} {editionInfo.paymentCurrency === "ETH" ? "ETH" : "tokens"}</span>
                </div>
                <div className="info-row">
                  <span className="label">Supply:</span>
                  <span className="value">{editionInfo.currentSupply} / {editionInfo.maxSupply}</span>
                </div>
                <div className="info-row">
                  <span className="label">Royalty:</span>
                  <span className="value">{editionInfo.royaltyPercent}%</span>
                </div>
                <div className="info-row">
                  <span className="label">Sale Status:</span>
                  <span className={`value ${editionInfo.saleActive ? 'active' : 'inactive'}`}>
                    {editionInfo.saleActive ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </div>

              {editionInfo.saleActive ? (
                <div className="mint-controls">
                  <div className="mint-amount-control">
                    <label htmlFor="mint-amount">Amount to mint:</label>
                    <div className="amount-input-group">
                      <button 
                        className="amount-button"
                        onClick={() => setMintAmount(Math.max(1, mintAmount - 1))}
                        disabled={loading || mintAmount <= 1}
                      >
                        -
                      </button>
                      <input
                        id="mint-amount"
                        type="number"
                        min="1"
                        max={editionInfo.maxSupply - editionInfo.currentSupply}
                        value={mintAmount}
                        onChange={(e) => setMintAmount(Math.max(1, parseInt(e.target.value) || 1))}
                        className="amount-input"
                        disabled={loading}
                      />
                      <button 
                        className="amount-button"
                        onClick={() => setMintAmount(Math.min(editionInfo.maxSupply - editionInfo.currentSupply, mintAmount + 1))}
                        disabled={loading || mintAmount >= (editionInfo.maxSupply - editionInfo.currentSupply)}
                      >
                        +
                      </button>
                    </div>
                  </div>

                  <div className="total-cost">
                    <strong>Total Cost: {(parseFloat(editionInfo.mintPrice) * mintAmount).toFixed(6)} {editionInfo.paymentCurrency === "ETH" ? "ETH" : "tokens"}</strong>
                  </div>

                  <div className="modal-actions">
                    <button 
                      className="cancel-button" 
                      onClick={handleClose}
                      disabled={loading}
                    >
                      Cancel
                    </button>
                    <button 
                      className="mint-button" 
                      onClick={handleMint}
                      disabled={loading || !editionInfo.saleActive || editionInfo.currentSupply >= editionInfo.maxSupply}
                    >
                      {loading ? 'Minting...' : 'Mint Edition'}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="sale-inactive-container">
                  <div className="sale-inactive-message">
                    <p>The sale for this edition is currently inactive.</p>
                    <p>You can start the sale to allow minting, or view the edition details below.</p>
                  </div>
                  
                  <div className="sale-management-actions">
                    <button 
                      className="start-sale-button" 
                      onClick={handleStartSale}
                      disabled={managingSale}
                    >
                      {managingSale ? 'Starting Sale...' : 'Start Sale'}
                    </button>
                    <button 
                      className="cancel-button" 
                      onClick={handleClose}
                      disabled={managingSale}
                    >
                      Close
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="error-message">
              <p>Failed to load edition information.</p>
              <button className="cancel-button" onClick={handleClose}>Close</button>
            </div>
          )}

          {debugInfo && (
            <div className="debug-info">
              <h4>Debug Information:</h4>
              <div>Current Wallet: {debugInfo.currentWallet}</div>
              <div>Contract Owner: {debugInfo.contractOwner}</div>
              <div>Profile Address: {debugInfo.profileAddress}</div>
              <div>ArtSales1155: {debugInfo.artSalesAddress}</div>
              <div>Is Owner: {debugInfo.isOwner ? 'YES' : 'NO'}</div>
              {debugInfo.error && <div style={{color: 'red'}}>Error: {debugInfo.error}</div>}
              <button onClick={checkOwnership} className="debug-button">
                Refresh Debug Info
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MintArtEdition; 