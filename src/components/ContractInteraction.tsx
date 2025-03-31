import { useState } from 'react';
import { useBlockchain } from '../utils/BlockchainContext';
import { retrieveValue, storeValue } from '../utils/demoContract';
import './ContractInteraction.css';

const ContractInteraction = () => {
  const { isConnected, walletAddress } = useBlockchain();
  const [contractAddress, setContractAddress] = useState('');
  const [value, setValue] = useState('');
  const [storedValue, setStoredValue] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleRetrieve = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isConnected || !contractAddress) return;
    
    setIsLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      const result = await retrieveValue(contractAddress);
      setStoredValue(result.toString());
      setSuccess('Value retrieved successfully!');
    } catch (err: any) {
      setError(err.message || 'Error retrieving value');
      setStoredValue(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStore = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isConnected || !contractAddress || !value || !walletAddress) return;
    
    setIsLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      await storeValue(contractAddress, parseInt(value));
      setSuccess('Value stored successfully!');
    } catch (err: any) {
      setError(err.message || 'Error storing value');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isConnected) {
    return (
      <div className="contract-interaction disabled">
        <h2>Contract Interaction</h2>
        <p>Connect to a blockchain network to interact with contracts</p>
      </div>
    );
  }

  return (
    <div className="contract-interaction">
      <h2>Contract Interaction</h2>
      
      <div className="contract-form">
        <div className="form-group">
          <label htmlFor="contract-address">Contract Address:</label>
          <input
            id="contract-address"
            type="text"
            value={contractAddress}
            onChange={(e) => setContractAddress(e.target.value)}
            placeholder="0x..."
            className="input-field"
          />
        </div>
        
        <div className="actions-container">
          <div className="action-section">
            <h3>Read Contract</h3>
            <form onSubmit={handleRetrieve}>
              <button 
                type="submit"
                disabled={!contractAddress || isLoading}
                className="action-button read"
              >
                {isLoading ? 'Loading...' : 'Retrieve Value'}
              </button>
            </form>
            
            {storedValue !== null && (
              <div className="result-display">
                <h4>Stored Value:</h4>
                <div className="value-box">{storedValue}</div>
              </div>
            )}
          </div>
          
          <div className="action-section">
            <h3>Write Contract</h3>
            <form onSubmit={handleStore}>
              <div className="form-group">
                <label htmlFor="value-input">Value to Store:</label>
                <input
                  id="value-input"
                  type="number"
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  placeholder="Enter a number"
                  className="input-field"
                />
              </div>
              <button 
                type="submit"
                disabled={!contractAddress || !value || isLoading || !walletAddress}
                className="action-button write"
              >
                {isLoading ? 'Processing...' : 'Store Value'}
              </button>
            </form>
          </div>
        </div>
        
        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}
      </div>
    </div>
  );
};

export default ContractInteraction; 