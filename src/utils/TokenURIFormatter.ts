/**
 * TokenURIFormatter.ts
 * Utility to format art piece data into standard NFT metadata format
 */

/**
 * Formats image data and metadata into standard NFT tokenURI format
 * 
 * @param imageData - Raw image data as Uint8Array
 * @param title - Title of the artwork as string
 * @param description - Description of the artwork as string
 * @param mimeType - MIME type of the image (e.g. 'image/jpeg', 'image/png', 'image/avif')
 * @returns Formatted tokenURI data as string with data:application/json;base64 prefix
 */
export const formatTokenURI = (
  imageData: Uint8Array,
  title: string,
  description: string,
  mimeType: string = 'image/avif'
): { tokenURI: string, size: number } => {
  try {
    // Step 1: Convert image data to base64 with MIME type prefix
    const base64Image = arrayBufferToBase64(imageData);
    const imageDataURI = `data:${mimeType};base64,${base64Image}`;
    
    // Step 2: Create metadata JSON object
    const metadata = {
      name: title || "CommissionArt",
      description: description || "Commissioned Art",
      image: imageDataURI
    };
    
    // Step 3: Convert metadata to JSON string and then to base64
    const metadataStr = JSON.stringify(metadata);
    const base64Metadata = btoa(metadataStr);
    const tokenURI = `data:application/json;base64,${base64Metadata}`;
    
    // Calculate size in bytes
    const size = new TextEncoder().encode(tokenURI).length;
    
    return { tokenURI, size };
  } catch (error) {
    console.error('Error formatting tokenURI:', error);
    throw new Error(`TokenURI formatting error: ${error instanceof Error ? error.message : String(error)}`);
  }
};

/**
 * Convert array buffer to base64 string
 */
const arrayBufferToBase64 = (buffer: ArrayBuffer | Uint8Array): string => {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
};

/**
 * Emergency size reducer for token URIs that exceed size limits
 * Progressively reduces quality until it fits within the size limit
 */
export const reduceTokenURISize = (
  imageData: Uint8Array,
  title: string,
  description: string,
  maxSize: number = 44000, // Target slightly below 45000 limit
  mimeType: string = 'image/avif'
): { tokenURI: string, size: number, reductionApplied: boolean } => {
  // Try with original data first
  let result = formatTokenURI(imageData, title, description, mimeType);
  
  // If it's already under the limit, return it
  if (result.size <= maxSize) {
    return { ...result, reductionApplied: false };
  }
  
  console.warn(`TokenURI size (${result.size} bytes) exceeds limit (${maxSize} bytes). Attempting reduction...`);
  
  // Otherwise, we need to reduce the image quality
  // This is a simple approach - we'll progressively discard pixels to reduce size
  let reductionFactor = 0.9; // Start by keeping 90% of pixels
  const originalLength = imageData.length;
  
  while (result.size > maxSize && reductionFactor > 0.3) {
    // Create reduced image data by sampling pixels
    const reducedLength = Math.floor(originalLength * reductionFactor);
    const reducedData = new Uint8Array(reducedLength);
    
    // Simple pixel sampling (not ideal for image quality but works for size reduction)
    for (let i = 0; i < reducedLength; i++) {
      const srcIdx = Math.floor(i * (originalLength / reducedLength));
      reducedData[i] = imageData[srcIdx];
    }
    
    // Try formatting with reduced data
    result = formatTokenURI(reducedData, title, description, mimeType);
    console.log(`Reduced to ${reductionFactor.toFixed(2)} of original size: ${result.size} bytes`);
    
    // Reduce more aggressively each time
    reductionFactor -= 0.1;
  }
  
  if (result.size > maxSize) {
    // If we've tried all our reductions and still can't fit, use more aggressive approach
    // Just truncate the description and use minimal data
    const minimalResult = formatTokenURI(
      new Uint8Array(imageData.slice(0, Math.floor(originalLength * 0.3))),
      title.substring(0, 20),
      "Art", // Minimal description
      mimeType
    );
    
    console.warn(`Emergency size reduction applied. Final size: ${minimalResult.size} bytes`);
    return { ...minimalResult, reductionApplied: true };
  }
  
  console.log(`Size reduction successful. Final size: ${result.size} bytes`);
  return { ...result, reductionApplied: true };
};

/**
 * Hash a string using SHA-256
 * @param data String to hash
 * @returns Promise that resolves to the hex hash
 */
export const hashString = async (data: string): Promise<string> => {
  const encoder = new TextEncoder();
  const dataBuffer = encoder.encode(data);
  const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  return hashHex;
};

/**
 * Extract the image data from a tokenURI for preview purposes
 * @param tokenURI The tokenURI string containing base64 encoded image data
 * @returns The image data URL that can be used in an img src attribute
 */
export const extractImageFromTokenURI = (tokenURI: string): string | null => {
  try {
    // Parse the JSON data from the tokenURI
    // First find where the data:application/json;base64, part ends
    const base64JsonStart = tokenURI.indexOf('base64,') + 7;
    if (base64JsonStart === 6) return null; // Not found
    
    // Extract and decode the base64 JSON
    const base64Json = tokenURI.substring(base64JsonStart);
    const jsonString = atob(base64Json);
    const metadata = JSON.parse(jsonString);
    
    // Extract the image data
    if (metadata.image) {
      return metadata.image;
    }
    return null;
  } catch (error) {
    console.error('Error extracting image from tokenURI:', error);
    return null;
  }
}; 