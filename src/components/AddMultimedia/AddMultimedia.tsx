import React, { useState, useRef, useCallback } from 'react';
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

  const fileInputRef = useRef<HTMLInputElement>(null);

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
          URL.revokeObjectURL(url);
          resolve({
            preview: url,
            duration: video.duration,
            dimensions: { width: video.videoWidth, height: video.videoHeight }
          });
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
          URL.revokeObjectURL(url);
          resolve({
            duration: audio.duration
          });
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
        <div
          className={`multimedia-dropzone ${isDragging ? 'active' : ''}`}
          onClick={handleDropzoneClick}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
        >
          {selectedFile ? (
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
              
              {selectedFile.mediaType === 'image' && selectedFile.preview && (
                <div className="preview-container">
                  <img src={selectedFile.preview} alt="Preview" className="preview-image" />
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
          {selectedFile && (
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
          
          {!isConnected && (
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