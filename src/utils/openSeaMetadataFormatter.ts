/**
 * OpenSea NFT Metadata Formatter
 * Formats NFT metadata to match OpenSea's standard format
 */

export interface OpenSeaAttribute {
  trait_type: string;
  value: string | number;
  display_type?: 'string' | 'number' | 'boost_percentage' | 'boost_number' | 'date';
}

export interface OpenSeaFileProperty {
  uri: string;
  type: string;
  cdn_uri?: string;
}

export interface OpenSeaProperties {
  files: OpenSeaFileProperty[];
  category?: string;
}

export interface OpenSeaMetadata {
  name: string;
  description: string;
  image: string;
  animation_url?: string;
  external_url?: string;
  attributes: OpenSeaAttribute[];
  properties: OpenSeaProperties;
  audio_url?: string;
  background_color?: string;
  youtube_url?: string;
}

export interface MetadataInput {
  // Basic info
  name: string;
  description: string;
  image: string;
  
  // Optional media URLs
  animationUrl?: string;
  externalUrl?: string;
  audioUrl?: string;
  youtubeUrl?: string;
  backgroundColor?: string;
  
  // Attributes
  attributes?: OpenSeaAttribute[];
  
  // Files for properties
  files?: OpenSeaFileProperty[];
  category?: string;
}

/**
 * Formats metadata input into OpenSea-compliant JSON structure
 */
export const formatOpenSeaMetadata = (input: MetadataInput): OpenSeaMetadata => {
  const metadata: OpenSeaMetadata = {
    name: input.name || "Untitled NFT",
    description: input.description || "",
    image: input.image,
    attributes: input.attributes || [],
    properties: {
      files: input.files || [],
      category: input.category || "multimedia"
    }
  };

  // Add optional fields only if they exist
  if (input.animationUrl) {
    metadata.animation_url = input.animationUrl;
  }
  
  if (input.externalUrl) {
    metadata.external_url = input.externalUrl;
  }
  
  if (input.audioUrl) {
    metadata.audio_url = input.audioUrl;
  }
  
  if (input.youtubeUrl) {
    metadata.youtube_url = input.youtubeUrl;
  }
  
  if (input.backgroundColor) {
    metadata.background_color = input.backgroundColor;
  }

  return metadata;
};

/**
 * Converts metadata to JSON string
 */
export const formatOpenSeaMetadataAsJSON = (input: MetadataInput): string => {
  const metadata = formatOpenSeaMetadata(input);
  return JSON.stringify(metadata, null, 2);
};

/**
 * Helper function to create a file property object
 */
export const createFileProperty = (uri: string, type: string, cdnUri?: string): OpenSeaFileProperty => {
  const file: OpenSeaFileProperty = { uri, type };
  if (cdnUri) {
    file.cdn_uri = cdnUri;
  }
  return file;
};

/**
 * Helper function to create an attribute object
 */
export const createAttribute = (
  traitType: string, 
  value: string | number, 
  displayType?: OpenSeaAttribute['display_type']
): OpenSeaAttribute => {
  const attribute: OpenSeaAttribute = { trait_type: traitType, value };
  if (displayType) {
    attribute.display_type = displayType;
  }
  return attribute;
};

/**
 * Helper to get MIME type from file extension or name
 */
export const getMimeTypeFromFile = (filename: string): string => {
  const ext = filename.toLowerCase().split('.').pop();
  const mimeTypes: { [key: string]: string } = {
    // Images
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'webp': 'image/webp',
    'avif': 'image/avif',
    'svg': 'image/svg+xml',
    
    // Videos
    'mp4': 'video/mp4',
    'webm': 'video/webm',
    'mov': 'video/quicktime',
    'avi': 'video/avi',
    
    // Audio
    'mp3': 'audio/mpeg',
    'wav': 'audio/wav',
    'ogg': 'audio/ogg',
    'flac': 'audio/flac',
    'm4a': 'audio/mp4'
  };
  
  return mimeTypes[ext || ''] || 'application/octet-stream';
}; 