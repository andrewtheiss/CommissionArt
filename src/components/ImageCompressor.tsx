import React, { useState, useRef } from 'react';
import './ImageCompressor.css';

interface CompressionResult {
  success: boolean;
  originalSize: number;
  compressedSize: number;
  dimensions: { width: number; height: number };
  error?: string;
  targetReached: boolean;
  format: string;
}

type FormatType = 'image/avif' | 'image/webp' | 'image/jpeg';

interface FormatOption {
  type: FormatType;
  name: string;
  extension: string;
}

const ImageCompressor: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [compressionResult, setCompressionResult] = useState<CompressionResult | null>(null);
  const [isCompressing, setIsCompressing] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [compressedBlob, setCompressedBlob] = useState<Blob | null>(null);
  const [preferredFormat, setPreferredFormat] = useState<FormatType>('image/avif');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Available format options
  const formatOptions: FormatOption[] = [
    { type: 'image/avif', name: 'AVIF', extension: 'avif' },
    { type: 'image/webp', name: 'WebP', extension: 'webp' },
    { type: 'image/jpeg', name: 'JPEG', extension: 'jpg' }
  ];

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setCompressionResult(null);
      setCompressedBlob(null);
      // Create preview URL
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
    }
  };

  const compressImageWithFormat = async (
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
      let smallestSize = Infinity;

      const binarySearch = () => {
        if (low > high) {
          resolveFormat({
            blob: optimalBlob,
            size: optimalBlob ? optimalBlob.size / 1024 : Infinity,
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
            
            if (sizeKB <= targetSizeKB) {
              // Save this as our best result so far
              if (sizeKB < smallestSize) {
                optimalBlob = blob;
                optimalQuality = mid;
                smallestSize = sizeKB;
              }
              
              // Try higher quality
              low = mid + 1;
            } else {
              // Even if we're above target size, track the smallest blob
              if (optimalBlob === null || sizeKB < smallestSize) {
                optimalBlob = blob;
                optimalQuality = mid;
                smallestSize = sizeKB;
              }
              
              // Try lower quality
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

  const compressImage = async (file: File, maxDimension = 1000, targetSizeKB = 45): Promise<CompressionResult> => {
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

        // Try each format at the initial size
        let bestResult: {
          blob: Blob;
          size: number;
          width: number;
          height: number;
          format: FormatType;
          targetReached: boolean;
        } | null = null;

        console.log("Starting compression with initial dimensions:", currentWidth, "x", currentHeight);

        for (const format of [preferredFormat, ...formatOptions.filter(f => f.type !== preferredFormat).map(f => f.type)]) {
          const result = await compressImageWithFormat(img, currentWidth, currentHeight, format, targetSizeKB);
          
          if (result.blob) {
            console.log(`${format} compression result:`, result.size.toFixed(2), "KB at quality", result.quality);
            
            const isTargetReached = result.size <= targetSizeKB;
            
            // Keep track of the best result across all formats
            if (!bestResult || result.size < bestResult.size) {
              bestResult = {
                blob: result.blob,
                size: result.size,
                width: currentWidth,
                height: currentHeight,
                format: format,
                targetReached: isTargetReached
              };
            }
            
            // If we've reached target size, we can stop here
            if (isTargetReached) {
              console.log(`Target size reached with ${format} format`);
              break;
            }
          }
        }

        // If we didn't reach target size with any format at full dimensions,
        // try reducing dimensions with the best format found
        if (bestResult && !bestResult.targetReached) {
          let attemptCount = 0;
          const maxAttempts = 4; // Try a few size reductions
          
          let scaleWidth = currentWidth;
          let scaleHeight = currentHeight;
          
          while (attemptCount < maxAttempts) {
            // Reduce dimensions by 20% (keeping 80%)
            scaleWidth = Math.floor(scaleWidth * 0.8);
            scaleHeight = Math.floor(scaleHeight * 0.8);
            attemptCount++;
            
            // Stop if dimensions become too small
            if (scaleWidth < 50 || scaleHeight < 50) {
              break;
            }
            
            console.log(`Trying reduced dimensions ${scaleWidth}x${scaleHeight} with ${bestResult.format}`);
            
            const reducedResult = await compressImageWithFormat(
              img, 
              scaleWidth, 
              scaleHeight, 
              bestResult.format, 
              targetSizeKB
            );
            
            if (reducedResult.blob) {
              const isTargetReached = reducedResult.size <= targetSizeKB;
              
              console.log(`Reduced size result: ${reducedResult.size.toFixed(2)} KB at quality ${reducedResult.quality}`);
              
              // Update best result if this is better
              if (reducedResult.size < bestResult.size) {
                bestResult = {
                  blob: reducedResult.blob,
                  size: reducedResult.size,
                  width: scaleWidth,
                  height: scaleHeight,
                  format: bestResult.format,
                  targetReached: isTargetReached
                };
              }
              
              // If we've reached target size, we can stop here
              if (isTargetReached) {
                console.log(`Target size reached with reduced dimensions`);
                break;
              }
            }
          }
        }
        
        // Use the best result we found
        if (bestResult) {
          setCompressedBlob(bestResult.blob);
          
          // Get format extension from our options
          const formatInfo = formatOptions.find(f => f.type === bestResult?.format);
          
          resolve({
            success: true,
            originalSize: file.size / 1024,
            compressedSize: bestResult.size,
            dimensions: { width: bestResult.width, height: bestResult.height },
            targetReached: bestResult.targetReached,
            format: formatInfo?.name || bestResult.format
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
            format: 'None'
          });
        }
      };

      reader.readAsDataURL(file);
    });
  };

  const handleCompress = async () => {
    if (!selectedFile) return;

    setIsCompressing(true);
    try {
      const result = await compressImage(selectedFile);
      setCompressionResult(result);
    } catch (error) {
      setCompressionResult({
        success: false,
        originalSize: selectedFile.size / 1024,
        compressedSize: 0,
        dimensions: { width: 0, height: 0 },
        error: error instanceof Error ? error.message : 'Unknown error occurred',
        targetReached: false,
        format: 'None'
      });
    } finally {
      setIsCompressing(false);
    }
  };

  const handleFormatChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setPreferredFormat(e.target.value as FormatType);
  };

  const handleDownload = () => {
    if (!compressedBlob || !selectedFile || !compressionResult) return;

    const url = URL.createObjectURL(compressedBlob);
    const link = document.createElement('a');
    link.href = url;
    
    // Get correct extension from format
    const formatInfo = formatOptions.find(f => f.name === compressionResult.format);
    const extension = formatInfo?.extension || 'avif';
    
    link.download = `${selectedFile.name.split('.')[0]}_compressed.${extension}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="image-compressor">
      <h2>Image Compressor</h2>
      <div className="compressor-controls">
        <input
          type="file"
          accept="image/*"
          onChange={handleFileSelect}
          ref={fileInputRef}
          className="file-input"
        />
        <div className="format-selector">
          <label htmlFor="format-select">Preferred Format:</label>
          <select 
            id="format-select" 
            value={preferredFormat}
            onChange={handleFormatChange}
            className="format-select"
          >
            {formatOptions.map(option => (
              <option key={option.type} value={option.type}>
                {option.name}
              </option>
            ))}
          </select>
        </div>
        {selectedFile && (
          <button 
            onClick={handleCompress} 
            disabled={isCompressing}
            className="compress-button"
          >
            {isCompressing ? 'Compressing...' : 'Compress Image'}
          </button>
        )}
      </div>

      {previewUrl && (
        <div className="preview-container">
          <img src={previewUrl} alt="Preview" className="preview-image" />
        </div>
      )}

      {compressionResult && (
        <div className="compression-results">
          <h3>Compression Results</h3>
          <p>Original Size: {compressionResult.originalSize.toFixed(2)} KB</p>
          <p>Compressed Size: {compressionResult.compressedSize.toFixed(2)} KB</p>
          <p>Format: {compressionResult.format}</p>
          <p>Dimensions: {compressionResult.dimensions.width}x{compressionResult.dimensions.height}</p>
          {!compressionResult.targetReached && compressionResult.success && (
            <p className="warning-message">
              Note: Could not reach target size of 45KB. This is the smallest achievable size.
            </p>
          )}
          {compressionResult.success && (
            <button onClick={handleDownload} className="download-button">
              Download Compressed Image
            </button>
          )}
          {compressionResult.error && (
            <p className="error-message">Error: {compressionResult.error}</p>
          )}
        </div>
      )}
    </div>
  );
};

export default ImageCompressor; 