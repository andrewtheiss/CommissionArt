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
import NFTPreviewModal from './NFTPreviewModal';

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
      setIsCompressing(true); // Reuse the compressing state to show loading

      // Get the image data directly from the preview URL instead of converting to bytes
      // This prevents any format conversion issues (AVIF to WebP)
      if (!compressedResult.preview) {
        throw new Error("Compressed image preview is not available");
      }
      
      const titleStr = artworkTitle.trim();
      const descriptionStr = artworkDescription.trim();
      
      // Log the original compressed image format and data
      console.log(`Using original compressed image in format: ${compressedResult.format}`);
      console.log(`Original image data URL starts with: ${compressedResult.preview.substring(0, 100)}...`);
      
      // Extract the MIME type from the data URL
      const mimeTypeMatch = compressedResult.preview.match(/^data:(image\/[^;]+);base64,/);
      const mimeType = mimeTypeMatch ? mimeTypeMatch[1] : 'image/avif';
      console.log(`Detected MIME type: ${mimeType}`);
      
      // Create a metadata object directly without converting to bytes first
      const metadata = {
        name: titleStr,
        description: descriptionStr,
        image: compressedResult.preview // Use the original data URL directly
      };
      
      // Convert to JSON and then to base64
      const metadataStr = JSON.stringify(metadata);
      let base64Metadata = '';
      try {
        base64Metadata = btoa(metadataStr);
      } catch (b64Error) {
        console.error("Error encoding metadata to base64:", b64Error);
        throw new Error("Failed to encode metadata to base64");
      }
      
      // Create the tokenURI directly
      const tokenURI = `data:application/json;base64,${base64Metadata}`;
      const tokenURISize = new TextEncoder().encode(tokenURI).length;
      
      // Check character count - this is what matters for the contract limit!
      const totalCharCount = tokenURI.length;
      console.log(`TokenURI character count: ${totalCharCount} chars`);

      // The actual limit is 45000 characters, not bytes
      const maxCharCount = 45000; 
      const maxSize = 44000; // Target slightly below 45,000 byte limit
      
      if (totalCharCount > maxCharCount) {
        console.warn(`TokenURI size (${totalCharCount} characters) exceeds limit (${maxCharCount} characters).`);
        console.warn("Will need to use a more aggressive reduction method.");
        
        // Try to create a reduced version directly by decreasing the image quality
        try {
          // First try to extract width and height from the original data URL
          const imgForReduction = document.createElement('img');
          await new Promise<void>((resolve, reject) => {
            imgForReduction.onload = () => resolve();
            imgForReduction.onerror = () => reject(new Error('Failed to load image for reduction'));
            imgForReduction.src = compressedResult.preview || '';
          });
          
          // Create a temporary image to draw from
          const tempImg = document.createElement('img');
          await new Promise<void>((resolve, reject) => {
            tempImg.onload = () => resolve();
            tempImg.onerror = () => reject(new Error('Failed to load image for emergency reduction'));
            tempImg.src = compressedResult.preview || '';
          });
          
          // Calculate smaller dimensions - target ~75% of original
          const width = Math.floor(imgForReduction.width * 0.75);
          const height = Math.floor(imgForReduction.height * 0.75);
          
          // Create a canvas with reduced dimensions
          const canvas = document.createElement('canvas');
          canvas.width = width;
          canvas.height = height;
          const ctx = canvas.getContext('2d');
          ctx?.drawImage(imgForReduction, 0, 0, width, height);
          
          // Get mime type
          const mimeType = mimeTypeMatch ? mimeTypeMatch[1] : 'image/avif';
          
          // Try a lower quality setting
          let quality = 0.5; // Start with 50% quality
          let reducedDataUrl;
          let reducedTokenURI;
          let reducedCharCount;
          
          do {
            // Create data URL with current quality
            reducedDataUrl = canvas.toDataURL(mimeType, quality);
            
            // Create new metadata with reduced image
            const reducedMetadata = {
              name: titleStr,
              description: descriptionStr,
              image: reducedDataUrl
            };
            
            // Convert to JSON and base64
            const reducedMetadataStr = JSON.stringify(reducedMetadata);
            const reducedBase64Metadata = btoa(reducedMetadataStr);
            
            // Create tokenURI
            reducedTokenURI = `data:application/json;base64,${reducedBase64Metadata}`;
            reducedCharCount = reducedTokenURI.length;
            
            console.log(`Reduced TokenURI: ${reducedCharCount} chars with quality ${quality}`);
            
            // If still over limit, reduce quality more
            if (reducedCharCount > maxCharCount) {
              quality -= 0.1;
              console.log(`Still over limit. Reducing quality to ${quality}`);
            }
            
          } while (reducedCharCount > maxCharCount && quality > 0.2);
          
          // If we found a working quality level
          if (reducedCharCount <= maxCharCount) {
            console.log(`Found working quality level: ${quality.toFixed(2)}`);
            console.log(`Reduced image dimensions: ${width}x${height}`);
            console.log(`Final char count: ${reducedCharCount}`);
            
            const tokenURIResult = {
              tokenURI: reducedTokenURI,
              size: reducedTokenURI.length
            };
            
            // Continue with this tokenURI
            handleContinueWithTokenURI(tokenURIResult, titleStr, descriptionStr, mimeType);
            return;
          }
        } catch (reductionError) {
          console.error("Error with direct reduction:", reductionError);
          console.log("Falling back to byte-based reduction method...");
        }
        
        // Fall back to the regular process with imageData bytes if needed
        if (!compressedResult.blob) {
          throw new Error("Compressed image blob is not available for fallback");
        }
        
        // Convert the image to bytes for the fallback method
        const imageDataArray = new Uint8Array(await compressedResult.blob.arrayBuffer());
        
        // Format the token URI with potential size reduction if needed
        const fallbackResult = reduceTokenURISize(
          imageDataArray,
          titleStr,
          descriptionStr,
          maxSize,
          mimeType // Pass the correct MIME type
        );
        
        console.log(`Used fallback method. Final size: ${fallbackResult.size} bytes`);
        console.log(`Final char count: ${fallbackResult.tokenURI.length} characters`);
        console.log(`Reduction applied: ${fallbackResult.reductionApplied}`);
        
        // Check character count again to be absolutely sure
        if (fallbackResult.tokenURI.length > maxCharCount) {
          console.error(`CRITICAL: Even after reduction, tokenURI is still ${fallbackResult.tokenURI.length} chars (max: ${maxCharCount})`);
          
          try {
            // Emergency measure: truncate description and use minimum quality JPEG
            const emergencyCanvas = document.createElement('canvas');
            emergencyCanvas.width = Math.min(200, Math.floor(compressedResult.dimensions.width * 0.3));
            emergencyCanvas.height = Math.min(200, Math.floor(compressedResult.dimensions.height * 0.3));
            const emergencyCtx = emergencyCanvas.getContext('2d');
            
            // Create a temporary image to draw from
            const tempImg = document.createElement('img');
            await new Promise<void>((resolve, reject) => {
              tempImg.onload = () => resolve();
              tempImg.onerror = () => reject(new Error('Failed to load image for emergency reduction'));
              tempImg.src = compressedResult.preview || '';
            });
            
            emergencyCtx?.drawImage(tempImg, 0, 0, emergencyCanvas.width, emergencyCanvas.height);
            
            const emergencyDataUrl = emergencyCanvas.toDataURL('image/jpeg', 0.3);
            const emergencyMetadata = {
              name: titleStr.substring(0, 20), // Truncate title to 20 chars max
              description: descriptionStr.substring(0, 30), // Truncate description to 30 chars max
              image: emergencyDataUrl
            };
            
            // Convert to JSON and base64
            const emergencyMetadataStr = JSON.stringify(emergencyMetadata);
            const emergencyBase64 = btoa(emergencyMetadataStr);
            const emergencyTokenURI = `data:application/json;base64,${emergencyBase64}`;
            
            console.log(`Emergency tokenURI created with ${emergencyTokenURI.length} chars`);
            
            const emergencyResult = {
              tokenURI: emergencyTokenURI,
              size: new TextEncoder().encode(emergencyTokenURI).length
            };
            
            // Use emergency tokenURI
            handleContinueWithTokenURI(emergencyResult, titleStr, descriptionStr, 'image/jpeg');
          } catch (emergencyError) {
            console.error("Emergency reduction failed:", emergencyError);
            alert("Could not reduce image size enough for blockchain storage. Please try a smaller or simpler image.");
            setIsCompressing(false);
            return;
          }
        } else {
          // Update the tokenURI and size
          const tokenURIResult = {
            tokenURI: fallbackResult.tokenURI,
            size: fallbackResult.size
          };
          
          // Continue with this tokenURI
          handleContinueWithTokenURI(tokenURIResult, titleStr, descriptionStr, mimeType);
        }
      } else {
        // The direct method worked, continue with the tokenURI
        console.log(`Direct tokenURI creation successful: ${tokenURISize} bytes, ${totalCharCount} characters`);
        
        const tokenURIResult = {
          tokenURI: tokenURI,
          size: tokenURISize
        };
        
        // Continue with this tokenURI
        handleContinueWithTokenURI(tokenURIResult, titleStr, descriptionStr, mimeType);
      }
    } catch (error) {
      setIsCompressing(false);
      console.error("Error preparing artwork:", error);
      alert(`Error preparing artwork: ${error instanceof Error ? error.message : String(error)}`);
    }
  };
  
  // Helper function to continue the registration process with a valid tokenURI
  const handleContinueWithTokenURI = async (
    tokenURIResult: { tokenURI: string, size: number },
    titleStr: string,
    descriptionStr: string,
    mimeType: string
  ) => {
    try {
      // Log the tokenURI details
      console.log(`Formatted tokenURI:`);
      console.log(`- Size: ${tokenURIResult.size} bytes`);
      console.log(`- First 100 chars: ${tokenURIResult.tokenURI.substring(0, 100)}...`);
      
      // Output detailed tokenURI examination
      console.log(`TokenURI analysis:`);
      const base64Section = tokenURIResult.tokenURI.split(',')[1];
      if (base64Section) {
        console.log(`- Base64 section length: ${base64Section.length} chars`);
        try {
          // Try to decode and parse the JSON
          const decodedJSON = atob(base64Section);
          console.log(`- Decoded JSON first 100 chars: ${decodedJSON.substring(0, 100)}...`);
          
          try {
            const parsedJSON = JSON.parse(decodedJSON);
            // Log the image data if it exists
            if (parsedJSON.image) {
              console.log(`- Image data in tokenURI exists: ${typeof parsedJSON.image === 'string'}`);
              console.log(`- Image data first 100 chars: ${parsedJSON.image.substring(0, 100)}...`);
              
              // Also check if it's a valid image data URL
              if (parsedJSON.image.startsWith('data:image/')) {
                console.log(`- Image appears to be a valid data URL`);
                const imgBase64 = parsedJSON.image.split(',')[1];
                if (imgBase64) {
                  console.log(`- Image base64 length: ${imgBase64.length} chars (approx ${Math.round(imgBase64.length * 0.75 / 1024)} KB raw)`);
                }
              } else {
                console.warn(`- Image data doesn't start with data:image/ - may be invalid`);
              }
            } else {
              console.warn(`- No image field found in tokenURI JSON`);
            }
          } catch (jsonErr) {
            console.error(`- Error parsing JSON from tokenURI: ${jsonErr}`);
          }
        } catch (b64Err) {
          console.error(`- Error decoding base64 from tokenURI: ${b64Err}`);
        }
      }
      
      // For hash comparison, we need to create a similar structure as before
      const imageDataArray = compressedResult?.blob ? 
        new Uint8Array(await compressedResult.blob.arrayBuffer()) : 
        new Uint8Array(0);
      
      // Use the improved hash comparison function
      const hashResult = await createComparisonHashes(
        {
          title: titleStr,
          description: descriptionStr, 
          image: imageDataArray
        },
        tokenURIResult.tokenURI
      );
      
      console.log(`Hash comparison result:`, hashResult);
      
      // Extract the image data for preview
      const previewImageUrl = extractImageFromTokenURI(tokenURIResult.tokenURI);
      console.log(`Preview image extracted: ${previewImageUrl ? 'Yes' : 'No'}`);
      console.log(`Preview image URL starts with: ${previewImageUrl ? previewImageUrl.substring(0, 50) + '...' : 'None'}`);
      
      // Log the first part of the tokenURI to check its format
      console.log(`TokenURI first 100 chars: ${tokenURIResult.tokenURI.substring(0, 100)}...`);
      
      // IMPORTANT: Always use the original compressed preview for the modal
      // Do NOT use the extracted image from tokenURI as it may be corrupted
      const modalImageUrl = compressedResult && compressedResult.preview ? compressedResult.preview : null;
      console.log(`Using original compressed preview URL: ${modalImageUrl ? modalImageUrl.substring(0, 50) + '...' : 'None'}`);
      
      if (!modalImageUrl) {
        console.error("No valid image URL available for modal preview. This should never happen.");
        // Try to create a new preview URL if needed
        if (compressedResult?.blob) {
          const emergencyUrl = URL.createObjectURL(compressedResult.blob);
          console.log("Created emergency preview URL from blob");
          
          // Show preview modal before proceeding
          setPreviewModalData({
            show: true,
            imageDataUrl: emergencyUrl, // Use emergency URL
            title: titleStr,
            description: descriptionStr,
            tokenURIHash: hashResult.tokenURIHash,
            originalHash: hashResult.originalHash,
            compressedSize: tokenURIResult.size / 1024,
            tokenURIString: tokenURIResult.tokenURI,
            hashesMatch: hashResult.match
          });
          
          setIsCompressing(false);
          return;
        }
      }
      
      // Show preview modal before proceeding
      setPreviewModalData({
        show: true,
        imageDataUrl: modalImageUrl, // Always use direct compressed preview
        title: titleStr,
        description: descriptionStr,
        tokenURIHash: hashResult.tokenURIHash,
        originalHash: hashResult.originalHash,
        compressedSize: tokenURIResult.size / 1024,
        tokenURIString: tokenURIResult.tokenURI,
        hashesMatch: hashResult.match
      });
      
      setIsCompressing(false);
    } catch (error) {
      setIsCompressing(false);
      console.error("Error in tokenURI handling:", error);
      alert(`Error preparing artwork metadata: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  // Update state for preview modal
  const [previewModalData, setPreviewModalData] = useState<{
    show: boolean;
    imageDataUrl: string | null;
    title: string;
    description: string;
    tokenURIHash: string;
    originalHash: string;
    compressedSize: number;
    tokenURIString: string;
    hashesMatch?: boolean;
  }>({
    show: false,
    imageDataUrl: null,
    title: '',
    description: '',
    tokenURIHash: '',
    originalHash: '',
    compressedSize: 0,
    tokenURIString: '',
    hashesMatch: true
  });

  // Function to handle modal close and proceed with registration
  const handleModalClose = () => {
    setPreviewModalData(prev => ({ ...prev, show: false }));
  };

  // Function to proceed with registration after preview
  const proceedWithRegistration = async () => {
    if (!isTrulyConnected) {
      alert("Please connect your wallet to register your artwork");
      connectWallet();
      return;
    }

    try {
      // Show loading state
      setIsCompressing(true);

      // First, make sure we're on the AnimeChain L3 network
      if (networkType !== 'animechain') {
        await switchToLayer('l3', 'mainnet');
      }

      // Get the signer for transaction
      const signer = await ethersService.getSigner();
      if (!signer) {
        throw new Error("Failed to get signer");
      }
      
      // Use the tokenURI string from preview modal data
      const tokenURIString = previewModalData.tokenURIString;
      const titleStr = previewModalData.title;
      const descriptionStr = previewModalData.description;
      
      // Get the commissionHub address from the config
      const commissionHubAddress = contractConfig.networks.mainnet.commissionHub.address || ethers.ZeroAddress;

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
        
        // Call the profile's createArtPiece function with the tokenURI string
        const tx = await profileContract.createArtPiece(
          artPieceAddress,
          tokenURIString, // Use tokenURI string instead of bytes
          titleStr,       // Use title string
          descriptionStr, // Use description string directly instead of bytes
          true, // is artist
          ethers.ZeroAddress, // no other party
          commissionHubAddress,
          false // not AI generated
        );
        
        // Wait for the transaction to be mined
        const receipt = await tx.wait();
        
        setIsCompressing(false);
        alert(`Artwork registered successfully via Profile!`);
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
        
        try {
          // There are two options:
          // 1. Create a profile and then register the artwork through the profile
          // 2. Use a direct contract deployment 
          
          // For simplicity and better user experience, let's create a profile for them
          // and register the artwork at the same time
          
          // Get the ProfileHub contract
          const profileHubAddress = contractConfig.networks.mainnet.profileHub.address;
          const profileHubAbi = abiLoader.loadABI('ProfileHub');
          
          if (!profileHubAddress || !profileHubAbi) {
            throw new Error("ProfileHub configuration not found");
          }
          
          const profileHub = new ethers.Contract(profileHubAddress, profileHubAbi, signer);
          
          // Get the template ArtPiece address
          const artPieceTemplateAddress = contractConfig.networks.mainnet.artPiece.address;
          if (!artPieceTemplateAddress) {
            throw new Error("ArtPiece template address not configured");
          }
          
          console.log("Creating profile and registering artwork in one transaction...");
          
          // Create profile and register artwork with tokenURI string
          const tx = await profileHub.createNewArtPieceAndRegisterProfile(
            artPieceTemplateAddress,
            tokenURIString, // Use tokenURI string instead of bytes
            titleStr,       // Use title string
            descriptionStr, // Use description string directly instead of bytes
            true, // is artist
            ethers.ZeroAddress, // no other party
            commissionHubAddress,
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
              const parsedLog = profileHub.interface.parseLog(log);
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
            tokenURISize: previewModalData.compressedSize,
            imageFormat: compressedResult?.format || preferredFormat,
            dimensions: compressedResult?.dimensions || { width: 0, height: 0 },
          });
          
        } catch (error) {
          console.error("Error deploying ArtPiece contract:", error);
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
        
        {/* Add the preview modal */}
        <NFTPreviewModal
          show={previewModalData.show}
          onClose={handleModalClose}
          imageDataUrl={previewModalData.imageDataUrl}
          title={previewModalData.title}
          description={previewModalData.description}
          tokenURIHash={previewModalData.tokenURIHash}
          originalHash={previewModalData.originalHash}
          compressedSize={previewModalData.compressedSize}
          onProceed={proceedWithRegistration}
          hashesMatch={previewModalData.hashesMatch}
          tokenURIString={previewModalData.tokenURIString}
        />
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