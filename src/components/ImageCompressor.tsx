import React, { useState, useRef } from 'react';
import './ImageCompressor.css';

interface CompressionOptions {
  format: 'webp' | 'jpeg' | 'avif';
  quality: number;
  maxWidth: number | null;
  maxHeight: number | null;
}

interface ImageInfo {
  dataUrl: string;
  size: string;
  dimensions: string;
  format: string;
}

/**
 * Compresses an image to a desired format and quality in the browser
 * @param input - The image to compress (File, Blob, or Data URL)
 * @param options - Compression options
 * @returns Promise that resolves with the compressed image as data URL
 */
const compressImage = async (
  input: File | Blob | string,
  options: CompressionOptions = { format: 'webp', quality: 0.8, maxWidth: null, maxHeight: null }
): Promise<string> => {
  const {
    format = 'webp',
    quality = 0.8,
    maxWidth = null,
    maxHeight = null
  } = options;
  
  // Validate format
  const validFormats = ['webp', 'jpeg', 'avif'];
  const outputFormat = format.toLowerCase() as 'webp' | 'jpeg' | 'avif';
  if (!validFormats.includes(outputFormat)) {
    throw new Error(`Invalid format: ${format}. Supported formats: ${validFormats.join(', ')}`);
  }

  // Convert input to data URL if it's a File or Blob
  let imageDataUrl: string;
  if (typeof input === 'string' && input.startsWith('data:')) {
    imageDataUrl = input;
  } else {
    imageDataUrl = await fileToDataUrl(input as File | Blob);
  }
  
  // Create an image element
  const img = document.createElement('img');
  
  // Create a promise to handle image loading
  const imageLoaded = new Promise<void>((resolve, reject) => {
    img.onload = () => resolve();
    img.onerror = () => reject(new Error('Failed to load image'));
  });
  
  // Set the image source
  img.src = imageDataUrl;
  
  // Wait for the image to load
  await imageLoaded;
  
  // Calculate dimensions while maintaining aspect ratio
  let width = img.width;
  let height = img.height;
  
  if (maxWidth && width > maxWidth) {
    height = (height * maxWidth) / width;
    width = maxWidth;
  }
  
  if (maxHeight && height > maxHeight) {
    width = (width * maxHeight) / height;
    height = maxHeight;
  }
  
  // Round dimensions to integers
  width = Math.round(width);
  height = Math.round(height);
  
  // Create a canvas with the desired dimensions
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  
  // Draw the image on the canvas
  const ctx = canvas.getContext('2d');
  ctx?.drawImage(img, 0, 0, width, height);
  
  // Get the mime type
  let mimeType: string;
  switch(outputFormat) {
    case 'webp':
      mimeType = 'image/webp';
      break;
    case 'jpeg':
      mimeType = 'image/jpeg';
      break;
    case 'avif':
      mimeType = 'image/avif';
      break;
    default:
      mimeType = 'image/webp';
  }
  
  // Convert canvas to compressed data URL
  return canvas.toDataURL(mimeType, quality);
};

/**
 * Helper function to convert a File or Blob to a data URL
 */
const fileToDataUrl = (file: File | Blob): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsDataURL(file);
  });
};

/**
 * Calculate size in KB from data URL
 */
const calculateSizeInKB = (dataUrl: string): string => {
  // Remove the data URL prefix (e.g., 'data:image/jpeg;base64,')
  const base64 = dataUrl.split(',')[1];
  // Calculate the size: base64 is 4/3 the size of binary
  const sizeInBytes = Math.ceil((base64.length * 3) / 4);
  return (sizeInBytes / 1024).toFixed(2);
};

/**
 * Extract image dimensions from width and height
 */
const getImageDimensions = (width: number, height: number): string => {
  return `${width} × ${height}`;
};

/**
 * Extract format from data URL
 */
const getImageFormat = (dataUrl: string): string => {
  const match = dataUrl.match(/data:image\/([a-zA-Z0-9]+);/);
  return match ? match[1].toUpperCase() : 'Unknown';
};

const ImageCompressor: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [originalImageInfo, setOriginalImageInfo] = useState<ImageInfo | null>(null);
  const [compressedImageInfo, setCompressedImageInfo] = useState<ImageInfo | null>(null);
  const [isCompressing, setIsCompressing] = useState(false);
  const [fileName, setFileName] = useState('No file selected');
  const [options, setOptions] = useState<CompressionOptions>({
    format: 'webp',
    quality: 0.8,
    maxWidth: null,
    maxHeight: null
  });
  const [sizeReduction, setSizeReduction] = useState<string>('-');
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setSelectedFile(file);
    setFileName(file.name);
    setCompressedImageInfo(null);
    setSizeReduction('-');

    try {
      // Display original image
      const originalDataUrl = await fileToDataUrl(file);
      
      // Create img element to get dimensions
      const img = document.createElement('img');
      const imageLoaded = new Promise<{width: number, height: number}>((resolve) => {
        img.onload = () => {
          resolve({width: img.width, height: img.height});
        };
        img.src = originalDataUrl;
      });
      
      const dimensions = await imageLoaded;
      
      setOriginalImageInfo({
        dataUrl: originalDataUrl,
        size: `${(file.size / 1024).toFixed(2)} KB`,
        dimensions: getImageDimensions(dimensions.width, dimensions.height),
        format: file.type.split('/')[1].toUpperCase()
      });
      
      // Update maxWidth and maxHeight placeholders based on original dimensions
      setOptions(prev => ({
        ...prev,
        maxWidth: dimensions.width,
        maxHeight: dimensions.height
      }));
    } catch (error) {
      console.error('Error reading file:', error);
    }
  };

  const handleFormatChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setOptions(prev => ({
      ...prev,
      format: e.target.value as 'webp' | 'jpeg' | 'avif'
    }));
  };

  const handleQualityChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setOptions(prev => ({
      ...prev,
      quality: parseInt(e.target.value) / 100
    }));
  };

  const handleMaxWidthChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value ? parseInt(e.target.value) : null;
    setOptions(prev => ({
      ...prev,
      maxWidth: value
    }));
  };

  const handleMaxHeightChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value ? parseInt(e.target.value) : null;
    setOptions(prev => ({
      ...prev,
      maxHeight: value
    }));
  };

  const handleCompress = async () => {
    if (!selectedFile || !originalImageInfo) return;
    
    setIsCompressing(true);
    
    try {
      // Compress the image
      const compressedDataUrl = await compressImage(
        selectedFile, 
        {
          format: options.format,
          quality: options.quality,
          maxWidth: options.maxWidth,
          maxHeight: options.maxHeight
        }
      );
      
      // Create img element to get dimensions
      const img = document.createElement('img');
      const imageLoaded = new Promise<{width: number, height: number}>((resolve) => {
        img.onload = () => {
          resolve({width: img.width, height: img.height});
        };
        img.src = compressedDataUrl;
      });
      
      const dimensions = await imageLoaded;
      
      const compressedSizeKB = calculateSizeInKB(compressedDataUrl);
      
      setCompressedImageInfo({
        dataUrl: compressedDataUrl,
        size: `${compressedSizeKB} KB`,
        dimensions: getImageDimensions(dimensions.width, dimensions.height),
        format: options.format.toUpperCase()
      });
      
      // Calculate size reduction
      const originalSizeKB = parseFloat((selectedFile.size / 1024).toFixed(2));
      const compressedSize = parseFloat(compressedSizeKB);
      const reductionPercent = (100 - (compressedSize / originalSizeKB * 100)).toFixed(1);
      setSizeReduction(`${reductionPercent}%`);
    } catch (error) {
      console.error('Compression failed:', error);
      alert(`Compression failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsCompressing(false);
    }
  };

  const handleDownload = () => {
    if (!compressedImageInfo) return;
    
    const link = document.createElement('a');
    link.href = compressedImageInfo.dataUrl;
    link.download = `compressed_${fileName}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="image-compressor">
      <h2>Image Compressor</h2>
      
      <div className="compressor-container">
        <div className="controls">
          <div className="control-group">
            <div className="file-input">
              <label className="file-input-label" onClick={() => fileInputRef.current?.click()}>
                Choose Image
              </label>
              <input 
                ref={fileInputRef}
                type="file" 
                onChange={handleFileSelect}
                accept="image/*"
                className="hidden-file-input"
              />
              <span className="file-name">{fileName}</span>
            </div>
          </div>
          
          <div className="control-group">
            <div className="control-item">
              <label htmlFor="formatSelect">Output Format</label>
              <select 
                id="formatSelect" 
                value={options.format}
                onChange={handleFormatChange}
                className="format-select"
              >
                <option value="webp">WebP</option>
                <option value="jpeg">JPEG</option>
                <option value="avif">AVIF</option>
              </select>
            </div>
            
            <div className="control-item">
              <label htmlFor="qualityRange">
                Quality: <span>{Math.round(options.quality * 100)}%</span>
              </label>
              <input 
                type="range" 
                id="qualityRange" 
                min="10" 
                max="100" 
                value={Math.round(options.quality * 100)}
                onChange={handleQualityChange}
                className="quality-range"
              />
            </div>
            
            <div className="control-item">
              <label htmlFor="maxWidthInput">Max Width (px)</label>
              <input 
                type="number" 
                id="maxWidthInput" 
                placeholder={options.maxWidth?.toString() || "Original"}
                value={options.maxWidth || ''}
                onChange={handleMaxWidthChange}
                min="50"
                className="dimension-input"
              />
            </div>
            
            <div className="control-item">
              <label htmlFor="maxHeightInput">Max Height (px)</label>
              <input 
                type="number" 
                id="maxHeightInput" 
                placeholder={options.maxHeight?.toString() || "Original"}
                value={options.maxHeight || ''}
                onChange={handleMaxHeightChange}
                min="50"
                className="dimension-input"
              />
            </div>
          </div>
          
          <div className="control-group">
            <button 
              onClick={handleCompress}
              disabled={!selectedFile || isCompressing}
              className="compress-button"
            >
              {isCompressing ? 'Compressing...' : 'Compress Image'}
            </button>
            {isCompressing && <div className="spinner"></div>}
          </div>
        </div>
        
        <div className="comparison">
          <div className="image-card">
            <div className="image-container">
              {originalImageInfo ? (
                <img 
                  src={originalImageInfo.dataUrl} 
                  alt="Original" 
                  className="preview-image"
                />
              ) : (
                <div className="no-image">No image selected</div>
              )}
            </div>
            <div className="image-info">
              <p><strong>Original Image</strong></p>
              <p>Size: {originalImageInfo?.size || '-'}</p>
              <p>Dimensions: {originalImageInfo?.dimensions || '-'}</p>
              <p>Format: {originalImageInfo?.format || '-'}</p>
            </div>
          </div>
          
          <div className="image-card">
            <div className="image-container">
              {compressedImageInfo ? (
                <img 
                  src={compressedImageInfo.dataUrl} 
                  alt="Compressed" 
                  className="preview-image"
                />
              ) : (
                <div className="no-image">
                  {selectedFile ? 'Click "Compress Image" to see result' : 'No image compressed yet'}
                </div>
              )}
            </div>
            <div className="image-info">
              <p><strong>Compressed Image</strong></p>
              <p>Size: {compressedImageInfo?.size || '-'}</p>
              <p>Dimensions: {compressedImageInfo?.dimensions || '-'}</p>
              <p>Format: {compressedImageInfo?.format || '-'}</p>
              <p>Reduction: {sizeReduction}</p>
              {compressedImageInfo && (
                <button onClick={handleDownload} className="download-button">
                  Download
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ImageCompressor; 