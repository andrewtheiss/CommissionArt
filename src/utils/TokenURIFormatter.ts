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
    // Validate inputs
    if (!imageData || imageData.byteLength === 0) {
      throw new Error("Invalid image data: empty or null");
    }
    
    if (!mimeType || !mimeType.startsWith('image/')) {
      console.warn(`Invalid or missing MIME type: ${mimeType}, defaulting to image/avif`);
      mimeType = 'image/avif';
    }
    
    // Step 1: Ensure the image data is correctly encoded
    // Convert array buffer to base64 with MIME type prefix
    let base64Image = '';
    try {
      base64Image = arrayBufferToBase64(imageData);
    } catch (encodeError) {
      console.error("Error encoding image data:", encodeError);
      throw new Error("Failed to encode image data to base64");
    }
    
    const imageDataURI = `data:${mimeType};base64,${base64Image}`;
    
    // Validate the image data URI
    if (imageDataURI.length < 50) {
      console.error("Generated image data URI is too short:", imageDataURI);
      throw new Error("Image data URI generation failed");
    }
    
    // Step 2: Create metadata JSON object with properly sanitized fields
    const metadata = {
      name: (title || "CommissionArt").trim(),
      description: (description || "Commissioned Art").trim(),
      image: imageDataURI
    };
    
    // Step 3: Convert metadata to JSON string and then to base64
    const metadataStr = JSON.stringify(metadata);
    
    // Validate the JSON string
    try {
      // Attempt to parse it back to ensure it's valid JSON
      JSON.parse(metadataStr);
    } catch (parseError) {
      console.error("Generated invalid JSON metadata:", metadataStr.substring(0, 100));
      throw new Error("Failed to generate valid JSON metadata");
    }
    
    // Encode to base64
    let base64Metadata = '';
    try {
      base64Metadata = btoa(metadataStr);
    } catch (b64Error) {
      console.error("Error encoding metadata to base64:", b64Error);
      throw new Error("Failed to encode metadata to base64");
    }
    
    const tokenURI = `data:application/json;base64,${base64Metadata}`;
    
    // Calculate size in bytes
    const size = new TextEncoder().encode(tokenURI).length;
    
    // Validate the final tokenURI
    if (size < 100) {
      console.error("Generated token URI is too small:", tokenURI);
      throw new Error("TokenURI generation failed: result too small");
    }
    
    // Log success details
    console.log(`TokenURI generated successfully:
      - Image size: ${imageData.byteLength} bytes
      - MIME type: ${mimeType}
      - Title: ${title}
      - Description length: ${description?.length || 0} chars
      - Final size: ${size} bytes`);
    
    return { tokenURI, size };
  } catch (error) {
    console.error('Error formatting tokenURI:', error);
    throw new Error(`TokenURI formatting error: ${error instanceof Error ? error.message : String(error)}`);
  }
};

/**
 * Convert array buffer to base64 string safely
 * @param buffer The array buffer or Uint8Array to convert
 * @returns Base64 encoded string
 */
const arrayBufferToBase64 = (buffer: ArrayBuffer | Uint8Array): string => {
  try {
    // Ensure we have a Uint8Array to work with
    const bytes = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
    
    // Check if buffer is valid
    if (bytes.length === 0) {
      throw new Error("Empty buffer provided");
    }
    
    // Modern approach using Uint8Array and chunk processing for larger buffers
    // This helps avoid call stack issues with very large arrays
    const CHUNK_SIZE = 0x8000; // 32KB chunks
    let binary = '';
    
    // Process in chunks to avoid call stack issues
    for (let i = 0; i < bytes.byteLength; i += CHUNK_SIZE) {
      const slice = bytes.subarray(i, Math.min(i + CHUNK_SIZE, bytes.byteLength));
      binary += String.fromCharCode.apply(null, Array.from(slice));
    }
    
    // Use safe Base64 encoding
    try {
      return btoa(binary);
    } catch (btoaError) {
      console.error('Error in btoa:', btoaError);
      
      // Fallback to manual base64 encoding if needed
      // This is a simplified implementation for emergency use
      const base64Chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
      let result = '';
      let i = 0;
      
      // Process 3 bytes at a time, output 4 characters
      while (i < binary.length) {
        const a = binary.charCodeAt(i++) || 0;
        const b = binary.charCodeAt(i++) || 0;
        const c = binary.charCodeAt(i++) || 0;
        
        // Combine three bytes into a single 24-bit number
        const triplet = (a << 16) | (b << 8) | c;
        
        // Extract 4 groups of 6 bits each
        for (let j = 0; j < 4; j++) {
          // If we're past the end of the input, add padding
          if (i > binary.length && j > 1) {
            result += '=';
          } else {
            // Get the 6-bit value
            const index = (triplet >> (6 * (3 - j))) & 0x3F;
            result += base64Chars[index];
          }
        }
      }
      
      console.log('Used fallback base64 encoding');
      return result;
    }
  } catch (error) {
    console.error('Error in arrayBufferToBase64:', error);
    throw new Error(`Base64 encoding error: ${error instanceof Error ? error.message : String(error)}`);
  }
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
 * Hash a string or object for comparison purposes
 * @param data String or object to hash
 * @returns Promise that resolves to the hex hash
 */
export const hashString = async (data: string | object): Promise<string> => {
  // Ensure we're always hashing a string
  const stringToHash = typeof data === 'string' ? data : JSON.stringify(data);
  
  // For objects, we want to normalize the JSON structure to ensure consistent hashing
  const normalizedData = typeof data === 'object' 
    ? JSON.stringify(data, Object.keys(data as object).sort())
    : stringToHash;
  
  // Now create the hash
  const encoder = new TextEncoder();
  const dataBuffer = encoder.encode(normalizedData);
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
    // First, check if the tokenURI is valid
    if (!tokenURI || typeof tokenURI !== 'string') {
      console.error('Invalid tokenURI provided:', tokenURI);
      return null;
    }
    
    // Parse the JSON data from the tokenURI
    // First find where the data:application/json;base64, part ends
    const base64JsonStart = tokenURI.indexOf('base64,') + 7;
    if (base64JsonStart === 6 || base64JsonStart >= tokenURI.length) {
      console.error('No base64 data found in tokenURI');
      return null; // Not found
    }
    
    // Extract and decode the base64 JSON
    const base64Json = tokenURI.substring(base64JsonStart);
    
    // Debugging
    console.log('Base64 JSON length:', base64Json.length);
    console.log('Base64 JSON preview:', base64Json.substring(0, 50) + '...');
    
    // Make sure we have valid base64 by checking for illegal characters
    if (!/^[A-Za-z0-9+/=]+$/.test(base64Json)) {
      console.error('Base64 string contains invalid characters');
      
      // Try to clean up the base64 string
      let cleanBase64 = base64Json.replace(/[^A-Za-z0-9+/=]/g, '');
      // Make sure the length is a multiple of the base64 chunk size
      const remainder = cleanBase64.length % 4;
      if (remainder > 0) {
        cleanBase64 += '='.repeat(4 - remainder);
      }
      
      console.log('Cleaned base64 length:', cleanBase64.length);
      
      // Use the cleaned version
      try {
        const jsonString = atob(cleanBase64);
        if (jsonString.length < 10) {
          console.error('Decoded JSON is too short:', jsonString);
          return null;
        }
        
        // Try to parse the JSON
        try {
          const metadata = JSON.parse(jsonString);
          if (!metadata.image) {
            console.error('No image property found in metadata');
            return null;
          }
          return metadata.image;
        } catch (parseError) {
          console.error('Failed to parse cleaned JSON:', parseError);
          return null;
        }
      } catch (cleanDecodeError) {
        console.error('Failed to decode cleaned base64:', cleanDecodeError);
        return null;
      }
    }
    
    // Decode base64 to JSON string
    let jsonString;
    try {
      jsonString = atob(base64Json);
    } catch (decodeError) {
      console.error('Failed to decode base64 JSON:', decodeError);
      console.error('Attempted base64:', base64Json.substring(0, 100) + '...');
      return null;
    }
    
    // Parse the JSON
    let metadata;
    try {
      metadata = JSON.parse(jsonString);
    } catch (parseError) {
      console.error('Failed to parse JSON:', parseError);
      console.log('JSON string preview:', jsonString.substring(0, 100) + '...');
      return null;
    }
    
    // Extract the image data
    if (!metadata.image) {
      console.error('No image property found in metadata:', metadata);
      return null;
    }
    
    // Validate the image URL format
    if (typeof metadata.image !== 'string' || !metadata.image.startsWith('data:image/')) {
      console.error('Invalid image data URL:', 
        typeof metadata.image === 'string' 
          ? metadata.image.substring(0, 30) + '...'
          : typeof metadata.image);
      return null;
    }
    
    // Return the image data URL directly - should be in format data:image/xxx;base64,data
    return metadata.image;
  } catch (error) {
    console.error('Error extracting image from tokenURI:', error);
    return null;
  }
};

/**
 * Create a more consistent hash for comparison by normalizing the data
 * @param originalData Original artwork data including image bytes, title, and description
 * @param tokenURI Final tokenURI string
 * @returns Promise resolving to an object with both hashes
 */
export const createComparisonHashes = async (
  originalData: { title: string, description: string, image: Uint8Array | number[] },
  tokenURI: string
): Promise<{ originalHash: string, tokenURIHash: string, match: boolean }> => {
  // For original data, we need to create a normalized structure
  // that will be comparable to what's in the tokenURI
  
  // 1. Extract the image from tokenURI for comparison
  const imageDataUrl = extractImageFromTokenURI(tokenURI);
  
  // 2. Hash the original data focusing on content only
  const originalDataForHashing = {
    name: originalData.title,
    description: originalData.description,
    // Don't include full image data in hash calculation - just length and sample
    imageSignature: {
      length: Array.isArray(originalData.image) ? originalData.image.length : originalData.image.byteLength,
      // Take samples from beginning, middle and end to create a signature
      sample: Array.isArray(originalData.image) ? 
        [
          originalData.image.slice(0, 10),
          originalData.image.slice(Math.floor(originalData.image.length/2), Math.floor(originalData.image.length/2) + 10),
          originalData.image.slice(-10)
        ] : 
        [
          Array.from(originalData.image.slice(0, 10)),
          Array.from(originalData.image.slice(Math.floor(originalData.image.byteLength/2), Math.floor(originalData.image.byteLength/2) + 10)),
          Array.from(originalData.image.slice(-10))
        ]
    }
  };
  
  // 3. For tokenURI, extract the key metadata for comparison
  // Extract JSON part from tokenURI
  const tokenURIData = imageDataUrl ? 
    {
      name: extractFieldFromTokenURI(tokenURI, 'name'),
      description: extractFieldFromTokenURI(tokenURI, 'description'),
      imageSignature: {
        length: imageDataUrl.length,
        // Create a similar signature from the image data URL
        sample: [
          imageDataUrl.substring(0, 30),
          imageDataUrl.substring(Math.floor(imageDataUrl.length/2), Math.floor(imageDataUrl.length/2) + 30),
          imageDataUrl.substring(imageDataUrl.length - 30)
        ]
      }
    } : 
    { error: 'Failed to extract image from tokenURI' };
  
  // 4. Hash both normalized structures
  const originalHash = await hashString(originalDataForHashing);
  const tokenURIHash = await hashString(tokenURIData);
  
  // For debugging
  console.log('Original data for hashing:', originalDataForHashing);
  console.log('TokenURI data for hashing:', tokenURIData);
  
  return {
    originalHash,
    tokenURIHash,
    match: originalHash === tokenURIHash
  };
};

/**
 * Extract a specific field from tokenURI JSON
 */
const extractFieldFromTokenURI = (tokenURI: string, fieldName: string): string => {
  try {
    const base64JsonStart = tokenURI.indexOf('base64,') + 7;
    if (base64JsonStart === 6) return '';
    
    const base64Json = tokenURI.substring(base64JsonStart);
    const jsonString = atob(base64Json);
    const metadata = JSON.parse(jsonString);
    
    return metadata[fieldName] || '';
  } catch (error) {
    console.error(`Error extracting ${fieldName} from tokenURI:`, error);
    return '';
  }
}; 