import React, { useState, useEffect } from 'react';
import { useBlockchain } from '../../utils/BlockchainContext';
import ethersService from '../../utils/ethers-service';
import abiLoader from '../../utils/abiLoader';
import { ethers } from 'ethers';
import './MintArtEdition.css';
import CrossChainWhitelistForm from './CrossChainWhitelistForm';

interface MintArtEditionProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (txHash: string) => void;
  onError: (error: string) => void;
  artPieceAddress: string | null;
  artSales1155Address: string | null;
}

interface TokenInfo {
  symbol: string;
  name: string;
  decimals: number;
  isERC20: boolean;
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
    saleType: number;
    currentPhase: number;
    basePrice: string;
  } | null>(null);

  // Phase pricing state
  const [phaseInfo, setPhaseInfo] = useState<{
    phases: Array<{ threshold: number; price: string }>;
    nextPhase: { threshold: number; price: string; type: 'quantity' | 'time' } | null;
  } | null>(null);
  
  // Real-time pricing state
  const [realTimePrice, setRealTimePrice] = useState<string | null>(null);
  const [priceLoading, setPriceLoading] = useState<boolean>(false);

  // ERC20 token state
  const [tokenInfo, setTokenInfo] = useState<TokenInfo | null>(null);
  const [tokenBalance, setTokenBalance] = useState<string>('0');
  const [tokenAllowance, setTokenAllowance] = useState<string>('0');
  const [needsApproval, setNeedsApproval] = useState<boolean>(false);
  const [approvingToken, setApprovingToken] = useState<boolean>(false);

      // State for sale management
    const [managingSale, setManagingSale] = useState<boolean>(false);
    const [debugInfo, setDebugInfo] = useState<any>(null);
  
  // Loading edition information
  useEffect(() => {
    if (isOpen && artSales1155Address && artPieceAddress) {
      loadEditionInfo();
    }
  }, [isOpen, artSales1155Address, artPieceAddress]);

  // Update real-time price when mint amount changes (for phased pricing)
  useEffect(() => {
    if (editionInfo?.saleActive && editionInfo?.erc1155Address) {
      updateRealTimePrice();
      checkTokenBalanceAndAllowance();
      // Reload phase info in case supply changes affect phase calculations
      loadPhaseInfo(editionInfo.erc1155Address);
    }
  }, [mintAmount, editionInfo?.erc1155Address, editionInfo?.saleActive, tokenInfo]);

  // Reformat cached price when token info becomes available 
  useEffect(() => {
    if (tokenInfo && editionInfo && !realTimePrice) {
      // If we have token info but the price might be formatted with wrong decimals
      console.log('[MintArtEdition] Reformatting cached price with correct token decimals');
      updateRealTimePrice();
    }
  }, [tokenInfo, editionInfo]);

  // Fetch ERC20 token information
  // Helper function to format prices using correct token decimals
  const formatPrice = (priceWei: bigint, decimals?: number): string => {
    const actualDecimals = decimals ?? tokenInfo?.decimals ?? 18;
    return ethers.formatUnits(priceWei, actualDecimals);
  };

  // Helper functions for unlimited supply handling
  const isUnlimitedSupply = (maxSupply: number): boolean => {
    return maxSupply > 1e15; // Very large number indicates unlimited
  };

  const getRemainingSupply = (maxSupply: number, currentSupply: number): number => {
    return isUnlimitedSupply(maxSupply) ? 999999 : maxSupply - currentSupply;
  };

  const canIncrementMintAmount = (mintAmount: number, maxSupply: number, currentSupply: number): boolean => {
    if (isUnlimitedSupply(maxSupply)) {
      return mintAmount < 999999; // Arbitrary large limit
    }
    return mintAmount < (maxSupply - currentSupply);
  };

  const isSoldOut = (maxSupply: number, currentSupply: number): boolean => {
    if (isUnlimitedSupply(maxSupply)) {
      return false; // Never sold out for unlimited
    }
    return currentSupply >= maxSupply;
  };

  const fetchTokenInfo = async (tokenAddress: string): Promise<TokenInfo> => {
    const defaultEthInfo: TokenInfo = {
      symbol: 'ETH',
      name: 'Ethereum',
      decimals: 18,
      isERC20: false
    };

    if (tokenAddress === ethers.ZeroAddress) {
      setTokenInfo(defaultEthInfo);
      return defaultEthInfo;
    }

    try {
      const provider = ethersService.getProvider();
      if (!provider) throw new Error("No provider available");

      // Standard ERC20 ABI for basic info
      const erc20Abi = [
        'function symbol() view returns (string)',
        'function name() view returns (string)',
        'function decimals() view returns (uint8)',
        'function balanceOf(address) view returns (uint256)',
        'function allowance(address owner, address spender) view returns (uint256)',
        'function approve(address spender, uint256 amount) returns (bool)'
      ];

      const tokenContract = new ethers.Contract(tokenAddress, erc20Abi, provider);
      
      const [symbol, name, decimals] = await Promise.all([
        tokenContract.symbol(),
        tokenContract.name(),
        tokenContract.decimals()
      ]);

      console.log('[MintArtEdition] ERC20 Token Info:', { symbol, name, decimals });

      const tokenInfoData: TokenInfo = {
        symbol,
        name,
        decimals: Number(decimals),
        isERC20: true
      };

      setTokenInfo(tokenInfoData);
      return tokenInfoData;

    } catch (error) {
      console.error('[MintArtEdition] Error fetching token info:', error);
      // Fallback for unknown tokens
      const fallbackInfo: TokenInfo = {
        symbol: 'TOKEN',
        name: 'Unknown Token',
        decimals: 18,
        isERC20: true
      };
      setTokenInfo(fallbackInfo);
      return fallbackInfo;
    }
  };

  // Check token balance and allowance for ERC20
  const checkTokenBalanceAndAllowance = async () => {
    if (!tokenInfo?.isERC20 || !editionInfo || !walletAddress) return;

    try {
      const signer = await ethersService.getSigner();
      if (!signer) return;

      const erc20Abi = [
        'function balanceOf(address) view returns (uint256)',
        'function allowance(address owner, address spender) view returns (uint256)'
      ];

      const tokenContract = new ethers.Contract(editionInfo.paymentCurrency, erc20Abi, signer);
      
      const [balance, allowance] = await Promise.all([
        tokenContract.balanceOf(walletAddress),
        tokenContract.allowance(walletAddress, editionInfo.erc1155Address)
      ]);

      setTokenBalance(ethers.formatUnits(balance, tokenInfo.decimals));
      setTokenAllowance(ethers.formatUnits(allowance, tokenInfo.decimals));

      // Calculate total cost needed
      const priceToUse = realTimePrice || editionInfo.mintPrice;
      const totalCost = parseFloat(priceToUse) * mintAmount;
      const allowanceAmount = parseFloat(ethers.formatUnits(allowance, tokenInfo.decimals));

      console.log('[MintArtEdition] Token allowance calculation:', {
        priceToUse,
        mintAmount,
        totalCost,
        allowanceAmount,
        needsApproval: allowanceAmount < totalCost
      });

      setNeedsApproval(allowanceAmount < totalCost);

      console.log('[MintArtEdition] Token balance check:', {
        balance: ethers.formatUnits(balance, tokenInfo.decimals),
        allowance: ethers.formatUnits(allowance, tokenInfo.decimals),
        totalCostNeeded: totalCost,
        needsApproval: allowanceAmount < totalCost
      });

    } catch (error) {
      console.error('[MintArtEdition] Error checking token balance/allowance:', error);
    }
  };

  const loadEditionInfo = async () => {
    console.log('[MintArtEdition] === LOAD EDITION INFO ===');
    console.log('[MintArtEdition] artSales1155Address:', artSales1155Address);
    console.log('[MintArtEdition] artPieceAddress:', artPieceAddress);
    
    if (!artSales1155Address || !artPieceAddress) {
      console.log('[MintArtEdition] ❌ Missing required addresses, returning early');
      console.log('[MintArtEdition] artSales1155Address missing:', !artSales1155Address);
      console.log('[MintArtEdition] artPieceAddress missing:', !artPieceAddress);
      return;
    }
    
    try {
      console.log('[MintArtEdition] ✅ Starting edition info load...');
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
      console.log('[MintArtEdition] Checking if art piece has editions...');
      const hasEditions = await artSalesContract.hasEditions(artPieceAddress);
      console.log('[MintArtEdition] hasEditions result:', hasEditions);
      if (!hasEditions) {
        throw new Error("No editions found for this art piece");
      }

      // Get the ERC1155 address mapped to this art piece
      console.log('[MintArtEdition] Getting ERC1155 address mapping...');
      const erc1155Address = await artSalesContract.artistPieceToErc1155Map(artPieceAddress);
      console.log('[MintArtEdition] ERC1155 address from mapping:', erc1155Address);
      if (!erc1155Address || erc1155Address === ethers.ZeroAddress) {
        throw new Error("No ERC1155 contract found for this art piece");
      }

      // Check if sale is active
      const saleActive = await artSalesContract.isSaleActive(erc1155Address);
      
      // Get sale info - ArtSales1155.getSaleInfo returns (saleType, currentPrice, currentSupply, maxSupply, isPaused, currentPhase)
      const saleInfo = await artSalesContract.getSaleInfo(erc1155Address);
      const [saleType, mintPrice, currentSupply, maxSupply, isPaused, currentPhase] = saleInfo;
      console.log('[MintArtEdition] Sale info from ArtSales1155:', {saleType, mintPrice: mintPrice.toString(), currentSupply, maxSupply, isPaused, currentPhase});

      // Load ArtEdition1155 ABI to get edition details
      const artEditionAbi = abiLoader.loadABI('ArtEdition1155');
      if (!artEditionAbi) {
        throw new Error("ArtEdition1155 ABI not found");
      }

      const editionContract = new ethers.Contract(erc1155Address, artEditionAbi, signer);
      
      // Get edition name and symbol
      const name = await editionContract.name();
      const symbol = await editionContract.symbol();
      
      // Get royalty percentage and base price from edition contract
      const royaltyPercent = await editionContract.royaltyPercent();
      const basePrice = await editionContract.basePrice();
      console.log('[MintArtEdition] Royalty percent from edition contract:', royaltyPercent.toString());
      console.log('[MintArtEdition] Base price from edition contract:', basePrice.toString());
      
      // Get payment currency (if applicable)
      let paymentCurrency = ethers.ZeroAddress; // Default to ETH
      try {
        const currencyAddress = await editionContract.paymentCurrency();
        if (currencyAddress && currencyAddress !== ethers.ZeroAddress) {
          paymentCurrency = currencyAddress;
        }
      } catch (err) {
        // Payment currency might not be implemented or might be ETH
        console.log("Payment currency not available, defaulting to ETH");
      }

      console.log('[MintArtEdition] Payment currency address:', paymentCurrency);

      // Fetch token info based on payment currency FIRST
      const fetchedTokenInfo = await fetchTokenInfo(paymentCurrency);
      
      // Use the returned token info directly to avoid state timing issues
      const tokenDecimals = fetchedTokenInfo.decimals;
      const tokenSymbol = fetchedTokenInfo.symbol;

      // Format the mint price using the payment token's actual decimals
      const formattedMintPrice = formatPrice(mintPrice, tokenDecimals);
      
      console.log('[MintArtEdition] Initial price formatting debug:', {
        rawMintPrice: mintPrice.toString(),
        formattedMintPrice,
        tokenSymbol,
        tokenDecimals,
        explanation: 'Using token-specific decimals for price formatting'
      });

      const editionData = {
        name,
        symbol,
        mintPrice: formattedMintPrice,
        maxSupply: Number(maxSupply),
        currentSupply: Number(currentSupply),
        royaltyPercent: Number(royaltyPercent) / 100, // Convert from basis points to percentage
        paymentCurrency,
        saleActive,
        erc1155Address,
        saleType: Number(saleType),
        currentPhase: Number(currentPhase),
        basePrice: formatPrice(basePrice, tokenDecimals)
      };
      
      console.log('[MintArtEdition] ✅ Edition info loaded successfully:', editionData);
      setEditionInfo(editionData);

      // Fetch real-time price and phase info after setting edition info
      if (saleActive) {
        await updateRealTimePrice(erc1155Address);
        await loadPhaseInfo(erc1155Address);
      }

    } catch (err: any) {
      console.error("Error loading edition info:", err);
      onError(`Failed to load edition information: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const updateRealTimePrice = async (erc1155Address?: string) => {
    if (!erc1155Address && !editionInfo?.erc1155Address) return;
    
    const contractAddress = erc1155Address || editionInfo!.erc1155Address;
    
    try {
      setPriceLoading(true);
      
      const provider = ethersService.getProvider();
      if (!provider) {
        throw new Error("No provider available");
      }

      const artEditionAbi = abiLoader.loadABI('ArtEdition1155');
      if (!artEditionAbi) {
        throw new Error("ArtEdition1155 ABI not found");
      }

      const editionContract = new ethers.Contract(contractAddress, artEditionAbi, provider);
      
      // Get real-time sale info
      const realTimeSaleInfo = await editionContract.getSaleInfo();
      const [, realTimePriceWei, , , , ] = realTimeSaleInfo;
      
      const tokenSymbol = tokenInfo?.symbol || 'ETH';
      
      // Format price using the payment token's actual decimals
      const realTimePriceFormatted = formatPrice(realTimePriceWei);
      
      console.log('[MintArtEdition] Price conversion debug:', {
        rawPriceWei: realTimePriceWei.toString(),
        formattedPrice: realTimePriceFormatted,
        tokenSymbol,
        tokenDecimals: tokenInfo?.decimals,
        explanation: 'Using token-specific decimals for price formatting'
      });
      
      console.log('[MintArtEdition] Updated real-time price:', realTimePriceFormatted, tokenSymbol);
      setRealTimePrice(realTimePriceFormatted);

    } catch (err: any) {
      console.error("Error fetching real-time price:", err);
      // Don't show error to user, just fallback to cached price
      setRealTimePrice(null);
    } finally {
      setPriceLoading(false);
    }
  };

  // Load phase information for phased pricing
  const loadPhaseInfo = async (erc1155Address: string) => {
    if (!editionInfo) return;

    try {
      const provider = ethersService.getProvider();
      if (!provider) throw new Error("No provider available");

      const artEditionAbi = abiLoader.loadABI('ArtEdition1155');
      if (!artEditionAbi) throw new Error("ArtEdition1155 ABI not found");

      const editionContract = new ethers.Contract(erc1155Address, artEditionAbi, provider);
      
      // Get phases from the contract
      const contractPhases = await editionContract.getPhases();
      console.log('[MintArtEdition] Raw phases from contract:', contractPhases);

      // Format phases using token-specific decimals
      const formattedPhases = contractPhases.map((phase: { threshold: bigint; price: bigint }) => ({
        threshold: Number(phase.threshold),
        price: formatPrice(phase.price)
      }));

      // Calculate next phase based on sale type
      let nextPhase = null;
      const currentSupply = editionInfo.currentSupply;
      const saleType = editionInfo.saleType;

      if (formattedPhases.length > 0) {
        if (saleType === 2) { // SALE_TYPE_QUANTITY_PHASES
          // Find next quantity threshold
          const nextQuantityPhase = formattedPhases.find((phase: { threshold: number; price: string }) => phase.threshold > currentSupply);
          if (nextQuantityPhase) {
            nextPhase = {
              threshold: nextQuantityPhase.threshold,
              price: nextQuantityPhase.price,
              type: 'quantity' as const
            };
          }
        } else if (saleType === 3) { // SALE_TYPE_TIME_PHASES
          // Find next time threshold
          const currentTime = Math.floor(Date.now() / 1000);
          const nextTimePhase = formattedPhases.find((phase: { threshold: number; price: string }) => phase.threshold > currentTime);
          if (nextTimePhase) {
            nextPhase = {
              threshold: nextTimePhase.threshold,
              price: nextTimePhase.price,
              type: 'time' as const
            };
          }
        }
      }

      const phaseData = {
        phases: formattedPhases,
        nextPhase
      };

      console.log('[MintArtEdition] Processed phase info:', phaseData);
      setPhaseInfo(phaseData);

    } catch (error) {
      console.error('[MintArtEdition] Error loading phase info:', error);
      setPhaseInfo(null);
    }
  };

  // Handle ERC20 token approval
  const handleApproval = async () => {
    if (!editionInfo || !tokenInfo?.isERC20) return;

    try {
      setApprovingToken(true);

      const signer = await ethersService.getSigner();
      if (!signer) throw new Error("Wallet not connected");

      const erc20Abi = [
        'function approve(address spender, uint256 amount) returns (bool)'
      ];

      const tokenContract = new ethers.Contract(editionInfo.paymentCurrency, erc20Abi, signer);
      
      // Calculate total cost needed
      const priceToUse = realTimePrice || editionInfo.mintPrice;
      const totalCost = parseFloat(priceToUse) * mintAmount;
      const totalCostWei = ethers.parseUnits(totalCost.toString(), tokenInfo.decimals);

      console.log('[MintArtEdition] Approving tokens:', {
        amount: totalCost,
        amountWei: totalCostWei.toString(),
        spender: editionInfo.erc1155Address,
        token: editionInfo.paymentCurrency
      });

      const tx = await tokenContract.approve(editionInfo.erc1155Address, totalCostWei);
      const receipt = await tx.wait();

      console.log("Token approval successful:", receipt);

      // Refresh allowance
      await checkTokenBalanceAndAllowance();

    } catch (err: any) {
      console.error("Error approving tokens:", err);
      let errorMessage = "Failed to approve tokens";
      
      if (err.message?.includes("insufficient funds")) {
        errorMessage = "Insufficient funds for approval";
      } else if (err.reason) {
        errorMessage = err.reason;
      }
      
      onError(errorMessage);
    } finally {
      setApprovingToken(false);
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
      
      // Get real-time sale info to account for phased pricing
      console.log('[MintArtEdition] Getting real-time sale info for accurate pricing...');
      const realTimeSaleInfo = await editionContract.getSaleInfo();
      const [saleType, realTimePrice, currentSupply, maxSupply, isPaused, currentPhase] = realTimeSaleInfo;
      // Get proper token decimals for logging  
      const logTokenDecimals = tokenInfo?.decimals || 18;
      const logTokenSymbol = tokenInfo?.symbol || 'ETH';
      
      console.log('[MintArtEdition] Real-time price (raw):', realTimePrice.toString());
      console.log('[MintArtEdition] Cached price:', editionInfo.mintPrice, logTokenSymbol);
      console.log('[MintArtEdition] Real-time price (formatted):', ethers.formatUnits(realTimePrice, logTokenDecimals), logTokenSymbol);
      
      // Enhanced debugging of contract state
      console.log('[MintArtEdition] === DETAILED CONTRACT STATE ===');
      console.log('[MintArtEdition] Sale type:', saleType.toString());
      console.log('[MintArtEdition] Current supply:', currentSupply.toString());
      console.log('[MintArtEdition] Max supply:', maxSupply.toString());
      console.log('[MintArtEdition] Is paused:', isPaused);
      console.log('[MintArtEdition] Current phase:', currentPhase.toString());
      console.log('[MintArtEdition] Mint amount requested:', mintAmount);
      console.log('[MintArtEdition] Supply after mint would be:', Number(currentSupply) + mintAmount);
      
      // Check payment currency details
      const paymentCurrency = await editionContract.paymentCurrency();
      const basePrice = await editionContract.basePrice();
      const proceedsAddress = await editionContract.proceedsAddress();
      console.log('[MintArtEdition] Payment currency address:', paymentCurrency);
      console.log('[MintArtEdition] Base price (wei):', basePrice.toString());
      console.log('[MintArtEdition] Payment currency is zero address (ETH):', paymentCurrency === ethers.ZeroAddress);
      console.log('[MintArtEdition] Proceeds address:', proceedsAddress);
      console.log('[MintArtEdition] Proceeds address is valid:', proceedsAddress !== ethers.ZeroAddress);
      
      // Validate mint conditions before attempting
      if (isPaused) {
        throw new Error("Sale is currently paused");
      }
      
      // Check if the mint would exceed max supply (only for limited editions)
      if (!isUnlimitedSupply(Number(maxSupply)) && Number(currentSupply) + mintAmount > Number(maxSupply)) {
        throw new Error(`Mint amount would exceed max supply. Current: ${currentSupply}, Max: ${maxSupply}, Requested: ${mintAmount}`);
      }
      
      if (realTimePrice === 0n) {
        throw new Error("Edition price is zero - edition may not be properly initialized");
      }
      
      if (proceedsAddress === ethers.ZeroAddress) {
        throw new Error("Proceeds address is not set - edition may not be properly initialized");
      }
      
      // Calculate total cost using real-time price
      const totalCost = realTimePrice * BigInt(mintAmount);
      const tokenSymbol = tokenInfo?.symbol || 'ETH';
      const tokenDecimals = tokenInfo?.decimals || 18;
      const isERC20Payment = tokenInfo?.isERC20 || false;
      
      console.log('[MintArtEdition] Total cost for', mintAmount, 'tokens:', ethers.formatUnits(totalCost, tokenDecimals), tokenSymbol);
      
      // Check appropriate balance based on payment type
      let hasInsufficientBalance = false;
      let balanceErrorMessage = '';
      
      if (isERC20Payment) {
        // Check ERC20 token balance
        const currentBalance = parseFloat(tokenBalance);
        const requiredAmount = parseFloat(ethers.formatUnits(totalCost, tokenDecimals));
        
        console.log('[MintArtEdition] ERC20 balance check:', {
          currentBalance,
          requiredAmount,
          tokenSymbol,
          hasEnough: currentBalance >= requiredAmount
        });
        
        if (currentBalance < requiredAmount) {
          hasInsufficientBalance = true;
          balanceErrorMessage = `Insufficient ${tokenSymbol} balance. Need ${requiredAmount.toFixed(6)} ${tokenSymbol}, have ${currentBalance.toFixed(6)} ${tokenSymbol}`;
        }
      } else {
        // Check ETH balance
        const walletBalance = await signer.provider.getBalance(await signer.getAddress());
        console.log('[MintArtEdition] ETH balance check:', {
          walletBalance: ethers.formatUnits(walletBalance, tokenDecimals),
          totalCost: ethers.formatUnits(totalCost, tokenDecimals),
          hasEnough: walletBalance >= totalCost
        });
        
        if (walletBalance < totalCost) {
          hasInsufficientBalance = true;
          balanceErrorMessage = `Insufficient ${tokenSymbol} balance. Need ${ethers.formatUnits(totalCost, tokenDecimals)} ${tokenSymbol}, have ${ethers.formatUnits(walletBalance, tokenDecimals)} ${tokenSymbol}`;
        }
      }
      
      if (hasInsufficientBalance) {
        throw new Error(balanceErrorMessage);
      }
      
      // CONTRACT VERIFICATION: Check if the contract actually exists and has expected functions
      console.log('[MintArtEdition] === CONTRACT VERIFICATION ===');
      try {
        // Check if contract exists by checking code
        const contractCode = await signer.provider.getCode(editionInfo.erc1155Address);
        console.log('[MintArtEdition] Contract code exists:', contractCode !== '0x');
        console.log('[MintArtEdition] Contract code length:', contractCode.length);
        
        if (contractCode === '0x') {
          throw new Error('Contract does not exist at this address');
        }
        
        // Test view functions to verify ABI
        const initialized = await editionContract.initialized();
        const owner = await editionContract.owner();
        const artPiece = await editionContract.artPiece();
        
        console.log('[MintArtEdition] Contract verification checks:');
        console.log('[MintArtEdition] - Initialized:', initialized);
        console.log('[MintArtEdition] - Owner:', owner);
        console.log('[MintArtEdition] - ArtPiece:', artPiece);
        
        // Check if we can estimate gas for a simpler view function
        console.log('[MintArtEdition] Testing gas estimation for balanceOf...');
        const balanceOfGas = await editionContract.balanceOf.estimateGas(await signer.getAddress(), 1);
        console.log('[MintArtEdition] balanceOf gas estimate:', balanceOfGas.toString());
        
      } catch (verificationError) {
        console.error('[MintArtEdition] Contract verification failed:', verificationError);
        throw new Error(`Contract verification failed: ${verificationError instanceof Error ? verificationError.message : String(verificationError)}`);
      }
      
      // FUNCTION SELECTOR VERIFICATION
      console.log('[MintArtEdition] === FUNCTION SELECTOR VERIFICATION ===');
      try {
        // Check if the mint function exists with correct selector
        const mintFunction = editionContract.interface.getFunction('mint');
        if (mintFunction) {
          console.log('[MintArtEdition] Mint function selector:', mintFunction.selector);
          console.log('[MintArtEdition] Mint function signature:', mintFunction.format());
        } else {
          console.log('[MintArtEdition] Mint function not found in ABI');
        }
        
        // Also check what functions are available
        const allFunctions = editionContract.interface.fragments.filter(f => f.type === 'function');
        console.log('[MintArtEdition] Available functions in ABI:', allFunctions.map(f => f.format()));
        
        // Try to see if there's a different mint function
        const mintFunctions = allFunctions.filter(f => f.format().includes('mint'));
        console.log('[MintArtEdition] Mint-related functions:', mintFunctions.map(f => f.format()));
        
      } catch (selectorError) {
        console.error('[MintArtEdition] Function selector verification failed:', selectorError);
      }
      
      // LOW-LEVEL CONTRACT CALL: Try calling with raw transaction data
      console.log('[MintArtEdition] === LOW-LEVEL CONTRACT CALL ===');
      try {
        // Build the transaction data manually based on payment type
        let callData;
        let expectedCall;
        if (paymentCurrency === ethers.ZeroAddress) {
          console.log('[MintArtEdition] Building ETH mint call data...');
          const mintSelector = '0xa0712d68'; // mint(uint256) selector
          const encodedAmount = ethers.AbiCoder.defaultAbiCoder().encode(['uint256'], [mintAmount]);
          callData = mintSelector + encodedAmount.slice(2);
          expectedCall = await editionContract.mint.populateTransaction(mintAmount);
        } else {
          console.log('[MintArtEdition] Building ERC20 mint call data...');
          // Get the correct selector from the interface
          const mintERC20Function = editionContract.interface.getFunction('mintERC20');
          if (!mintERC20Function) {
            throw new Error('mintERC20 function not found in contract interface');
          }
          const mintERC20Selector = mintERC20Function.selector;
          const encodedAmount = ethers.AbiCoder.defaultAbiCoder().encode(['uint256'], [mintAmount]);
          callData = mintERC20Selector + encodedAmount.slice(2);
          expectedCall = await editionContract.mintERC20.populateTransaction(mintAmount);
        }
        
        console.log('[MintArtEdition] Manual call data:', callData);
        console.log('[MintArtEdition] Expected call data from ethers:', expectedCall);
        
        // Try a low-level call to get better error info
        const result = await signer.provider.call({
          to: editionInfo.erc1155Address,
          data: callData,
          value: paymentCurrency === ethers.ZeroAddress ? ethers.toQuantity(totalCost) : undefined,
          from: await signer.getAddress()
        });
        
        console.log('[MintArtEdition] Low-level call result:', result);
        
              } catch (lowLevelError) {
          console.error('[MintArtEdition] Low-level call failed:', lowLevelError);
          
          // The error might give us more details
          if (lowLevelError instanceof Error && lowLevelError.message.includes('revert')) {
            console.log('[MintArtEdition] Contract reverted, checking for specific revert reason...');
          }
        }
        
        // PROCEEDS ADDRESS VERIFICATION: Check if the proceeds address can receive ETH
        console.log('[MintArtEdition] === PROCEEDS ADDRESS VERIFICATION ===');
        try {
          // Check if proceeds address is a contract
          const proceedsCode = await signer.provider.getCode(proceedsAddress);
          const isContract = proceedsCode !== '0x';
          console.log('[MintArtEdition] Proceeds address is contract:', isContract);
          console.log('[MintArtEdition] Proceeds code length:', proceedsCode.length);
          
          // Check proceeds address balance
          const proceedsBalance = await signer.provider.getBalance(proceedsAddress);
          console.log('[MintArtEdition] Proceeds address balance:', ethers.formatUnits(proceedsBalance, tokenDecimals), tokenSymbol);
          
          if (isContract) {
            console.log('[MintArtEdition] ⚠️ Proceeds address is a contract - checking if it can receive ETH...');
            
            // Try to send a tiny amount of ETH to test if it can receive
            try {
              await signer.estimateGas({
                to: proceedsAddress,
                value: 1n, // 1 wei
                data: '0x'
              });
              console.log('[MintArtEdition] ✅ Proceeds address can receive ETH');
            } catch (receiveError) {
              console.error('[MintArtEdition] ❌ Proceeds address CANNOT receive ETH:', receiveError);
              throw new Error(`Proceeds address ${proceedsAddress} cannot receive ETH. This is likely the cause of the mint failure.`);
            }
          } else {
            console.log('[MintArtEdition] ✅ Proceeds address is EOA, should be able to receive ETH');
          }
          
        } catch (proceedsError) {
          console.error('[MintArtEdition] Proceeds address verification failed:', proceedsError);
          if (proceedsError instanceof Error && proceedsError.message.includes('cannot receive ETH')) {
            throw proceedsError; // Re-throw the specific error
          }
        }
        
        // ALTERNATIVE MINT ATTEMPT: Try with different gas settings
        console.log('[MintArtEdition] === ALTERNATIVE MINT ATTEMPT ===');
        try {
          console.log('[MintArtEdition] Trying mint with manual gas limit...');
          
          // Try with a higher gas limit using the correct function
          let gasEstimateAlternative;
          if (paymentCurrency === ethers.ZeroAddress) {
            gasEstimateAlternative = await editionContract.mint.estimateGas(mintAmount, {
              value: totalCost,
              gasLimit: 500000 // Manual gas limit
            });
          } else {
            gasEstimateAlternative = await editionContract.mintERC20.estimateGas(mintAmount, {
              gasLimit: 500000 // Manual gas limit
            });
          }
          console.log('[MintArtEdition] Alternative gas estimate with manual limit:', gasEstimateAlternative.toString());
          
        } catch (altError) {
          console.error('[MintArtEdition] Alternative gas estimation also failed:', altError);
        }
      
      // MANUAL GAS ESTIMATION: Try to estimate gas before the actual transaction
      console.log('[MintArtEdition] === MANUAL GAS ESTIMATION ===');
      try {
        let gasEstimate;
        if (paymentCurrency === ethers.ZeroAddress) {
          console.log('[MintArtEdition] Estimating gas for ETH mint...');
          gasEstimate = await editionContract.mint.estimateGas(mintAmount, {
            value: totalCost,
            from: await signer.getAddress()
          });
        } else {
          console.log('[MintArtEdition] Estimating gas for ERC20 mint...');
          gasEstimate = await editionContract.mintERC20.estimateGas(mintAmount, {
            from: await signer.getAddress()
          });
        }
        console.log('[MintArtEdition] Gas estimate for mint:', gasEstimate.toString());
      } catch (gasError) {
        console.error('[MintArtEdition] Gas estimation failed:', gasError);
        
        // Try to get more specific error by calling the contract read-only
        try {
          console.log('[MintArtEdition] Trying static call to see detailed error...');
          if (paymentCurrency === ethers.ZeroAddress) {
            await editionContract.mint.staticCall(mintAmount, {
              value: totalCost,
              from: await signer.getAddress()
            });
          } else {
            await editionContract.mintERC20.staticCall(mintAmount, {
              from: await signer.getAddress()
            });
          }
        } catch (staticError) {
          console.error('[MintArtEdition] Static call failed with detailed error:', staticError);
          throw new Error(`Transaction would fail: ${staticError instanceof Error ? staticError.message : String(staticError)}`);
        }
        
        throw new Error(`Gas estimation failed: ${gasError instanceof Error ? gasError.message : String(gasError)}`);
      }
      
      // Check if payment is in ETH or ERC20
      let tx;
      if (paymentCurrency === ethers.ZeroAddress) {
        console.log('[MintArtEdition] Using ETH payment...');
        // Mint with ETH - contract mints to msg.sender automatically
        tx = await editionContract.mint(mintAmount, {
          value: totalCost
        });
      } else {
        console.log('[MintArtEdition] Using ERC20 payment...');
        // For ERC20 payments - use mintERC20 function
        tx = await editionContract.mintERC20(mintAmount);
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
      console.log('[MintArtEdition] === STARTING SALE ===');
      console.log('[MintArtEdition] Edition address:', editionInfo.erc1155Address);
      
      // Check current network BEFORE any wallet operations
      const provider = ethersService.getProvider();
      if (provider) {
        const network = await provider.getNetwork();
        const currentChainId = Number(network.chainId);
        console.log('[MintArtEdition] Pre-transaction network:', currentChainId, network.name);
        
        // Compare with debug network if available
        if (debugInfo?.currentNetwork?.chainId && debugInfo.currentNetwork.chainId !== currentChainId) {
          console.warn('[MintArtEdition] ⚠️ NETWORK MISMATCH DETECTED!');
          console.warn('[MintArtEdition] Debug showed network:', debugInfo.currentNetwork.chainId, debugInfo.currentNetwork.name);
          console.warn('[MintArtEdition] But transaction network is:', currentChainId, network.name);
          
          // Stop here to prevent transaction on wrong network
          throw new Error(`Network mismatch: Debug analyzed contracts on ${debugInfo.currentNetwork.name} (${debugInfo.currentNetwork.chainId}) but transaction would go to ${network.name} (${currentChainId})`);
        }
      }
      
      setManagingSale(true);
      
      const signer = await ethersService.getSigner();
      if (!signer) {
        throw new Error("Wallet not connected");
      }
      
      // Double-check network after getting signer
      const signerNetwork = await signer.provider.getNetwork();
      const signerChainId = Number(signerNetwork.chainId);
      console.log('[MintArtEdition] Signer network:', signerChainId, signerNetwork.name);

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
      setRealTimePrice(null);
      setManagingSale(false);
      onClose();
    }
  };

  // Debug function to check ownership
  const checkOwnership = async () => {
    try {
      console.log('[MintArtEdition] Checking ownership...');
      
      // Check if wallet is connected
      if (!isConnected || !walletAddress) {
        setDebugInfo({ error: 'Wallet not connected' });
        return;
      }

      const provider = ethersService.getProvider();
      if (!provider) {
        setDebugInfo({ error: 'No provider available' });
        return;
      }

      console.log('[MintArtEdition] Current wallet address:', walletAddress);

      // Get current network info
      const network = await provider.getNetwork();
      const currentChainId = Number(network.chainId);
      const currentNetworkName = network.name;
      
      console.log('[MintArtEdition] === DEBUG CONTEXT ===');
      console.log('[MintArtEdition] editionInfo:', editionInfo);
      console.log('[MintArtEdition] editionInfo.erc1155Address:', editionInfo?.erc1155Address);
      console.log('[MintArtEdition] artPieceAddress:', artPieceAddress);
      console.log('[MintArtEdition] artSales1155Address:', artSales1155Address);
      
      console.log('[MintArtEdition] === Current Network ===');
      console.log('[MintArtEdition] Chain ID:', currentChainId);
      console.log('[MintArtEdition] Network name:', currentNetworkName);
      console.log('[MintArtEdition] Network object:', network);

      if (!artSales1155Address) {
        console.log('[MintArtEdition] No ArtSales1155 address available');
        setDebugInfo({ 
          error: 'No ArtSales1155 address available',
          currentNetwork: {
            chainId: currentChainId,
            name: currentNetworkName
          }
        });
        return;
      }

      // Load all necessary ABIs
      const [ArtSales1155ABI, ProfileABI, ArtPieceABI, ArtEdition1155ABI] = await Promise.all([
        import('../../assets/abis/ArtSales1155.json').then(m => m.default),
        import('../../assets/abis/Profile.json').then(m => m.default),
        import('../../assets/abis/ArtPiece.json').then(m => m.default),
        import('../../assets/abis/ArtEdition1155.json').then(m => m.default)
      ]);

      // ArtSales1155 contract details
      const salesContract = new ethers.Contract(artSales1155Address, ArtSales1155ABI, provider);
      const salesOwner = await salesContract.owner();
      const profileAddress = await salesContract.profileAddress();
      
      console.log('[MintArtEdition] === ArtSales1155 Details ===');
      console.log('[MintArtEdition] ArtSales1155 address:', artSales1155Address);
      console.log('[MintArtEdition] ArtSales1155 owner:', salesOwner);
      console.log('[MintArtEdition] ArtSales1155 profile address:', profileAddress);

      // Profile contract details
      let profileOwner = '';
      let profileIsArtist = false;
      let profileArtSales1155 = '';
      if (profileAddress && profileAddress !== ethers.ZeroAddress) {
        try {
          const profileContract = new ethers.Contract(profileAddress, ProfileABI, provider);
          profileOwner = await profileContract.owner();
          profileIsArtist = await profileContract.isArtist();
          profileArtSales1155 = await profileContract.artSales1155();
          
          console.log('[MintArtEdition] === Profile Details ===');
          console.log('[MintArtEdition] Profile address:', profileAddress);
          console.log('[MintArtEdition] Profile owner:', profileOwner);
          console.log('[MintArtEdition] Profile isArtist:', profileIsArtist);
          console.log('[MintArtEdition] Profile artSales1155:', profileArtSales1155);
        } catch (error) {
          console.error('[MintArtEdition] Error reading profile:', error);
        }
      }

      // Art piece details
      let artPieceArtist = '';
      let artPieceOwner = '';
      let artPieceTitle = '';
      if (artPieceAddress) {
        try {
          const artPieceContract = new ethers.Contract(artPieceAddress, ArtPieceABI, provider);
          artPieceArtist = await artPieceContract.getArtist();
          artPieceOwner = await artPieceContract.getOwner();
          artPieceTitle = await artPieceContract.getTitle();
          
          console.log('[MintArtEdition] === Art Piece Details ===');
          console.log('[MintArtEdition] Art piece address:', artPieceAddress);
          console.log('[MintArtEdition] Art piece title:', artPieceTitle);
          console.log('[MintArtEdition] Art piece artist:', artPieceArtist);
          console.log('[MintArtEdition] Art piece owner:', artPieceOwner);
        } catch (error) {
          console.error('[MintArtEdition] Error reading art piece:', error);
        }
      }

      // Edition details
      let editionOwner = '';
      let editionArtSales1155 = '';
      let editionArtPiece = '';
      let editionSaleInfo = null;
      if (editionInfo?.erc1155Address) {
        try {
          const editionContract = new ethers.Contract(editionInfo.erc1155Address, ArtEdition1155ABI, provider);
          editionOwner = await editionContract.owner();
          editionArtSales1155 = await editionContract.artSales1155();
          editionArtPiece = await editionContract.getLinkedArtPiece();
          editionSaleInfo = await editionContract.getSaleInfo();
          
          console.log('[MintArtEdition] === Edition Details ===');
          console.log('[MintArtEdition] Edition address:', editionInfo.erc1155Address);
          console.log('[MintArtEdition] Edition owner:', editionOwner);
          console.log('[MintArtEdition] Edition artSales1155:', editionArtSales1155);
          console.log('[MintArtEdition] Edition linked art piece:', editionArtPiece);
          console.log('[MintArtEdition] Edition sale info:', editionSaleInfo);
          
          // CRITICAL DEBUG: Compare owners
          console.log('[MintArtEdition] 🔍 OWNERSHIP COMPARISON:');
          console.log('[MintArtEdition] Your wallet:', walletAddress);
          console.log('[MintArtEdition] ArtSales1155 owner:', salesOwner);  
          console.log('[MintArtEdition] ArtEdition1155 owner:', editionOwner);
          console.log('[MintArtEdition] ArtSales1155 === Edition owner?', salesOwner.toLowerCase() === editionOwner.toLowerCase());
          console.log('[MintArtEdition] Your wallet === Edition owner?', walletAddress.toLowerCase() === editionOwner.toLowerCase());
        } catch (error) {
          console.error('[MintArtEdition] Error reading edition:', error);
        }
      }

      // Ownership checks (with null safety)
      const walletIsProfileOwner = profileOwner && walletAddress.toLowerCase() === profileOwner.toLowerCase();
      const walletIsSalesOwner = salesOwner && walletAddress.toLowerCase() === salesOwner.toLowerCase();
      const walletIsArtist = artPieceArtist && walletAddress.toLowerCase() === artPieceArtist.toLowerCase();
      const walletIsArtOwner = artPieceOwner && walletAddress.toLowerCase() === artPieceOwner.toLowerCase();
      const walletIsEditionOwner = editionOwner && walletAddress.toLowerCase() === editionOwner.toLowerCase();

      console.log('[MintArtEdition] === Ownership Analysis ===');
      console.log('[MintArtEdition] Wallet is Profile owner:', walletIsProfileOwner);
      console.log('[MintArtEdition] Wallet is ArtSales1155 owner:', walletIsSalesOwner);
      console.log('[MintArtEdition] Wallet is Art piece artist:', walletIsArtist);
      console.log('[MintArtEdition] Wallet is Art piece owner:', walletIsArtOwner);
      console.log('[MintArtEdition] Wallet is Edition owner:', walletIsEditionOwner);

      // Contract relationship checks
      const profileLinksToSales = profileArtSales1155 && artSales1155Address && 
        profileArtSales1155.toLowerCase() === artSales1155Address.toLowerCase();
      const salesLinksToProfile = profileAddress && salesOwner && true; // Always true if both exist
      const editionLinksToArtPiece = editionArtPiece && artPieceAddress && 
        editionArtPiece.toLowerCase() === artPieceAddress.toLowerCase();

      console.log('[MintArtEdition] === Contract Relationships ===');
      console.log('[MintArtEdition] Profile links to correct ArtSales1155:', profileLinksToSales);
      console.log('[MintArtEdition] ArtSales1155 links to correct Profile:', salesLinksToProfile);
      console.log('[MintArtEdition] Edition links to correct Art piece:', editionLinksToArtPiece);

      setDebugInfo({
        currentWallet: walletAddress,
        
        // Network info
        currentNetwork: {
          chainId: currentChainId,
          name: currentNetworkName,
          isArbitrumSepolia: currentChainId === 421614
        },
        
        // ArtSales1155 info
        artSales1155Address,
        salesOwner,
        salesProfileAddress: profileAddress,
        
        // Profile info
        profileAddress,
        profileOwner,
        profileIsArtist,
        profileArtSales1155,
        
        // Art piece info
        artPieceAddress,
        artPieceTitle,
        artPieceArtist,
        artPieceOwner,
        
        // Edition info
        editionAddress: editionInfo?.erc1155Address || '',
        editionOwner,
        editionArtSales1155,
        editionArtPiece,
        editionSaleInfo,
        
        // Ownership checks
        walletIsProfileOwner,
        walletIsSalesOwner,
        walletIsArtist,
        walletIsArtOwner,
        walletIsEditionOwner,
        
        // Relationship checks
        profileLinksToSales,
        salesLinksToProfile,
        editionLinksToArtPiece,
        
        // Overall assessment
        canStartSale: walletIsSalesOwner || walletIsArtist,
        whyCantStartSale: !walletIsSalesOwner && !walletIsArtist ? 
          'Wallet is neither ArtSales1155 owner nor original artist' : ''
      });

    } catch (error) {
      console.error('[MintArtEdition] Error checking ownership:', error);
      setDebugInfo({ error: error instanceof Error ? error.message : String(error) });
    }
  };

     // Check ownership when modal opens or wallet connection changes
   useEffect(() => {
     if (isOpen && isConnected && artSales1155Address) {
       checkOwnership();
     }
   }, [isOpen, isConnected, walletAddress, artSales1155Address, editionInfo]);

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
                  <span className="value">
                    {priceLoading ? (
                      "Loading..."
                    ) : (
                      `${parseFloat(realTimePrice || editionInfo.mintPrice).toFixed(6)} ${tokenInfo?.symbol || 'ETH'}`
                    )}
                  </span>
                </div>
                {tokenInfo?.isERC20 && (
                  <div className="info-row">
                    <span className="label">Payment Token:</span>
                    <span className="value">{tokenInfo.name} ({tokenInfo.symbol})</span>
                  </div>
                )}
                {tokenInfo?.isERC20 && (
                  <div className="info-row">
                    <span className="label">Your Balance:</span>
                    <span className="value">{parseFloat(tokenBalance).toFixed(6)} {tokenInfo.symbol}</span>
                  </div>
                )}
                <div className="info-row">
                  <span className="label">Supply:</span>
                  <span className="value">
                    {editionInfo.currentSupply} / {editionInfo.maxSupply > 1e15 ? 'Unlimited' : editionInfo.maxSupply.toLocaleString()}
                  </span>
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
                {editionInfo.saleType === 2 && phaseInfo?.phases && phaseInfo.phases.length > 0 && (
                  <div className="info-row">
                    <span className="label">Pricing Phases:</span>
                    <div className="value" style={{fontSize: '0.9em'}}>
                      <div>Base: {parseFloat(editionInfo.basePrice).toFixed(6)} {tokenInfo?.symbol || 'ETH'}</div>
                      {phaseInfo.phases.map((phase, index) => (
                        <div key={index} style={{color: editionInfo.currentSupply >= phase.threshold ? 'green' : 'var(--text-secondary)'}}>
                          {editionInfo.currentSupply >= phase.threshold ? '✅' : '⏳'} At {phase.threshold}: {parseFloat(phase.price).toFixed(6)} {tokenInfo?.symbol || 'ETH'}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {editionInfo.saleType === 3 && phaseInfo?.phases && phaseInfo.phases.length > 0 && (
                  <div className="info-row">
                    <span className="label">Time-based Phases:</span>
                    <div className="value" style={{fontSize: '0.9em'}}>
                      <div>Base: {parseFloat(editionInfo.basePrice).toFixed(6)} {tokenInfo?.symbol || 'ETH'}</div>
                      {phaseInfo.phases.map((phase, index) => {
                        const phaseTime = new Date(phase.threshold * 1000);
                        const isPast = Date.now() > phase.threshold * 1000;
                        return (
                          <div key={index} style={{color: isPast ? 'green' : 'var(--text-secondary)'}}>
                            {isPast ? '✅' : '⏳'} {phaseTime.toLocaleString()}: {parseFloat(phase.price).toFixed(6)} {tokenInfo?.symbol || 'ETH'}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
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
                        max={getRemainingSupply(editionInfo.maxSupply, editionInfo.currentSupply)}
                        value={mintAmount}
                        onChange={(e) => setMintAmount(Math.max(1, parseInt(e.target.value) || 1))}
                        className="amount-input"
                        disabled={loading}
                      />
                      <button 
                        className="amount-button"
                        onClick={() => setMintAmount(Math.min(getRemainingSupply(editionInfo.maxSupply, editionInfo.currentSupply), mintAmount + 1))}
                        disabled={loading || !canIncrementMintAmount(mintAmount, editionInfo.maxSupply, editionInfo.currentSupply)}
                      >
                        +
                      </button>
                    </div>
                  </div>

                  <div className="total-cost">
                    {priceLoading ? (
                      <strong>Calculating real-time price...</strong>
                    ) : (
                      <strong>Total Cost: {(() => {
                        const priceToUse = realTimePrice || editionInfo.mintPrice;
                        const totalCost = parseFloat(priceToUse) * mintAmount;
                        return totalCost.toFixed(6);
                      })()} {tokenInfo?.symbol || 'ETH'}</strong>
                    )}
                    {realTimePrice && realTimePrice !== editionInfo.mintPrice && (
                      <div style={{fontSize: '0.8em', color: 'var(--text-secondary)', marginTop: '4px'}}>
                        Real-time price: {parseFloat(realTimePrice).toFixed(6)} {tokenInfo?.symbol || 'ETH'} per token
                      </div>
                    )}
                                    {tokenInfo?.isERC20 && needsApproval && (
                  <div style={{fontSize: '0.8em', color: 'orange', marginTop: '4px'}}>
                    ⚠️ Token approval required before minting
                  </div>
                )}
                {phaseInfo?.nextPhase && (
                  <div style={{fontSize: '0.8em', color: 'var(--text-secondary)', marginTop: '4px'}}>
                    📈 Next price: {parseFloat(phaseInfo.nextPhase.price).toFixed(6)} {tokenInfo?.symbol || 'ETH'} 
                    {phaseInfo.nextPhase.type === 'quantity' 
                      ? ` at ${phaseInfo.nextPhase.threshold} sold`
                      : ` at ${new Date(phaseInfo.nextPhase.threshold * 1000).toLocaleString()}`
                    }
                  </div>
                )}
                  </div>

                  <div className="modal-actions">
                    <button 
                      className="cancel-button" 
                      onClick={handleClose}
                      disabled={loading || approvingToken}
                    >
                      Cancel
                    </button>
                    
                    {tokenInfo?.isERC20 && needsApproval ? (
                      <>
                        <button 
                          className="approve-button" 
                          onClick={handleApproval}
                          disabled={loading || approvingToken || !editionInfo.saleActive}
                          style={{backgroundColor: 'orange', color: 'white'}}
                        >
                          {approvingToken ? 'Approving...' : `Approve ${tokenInfo.symbol}`}
                        </button>
                        <button 
                          className="mint-button" 
                          onClick={handleMint}
                          disabled={true}
                          style={{opacity: 0.5}}
                        >
                          Mint Edition (Approval Required)
                        </button>
                      </>
                    ) : (
                      <button 
                        className="mint-button" 
                        onClick={handleMint}
                        disabled={loading || approvingToken || !editionInfo.saleActive || isSoldOut(editionInfo.maxSupply, editionInfo.currentSupply)}
                      >
                        {loading ? 'Minting...' : 'Mint Edition'}
                      </button>
                    )}
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

          {/* Cross-Chain Management Section */}
          {editionInfo && debugInfo?.walletIsEditionOwner && (
            <div className="cross-chain-management" style={{marginTop: '20px', padding: '16px', border: '1px solid var(--border-primary)', borderRadius: '8px', backgroundColor: 'var(--card-background)'}}>
              <h4>🌉 Cross-Chain Management</h4>
              
              <div style={{marginBottom: '16px'}}>
                <div><strong>ArtEdition Contract Address:</strong></div>
                <div style={{fontFamily: 'monospace', fontSize: '0.9em', color: 'var(--text-secondary)', wordBreak: 'break-all', padding: '4px 8px', backgroundColor: 'var(--background-secondary)', borderRadius: '4px', margin: '4px 0'}}>
                  {editionInfo.erc1155Address}
                </div>
              </div>

              <CrossChainWhitelistForm editionAddress={editionInfo.erc1155Address} />
            </div>
          )}

          {debugInfo && (
            <div className="debug-info">
              <h4>🔍 Contract Analysis</h4>
              
              {debugInfo.error ? (
                <div style={{color: 'red'}}>Error: {debugInfo.error}</div>
              ) : (
                <div>
                  <div><strong>📱 Your Wallet:</strong> {debugInfo.currentWallet}</div>
                  
                  <hr style={{margin: '10px 0', border: '1px solid var(--border-secondary)'}} />
                  
                  <div><strong>🌐 Current Network:</strong></div>
                  <div style={{marginLeft: '10px', fontSize: '0.85em'}}>
                    <div>Chain ID: {debugInfo.currentNetwork?.chainId}</div>
                    <div>Name: {debugInfo.currentNetwork?.name}</div>
                    <div style={{color: debugInfo.currentNetwork?.isArbitrumSepolia ? 'orange' : 'green'}}>
                      {debugInfo.currentNetwork?.isArbitrumSepolia ? '⚠️ Arbitrum Sepolia' : '✅ Other Network'}
                    </div>
                  </div>
                  
                  <hr style={{margin: '10px 0', border: '1px solid var(--border-secondary)'}} />
                  
                  <div><strong>🏪 ArtSales1155 Contract:</strong></div>
                  <div style={{marginLeft: '10px', fontSize: '0.85em'}}>
                    <div>Address: {debugInfo.artSales1155Address}</div>
                    <div>Owner: {debugInfo.salesOwner}</div>
                    <div style={{color: debugInfo.walletIsSalesOwner ? 'green' : 'red'}}>
                      You are owner: {debugInfo.walletIsSalesOwner ? '✅ YES' : '❌ NO'}
                    </div>
                  </div>
                  
                  <hr style={{margin: '10px 0', border: '1px solid var(--border-secondary)'}} />
                  
                  <div><strong>👤 Profile Contract:</strong></div>
                  <div style={{marginLeft: '10px', fontSize: '0.85em'}}>
                    <div>Address: {debugInfo.profileAddress}</div>
                    <div>Owner: {debugInfo.profileOwner}</div>
                    <div>Is Artist: {debugInfo.profileIsArtist ? 'Yes' : 'No'}</div>
                    <div>ArtSales1155: {debugInfo.profileArtSales1155}</div>
                    <div style={{color: debugInfo.walletIsProfileOwner ? 'green' : 'red'}}>
                      You are owner: {debugInfo.walletIsProfileOwner ? '✅ YES' : '❌ NO'}
                    </div>
                  </div>
                  
                  <hr style={{margin: '10px 0', border: '1px solid var(--border-secondary)'}} />
                  
                  <div><strong>🎨 Art Piece Contract:</strong></div>
                  <div style={{marginLeft: '10px', fontSize: '0.85em'}}>
                    <div>Address: {debugInfo.artPieceAddress}</div>
                    <div>Title: {debugInfo.artPieceTitle}</div>
                    <div>Artist: {debugInfo.artPieceArtist}</div>
                    <div>Owner: {debugInfo.artPieceOwner}</div>
                    <div style={{color: debugInfo.walletIsArtist ? 'green' : 'orange'}}>
                      You are artist: {debugInfo.walletIsArtist ? '✅ YES' : '❌ NO'}
                    </div>
                    <div style={{color: debugInfo.walletIsArtOwner ? 'green' : 'orange'}}>
                      You are owner: {debugInfo.walletIsArtOwner ? '✅ YES' : '❌ NO'}
                    </div>
                  </div>
                  
                  <hr style={{margin: '10px 0', border: '1px solid var(--border-secondary)'}} />
                  
                  <div><strong>🎯 Edition Contract:</strong></div>
                  <div style={{marginLeft: '10px', fontSize: '0.85em'}}>
                    <div>Address: {debugInfo.editionAddress}</div>
                    <div>Owner: {debugInfo.editionOwner}</div>
                    <div>ArtSales1155: {debugInfo.editionArtSales1155}</div>
                    <div>Linked Art Piece: {debugInfo.editionArtPiece}</div>
                    <div style={{color: debugInfo.walletIsEditionOwner ? 'green' : 'red'}}>
                      You are owner: {debugInfo.walletIsEditionOwner ? '✅ YES' : '❌ NO'}
                    </div>
                    
                    <div style={{marginTop: '8px', padding: '8px', background: 'rgba(255,215,0,0.1)', border: '1px solid orange', borderRadius: '4px'}}>
                      <div style={{fontWeight: 'bold', color: 'orange'}}>🔍 CRITICAL OWNERSHIP ANALYSIS:</div>
                      <div style={{fontSize: '0.8em', marginTop: '4px'}}>
                        <div>ArtSales1155 owner: {debugInfo.salesOwner}</div>
                        <div>ArtEdition1155 owner: {debugInfo.editionOwner}</div>
                        <div style={{color: debugInfo.salesOwner && debugInfo.editionOwner && debugInfo.salesOwner.toLowerCase() === debugInfo.editionOwner.toLowerCase() ? 'green' : 'red', fontWeight: 'bold'}}>
                          Owners match: {debugInfo.salesOwner && debugInfo.editionOwner && debugInfo.salesOwner.toLowerCase() === debugInfo.editionOwner.toLowerCase() ? '✅ YES' : '❌ NO - THIS IS THE BUG!'}
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <hr style={{margin: '10px 0', border: '1px solid var(--border-secondary)'}} />
                  
                  <div><strong>🔗 Contract Relationships:</strong></div>
                  <div style={{marginLeft: '10px', fontSize: '0.85em'}}>
                    <div style={{color: debugInfo.profileLinksToSales ? 'green' : 'red'}}>
                      Profile → ArtSales1155: {debugInfo.profileLinksToSales ? '✅ Linked' : '❌ Broken'}
                    </div>
                    <div style={{color: debugInfo.editionLinksToArtPiece ? 'green' : 'red'}}>
                      Edition → Art Piece: {debugInfo.editionLinksToArtPiece ? '✅ Linked' : '❌ Broken'}
                    </div>
                  </div>
                  
                  <hr style={{margin: '10px 0', border: '1px solid var(--border-secondary)'}} />
                  
                  <div><strong>⚖️ Authorization Analysis:</strong></div>
                  <div style={{marginLeft: '10px', fontSize: '0.85em'}}>
                    <div style={{color: debugInfo.canStartSale ? 'green' : 'red', fontWeight: 'bold'}}>
                      Can start sale: {debugInfo.canStartSale ? '✅ YES' : '❌ NO'}
                    </div>
                    {debugInfo.whyCantStartSale && (
                      <div style={{color: 'red', fontSize: '0.9em'}}>
                        Why not: {debugInfo.whyCantStartSale}
                      </div>
                    )}
                    <div style={{fontSize: '0.8em', marginTop: '5px', color: 'var(--text-secondary)'}}>
                      Required: Be ArtSales1155 owner OR original artist
                    </div>
                  </div>
                </div>
              )}
              
              <button onClick={checkOwnership} className="debug-button" style={{marginTop: '10px'}}>
                🔄 Refresh Analysis
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MintArtEdition; 