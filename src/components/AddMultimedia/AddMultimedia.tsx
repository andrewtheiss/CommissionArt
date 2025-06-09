import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useBlockchain } from '../../utils/BlockchainContext';
import { 
  shouldRecommendArWeave, 
  uploadToArWeave,
  ArWeaveUploadResult 
} from '../../utils/arweave';
import './AddMultimedia.css';

export type MediaType = 'image' | 'video' | 'audio' | 'unknown';

interface MultimediaData {
  file: File;
  mediaType: MediaType;
  preview?: string;
  duration?: number; // For video/audio
  dimensions?: { width: number; height: number }; // For images/video
}

interface AddMultimediaProps {
  onFileSelect?: (data: MultimediaData) => void;
  onUploadComplete?: (result: ArWeaveUploadResult, data: MultimediaData) => void;
  onError?: (error: string) => void;
  acceptedTypes?: string; // MIME types, defaults to image/*,video/*,audio/*
  maxSizeMB?: number; // Maximum file size in MB
  showArweaveOption?: boolean;
}

const AddMultimedia: React.FC<AddMultimediaProps> = ({
  onFileSelect,
  onUploadComplete,
  onError,
  acceptedTypes = "image/*,video/*,audio/*",
  maxSizeMB = 100,
  showArweaveOption = true
}) => {
  const { isConnected } = useBlockchain();

  const [selectedFile, setSelectedFile] = useState<MultimediaData | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<ArWeaveUploadResult | null>(null);
  const [showArWeaveOption, setShowArWeaveOption] = useState<boolean>(false);
  const [fileUrl, setFileUrl] = useState<string>('');
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifiedFileInfo, setVerifiedFileInfo] = useState<MultimediaData | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const objectUrlsRef = useRef<string[]>([]);

  // Cleanup object URLs
  const cleanupObjectUrls = () => {
    objectUrlsRef.current.forEach(url => {
      try {
        URL.revokeObjectURL(url);
      } catch (e) {
        // Ignore errors when revoking URLs
      }
    });
    objectUrlsRef.current = [];
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanupObjectUrls();
    };
  }, []);

  // Verify file from URL
  const verifyFileFromUrl = async (url: string) => {
    if (!url.trim()) {
      setVerifiedFileInfo(null);
      return;
    }

    setIsVerifying(true);
    setError(null);

    try {
      // Try to fetch basic info about the URL
      const response = await fetch(url, { method: 'HEAD' });
      
      if (!response.ok) {
        throw new Error(`Failed to verify URL: ${response.status} ${response.statusText}`);
      }

      const contentType = response.headers.get('content-type') || '';
      const contentLength = response.headers.get('content-length');
      const filename = url.split('/').pop() || 'unknown';

      // Create a mock file object for type detection
      const mockFile = {
        type: contentType,
        name: filename,
        size: contentLength ? parseInt(contentLength) : 0
      } as File;

      const mediaType = detectMediaType(mockFile);
      
      if (mediaType === 'unknown') {
        throw new Error('Unsupported file type detected from URL');
      }

      // Create file info
      const fileInfo: MultimediaData = {
        file: mockFile,
        mediaType,
        preview: mediaType === 'image' ? url : undefined
      };

      setVerifiedFileInfo(fileInfo);
      onFileSelect?.(fileInfo);

    } catch (err) {
      const errorMsg = `Failed to verify URL: ${err instanceof Error ? err.message : 'Unknown error'}`;
      setError(errorMsg);
      onError?.(errorMsg);
      setVerifiedFileInfo(null);
    } finally {
      setIsVerifying(false);
    }
  };

  // Handle URL input change
  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const url = e.target.value;
    setFileUrl(url);
    
    // Clear upload-related state when URL is entered
    if (url.trim()) {
      setSelectedFile(null);
      setUploadResult(null);
      setShowArWeaveOption(false);
    }
    
    // Debounce URL verification
    const timeoutId = setTimeout(() => {
      if (url.trim()) {
        verifyFileFromUrl(url);
      } else {
        setVerifiedFileInfo(null);
      }
    }, 500);

    return () => clearTimeout(timeoutId);
  };

  // Detect media type from file
  const detectMediaType = (file: File): MediaType => {
    const type = file.type.toLowerCase();
    
    if (type.startsWith('image/')) {
      return 'image';
    } else if (type.startsWith('video/')) {
      return 'video';
    } else if (type.startsWith('audio/')) {
      return 'audio';
    }
    
    // Fallback to file extension
    const extension = file.name.split('.').pop()?.toLowerCase();
    const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'avif'];
    const videoExts = ['mp4', 'webm', 'ogg', 'avi', 'mov', 'wmv', 'flv', 'mkv'];
    const audioExts = ['mp3', 'wav', 'ogg', 'aac', 'flac', 'wma', 'm4a'];
    
    if (extension) {
      if (imageExts.includes(extension)) return 'image';
      if (videoExts.includes(extension)) return 'video';
      if (audioExts.includes(extension)) return 'audio';
    }
    
    return 'unknown';
  };

  // Get media metadata
  const getMediaMetadata = (file: File, mediaType: MediaType): Promise<Partial<MultimediaData>> => {
    return new Promise((resolve) => {
      if (mediaType === 'image') {
        const img = new Image();
        const url = URL.createObjectURL(file);
        
        img.onload = () => {
          URL.revokeObjectURL(url);
          resolve({
            preview: url,
            dimensions: { width: img.width, height: img.height }
          });
        };
        
        img.onerror = () => {
          URL.revokeObjectURL(url);
          resolve({ preview: url });
        };
        
        img.src = url;
      } else if (mediaType === 'video') {
        const video = document.createElement('video');
        const url = URL.createObjectURL(file);
        video.preload = 'metadata';
        
        video.onloadedmetadata = () => {
          resolve({
            duration: video.duration,
            dimensions: { width: video.videoWidth, height: video.videoHeight }
          });
          // Don't revoke URL immediately for video as we need it for playback
        };
        
        video.onerror = () => {
          URL.revokeObjectURL(url);
          resolve({});
        };
        
        video.src = url;
      } else if (mediaType === 'audio') {
        const audio = document.createElement('audio');
        const url = URL.createObjectURL(file);
        audio.preload = 'metadata';
        
        audio.onloadedmetadata = () => {
          resolve({
            duration: audio.duration
          });
          // Don't revoke URL immediately for audio as we need it for playback
        };
        
        audio.onerror = () => {
          URL.revokeObjectURL(url);
          resolve({});
        };
        
        audio.src = url;
      } else {
        resolve({});
      }
    });
  };

  // Handle file selection
  const handleFileSelect = async (file: File) => {
    if (!file) return;

    // Cleanup previous object URLs
    cleanupObjectUrls();

    setError(null);
    setUploadResult(null);

    // Check file size
    const fileSizeMB = file.size / (1024 * 1024);
    if (fileSizeMB > maxSizeMB) {
      const errorMsg = `File too large. Maximum size is ${maxSizeMB}MB. Your file is ${fileSizeMB.toFixed(2)}MB.`;
      setError(errorMsg);
      onError?.(errorMsg);
      return;
    }

    try {
      const mediaType = detectMediaType(file);
      
      if (mediaType === 'unknown') {
        const errorMsg = `Unsupported file type: ${file.type || 'unknown'}. Please select an image, video, or audio file.`;
        setError(errorMsg);
        onError?.(errorMsg);
        return;
      }

      // Get metadata
      const metadata = await getMediaMetadata(file, mediaType);
      
      const multimediaData: MultimediaData = {
        file,
        mediaType,
        ...metadata
      };

      setSelectedFile(multimediaData);
      
      // Check if ArWeave should be recommended for large files
      if (showArweaveOption && fileSizeMB > 10) { // Recommend for files > 10MB
        setShowArWeaveOption(true);
      }

      // Notify parent component
      onFileSelect?.(multimediaData);

    } catch (err) {
      const errorMsg = `Failed to process file: ${err instanceof Error ? err.message : 'Unknown error'}`;
      setError(errorMsg);
      onError?.(errorMsg);
    }
  };

  // Handle drag and drop
  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
      e.dataTransfer.clearData();
    }
  }, []);

  const handleDropzoneClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelect(e.target.files[0]);
    }
  };

  // Handle ArWeave upload
  const handleUpload = async () => {
    if (!selectedFile) {
      setError('No file selected for upload');
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const tags = [
        { name: 'App-Name', value: 'CommissionArt' },
        { name: 'Content-Type', value: selectedFile.file.type },
        { name: 'File-Name', value: selectedFile.file.name },
        { name: 'Media-Type', value: selectedFile.mediaType },
        { name: 'File-Size', value: selectedFile.file.size.toString() }
      ];

      // Add media-specific tags
      if (selectedFile.dimensions) {
        tags.push({ name: 'Width', value: selectedFile.dimensions.width.toString() });
        tags.push({ name: 'Height', value: selectedFile.dimensions.height.toString() });
      }
      if (selectedFile.duration) {
        tags.push({ name: 'Duration', value: selectedFile.duration.toString() });
      }

      const result = await uploadToArWeave(selectedFile.file, tags);
      setUploadResult(result);

      if (result.success) {
        // Populate URL field with successful upload result
        if (result.url) {
          setFileUrl(result.url);
          // Verify the uploaded file
          await verifyFileFromUrl(result.url);
        }
        onUploadComplete?.(result, selectedFile);
      } else {
        setError(result.error || 'Upload failed');
        onError?.(result.error || 'Upload failed');
      }
    } catch (err) {
      const errorMsg = `Upload failed: ${err instanceof Error ? err.message : 'Unknown error'}`;
      setError(errorMsg);
      onError?.(errorMsg);
    } finally {
      setIsUploading(false);
    }
  };

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Format duration
  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getMediaTypeIcon = (mediaType: MediaType): string => {
    switch (mediaType) {
      case 'image': return '🖼️';
      case 'video': return '🎥';
      case 'audio': return '🎵';
      default: return '📄';
    }
  };

  return (
    <div className="add-multimedia">
      <div className="multimedia-header">
        <h3>Add Multimedia</h3>
        <p className="multimedia-description">
          Upload images, videos, or audio files to store on the decentralized web
        </p>
      </div>

      <div className="multimedia-upload-section">
        {/* URL Input Section */}
        <div className="url-input-section">
          <label htmlFor="file-url" className="url-label">
            File URL (ArWeave, IPFS, or direct link)
          </label>
          <div className="url-input-wrapper">
            <input
              id="file-url"
              type="url"
              value={fileUrl}
              onChange={handleUrlChange}
              placeholder="https://arweave.net/transaction-id or https://example.com/file.mp4"
              className="url-input"
            />
            {isVerifying && (
              <div className="url-status verifying">
                <span className="spinner"></span>
                Verifying...
              </div>
            )}
            {verifiedFileInfo && !isVerifying && (
              <div className="url-status verified">
                <span className="success-icon">✅</span>
                {verifiedFileInfo.mediaType === 'image' ? 'Image ready for preview' :
                 verifiedFileInfo.mediaType === 'video' ? 'Video ready to play' :
                 verifiedFileInfo.mediaType === 'audio' ? 'Audio ready to play' :
                 `Verified ${verifiedFileInfo.mediaType}`}
              </div>
            )}
          </div>
        </div>

        {/* Upload Section - disabled when URL is present */}
        <div className="upload-separator">
          <span>OR</span>
        </div>

        <div
          className={`multimedia-dropzone ${isDragging ? 'active' : ''} ${fileUrl.trim() ? 'disabled' : ''}`}
          onClick={fileUrl.trim() ? undefined : handleDropzoneClick}
          onDragEnter={fileUrl.trim() ? undefined : handleDragEnter}
          onDragLeave={fileUrl.trim() ? undefined : handleDragLeave}
          onDragOver={fileUrl.trim() ? undefined : handleDragOver}
          onDrop={fileUrl.trim() ? undefined : handleDrop}
        >
          {fileUrl.trim() ? (
            <div className="url-file-display">
              <div className="disabled-overlay">
                <span>Upload disabled - using URL file</span>
              </div>
              {verifiedFileInfo && (
                <div className="multimedia-preview">
                  <div className="media-info">
                    <div className="media-icon">{getMediaTypeIcon(verifiedFileInfo.mediaType)}</div>
                    <div className="media-details">
                      <h4>{verifiedFileInfo.file.name}</h4>
                      <p>Type: {verifiedFileInfo.mediaType.toUpperCase()}</p>
                      <p>Source: URL</p>
                      {verifiedFileInfo.file.size > 0 && (
                        <p>Size: {formatFileSize(verifiedFileInfo.file.size)}</p>
                      )}
                    </div>
                  </div>
                  
                  {/* Media Preview for URL files */}
                  {verifiedFileInfo.mediaType === 'image' && (
                    <div className="preview-container">
                      <img src={fileUrl} alt="Preview" className="preview-image" />
                    </div>
                  )}
                  {verifiedFileInfo.mediaType === 'video' && (
                    <div className="preview-container">
                      <video 
                        controls 
                        className="preview-video"
                        preload="metadata"
                        onError={(e) => {
                          console.warn('Video preview failed:', e);
                          setError('Video file appears to be corrupted or invalid format');
                        }}
                      >
                        <source src={fileUrl} />
                        Your browser does not support video playback.
                      </video>
                    </div>
                  )}
                  {verifiedFileInfo.mediaType === 'audio' && (
                    <div className="preview-container">
                      <audio 
                        controls 
                        className="preview-audio"
                        preload="metadata"
                        onError={(e) => {
                          console.warn('Audio preview failed:', e);
                          setError('Audio file appears to be corrupted or invalid format');
                        }}
                      >
                        <source src={fileUrl} />
                        Your browser does not support audio playback.
                      </audio>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : selectedFile ? (
            <div className="multimedia-preview">
              <div className="media-info">
                <div className="media-icon">{getMediaTypeIcon(selectedFile.mediaType)}</div>
                <div className="media-details">
                  <h4>{selectedFile.file.name}</h4>
                  <p>Type: {selectedFile.mediaType.toUpperCase()}</p>
                  <p>Size: {formatFileSize(selectedFile.file.size)}</p>
                  {selectedFile.dimensions && (
                    <p>Dimensions: {selectedFile.dimensions.width} × {selectedFile.dimensions.height}</p>
                  )}
                  {selectedFile.duration && (
                    <p>Duration: {formatDuration(selectedFile.duration)}</p>
                  )}
                </div>
              </div>
              
              {/* Media Preview for uploaded files */}
              {selectedFile.mediaType === 'image' && selectedFile.preview && (
                <div className="preview-container">
                  <img src={selectedFile.preview} alt="Preview" className="preview-image" />
                </div>
              )}
              {selectedFile.mediaType === 'video' && (
                <div className="preview-container">
                  <video 
                    controls 
                    className="preview-video"
                    preload="metadata"
                    onError={(e) => {
                      console.warn('Video preview failed:', e);
                      setError('Video file appears to be corrupted or invalid format');
                    }}
                  >
                    <source src={(() => {
                      const url = URL.createObjectURL(selectedFile.file);
                      objectUrlsRef.current.push(url);
                      return url;
                    })()} />
                    Your browser does not support video playback.
                  </video>
                </div>
              )}
              {selectedFile.mediaType === 'audio' && (
                <div className="preview-container">
                  <audio 
                    controls 
                    className="preview-audio"
                    preload="metadata"
                    onError={(e) => {
                      console.warn('Audio preview failed:', e);
                      setError('Audio file appears to be corrupted or invalid format');
                    }}
                  >
                    <source src={(() => {
                      const url = URL.createObjectURL(selectedFile.file);
                      objectUrlsRef.current.push(url);
                      return url;
                    })()} />
                    Your browser does not support audio playback.
                  </audio>
                </div>
              )}
            </div>
          ) : (
            <div className="dropzone-placeholder">
              <div className="upload-icon">📁</div>
              <p className="upload-text">Drop multimedia files here or click to browse</p>
              <p className="upload-subtext">Supports images, videos, and audio files (max {maxSizeMB}MB)</p>
            </div>
          )}
          
          <input
            ref={fileInputRef}
            type="file"
            accept={acceptedTypes}
            onChange={handleFileInputChange}
            style={{ display: 'none' }}
          />
        </div>

        {showArWeaveOption && selectedFile && (
          <div className="arweave-recommendation">
            <p>📊 Large file detected - ArWeave upload recommended for permanent storage</p>
            {selectedFile.file.size > 100 * 1024 * 1024 && (
              <p className="upload-warning">
                ⏳ Large file uploads may take several minutes. Please keep this tab open during upload.
              </p>
            )}
          </div>
        )}

        {error && (
          <div className="multimedia-error">
            <span className="error-icon">⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {uploadResult && uploadResult.success && (
          <div className="upload-success">
            <span className="success-icon">✅</span>
            <span>Upload successful!</span>
            <a 
              href={uploadResult.url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="arweave-link"
            >
              View on ArWeave
            </a>
          </div>
        )}

        <div className="multimedia-actions">
          {selectedFile && !fileUrl.trim() && (
            <button
              onClick={handleUpload}
              disabled={isUploading || !isConnected}
              className={`upload-button ${isUploading ? 'uploading' : ''}`}
            >
              {isUploading ? (
                <>
                  <span className="spinner"></span>
                  {selectedFile && selectedFile.file.size > 100 * 1024 * 1024 ? 
                    `Uploading large file... (${formatFileSize(selectedFile.file.size)})` : 
                    'Uploading...'
                  }
                </>
              ) : (
                'Upload to ArWeave'
              )}
            </button>
          )}
          
          {fileUrl.trim() && verifiedFileInfo && (
            <div className="url-status-info">
              <span className="success-icon">✅</span>
              <span>File loaded from URL - ready to use</span>
            </div>
          )}
          
          {!isConnected && !fileUrl.trim() && (
            <p className="connection-warning">
              Connect your wallet to upload files
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default AddMultimedia; 