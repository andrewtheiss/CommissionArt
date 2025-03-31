import { useState } from 'react'
import './App.css'

function App() {
  const [imageData, setImageData] = useState<string | null>(null);
  const [rawData, setRawData] = useState<string | null>(null);

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    
    // Read the file as DataURL (base64)
    reader.readAsDataURL(file);
    
    reader.onload = () => {
      const dataUrl = reader.result as string;
      setImageData(dataUrl);
      
      // Convert to raw data (array buffer)
      const rawReader = new FileReader();
      rawReader.readAsArrayBuffer(file);
      
      rawReader.onload = () => {
        const arrayBuffer = rawReader.result as ArrayBuffer;
        const uint8Array = new Uint8Array(arrayBuffer);
        
        // Convert to hex string for display
        const hexString = Array.from(uint8Array)
          .map(b => b.toString(16).padStart(2, '0'))
          .join(' ');
        
        setRawData(hexString);
      };
    };
  };

  return (
    <div className="container">
      <h1>Image to Raw Data Converter</h1>
      
      <div className="upload-section">
        <label htmlFor="image-upload" className="upload-button">
          Choose Image
          <input
            id="image-upload"
            type="file"
            accept="image/*"
            onChange={handleFileUpload}
            style={{ display: 'none' }}
          />
        </label>
      </div>
      
      {imageData && (
        <div className="image-preview">
          <h2>Image Preview</h2>
          <img src={imageData} alt="Uploaded preview" />
        </div>
      )}
      
      {rawData && (
        <div className="raw-data">
          <h2>Raw Image Data (Hex)</h2>
          <div className="data-container">
            {rawData}
          </div>
        </div>
      )}
    </div>
  )
}

export default App
