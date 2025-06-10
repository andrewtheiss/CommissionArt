import { compressImage as compress } from './ImageCompressorUtil';
import type { FormatType, CompressionResult as UtilCompressionResult } from './ImageCompressorUtil';

export interface CompressionResult {
  dataUrl: string;
  byteArray: Uint8Array;
  width: number;
  height: number;
  sizeKB: number;
  format: string;
}

export interface CompressionOptions {
  format: 'webp' | 'jpeg' | 'avif';
  quality: number;
  maxWidth: number | null;
  maxHeight: number | null;
  targetSizeKB?: number;
  autoOptimize?: boolean;
}

export const fileToDataUrl = (file: File | Blob): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsDataURL(file);
  });
};

export const dataUrlToByteArray = (dataUrl: string): Uint8Array => {
  const base64 = dataUrl.split(',')[1];
  const binaryString = window.atob(base64);
  const len = binaryString.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes;
};


export const getImageInfo = async (file: File) => {
  const dataUrl = await fileToDataUrl(file);
  const img = document.createElement('img');
  const imageLoaded = new Promise<{ width: number; height: number }>((resolve) => {
    img.onload = () => {
      resolve({ width: img.width, height: img.height });
    };
    img.src = dataUrl;
  });
  const dimensions = await imageLoaded;
  return {
    dataUrl,
    sizeKB: file.size / 1024,
    dimensions,
    format: file.type.split('/')[1].toUpperCase(),
  };
};

export const compressImage = async (file: File, options: CompressionOptions): Promise<CompressionResult> => {
  const format = options.format.replace('image/', '') as FormatType;
  const result: UtilCompressionResult = await compress(file, format, options.maxWidth || 1000, options.targetSizeKB || 43);
  
  if (!result.success || !result.blob || !result.preview) {
    throw new Error(result.error || 'Compression failed');
  }

  const byteArray = new Uint8Array(await result.blob.arrayBuffer());

  // If dimensions are 0 (compression was skipped), get them from the original file
  let width = result.dimensions.width;
  let height = result.dimensions.height;
  
  if (width === 0 || height === 0) {
    // Get dimensions from the original file
    const img = document.createElement('img');
    const dataUrl = await fileToDataUrl(file);
    
    await new Promise<void>((resolve) => {
      img.onload = () => {
        width = img.width;
        height = img.height;
        resolve();
      };
      img.src = dataUrl;
    });
  }

  return {
    dataUrl: result.preview,
    byteArray,
    width,
    height,
    sizeKB: result.compressedSize,
    format: result.format,
  };
}; 