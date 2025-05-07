/**
 * TokenURIDecoder.ts
 * Utility to decode token URI data in standard NFT format
 */

/**
 * Interface for the decoded metadata from tokenURI
 */
export interface DecodedTokenURI {
  name: string;
  description: string;
  image: string;
  imageDataUrl: string;
  originalData: string;
}

/**
 * Decodes a tokenURI that follows the standard format:
 * data:application/json;base64,<BASE64_ENCODED_JSON>
 * 
 * Where the JSON contains:
 * {
 *   name: string;
 *   description: string;
 *   image: string; // In format data:image/xxx;base64,<BASE64_ENCODED_IMAGE>
 * }
 * 
 * @param tokenURI - The tokenURI string retrieved from the smart contract
 * @returns Decoded metadata object or null if decoding fails
 */
export const decodeTokenURI = (tokenURI: string): DecodedTokenURI | null => {
  try {
    // Check if it's in the expected format
    if (!tokenURI.startsWith('data:application/json;base64,')) {
      console.warn('TokenURI is not in expected format', tokenURI.substring(0, 50) + '...');
      return null;
    }
    
    // Extract the base64 encoded JSON part
    const base64Json = tokenURI.replace('data:application/json;base64,', '');
    
    // Decode the base64 JSON
    const jsonString = atob(base64Json);
    
    // Parse the JSON
    const metadata = JSON.parse(jsonString);
    
    // Validate that it has the expected fields
    if (!metadata.name || !metadata.image) {
      console.warn('Decoded metadata is missing required fields', metadata);
      return null;
    }
    
    // For image, it should be a data URL
    const imageDataUrl = metadata.image;
    
    // Return the decoded metadata with original data included
    return {
      name: metadata.name,
      description: metadata.description || '',
      image: imageDataUrl,
      imageDataUrl: imageDataUrl,
      originalData: tokenURI
    };
  } catch (error) {
    console.error('Error decoding tokenURI:', error);
    console.error('TokenURI that failed to decode:', tokenURI ? tokenURI.substring(0, 100) + '...' : 'undefined');
    return null;
  }
};

/**
 * Create a data URL from raw binary image data
 * Automatically detects the image format from magic numbers
 * 
 * @param imageData - Raw binary image data
 * @param format - Optional format hint (avif, webp, jpeg, png, etc.)
 * @returns A data URL that can be used as src for an img element
 */
export const createImageDataUrl = (imageData: Uint8Array, format?: string): string => {
  // Detect the MIME type if not provided
  let mimeType: string;
  
  if (format) {
    // Format hint provided
    mimeType = `image/${format}`;
  } else {
    // Detect format using magic numbers
    mimeType = detectImageFormat(imageData);
  }
  
  // Convert to base64
  let binary = '';
  const bytes = new Uint8Array(imageData);
  const len = bytes.byteLength;
  
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  
  const base64 = btoa(binary);
  return `data:${mimeType};base64,${base64}`;
};

/**
 * Converts raw binary imageData from contract to various formats
 * Handles both the legacy raw binary format and the new tokenURI format
 * 
 * @param imageData - The raw image data from the smart contract
 * @returns Various representations of the image or null if invalid
 */
export const processArtworkData = (
  imageData: Uint8Array | string
): {
  imageUrl: string | null;
  decodedTokenURI: DecodedTokenURI | null;
  isTokenURIFormat: boolean;
  mimeType: string;
} => {
  let imageUrl: string | null = null;
  let decodedTokenURI: DecodedTokenURI | null = null;
  let isTokenURIFormat = false;
  let mimeType = 'image/avif'; // Default mime type
  
  try {
    // If it's a Uint8Array, try to detect the image format
    if (imageData instanceof Uint8Array) {
      // Check if it's a known image format by examining its magic numbers
      mimeType = detectImageFormat(imageData);
      console.log(`Detected image MIME type from raw data: ${mimeType}`);
      console.log(`First bytes: [${Array.from(imageData.slice(0, 8)).map(b => b.toString(16).padStart(2, '0')).join(' ')}...]`);
      
      // Try to convert to a string first to see if it's a tokenURI
      // but only check a small slice to avoid conversion issues with binary data
      const firstBytes = imageData.slice(0, 40);
      try {
        const str = new TextDecoder().decode(firstBytes);
        
        // Check if it's in tokenURI format
        if (str.startsWith('data:application/json;base64,')) {
          // It's a tokenURI, try to decode the full string
          try {
            const fullStr = new TextDecoder().decode(imageData);
            decodedTokenURI = decodeTokenURI(fullStr);
            if (decodedTokenURI) {
              imageUrl = decodedTokenURI.imageDataUrl;
              isTokenURIFormat = true;
              return { imageUrl, decodedTokenURI, isTokenURIFormat, mimeType };
            }
          } catch (err) {
            console.warn('Failed to decode complete tokenURI from binary data:', err);
          }
        }
      } catch (err) {
        console.warn('Error checking for tokenURI format in binary data:', err);
      }
      
      // If we get here, treat it as raw image data
      const blob = new Blob([imageData], { type: mimeType });
      imageUrl = URL.createObjectURL(blob);
    } 
    // If it's a string, check if it's a tokenURI or a hex representation
    else if (typeof imageData === 'string') {
      // Check if it looks like a hex string (starts with 0x)
      if (imageData.startsWith('0x')) {
        try {
          // Convert hex string to bytes
          const hexString = imageData.slice(2); // Remove 0x prefix
          const bytes = new Uint8Array(hexString.length / 2);
          for (let i = 0; i < bytes.length; i++) {
            bytes[i] = parseInt(hexString.substring(i * 2, i * 2 + 2), 16);
          }
          
          // Detect format and create blob URL
          mimeType = detectImageFormat(bytes);
          console.log(`Detected image MIME type from hex string: ${mimeType}`);
          const blob = new Blob([bytes], { type: mimeType });
          imageUrl = URL.createObjectURL(blob);
        } catch (err) {
          console.error('Failed to process hex string as image data:', err);
        }
      }
      // Check if it's a data URL for a raw image (not wrapped in JSON)
      else if (imageData.startsWith('data:image/')) {
        // It's already an image data URL, use it directly
        imageUrl = imageData;
        // Extract MIME type
        const mimeMatch = imageData.match(/^data:(image\/[^;]+);/);
        if (mimeMatch) {
          mimeType = mimeMatch[1];
        }
      }
      // Otherwise try to decode it as a tokenURI
      else {
        decodedTokenURI = decodeTokenURI(imageData);
        if (decodedTokenURI) {
          imageUrl = decodedTokenURI.imageDataUrl;
          isTokenURIFormat = true;
          // Extract MIME type from the image data URL if available
          const mimeMatch = decodedTokenURI.imageDataUrl.match(/^data:(image\/[^;]+);base64,/);
          if (mimeMatch) {
            mimeType = mimeMatch[1];
          }
        }
      }
    }
  } catch (error) {
    console.error('Error processing artwork data:', error);
  }
  
  return { imageUrl, decodedTokenURI, isTokenURIFormat, mimeType };
};

/**
 * Detects the MIME type of an image by examining its magic numbers
 * @param data - The binary image data
 * @returns The detected MIME type or the default 'image/avif'
 */
export const detectImageFormat = (data: Uint8Array): string => {
  // Check for file signatures
  if (data.length < 4) return 'image/avif'; // Default if not enough data

  // JPEG signature: FF D8 FF
  if (data[0] === 0xFF && data[1] === 0xD8 && data[2] === 0xFF) {
    return 'image/jpeg';
  }
  
  // PNG signature: 89 50 4E 47
  if (data[0] === 0x89 && data[1] === 0x50 && data[2] === 0x4E && data[3] === 0x47) {
    return 'image/png';
  }
  
  // GIF signature: 47 49 46 38
  if (data[0] === 0x47 && data[1] === 0x49 && data[2] === 0x46 && data[3] === 0x38) {
    return 'image/gif';
  }
  
  // WebP signature: 52 49 46 46 ... 57 45 42 50 (RIFF....WEBP)
  if (data[0] === 0x52 && data[1] === 0x49 && data[2] === 0x46 && data[3] === 0x46) {
    // We need to check for "WEBP" which is 8 bytes in
    if (data.length >= 12 && 
        data[8] === 0x57 && data[9] === 0x45 && data[10] === 0x42 && data[11] === 0x50) {
      return 'image/webp';
    }
  }
  
  // AVIF signature checks
  // Full AVIF check (look for ftyp and avif markers)
  const searchAvif = (d: Uint8Array): boolean => {
    for (let i = 0; i < Math.min(d.length - 8, 50); i++) { // Check first 50 bytes only
      // Look for "ftyp" marker followed by "avif"
      if (d[i] === 0x66 && d[i+1] === 0x74 && d[i+2] === 0x79 && d[i+3] === 0x70 &&
          d[i+4] === 0x61 && d[i+5] === 0x76 && d[i+6] === 0x69 && d[i+7] === 0x66) {
        return true;
      }
    }
    return false;
  };
  
  if (searchAvif(data)) {
    return 'image/avif';
  }

  // Check for HEIF/HEIC signature - similar to AVIF but with different brand
  const searchHeif = (d: Uint8Array): boolean => {
    for (let i = 0; i < Math.min(d.length - 8, 50); i++) {
      // Look for "ftyp" followed by HEIF brands (heic, heix, mif1)
      if (d[i] === 0x66 && d[i+1] === 0x74 && d[i+2] === 0x79 && d[i+3] === 0x70) {
        // Check for heic or heix
        if ((d[i+4] === 0x68 && d[i+5] === 0x65 && d[i+6] === 0x69 && 
            (d[i+7] === 0x63 || d[i+7] === 0x78)) ||
            // Check for mif1
            (d[i+4] === 0x6d && d[i+5] === 0x69 && d[i+6] === 0x66 && d[i+7] === 0x31)) {
          return true;
        }
      }
    }
    return false;
  };
  
  if (searchHeif(data)) {
    return 'image/heic';
  }
  
  // Additional check for BMP signature: 42 4D
  if (data[0] === 0x42 && data[1] === 0x4D) {
    return 'image/bmp';
  }
  
  // Analyze the data probability-based approach
  // If it starts with 0xFF 0xD8 it's highly likely to be JPEG
  if (data[0] === 0xFF && data[1] === 0xD8) {
    console.log("Detected probable JPEG from partial signature");
    return 'image/jpeg';
  }
  
  // Log the first few bytes to help with debugging
  const firstBytes = Array.from(data.slice(0, 16))
    .map(b => b.toString(16).padStart(2, '0'))
    .join(' ');
    
  console.log(`Unknown image format. First 16 bytes: ${firstBytes}`);
  
  // For a true unknown format, try to guess based on the data pattern
  // Many image formats have headers with some text or distinctive patterns
  
  // Default to JPEG for 0xFF byte sequences which are common in JPEG
  let ffCount = 0;
  for (let i = 0; i < Math.min(data.length, 50); i++) {
    if (data[i] === 0xFF) ffCount++;
  }
  
  if (ffCount > 5) {
    console.log("Detected probable JPEG based on byte frequency analysis");
    return 'image/jpeg';
  }
  
  // Default to AVIF for unknown formats
  return 'image/avif';
};

/**
 * Helper to safely revoke object URLs
 */
export const safeRevokeUrl = (url: string | null) => {
  if (url && url.startsWith('blob:')) {
    try {
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('Error revoking URL:', e);
    }
  }
}; 