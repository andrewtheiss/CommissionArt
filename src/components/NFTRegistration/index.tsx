import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useBlockchain } from '../../utils/BlockchainContext';
import { getImageOrientation, revokePreviewUrl } from '../../utils/ImageCompressorUtil';
import type { FormatType } from '../../utils/ImageCompressorUtil';
import { formatTokenURI, reduceTokenURISize, hashString, extractImageFromTokenURI, createComparisonHashes } from '../../utils/TokenURIFormatter';
import './NFTRegistration.css';
import { ethers } from 'ethers';
import contractConfig from '../../assets/contract_config.json';
import abiLoader from '../../utils/abiLoader';
import ethersService from '../../utils/ethers-service';
import profileService from '../../utils/profile-service';

// Add interfaces for our new compression code:
interface CompressionResult {
  blob: Blob | null;
  preview: string | null;
  compressedSize: number;
  originalSize: number;
  dimensions: { width: number; height: number };
  success: boolean;
  targetReached: boolean;
  format: string;
  error?: string;
}

interface CompressionOptions {
  format: 'webp' | 'jpeg' | 'avif';
  quality: number;
  maxWidth: number | null;
  maxHeight: number | null;
  targetSizeKB?: number;
  autoOptimize?: boolean;
}

interface OptimizedCompressionResult {
  dataUrl: string;
  width: number;
  height: number;
  sizeKB: number;
  format: 'webp' | 'jpeg' | 'avif';
  quality: number;
}

// Define ArtistForm as a separate component with onBack prop
const ArtistForm: React.FC<{
  artworkTitle: string;
  setArtworkTitle: (title: string) => void;
  artworkDescription: string;
  setArtworkDescription: (desc: string) => void;
  selectedImage: File | null;
  setSelectedImage: (file: File | null) => void;
  originalPreviewUrl: string | null;
  setOriginalPreviewUrl: (url: string | null) => void;
  compressedResult: CompressionResult | null;
  setCompressedResult: (result: CompressionResult | null) => void;
  isCompressing: boolean;
  setIsCompressing: (compressing: boolean) => void;
  imageOrientation: 'portrait' | 'landscape' | 'square' | null;
  setImageOrientation: (orientation: 'portrait' | 'landscape' | 'square' | null) => void;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  isTrulyConnected: boolean;
  connectWallet: () => void;
  walletAddress: string | null;
  networkType: string;
  switchToLayer: (layer: 'l1' | 'l2' | 'l3', environment: 'testnet' | 'mainnet') => void;
  hasProfile: boolean;
  preferredFormat: FormatType;
  setPreferredFormat: (format: FormatType) => void;
  onBack: () => void;
}> = ({
  artworkTitle,
  setArtworkTitle,
  artworkDescription,
  setArtworkDescription,
  selectedImage,
  setSelectedImage,
  originalPreviewUrl,
  setOriginalPreviewUrl,
  compressedResult,
  setCompressedResult,
  isCompressing,
  setIsCompressing,
  imageOrientation,
  setImageOrientation,
  fileInputRef,
  isTrulyConnected,
  connectWallet,
  walletAddress,
  networkType,
  switchToLayer,
  hasProfile,
  preferredFormat,
  setPreferredFormat,
  onBack,
}) => {
  const handleTitleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setArtworkTitle(e.target.value);
  }, [setArtworkTitle]);

  const handleDescriptionChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value;
    if (text.length <= 200) {
      setArtworkDescription(text);
    }
  }, [setArtworkDescription]);

  const handleImageSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (originalPreviewUrl) revokePreviewUrl(originalPreviewUrl);
    if (compressedResult?.preview) revokePreviewUrl(compressedResult.preview);

    setSelectedImage(file);
    const previewUrl = URL.createObjectURL(file);
    setOriginalPreviewUrl(previewUrl);

    const img = new Image();
    img.onload = () => {
      const orientation = getImageOrientation(img.width, img.height);
      setImageOrientation(orientation);
      compressImageFile(file);
    };
    img.src = previewUrl;
  };

  const compressImageFile = async (file: File) => {
    if (!file) return;
    
    setIsCompressing(true);
    
    try {
      // Use our optimized compression function targeting 43.5KB (43500 bytes)
      const result = await optimizeImageForSize(file, 43.5);
      
      // Convert the optimized result to the expected CompressionResult format
      const blob = dataURLtoBlob(result.dataUrl);
      const compressedResult: CompressionResult = {
        blob: blob,
        preview: result.dataUrl,
        compressedSize: result.sizeKB,
        originalSize: file.size / 1024,
        dimensions: { width: result.width, height: result.height },
        success: true,
        targetReached: result.sizeKB <= 43.5,
        format: result.format.toUpperCase()
      };
      
      // Log compression results for debugging
      console.log(`Compression successful:
        - Original size: ${(file.size / 1024).toFixed(2)} KB
        - Compressed size: ${result.sizeKB.toFixed(2)} KB
        - Dimensions: ${result.width}x${result.height}
        - Format: ${result.format}
        - Quality: ${(result.quality * 100).toFixed(0)}%
        - Target reached: ${result.sizeKB <= 43.5 ? 'Yes' : 'No'}
      `);
      
      // Log the first part of the compressed image data URL
      console.log("Compressed image data preview (first 100 chars):", result.dataUrl.substring(0, 100));
      
      // Log base64 length as an indicator of the image data size
      const base64Data = result.dataUrl.split(',')[1];
      if (base64Data) {
        console.log(`Base64 data length: ${base64Data.length} chars (approx ${Math.round(base64Data.length * 0.75 / 1024)} KB raw)`);
      }
      
      setCompressedResult(compressedResult);
      
      // Log detailed compression information
      console.log(`Optimized image compression:`);
      console.log(`- Original: ${(file.size / 1024).toFixed(2)} KB`);
      console.log(`- Compressed: ${result.sizeKB.toFixed(2)} KB (${(result.sizeKB * 1024).toFixed(0)} bytes)`);
      console.log(`- Dimensions: ${result.width}x${result.height}`);
      console.log(`- Format: ${result.format.toUpperCase()}`);
      console.log(`- Quality: ${(result.quality * 100).toFixed(0)}%`);
      
      // Warn if we're still close to the limit
      if (result.sizeKB * 1024 > 44000) {
        console.warn('Image size is very close to the 45,000 byte limit. Consider using even smaller target size.');
      }
      
      // Get orientation from dimensions
      const orientation = getImageOrientation(result.width, result.height);
      setImageOrientation(orientation);
    } catch (error) {
      console.error('Error compressing image:', error);
      alert(`Failed to compress image: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsCompressing(false);
    }
  };

  // Helper function to convert data URL to Blob
  const dataURLtoBlob = (dataURL: string): Blob => {
    const parts = dataURL.split(';base64,');
    const contentType = parts[0].split(':')[1];
    const raw = window.atob(parts[1]);
    const rawLength = raw.length;
    const uInt8Array = new Uint8Array(rawLength);
    
    for (let i = 0; i < rawLength; ++i) {
      uInt8Array[i] = raw.charCodeAt(i);
    }
    
    return new Blob([uInt8Array], { type: contentType });
  };

  // Advanced image optimization function
  const optimizeImageForSize = async (
    input: File | Blob | string,
    targetSizeKB: number = 43.5
  ): Promise<OptimizedCompressionResult> => {
    console.log(`Starting auto-optimization to target ${targetSizeKB}KB`);
    
    // Format options in order of preference (better quality comes first)
    const formatOptions: Array<'avif' | 'webp' | 'jpeg'> = ['avif', 'webp', 'jpeg'];
    
    // Load the image
    let imageDataUrl: string;
    if (typeof input === 'string' && input.startsWith('data:')) {
      imageDataUrl = input;
    } else {
      imageDataUrl = await fileToDataUrl(input as File | Blob);
    }
    
    // Get original image dimensions
    const img = document.createElement('img');
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve();
      img.onerror = () => reject(new Error('Failed to load image'));
      img.src = imageDataUrl;
    });
    
    const originalWidth = img.width;
    const originalHeight = img.height;
    
    console.log(`Original dimensions: ${originalWidth}x${originalHeight}`);
    
    // Start with original dimensions and try all formats and qualities
    let bestResult: OptimizedCompressionResult | null = null;
    
    // Try different formats and quality levels
    for (const format of formatOptions) {
      // Try high quality first, then lower if needed
      for (let quality = 0.9; quality >= 0.4; quality -= 0.1) {
        // Create a canvas with original dimensions
        const canvas = document.createElement('canvas');
        canvas.width = originalWidth;
        canvas.height = originalHeight;
        const ctx = canvas.getContext('2d');
        ctx?.drawImage(img, 0, 0, originalWidth, originalHeight);
        
        // Get mime type
        const mimeType = `image/${format}`;
        
        // Convert canvas to data URL with current format and quality
        try {
          const dataUrl = canvas.toDataURL(mimeType, quality);
          const sizeKB = calculateDataUrlSizeKB(dataUrl);
          
          console.log(`Format: ${format}, Quality: ${quality.toFixed(1)}, Size: ${sizeKB.toFixed(2)}KB`);
          
          // Check if this result is better than our previous best
          if (sizeKB <= targetSizeKB && (!bestResult || sizeKB > bestResult.sizeKB)) {
            bestResult = {
              dataUrl,
              width: originalWidth,
              height: originalHeight,
              sizeKB,
              format,
              quality
            };
            console.log(`New best result: ${format} at ${quality.toFixed(1)} quality (${sizeKB.toFixed(2)}KB)`);
            
            // If we're very close to target with a good format, we can stop early
            if (sizeKB > targetSizeKB * 0.95 && (format === 'avif' || format === 'webp')) {
              console.log(`Optimal result found early, stopping search`);
              return bestResult;
            }
          }
        } catch (error) {
          console.warn(`Format ${format} not supported by browser, skipping`);
          // Skip this format as browser doesn't support it
          break;
        }
      }
    }
    
    // If we haven't found a good result yet, try reducing dimensions
    if (!bestResult) {
      console.log(`Unable to meet target size with original dimensions, trying reduced dimensions`);
      
      // Try different scale factors (90%, 80%, 70%, etc.)
      for (let scale = 0.9; scale >= 0.3; scale -= 0.1) {
        const width = Math.round(originalWidth * scale);
        const height = Math.round(originalHeight * scale);
        
        console.log(`Trying scaled dimensions: ${width}x${height} (${Math.round(scale * 100)}%)`);
        
        // Try different formats and quality levels at reduced dimensions
        for (const format of formatOptions) {
          // With smaller dimensions, we can use higher quality
          for (let quality = 0.9; quality >= 0.5; quality -= 0.1) {
            // Create a canvas with scaled dimensions
            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            ctx?.drawImage(img, 0, 0, width, height);
            
            // Get mime type
            const mimeType = `image/${format}`;
            
            try {
              // Convert canvas to data URL with current format and quality
              const dataUrl = canvas.toDataURL(mimeType, quality);
              const sizeKB = calculateDataUrlSizeKB(dataUrl);
              
              console.log(`Scale: ${Math.round(scale * 100)}%, Format: ${format}, Quality: ${quality.toFixed(1)}, Size: ${sizeKB.toFixed(2)}KB`);
              
              // Check if this result is better than our previous best
              if (sizeKB <= targetSizeKB && (!bestResult || sizeKB > bestResult.sizeKB)) {
                bestResult = {
                  dataUrl,
                  width,
                  height,
                  sizeKB,
                  format,
                  quality
                };
                console.log(`New best result: ${width}x${height} ${format} at ${quality.toFixed(1)} quality (${sizeKB.toFixed(2)}KB)`);
                
                // If we're very close to target with a good format, we can stop early
                if (sizeKB > targetSizeKB * 0.95 && (format === 'avif' || format === 'webp')) {
                  console.log(`Optimal result found, stopping search`);
                  return bestResult;
                }
              }
            } catch (error) {
              console.warn(`Format ${format} not supported by browser, skipping`);
              // Skip this format as browser doesn't support it
              break;
            }
          }
        }
        
        // If we've found a result that's at least 90% of our target size, stop reducing dimensions
        if (bestResult && bestResult.sizeKB > targetSizeKB * 0.9) {
          console.log(`Found good result at ${Math.round(scale * 100)}% scale, stopping dimension reduction`);
          break;
        }
      }
    }
    
    // If we still haven't found a good result, use the smallest JPEG at lowest quality as fallback
    if (!bestResult) {
      console.log(`Unable to meet target size, using minimum size JPEG fallback`);
      
      const width = Math.round(originalWidth * 0.3);
      const height = Math.round(originalHeight * 0.3);
      
      // Create a canvas with minimum dimensions
      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d');
      ctx?.drawImage(img, 0, 0, width, height);
      
      // Use JPEG at lowest quality
      const dataUrl = canvas.toDataURL('image/jpeg', 0.3);
      const sizeKB = calculateDataUrlSizeKB(dataUrl);
      
      bestResult = {
        dataUrl,
        width,
        height,
        sizeKB,
        format: 'jpeg',
        quality: 0.3
      };
      
      console.log(`Fallback result: ${width}x${height} JPEG at minimum quality (${sizeKB.toFixed(2)}KB)`);
    }
    
    return bestResult;
  };
  
  // Helper function to convert File/Blob to data URL
  const fileToDataUrl = (file: File | Blob): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = () => reject(new Error('Failed to read file'));
      reader.readAsDataURL(file);
    });
  };
  
  // Calculate size in KB from data URL
  const calculateDataUrlSizeKB = (dataUrl: string): number => {
    // Remove the data URL prefix (e.g., 'data:image/jpeg;base64,')
    const base64 = dataUrl.split(',')[1];
    // Calculate the size: base64 is 4/3 the size of binary
    const sizeInBytes = Math.ceil((base64.length * 3) / 4);
    return sizeInBytes / 1024;
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleRegisterArtwork = async () => {
    if (!isTrulyConnected) {
      alert("Please connect your wallet to register your artwork");
      connectWallet();
      return;
    }
    if (!selectedImage || !compressedResult || isCompressing) {
      alert("Please upload an image for your artwork");
      return;
    }
    if (!artworkTitle.trim()) {
      alert("Please enter a title for your artwork");
      return;
    }

    try {
      // Show loading state first
      setIsCompressing(true);

      if (!compressedResult.blob) {
        throw new Error("Compressed image blob is not available");
      }
      
      const titleStr = artworkTitle.trim();
      const descriptionStr = artworkDescription.trim();
      
      // Log the original compressed image format and data
      console.log(`Using compressed image in format: ${compressedResult.format}`);
      
      // Convert the image to raw byte array
      const imageDataArray = new Uint8Array(await compressedResult.blob.arrayBuffer());
      console.log(`Raw image data length: ${imageDataArray.length} bytes`);
      console.log(`First few bytes: [${Array.from(imageDataArray.slice(0, 10)).join(', ')}...]`);
      
      // Extract the format from the MIME type
      const mimeTypeMatch = compressedResult.preview?.match(/^data:(image\/[^;]+);base64,/);
      const mimeType = mimeTypeMatch ? mimeTypeMatch[1] : 'image/avif';
      const formatStr = mimeType.split('/')[1]; // Extract just the format part (avif, webp, jpeg)
      console.log(`Detected MIME type: ${mimeType}, Format: ${formatStr}`);

      // Proceed directly with registration using raw image data and format
      await proceedWithRegistration(
        titleStr,
        descriptionStr,
        imageDataArray,
        formatStr
      );
    } catch (error) {
      setIsCompressing(false);
      console.error("Error preparing artwork:", error);
      alert(`Error preparing artwork: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  // Function to proceed with registration
  const proceedWithRegistration = async (
    titleStr: string,
    descriptionStr: string,
    imageDataArray: Uint8Array,
    mimeType: string
  ) => {
    if (!isTrulyConnected) {
      alert("Please connect your wallet to register your artwork");
      connectWallet();
      return;
    }
    
    // Helper function for encoding byte arrays for debugging
    const inspectByteArray = (data: Uint8Array): string => {
      const hex = Array.from(data.slice(0, 50))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');
      
      const maxBytes = 50;
      const displayLength = Math.min(data.length, maxBytes);
      
      return `First ${displayLength} bytes as hex: 0x${hex}${data.length > maxBytes ? '...' : ''}`;
    };
    
    try {
      // First, make sure we're on the AnimeChain L3 network
      if (networkType !== 'animechain') {
        await switchToLayer('l3', 'mainnet');
      }

      // Get the signer for transaction
      const signer = await ethersService.getSigner();
      if (!signer) {
        throw new Error("Failed to get signer");
      }
      
      // Get the artCommissionHub address from the config
      const artCommissionHubAddress = contractConfig.networks.mainnet.artCommissionHub.address || ethers.ZeroAddress;

      if (hasProfile) {
        // Register artwork via profile
        console.log("Registering artwork via Profile...");
        
        // Get the profile contract
        const profileContract = await profileService.getMyProfile();
        if (!profileContract) {
          throw new Error("Failed to get profile contract");
        }
        
        // Use the ArtPiece address as the factory address (temporary solution)
        const artPieceAddress = contractConfig.networks.mainnet.artPiece.address;
        if (!artPieceAddress) {
          throw new Error("ArtPiece address not configured");
        }
        
        // Log byte array information
        console.log(`Image byte array length: ${imageDataArray.length} bytes`);
        console.log(`First few bytes: [${Array.from(imageDataArray.slice(0, 20)).join(', ')}...]`);
        console.log(`MIME type: ${mimeType}, Format: ${mimeType.split('/')[1]}`);
        console.log(`Title: "${titleStr}", Description: "${descriptionStr}"`);
        console.log(`ArtPiece template address: ${artPieceAddress}`);
        console.log(`Commission Hub address: ${artCommissionHubAddress}`);

        // Debug: log contract address and ABI
        console.log(`Profile contract address: ${profileContract.target}`);
        try {
          const fragment = profileContract.interface.getFunction('createArtPiece');
          console.log(`Found createArtPiece fragment:`, fragment);
        } catch (e) {
          console.error(`Could not find createArtPiece in ABI:`, e);
        }

        try {
          // Call the profile's createArtPiece function with the raw image data
          console.log("Attempting to call createArtPiece...");

          // Try to ensure proper serialization by converting to BytesLike
          const bytesData = ethers.hexlify(ethers.concat([imageDataArray]));
          console.log(`Sending as hex (via ethers.hexlify): ${bytesData.substring(0, 100)}...`);

          // Check the size of the data
          const dataSize = imageDataArray.length;
          if (dataSize > 45000) {
            console.warn(`Image data exceeds the contract limit of 45000 bytes. Current size: ${dataSize} bytes`);
            throw new Error(`Image size (${dataSize} bytes) exceeds the contract limit of 45000 bytes. Please use a smaller image.`);
          }

          const tx = await profileContract.createArtPiece(
            artPieceAddress,
            bytesData, // Send as hex string using ethers.js utilities
            mimeType, // Just the format part (jpeg, avif, webp)
            titleStr,      
            descriptionStr,
            true, // is artist
            ethers.ZeroAddress, // no other party
            artCommissionHubAddress,
            false // not AI generated
          );
          
          console.log("Transaction sent:", tx.hash);
          
          // Wait for the transaction to be mined
          const receipt = await tx.wait();
          console.log("Transaction confirmed:", receipt);
          
          setIsCompressing(false);
          alert(`Artwork registered successfully via Profile!`);
        } catch (error: any) {
          console.error("Error in createArtPiece:", error);
          // Try to get more detailed error information
          if (error.reason) console.error("Error reason:", error.reason);
          if (error.code) console.error("Error code:", error.code);
          if (error.data) console.error("Error data:", error.data);
          throw error;
        }
      } else {
        // Direct ArtPiece creation flow for users without a profile
        console.log("Deploying ArtPiece contract directly...");

        // Get the ArtPiece contract factory from the ABI
        const artPieceAbi = abiLoader.loadABI('ArtPiece');
        console.log("ArtPiece ABI loaded:", artPieceAbi ? "Success" : "Failed");
        
        if (artPieceAbi) {
          // Debug the ABI methods
          const methods = artPieceAbi
            .filter((item: any) => item.type === 'function')
            .map((item: any) => item.name);
          console.log("Available ABI methods:", methods);
          console.log("Has aiGenerated method:", methods.includes('aiGenerated'));
          console.log("Has getAIGenerated method:", methods.includes('getAIGenerated'));
        }
        
        if (!artPieceAbi) {
          throw new Error("Failed to load ArtPiece ABI");
        }
        
        // Get the ProfileFactoryAndRegistry contract
        const profileFactoryAndRegistryAddress = contractConfig.networks.mainnet.profileFactoryAndRegistry.address;
        const profileFactoryAndRegistryAbi = abiLoader.loadABI('ProfileFactoryAndRegistry');
        
        if (!profileFactoryAndRegistryAddress || !profileFactoryAndRegistryAbi) {
          throw new Error("ProfileFactoryAndRegistry configuration not found");
        }
        
        const profileFactoryAndRegistry = new ethers.Contract(profileFactoryAndRegistryAddress, profileFactoryAndRegistryAbi, signer);
        
        // Get the template ArtPiece address
        const artPieceTemplateAddress = contractConfig.networks.mainnet.artPiece.address;
        if (!artPieceTemplateAddress) {
          throw new Error("ArtPiece template address not configured");
        }
        
        console.log("Creating profile and registering artwork in one transaction...");
        
        // Debug: log parameters and contract details
        console.log(`Image byte array length: ${imageDataArray.length} bytes`);
        console.log(`First few bytes: [${Array.from(imageDataArray.slice(0, 20)).join(', ')}...]`);
        console.log(`MIME type: ${mimeType}, Format: ${mimeType.split('/')[1]}`);
        console.log(`Title: "${titleStr}", Description: "${descriptionStr}"`);
        console.log(`ArtPiece template address: ${artPieceTemplateAddress}`);
        console.log(`Commission Hub address: ${artCommissionHubAddress}`);

        // Debug: log contract address and ABI
        console.log(`ProfileFactoryAndRegistry contract address: ${profileFactoryAndRegistry.target}`);
        try {
          const fragment = profileFactoryAndRegistry.interface.getFunction('createNewArtPieceAndRegisterProfileAndAttachToHub');
          console.log(`Found createNewArtPieceAndRegisterProfileAndAttachToHub fragment:`, fragment);
        } catch (e) {
          console.error(`Could not find createNewArtPieceAndRegisterProfileAndAttachToHub in ABI:`, e);
        }

        try {
          // Create profile and register artwork with raw image data
          console.log("Attempting to call createNewArtPieceAndRegisterProfileAndAttachToHub...");

          // Try to ensure proper serialization by converting to BytesLike
          const bytesData2 = ethers.hexlify(ethers.concat([imageDataArray]));
          console.log(`Sending as hex (via ethers.hexlify): ${bytesData2.substring(0, 100)}...`);

          // Check the size of the data
          const dataSize2 = imageDataArray.length;
          if (dataSize2 > 45000) {
            console.warn(`Image data exceeds the contract limit of 45000 bytes. Current size: ${dataSize2} bytes`);
            throw new Error(`Image size (${dataSize2} bytes) exceeds the contract limit of 45000 bytes. Please use a smaller image.`);
          }

          const tx = await profileFactoryAndRegistry.createNewArtPieceAndRegisterProfileAndAttachToHub(
            artPieceTemplateAddress,
            bytesData2, // Send as hex string using ethers.js utilities
            mimeType, // Just the format part (jpeg, avif, webp)
            titleStr,      
            descriptionStr,
            true, // is artist
            ethers.ZeroAddress, // no other party
            artCommissionHubAddress,
            false // not AI generated
          );
          
          console.log("Transaction sent:", tx.hash);
          
          // Wait for the transaction to be mined
          const receipt = await tx.wait();
          console.log("Transaction confirmed:", receipt);
          
          // Extract profile and art piece addresses from the event logs
          let profileAddress = null;
          let artPieceAddress = null;
          
          for (const log of receipt.logs) {
            try {
              const parsedLog = profileFactoryAndRegistry.interface.parseLog(log);
              if (parsedLog && parsedLog.name === "ProfileCreated") {
                profileAddress = parsedLog.args.profile;
              } else if (parsedLog && parsedLog.name === "ArtPieceCreated") {
                artPieceAddress = parsedLog.args.art_piece;
              }
            } catch (error) {
              // Skip logs that can't be parsed
              continue;
            }
          }
          
          if (!profileAddress || !artPieceAddress) {
            throw new Error("Failed to extract profile or artwork addresses from receipt");
          }
          
          setIsCompressing(false);
          alert(`Profile created and artwork registered successfully!\nProfile: ${profileAddress}\nArtwork: ${artPieceAddress}`);
          console.log("Registration successful:", {
            profileAddress,
            artPieceAddress,
            artist: walletAddress,
            owner: walletAddress,
            artworkTitle: titleStr,
            imageDataSize: imageDataArray.length,
            imageFormat: compressedResult?.format || preferredFormat,
            dimensions: compressedResult?.dimensions || { width: 0, height: 0 },
          });
        } catch (error: any) {
          console.error("Error in createNewArtPieceAndRegisterProfileAndAttachToHub:", error);
          // Try to get more detailed error information
          if (error.reason) console.error("Error reason:", error.reason);
          if (error.code) console.error("Error code:", error.code);
          if (error.data) console.error("Error data:", error.data);
          
          setIsCompressing(false);
          
          if (String(error).includes("execution reverted")) {
            alert(`Error: Your transaction was reverted. This could be because the contract already exists or there was an issue with the parameters.`);
          } else {
            alert(`Error deploying artwork contract: ${error instanceof Error ? error.message : String(error)}`);
          }
        }
      }
    } catch (error) {
      setIsCompressing(false);
      console.error("Error registering artwork:", error);
      alert(`Error registering artwork: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  return (
    <div className="registration-form">
      <h3>Artist Registration</h3>
      <div className="form-instructions">
        <p>As an artist, you'll be able to create and register your artwork on-chain.</p>
        {!isTrulyConnected && (
          <p className="connect-reminder">
            <span className="highlight">You can fill out the form now</span>, and connect your wallet when you're ready to register.
          </p>
        )}
        {isTrulyConnected && hasProfile && (
          <p className="profile-info highlight-box">
            <span className="highlight">Your profile was detected!</span> Your artwork will be registered through your profile.
          </p>
        )}
      </div>
      <div className={`artist-form-container ${imageOrientation || ''}`}>
        {imageOrientation === 'landscape' && compressedResult && compressedResult.preview ? (
          <div className="artwork-banner">
            <div className="artwork-preview landscape">
              <img src={compressedResult.preview} alt="Artwork Preview" className="preview-image" />
              <div className="preview-overlay">
                <div className="preview-actions">
                  <button onClick={handleUploadClick} className="change-image-btn">
                    Change Image
                  </button>
                </div>
                <div className="image-info">
                  <span>Size: {compressedResult.compressedSize.toFixed(2)} KB</span>
                  <span>Format: {compressedResult.format}</span>
                  <span>Dimensions: {compressedResult.dimensions.width}x{compressedResult.dimensions.height}</span>
                  <div className="format-selector-overlay">
                    <span className="format-label">Format:</span>
                    <div className="format-options-overlay">
                      {[
                        { type: 'image/avif', name: 'AVIF (preferred)' },
                        { type: 'image/webp', name: 'WebP' },
                        { type: 'image/jpeg', name: 'JPEG' }
                      ].map(format => (
                        <div 
                          key={format.type}
                          className={`format-radio ${preferredFormat === format.type ? 'selected' : ''}`}
                          onClick={() => {
                            setPreferredFormat(format.type as FormatType);
                            if (selectedImage) {
                              compressImageFile(selectedImage);
                            }
                          }}
                        >
                          <div className="radio-outer-small">
                            <div className={`radio-inner-small ${preferredFormat === format.type ? 'active' : ''}`}></div>
                          </div>
                          <span className="format-name-small">{format.name}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : null}
        {(imageOrientation !== 'landscape' || !compressedResult || !compressedResult.preview) && (
          <div className="artwork-upload-section">
            <input
              ref={fileInputRef}
              type="file"
              id="artwork-image"
              accept="image/*"
              onChange={handleImageSelect}
              className="file-input"
              style={{ display: 'none' }}
            />
            {!compressedResult || !compressedResult.preview ? (
              <div className="upload-placeholder" onClick={handleUploadClick}>
                <div className="placeholder-content">
                  <div className="upload-icon">+</div>
                  <div className="upload-text">Upload Image</div>
                  <div className="upload-subtext">Max size: 45KB (will be automatically compressed)</div>
                </div>
              </div>
            ) : isCompressing ? (
              <div className="compressing-indicator">
                <div className="spinner"></div>
                <div>Optimizing image...</div>
                <div className="optimization-note">Finding best format & quality under 43.5KB</div>
              </div>
            ) : (
              <div className={`artwork-preview ${imageOrientation || ''}`}>
                <img src={compressedResult.preview} alt="Artwork Preview" className="preview-image" />
                <div className="preview-overlay">
                  <div className="preview-actions">
                    <button onClick={handleUploadClick} className="change-image-btn">
                      Change Image
                    </button>
                  </div>
                  <div className="image-info">
                    <div className="optimization-summary">
                      <span className="optimization-title">Auto-Optimized Image</span>
                      {compressedResult.compressedSize * 1024 > 44000 ? (
                        <span className="size-warning">Size is close to limit!</span>
                      ) : (
                        <span className="size-success">Size is within limits</span>
                      )}
                    </div>
                    <div className="stat-row">
                      <span className="stat-label">Original:</span>
                      <span className="stat-value">{compressedResult.originalSize.toFixed(2)} KB</span>
                    </div>
                    <div className="stat-row">
                      <span className="stat-label">Compressed:</span>
                      <span className="stat-value">{compressedResult.compressedSize.toFixed(2)} KB ({(compressedResult.compressedSize * 1024).toFixed(0)} bytes)</span>
                    </div>
                    <div className="stat-row">
                      <span className="stat-label">Format:</span>
                      <span className="stat-value">{compressedResult.format}</span>
                    </div>
                    <div className="stat-row">
                      <span className="stat-label">Dimensions:</span>
                      <span className="stat-value">{compressedResult.dimensions.width}×{compressedResult.dimensions.height}</span>
                    </div>
                    <div className="stat-row">
                      <span className="stat-label">Reduction:</span>
                      <span className="stat-value">
                        {compressedResult.originalSize > 0 
                          ? ((1 - compressedResult.compressedSize / compressedResult.originalSize) * 100).toFixed(1) + '%' 
                          : '-'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
        
        <form>
          <div className="form-content">
            <div className="form-group">
              <label htmlFor="artwork-title">
                Artwork Title <span className="required">*</span>
              </label>
              <input
                type="text"
                id="artwork-title"
                className="form-input"
                placeholder="Enter the title of your artwork"
                value={artworkTitle}
                onChange={handleTitleChange}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="artwork-description">
                Description <span className="byte-counter">{artworkDescription.length}/200 characters</span>
              </label>
              <textarea
                id="artwork-description"
                value={artworkDescription}
                onChange={handleDescriptionChange}
                placeholder="Enter a description for your artwork"
                className="form-control"
              />
            </div>
            <div className="form-actions">
              <button 
                type="button"
                className={`submit-button ${hasProfile ? 'profile-button' : ''}`}
                disabled={!compressedResult || isCompressing}
                onClick={handleRegisterArtwork}
              >
                {hasProfile ? 'Register Artwork in Profile' : 'Register Artwork'}
              </button>
            </div>
          </div>
          <div className="form-footer">
            <button type="button" className="form-back-button" onClick={onBack}>
              Back
            </button>
            <button
              type="button"
              className={`submit-button ${hasProfile ? 'profile-button' : ''}`}
              disabled={!compressedResult || isCompressing}
              onClick={handleRegisterArtwork}
            >
              {hasProfile ? 'Register Artwork in Profile' : 'Register Artwork'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const NFTRegistration: React.FC = () => {
  const [userType, setUserType] = useState<'artist' | 'commissioner' | null>(null);
  const { isConnected, connectWallet, walletAddress, networkType, switchToLayer } = useBlockchain();

  const [artworkTitle, setArtworkTitle] = useState<string>('');
  const [artworkDescription, setArtworkDescription] = useState<string>('');
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [originalPreviewUrl, setOriginalPreviewUrl] = useState<string | null>(null);
  const [compressedResult, setCompressedResult] = useState<CompressionResult | null>(null);
  const [isCompressing, setIsCompressing] = useState<boolean>(false);
  const [imageOrientation, setImageOrientation] = useState<'portrait' | 'landscape' | 'square' | null>(null);
  const [hasProfile, setHasProfile] = useState<boolean>(false);
  const [checkingProfile, setCheckingProfile] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const isTrulyConnected = isConnected && !!walletAddress;
  const [preferredFormat, setPreferredFormat] = useState<FormatType>('image/avif');

  // Check for profile when wallet is connected
  useEffect(() => {
    if (isTrulyConnected) {
      checkForProfile();
    }
  }, [isTrulyConnected, walletAddress]);

  // Function to check if user has a profile
  const checkForProfile = async () => {
    setCheckingProfile(true);
    try {
      const profileExists = await profileService.hasProfile();
      setHasProfile(profileExists);
      console.log("Profile check:", profileExists ? "User has a profile" : "User has no profile");
    } catch (error) {
      console.error("Error checking for profile:", error);
      setHasProfile(false);
    } finally {
      setCheckingProfile(false);
    }
  };

  // Updated useEffect to only revoke URLs without resetting userType
  useEffect(() => {
    return () => {
      if (originalPreviewUrl) revokePreviewUrl(originalPreviewUrl);
      if (compressedResult?.preview) revokePreviewUrl(compressedResult.preview);
    };
  }, [originalPreviewUrl, compressedResult]);

  const handleUserTypeSelection = (type: 'artist' | 'commissioner') => {
    setUserType(type);
  };

  const handleDisconnect = () => {
    if (window.ethereum && window.ethereum.removeAllListeners) {
      try {
        window.ethereum.removeAllListeners();
      } catch (err) {
        console.error("Failed to remove ethereum listeners:", err);
      }
    }
    localStorage.setItem('active_tab', 'registration');
    localStorage.setItem('wallet_disconnect_requested', 'true');
    window.location.reload();
  };

  useEffect(() => {
    if (localStorage.getItem('wallet_disconnect_requested') === 'true') {
      localStorage.removeItem('wallet_disconnect_requested');
      console.log("Wallet disconnected as requested");
      if (window.ethereum) {
        try {
          if (window.ethereum._state && window.ethereum._state.accounts) {
            window.ethereum._state.accounts = [];
          }
        } catch (err) {
          console.error("Error forcing wallet disconnect:", err);
        }
      }
    }
  }, []);

  const ConnectionBar = () => (
    <div className="connection-bar">
      {!isTrulyConnected ? (
        <>
          <div className="connection-status disconnected">
            <span className="status-icon"></span>
            <span className="status-text">Wallet Not Connected</span>
          </div>
          <button className="connect-wallet-button" onClick={connectWallet}>
            Connect Wallet
          </button>
          {isConnected && !walletAddress && (
            <div className="connection-error-message">
              <p>Connection detected but no wallet address available. Please try reconnecting.</p>
            </div>
          )}
        </>
      ) : (
        <>
          <div className="connection-status connected">
            <span className="status-icon"></span>
            <div className="connection-details">
              <span className="status-text">
                Connected to: <span className="network-name">
                  {networkType === 'arbitrum_testnet' ? 'L3 (Arbitrum Sepolia)' : networkType}
                </span>
              </span>
              <span className="wallet-address">
                {walletAddress ? `${walletAddress.substring(0, 6)}...${walletAddress.substring(walletAddress.length - 4)}` : 'Not connected'}
              </span>
            </div>
          </div>
          <button className="disconnect-wallet-button" onClick={handleDisconnect}>
            Disconnect
          </button>
        </>
      )}
    </div>
  );

  const CommissionerForm = () => (
    <div className="registration-form">
      <h3>Commissioner Registration</h3>
      <div className="form-instructions">
        <p>As a commissioner, you can request and fund new commissioned artworks.</p>
        {!isTrulyConnected && (
          <p className="connect-reminder">
            <span className="highlight">You can fill out the form now</span>, and connect your wallet when you're ready to register.
          </p>
        )}
      </div>
      <form>
        <div className="form-content">
          <div className="form-group">
            <label>Commissioner form coming soon...</label>
            <p>Fill out your details and register when you're ready.</p>
          </div>
        </div>
        <div className="form-footer">
          <button type="button" className="form-back-button" onClick={() => setUserType(null)}>
            Back
          </button>
          <button
            type="button"
            className="submit-button"
            onClick={() => {
              if (!isTrulyConnected) {
                alert("Please connect your wallet to register as a commissioner");
                connectWallet();
              } else {
                alert("Commissioner registration would be processed here");
              }
            }}
          >
            Register as Commissioner
          </button>
        </div>
      </form>
    </div>
  );

  return (
    <div className="nft-registration-container">
      <h2>Commission Art</h2>
      <ConnectionBar />
      {userType === null ? (
        <div className="user-type-selection">
          <p className="selection-prompt">I'm a:</p>
          <div className="selection-buttons">
            <button className="selection-button artist-button" onClick={() => handleUserTypeSelection('artist')}>
              Artist
            </button>
            <button className="selection-button commissioner-button" onClick={() => handleUserTypeSelection('commissioner')}>
              Commissioner
            </button>
          </div>
        </div>
      ) : userType === 'artist' ? (
        <ArtistForm
          artworkTitle={artworkTitle}
          setArtworkTitle={setArtworkTitle}
          artworkDescription={artworkDescription}
          setArtworkDescription={setArtworkDescription}
          selectedImage={selectedImage}
          setSelectedImage={setSelectedImage}
          originalPreviewUrl={originalPreviewUrl}
          setOriginalPreviewUrl={setOriginalPreviewUrl}
          compressedResult={compressedResult}
          setCompressedResult={setCompressedResult}
          isCompressing={isCompressing}
          setIsCompressing={setIsCompressing}
          imageOrientation={imageOrientation}
          setImageOrientation={setImageOrientation}
          fileInputRef={fileInputRef}
          isTrulyConnected={isTrulyConnected}
          connectWallet={connectWallet}
          walletAddress={walletAddress}
          networkType={networkType}
          switchToLayer={switchToLayer}
          hasProfile={hasProfile}
          preferredFormat={preferredFormat}
          setPreferredFormat={setPreferredFormat}
          onBack={() => setUserType(null)}
        />
      ) : (
        <CommissionerForm />
      )}
    </div>
  );
};

export default NFTRegistration;