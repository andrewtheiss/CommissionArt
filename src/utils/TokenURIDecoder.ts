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
} => {
  let imageUrl: string | null = null;
  let decodedTokenURI: DecodedTokenURI | null = null;
  let isTokenURIFormat = false;
  
  try {
    // If it's a Uint8Array, first try to interpret as a raw image
    if (imageData instanceof Uint8Array) {
      // Try to convert to a string first to see if it's a tokenURI
      const str = new TextDecoder().decode(imageData);
      
      // Check if it's in tokenURI format
      if (str.startsWith('data:application/json;base64,')) {
        // It's a tokenURI, try to decode it
        decodedTokenURI = decodeTokenURI(str);
        if (decodedTokenURI) {
          imageUrl = decodedTokenURI.imageDataUrl;
          isTokenURIFormat = true;
        }
      } else {
        // It's a raw image, create a blob URL
        const blob = new Blob([imageData], { type: 'image/avif' });
        imageUrl = URL.createObjectURL(blob);
      }
    } 
    // If it's a string, assume it's already a tokenURI
    else if (typeof imageData === 'string') {
      decodedTokenURI = decodeTokenURI(imageData);
      if (decodedTokenURI) {
        imageUrl = decodedTokenURI.imageDataUrl;
        isTokenURIFormat = true;
      }
    }
  } catch (error) {
    console.error('Error processing artwork data:', error);
  }
  
  return { imageUrl, decodedTokenURI, isTokenURIFormat };
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