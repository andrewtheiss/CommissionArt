export interface CompressionResult {
  success: boolean;
  originalSize: number;
  compressedSize: number;
  dimensions: { width: number; height: number };
  error?: string;
  targetReached: boolean;
  format: string;
  blob: Blob | null;
  preview: string | null;
}

export type FormatType = 'image/avif' | 'image/webp' | 'image/jpeg';

export interface FormatOption {
  type: FormatType;
  name: string;
  extension: string;
  qualityFactor: number; // Higher means we prefer this format for quality
}

// Prioritize AVIF and WebP over JPEG by assigning quality factors
export const formatOptions: FormatOption[] = [
  { type: 'image/avif', name: 'AVIF', extension: 'avif', qualityFactor: 10 },
  { type: 'image/webp', name: 'WebP', extension: 'webp', qualityFactor: 7 },
  { type: 'image/jpeg', name: 'JPEG', extension: 'jpg', qualityFactor: 4 }
];

// Get formats in priority order
export const getFormatsByPriority = (preferredFormat: FormatType = 'image/avif'): FormatType[] => {
  // Always put preferred format first
  const orderedFormats = [preferredFormat];
  
  // Then add remaining formats in order of qualityFactor
  const remainingFormats = formatOptions
    .filter(format => format.type !== preferredFormat)
    .sort((a, b) => b.qualityFactor - a.qualityFactor)
    .map(format => format.type);
    
  return [...orderedFormats, ...remainingFormats];
};

/**
 * Compresses an image with the specified format, dimensions, and target size
 * Optimized to get as close to the target size as possible while staying under
 */
export const compressImageWithFormat = async (
  img: HTMLImageElement, 
  width: number, 
  height: number, 
  format: FormatType, 
  targetSizeKB: number
): Promise<{blob: Blob | null, size: number, quality: number}> => {
  return new Promise((resolveFormat) => {
    // Create canvas and draw image
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    ctx?.drawImage(img, 0, 0, width, height);

    // Binary search to find optimal quality
    let low = 1;
    let high = 100;
    let optimalQuality = 1;
    let optimalBlob: Blob | null = null;
    let optimalSize = 0;
    
    // We want to get as close to the target as possible while staying under
    // This threshold represents how close we want to get (0.998 = 99.8% of target)
    const targetThreshold = 0.998; 

    const binarySearch = () => {
      // If our search range is very narrow or we've found a near-perfect match, stop
      if (low > high || (optimalSize > 0 && optimalSize > targetSizeKB * targetThreshold && optimalSize < targetSizeKB)) {
        console.log(`Optimized ${format} to ${optimalSize.toFixed(2)}KB (${(optimalSize/targetSizeKB*100).toFixed(1)}% of target) with quality ${optimalQuality}`);
        resolveFormat({
          blob: optimalBlob,
          size: optimalSize,
          quality: optimalQuality
        });
        return;
      }

      const mid = Math.floor((low + high) / 2);
      
      canvas.toBlob(
        (blob) => {
          if (!blob) {
            high = mid - 1;
            binarySearch();
            return;
          }

          const sizeKB = blob.size / 1024;
          const closenessRatio = sizeKB / targetSizeKB;
          
          if (sizeKB <= targetSizeKB) {
            // Save this as our best result so far if it's closer to target
            if (sizeKB > optimalSize || optimalBlob === null) {
              optimalBlob = blob;
              optimalQuality = mid;
              optimalSize = sizeKB;
            }
            
            // If we're very close to the target (within 99.8%), we can stop
            if (closenessRatio > targetThreshold) {
              console.log(`Found near-optimal size: ${sizeKB.toFixed(2)}KB (${(closenessRatio*100).toFixed(1)}% of target)`);
              resolveFormat({
                blob,
                size: sizeKB,
                quality: mid
              });
              return;
            }
            
            // Try higher quality to get closer to target
            low = mid + 1;
          } else {
            // We're over target, so try lower quality
            high = mid - 1;
          }
          
          binarySearch();
        },
        format,
        mid / 100
      );
    };

    binarySearch();
  });
};

/**
 * Compresses an image file to get as close to the target size as possible while staying under
 * Prioritizes higher quality formats (AVIF, WebP) over lower quality ones (JPEG)
 * Default target size is 43KB to ensure staying safely under the 45,000 bytes limit
 */
export const compressImage = async (
  file: File, 
  preferredFormat: FormatType = 'image/avif', 
  maxDimension = 1000, 
  targetSizeKB = 43
): Promise<CompressionResult> => {
  return new Promise((resolve) => {
    const img = new Image();
    const reader = new FileReader();

    reader.onload = (e) => {
      img.src = e.target?.result as string;
    };

    img.onload = async () => {
      // Calculate initial dimensions while maintaining aspect ratio
      let currentWidth = img.width;
      let currentHeight = img.height;

      if (currentWidth > maxDimension || currentHeight > maxDimension) {
        if (currentWidth > currentHeight) {
          currentHeight = Math.round((currentHeight * maxDimension) / currentWidth);
          currentWidth = maxDimension;
        } else {
          currentWidth = Math.round((currentWidth * maxDimension) / currentHeight);
          currentHeight = maxDimension;
        }
      }

      // Try different formats to find the one that gives us the best quality
      // while staying under the target size
      let bestResult: {
        blob: Blob;
        size: number;
        width: number;
        height: number;
        format: FormatType;
        targetReached: boolean;
        closenessRatio: number; // How close to target (higher is better)
        formatQuality: number;  // Quality factor of the format
      } | null = null;

      console.log(`Targeting compression size of ${targetSizeKB.toFixed(2)}KB`);
      console.log(`Starting compression with dimensions: ${currentWidth}x${currentHeight}`);

      // Get formats in priority order (AVIF first, then WebP, etc.)
      const formatPriority = getFormatsByPriority(preferredFormat);
      
      // Try each format in order of priority
      for (const format of formatPriority) {
        const formatInfo = formatOptions.find(f => f.type === format);
        if (!formatInfo) continue;
        
        console.log(`Trying ${formatInfo.name} format (quality factor: ${formatInfo.qualityFactor})...`);
        
        const result = await compressImageWithFormat(img, currentWidth, currentHeight, format, targetSizeKB);
        
        if (result.blob) {
          const isTargetReached = result.size <= targetSizeKB;
          const closenessRatio = result.size / targetSizeKB;
          
          console.log(`${formatInfo.name} result: ${result.size.toFixed(2)}KB, ${isTargetReached ? 'under' : 'over'} target (${(closenessRatio*100).toFixed(1)}%)`);
          
          // Calculate a composite score that balances size closeness and format quality
          // This helps us prefer high-quality formats when sizes are similar
          const compositeScore = isTargetReached ? 
            (closenessRatio * 0.7) + ((formatInfo.qualityFactor / 10) * 0.3) : 0;
            
          console.log(`${formatInfo.name} composite score: ${compositeScore.toFixed(3)} (size weight: 70%, quality weight: 30%)`);
          
          // Update best result if this is better by our composite scoring
          if (!bestResult || 
              (isTargetReached && !bestResult.targetReached) || 
              (isTargetReached && bestResult.targetReached && compositeScore > 
                ((bestResult.closenessRatio * 0.7) + ((bestResult.formatQuality / 10) * 0.3))
              )) {
            bestResult = {
              blob: result.blob,
              size: result.size,
              width: currentWidth,
              height: currentHeight,
              format: format,
              targetReached: isTargetReached,
              closenessRatio: closenessRatio,
              formatQuality: formatInfo.qualityFactor
            };
            
            // If we have an excellent result with AVIF (high quality format + close to target),
            // we can stop early as this is likely the best option
            if (isTargetReached && format === 'image/avif' && closenessRatio > 0.97) {
              console.log(`Found excellent AVIF result: ${result.size.toFixed(2)}KB (${(closenessRatio*100).toFixed(1)}% of target). Stopping early.`);
              break;
            }
          }
        }
      }

      // If we're not close enough to target size with any format,
      // try fine-tuning dimensions while keeping our format preference
      if (bestResult && bestResult.targetReached && bestResult.closenessRatio < 0.97) {
        console.log(`Best result so far is ${bestResult.size.toFixed(2)}KB with ${bestResult.format} (${(bestResult.closenessRatio*100).toFixed(1)}% of target)`);
        console.log(`Trying dimension adjustments to get closer to target...`);
        
        // Try slightly increasing dimensions to get closer to target if we're under
        let scaleFactor = 1.05; // Start with 5% increase
        let attemptCount = 0;
        const maxAttempts = 5;
        
        while (attemptCount < maxAttempts && bestResult.closenessRatio < 0.97) {
          const scaleWidth = Math.min(Math.floor(currentWidth * scaleFactor), maxDimension);
          const scaleHeight = Math.min(Math.floor(currentHeight * scaleFactor), maxDimension);
          
          // Don't scale beyond max dimension
          if (scaleWidth === currentWidth && scaleHeight === currentHeight) {
            break;
          }
          
          console.log(`Trying increased dimensions ${scaleWidth}x${scaleHeight} with ${bestResult.format}`);
          
          const scaledResult = await compressImageWithFormat(
            img, 
            scaleWidth, 
            scaleHeight, 
            bestResult.format, 
            targetSizeKB
          );
          
          if (scaledResult.blob) {
            const scaledTargetReached = scaledResult.size <= targetSizeKB;
            const scaledClosenessRatio = scaledResult.size / targetSizeKB;
            
            console.log(`Scaled result: ${scaledResult.size.toFixed(2)}KB (${(scaledClosenessRatio*100).toFixed(1)}% of target)`);
            
            // Update best result if this is better
            if (scaledTargetReached && scaledClosenessRatio > bestResult.closenessRatio) {
              bestResult = {
                blob: scaledResult.blob,
                size: scaledResult.size,
                width: scaleWidth,
                height: scaleHeight,
                format: bestResult.format,
                targetReached: scaledTargetReached,
                closenessRatio: scaledClosenessRatio,
                formatQuality: bestResult.formatQuality
              };
              
              // If we're within 97% of target, we're done
              if (scaledClosenessRatio > 0.97) {
                console.log(`Excellent result after scaling: ${scaledResult.size.toFixed(2)}KB (${(scaledClosenessRatio*100).toFixed(1)}% of target)`);
                break;
              }
            }
          }
          
          // Reduce the scaling factor for next attempt
          scaleFactor = 1 + (scaleFactor - 1) * 0.5;
          attemptCount++;
        }
      }

      // Handle the case where all formats are over the target size
      if (!bestResult || !bestResult.targetReached) {
        console.log("All formats exceeded target size, reducing dimensions...");
        
        // Start with original dimensions and reduce until we find a size that works
        let scaleWidth = currentWidth;
        let scaleHeight = currentHeight;
        let reductionFactor = 0.9; // Start with 10% reduction
        let attemptCount = 0;
        const maxAttempts = 8;
        
        while (attemptCount < maxAttempts) {
          scaleWidth = Math.floor(scaleWidth * reductionFactor);
          scaleHeight = Math.floor(scaleHeight * reductionFactor);
          attemptCount++;
          
          // Stop if dimensions become too small
          if (scaleWidth < 50 || scaleHeight < 50) {
            break;
          }
          
          console.log(`Trying reduced dimensions ${scaleWidth}x${scaleHeight}`);
          
          // Try formats in priority order with reduced dimensions
          let foundUnderTarget = false;
          
          for (const format of getFormatsByPriority(preferredFormat)) {
            const formatInfo = formatOptions.find(f => f.type === format);
            if (!formatInfo) continue;
            
            console.log(`Trying ${formatInfo.name} with reduced dimensions...`);
            
            const reducedResult = await compressImageWithFormat(
              img, 
              scaleWidth, 
              scaleHeight, 
              format, 
              targetSizeKB
            );
            
            if (reducedResult.blob) {
              const reducedTargetReached = reducedResult.size <= targetSizeKB;
              const reducedClosenessRatio = reducedResult.size / targetSizeKB;
              
              console.log(`Reduced ${formatInfo.name} result: ${reducedResult.size.toFixed(2)}KB (${(reducedClosenessRatio*100).toFixed(1)}% of target)`);
              
              if (reducedTargetReached) {
                foundUnderTarget = true;
                
                // Calculate composite score for this result
                const compositeScore = (reducedClosenessRatio * 0.7) + ((formatInfo.qualityFactor / 10) * 0.3);
                
                // Update best result if this is better by our composite scoring
                const bestScore = bestResult && bestResult.targetReached ? 
                  (bestResult.closenessRatio * 0.7) + ((bestResult.formatQuality / 10) * 0.3) : 0;
                  
                if (!bestResult || !bestResult.targetReached || compositeScore > bestScore) {
                  bestResult = {
                    blob: reducedResult.blob,
                    size: reducedResult.size,
                    width: scaleWidth,
                    height: scaleHeight,
                    format: format,
                    targetReached: true,
                    closenessRatio: reducedClosenessRatio,
                    formatQuality: formatInfo.qualityFactor
                  };
                  
                  // If we have a good result with AVIF or WebP, we can stop trying other formats
                  // but continue with dimension reduction in case we can get a better result
                  if ((format === 'image/avif' || format === 'image/webp') && reducedClosenessRatio > 0.95) {
                    break;
                  }
                }
              }
            }
          }
          
          // If we found at least one high-quality format (AVIF/WebP) under target
          // with a good closeness ratio, we can stop reducing dimensions
          if (foundUnderTarget && bestResult && 
              (bestResult.format === 'image/avif' || bestResult.format === 'image/webp') && 
              bestResult.closenessRatio > 0.97) {
            console.log(`Found excellent result with ${bestResult.format}: stopping dimension reduction`);
            break;
          }
          
          // Make reduction more aggressive after a few attempts
          if (attemptCount > 3) {
            reductionFactor = 0.8;
          }
        }
      }
      
      // Use the best result we found
      if (bestResult && bestResult.targetReached) {
        // Get format extension from our options
        const formatInfo = formatOptions.find(f => f.type === bestResult?.format);
        
        // Create preview URL from the blob
        const previewUrl = URL.createObjectURL(bestResult.blob);
        
        // Check if the blob size is under 45000 bytes (contract limit)
        if (bestResult.blob.size >= 45000) {
          console.warn(`Final image size (${bestResult.blob.size} bytes) exceeds the 45,000 bytes contract limit.`);
          
          // Attempt emergency dimension reduction
          console.log("Performing emergency dimension reduction to fit within byte limit");
          const emergencyWidth = Math.floor(bestResult.width * 0.9);
          const emergencyHeight = Math.floor(bestResult.height * 0.9);
          
          // Emergency canvas resize
          const canvas = document.createElement('canvas');
          canvas.width = emergencyWidth;
          canvas.height = emergencyHeight;
          const ctx = canvas.getContext('2d');
          ctx?.drawImage(img, 0, 0, emergencyWidth, emergencyHeight);
          
          // Use a lower quality setting
          const emergencyQuality = 0.7;
          
          // Convert to blob with lower quality
          canvas.toBlob(
            (reducedBlob) => {
              if (reducedBlob && reducedBlob.size < 45000) {
                console.log(`Emergency reduction successful: ${reducedBlob.size} bytes`);
                const reducedPreviewUrl = URL.createObjectURL(reducedBlob);
                
                resolve({
                  success: true,
                  originalSize: file.size / 1024,
                  compressedSize: reducedBlob.size / 1024,
                  dimensions: { width: emergencyWidth, height: emergencyHeight },
                  targetReached: true,
                  format: formatInfo?.name || bestResult.format,
                  blob: reducedBlob,
                  preview: reducedPreviewUrl
                });
              } else {
                // If emergency reduction failed, return the original result with a warning
                console.error("Emergency reduction failed. Image may be too large for the contract.");
                resolve({
                  success: true,
                  originalSize: file.size / 1024,
                  compressedSize: bestResult.size,
                  dimensions: { width: bestResult.width, height: bestResult.height },
                  targetReached: false,
                  format: formatInfo?.name || bestResult.format,
                  blob: bestResult.blob,
                  preview: previewUrl,
                  error: "Image exceeds 45,000 bytes contract limit even after compression."
                });
              }
            },
            bestResult.format,
            emergencyQuality
          );
          return;
        }
        
        console.log(`Final result: ${formatInfo?.name || bestResult.format} at ${bestResult.size.toFixed(2)}KB (${(bestResult.closenessRatio*100).toFixed(1)}% of target), ${bestResult.blob.size} bytes`);
        
        resolve({
          success: true,
          originalSize: file.size / 1024,
          compressedSize: bestResult.size,
          dimensions: { width: bestResult.width, height: bestResult.height },
          targetReached: true,
          format: formatInfo?.name || bestResult.format,
          blob: bestResult.blob,
          preview: previewUrl
        });
      } else if (bestResult) {
        // We have a result but it's over the target size
        const formatInfo = formatOptions.find(f => f.type === bestResult.format);
        const previewUrl = URL.createObjectURL(bestResult.blob);
        
        console.warn(`Could not reach target size of ${targetSizeKB}KB. Best result: ${bestResult.size.toFixed(2)}KB with ${formatInfo?.name || bestResult.format}`);
        
        resolve({
          success: true,
          originalSize: file.size / 1024,
          compressedSize: bestResult.size,
          dimensions: { width: bestResult.width, height: bestResult.height },
          targetReached: false,
          format: formatInfo?.name || bestResult.format,
          blob: bestResult.blob,
          preview: previewUrl
        });
      } else {
        // This should never happen as long as we have a valid image
        resolve({
          success: false,
          originalSize: file.size / 1024,
          compressedSize: 0,
          dimensions: { width: 0, height: 0 },
          error: 'Could not compress image',
          targetReached: false,
          format: 'None',
          blob: null,
          preview: null
        });
      }
    };

    reader.readAsDataURL(file);
  });
};

/**
 * Determines if an image is portrait, landscape, or square based on its dimensions
 */
export const getImageOrientation = (width: number, height: number): 'portrait' | 'landscape' | 'square' => {
  if (width > height) {
    return 'landscape';
  } else if (height > width) {
    return 'portrait';
  } else {
    return 'square';
  }
};

/**
 * Creates a data URL from a blob
 */
export const createPreviewUrl = (blob: Blob): string => {
  return URL.createObjectURL(blob);
};

/**
 * Revokes a data URL to free up memory
 */
export const revokePreviewUrl = (url: string): void => {
  URL.revokeObjectURL(url);
}; 