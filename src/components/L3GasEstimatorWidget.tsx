import React, { useState, useEffect } from 'react';
import { estimateL3Gas, formatWeiToEth, formatWeiToGwei, L3GasEstimates } from '../utils/l3GasEstimator';

interface L3GasEstimatorWidgetProps {
  nftContract: string;
  tokenId: string;
  ownerAddress: string;
  onGasEstimated?: (estimates: L3GasEstimates) => void;
}

const L3GasEstimatorWidget: React.FC<L3GasEstimatorWidgetProps> = ({
  nftContract,
  tokenId,
  ownerAddress,
  onGasEstimated
}) => {
  const [gasEstimates, setGasEstimates] = useState<L3GasEstimates | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const estimateGas = async () => {
    if (!nftContract || !tokenId || !ownerAddress) {
      setError('Please fill in all fields to estimate gas');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const estimates = await estimateL3Gas(nftContract, tokenId, ownerAddress);
      setGasEstimates(estimates);
      setLastUpdated(new Date());
      
      // Call the callback if provided
      if (onGasEstimated) {
        onGasEstimated(estimates);
      }
    } catch (err: any) {
      setError(`Failed to estimate gas: ${err.message || 'Unknown error'}`);
      console.error('Gas estimation error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Auto-estimate gas when inputs change
  useEffect(() => {
    if (nftContract && tokenId && ownerAddress) {
      estimateGas();
    }
  }, [nftContract, tokenId, ownerAddress]);

  return (
    <div className="l3-gas-estimator">
      <div className="estimator-header">
        <h3>L3 Mainnet Gas Estimates</h3>
        <button 
          className="refresh-button" 
          onClick={estimateGas} 
          disabled={isLoading}
        >
          {isLoading ? 'Estimating...' : 'Refresh'}
        </button>
      </div>

      {error && (
        <div className="error-message">{error}</div>
      )}

      {gasEstimates && (
        <div className="gas-estimates">
          <div className="estimate-row">
            <span className="estimate-label">Max Submission Cost:</span>
            <span className="estimate-value">{formatWeiToEth(gasEstimates.maxSubmissionCost)} ETH</span>
          </div>
          <div className="estimate-row">
            <span className="estimate-label">Gas Limit:</span>
            <span className="estimate-value">{gasEstimates.gasLimit} units</span>
          </div>
          <div className="estimate-row">
            <span className="estimate-label">Max Fee Per Gas:</span>
            <span className="estimate-value">{formatWeiToGwei(gasEstimates.maxFeePerGas)} Gwei</span>
          </div>
          <div className="estimate-row">
            <span className="estimate-label">Current L3 Gas Price:</span>
            <span className="estimate-value">{formatWeiToGwei(gasEstimates.l3GasPrice)} Gwei</span>
          </div>
          <div className="estimate-row total">
            <span className="estimate-label">Total Estimated Cost:</span>
            <span className="estimate-value">{formatWeiToEth(gasEstimates.totalCost)} ETH</span>
          </div>
          {lastUpdated && (
            <div className="last-updated">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default L3GasEstimatorWidget; 