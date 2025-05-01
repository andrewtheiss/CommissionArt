import React, { useState, useRef } from 'react';
import './ImageCompressor.css';

interface CompressionOptions {
  format: 'webp' | 'jpeg' | 'avif';
  quality: number;
  maxWidth: number | null;
  maxHeight: number | null;
  targetSizeKB?: number;
  autoOptimize?: boolean;
}

interface ImageInfo {
  dataUrl: string;
  size: string;
  dimensions: string;
  format: string;
}

interface CompressionResult {
  dataUrl: string;
  width: number;
  height: number;
  sizeKB: number;
  format: 'webp' | 'jpeg' | 'avif';
  quality: number;
}

/**
 * Compresses an image to a desired format and quality in the browser
 * Automatically finds the best format and compression settings to meet target size
 */
const compressImage = async (
  input: File | Blob | string,
  options: CompressionOptions = { 
    format: 'webp', 
    quality: 0.8, 
    maxWidth: null, 
    maxHeight: null,
    targetSizeKB: 43,
    autoOptimize: true
  }
): Promise<string | CompressionResult> => {
  const {
    format = 'webp',
    quality = 0.8,
    maxWidth = null,
    maxHeight = null,
    targetSizeKB = 43,
    autoOptimize = true
  } = options;

  // If autoOptimize is true, use the advanced optimization logic
  if (autoOptimize) {
    return optimizeImageForSize(input, targetSizeKB);
  }
  
  // Regular compression logic for when autoOptimize is false
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
 * Optimizes image by trying different formats and dimensions to achieve target size
 */
const optimizeImageForSize = async (
  input: File | Blob | string,
  targetSizeKB: number = 43
): Promise<CompressionResult> => {
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
  let bestResult: CompressionResult | null = null;
  
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

/**
 * Calculate size in KB from data URL
 */
const calculateDataUrlSizeKB = (dataUrl: string): number => {
  // Remove the data URL prefix (e.g., 'data:image/jpeg;base64,')
  const base64 = dataUrl.split(',')[1];
  // Calculate the size: base64 is 4/3 the size of binary
  const sizeInBytes = Math.ceil((base64.length * 3) / 4);
  return sizeInBytes / 1024;
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
  return calculateDataUrlSizeKB(dataUrl).toFixed(2);
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
    maxHeight: null,
    targetSizeKB: 43,
    autoOptimize: true
  });
  const [sizeReduction, setSizeReduction] = useState<string>('-');
  const [optimizationDetails, setOptimizationDetails] = useState<string>('');
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setSelectedFile(file);
    setFileName(file.name);
    setCompressedImageInfo(null);
    setSizeReduction('-');
    setOptimizationDetails('');

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
      format: e.target.value as 'webp' | 'jpeg' | 'avif',
      autoOptimize: false // Turn off auto-optimize when user selects a specific format
    }));
  };

  const handleQualityChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setOptions(prev => ({
      ...prev,
      quality: parseInt(e.target.value) / 100,
      autoOptimize: false // Turn off auto-optimize when user selects a specific quality
    }));
  };

  const handleMaxWidthChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value ? parseInt(e.target.value) : null;
    setOptions(prev => ({
      ...prev,
      maxWidth: value,
      autoOptimize: false // Turn off auto-optimize when user selects specific dimensions
    }));
  };

  const handleMaxHeightChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value ? parseInt(e.target.value) : null;
    setOptions(prev => ({
      ...prev,
      maxHeight: value,
      autoOptimize: false // Turn off auto-optimize when user selects specific dimensions
    }));
  };

  const handleTargetSizeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value);
    setOptions(prev => ({
      ...prev,
      targetSizeKB: value
    }));
  };

  const handleAutoOptimizeToggle = (e: React.ChangeEvent<HTMLInputElement>) => {
    setOptions(prev => ({
      ...prev,
      autoOptimize: e.target.checked
    }));
  };

  const handleCompress = async () => {
    if (!selectedFile || !originalImageInfo) return;
    
    setIsCompressing(true);
    
    try {
      // Compress the image
      const result = await compressImage(
        selectedFile, 
        options
      );
      
      // Handle result based on whether it's a string (regular compression) or CompressionResult (auto-optimized)
      let compressedDataUrl: string;
      let details = '';
      
      if (typeof result === 'string') {
        compressedDataUrl = result;
        
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
        
        // Log the first part of the compressed image data
        console.log("Compressed image data (first 100 chars):", compressedDataUrl.substring(0, 100));
        
        setCompressedImageInfo({
          dataUrl: compressedDataUrl,
          size: `${compressedSizeKB} KB`,
          dimensions: getImageDimensions(dimensions.width, dimensions.height),
          format: options.format.toUpperCase()
        });
        
      } else {
        // It's an auto-optimized result
        compressedDataUrl = result.dataUrl;
        
        // Log the first part of the compressed image data
        console.log("Auto-optimized image data (first 100 chars):", compressedDataUrl.substring(0, 100));
        console.log(`Compression format: ${result.format}, Quality: ${result.quality.toFixed(2)}, Size: ${result.sizeKB.toFixed(2)}KB`);
        
        details = `Optimized to ${result.width}x${result.height} at ${Math.round(result.quality * 100)}% quality using ${result.format.toUpperCase()}`;
        setOptimizationDetails(details);
        
        setCompressedImageInfo({
          dataUrl: compressedDataUrl,
          size: `${result.sizeKB.toFixed(2)} KB`,
          dimensions: getImageDimensions(result.width, result.height),
          format: result.format.toUpperCase()
        });
      }
      
      // Calculate size reduction
      const originalSizeKB = parseFloat((selectedFile.size / 1024).toFixed(2));
      const compressedSizeKB = parseFloat(compressedImageInfo?.size?.split(' ')[0] || '0');
      const reductionPercent = (100 - (compressedSizeKB / originalSizeKB * 100)).toFixed(1);
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
            
            <div className="control-item">
              <label>
                <input 
                  type="checkbox" 
                  checked={options.autoOptimize} 
                  onChange={handleAutoOptimizeToggle}
                />
                Auto-optimize
              </label>
              <div className="help-text">
                Automatically finds the best format, quality and dimensions
              </div>
            </div>
            
            <div className="control-item">
              <label htmlFor="targetSizeInput">Target Size (KB)</label>
              <input 
                type="number" 
                id="targetSizeInput" 
                value={options.targetSizeKB}
                onChange={handleTargetSizeChange}
                min="10"
                max="100"
                className="dimension-input"
              />
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
                disabled={options.autoOptimize}
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
                disabled={options.autoOptimize}
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
                disabled={options.autoOptimize}
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
                disabled={options.autoOptimize}
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
              {optimizationDetails && <p className="optimization-details">{optimizationDetails}</p>}
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