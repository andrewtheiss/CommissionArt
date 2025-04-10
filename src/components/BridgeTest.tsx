const renderNFTQueryForm = () => {
  // ... existing code ...
  return (
    <div className="nft-query-section">
      <h3>Query NFT Ownership</h3>
      <div className="notice-message">
        <p><strong>Important:</strong> Querying NFT ownership requires sending a message from Arbitrum (L2) to Ethereum (L1) and back. This cross-chain messaging process takes time to complete.</p>
        <p>Please wait approximately 10-15 minutes for the ownership information to be retrieved. The app will automatically update the status when a response is received.</p>
        <p>If you encounter connection issues or RPC errors, the app will attempt to use alternative endpoints.</p>
      </div>
      
      <form className="nft-query-form" onSubmit={handleNFTQuery}>
        <div className="input-group">
          <label htmlFor="nftContract">NFT Contract Address:</label>
          <input
            id="nftContract"
            type="text"
            value={nftContract}
            onChange={e => setNftContract(e.target.value)}
            disabled={!connectedToArbitrum || submitting}
            placeholder="0x..."
            required
          />
        </div>
        
        <div className="input-group">
          <label htmlFor="tokenId">Token ID:</label>
          <input
            id="tokenId"
            type="text"
            value={tokenId}
            onChange={e => setTokenId(e.target.value)}
            disabled={!connectedToArbitrum || submitting}
            placeholder="123"
            required
          />
        </div>
        
        <div className="input-group">
          <label htmlFor="ethValue">ETH Value (for cross-chain message fees):</label>
          <input
            id="ethValue"
            type="text"
            value={ethValue}
            onChange={e => setEthValue(e.target.value)}
            disabled={!connectedToArbitrum || submitting}
            placeholder="0.005"
            required
          />
          <span className="field-help">Recommended minimum: 0.005 ETH for cross-chain message fees</span>
        </div>
        
        <div className="action-buttons">
          {!account ? (
            <button
              type="button"
              className="connect-button"
              onClick={handleConnect}
            >
              Connect Wallet
            </button>
          ) : (
            <button
              type="submit"
              className={`submit-button ${submitting ? 'processing' : ''}`}
              disabled={!connectedToArbitrum || submitting}
            >
              {submitting ? 'Processing...' : 'Query Ownership'}
            </button>
          )}
        </div>
      </form>
      
      {/* ... existing code ... */}
    </div>
  );
}; 