import { useState, useEffect } from 'react';
import { useBlockchain } from '../utils/BlockchainContext';

const NetworkSelector = () => {
  const { networkType, switchNetwork, isConnected, connectWallet, walletAddress } = useBlockchain();
  const [selectedNetwork, setSelectedNetwork] = useState(networkType);

  // Keep local state in sync with context
  useEffect(() => {
    setSelectedNetwork(networkType);
  }, [networkType]);

  const handleNetworkChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newNetwork = e.target.value as 'animechain' | 'dev' | 'prod' | 'local';
    setSelectedNetwork(newNetwork); // Update local state immediately for UI
    switchNetwork(newNetwork); // Update the actual connection
  };

  return (
    <div className="network-selector">
      <div className="network-status">
        <span>Network: </span>
        <select 
          value={selectedNetwork}
          onChange={handleNetworkChange}
          className="network-dropdown"
        >
          <option value="animechain">AnimeChain L3</option>
          <option value="dev">Development (Sepolia)</option>
          <option value="prod">Production (Mainnet)</option>
          <option value="local">Local Ganache (127.0.0.1:8545)</option>
        </select>
        
        <span className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
          {isConnected ? '● Connected' : '○ Disconnected'}
        </span>
      </div>

      <div className="wallet-section">
        {walletAddress ? (
          <div className="wallet-info">
            <span>Connected: </span>
            <span className="wallet-address">{`${walletAddress.substring(0, 6)}...${walletAddress.substring(38)}`}</span>
          </div>
        ) : (
          <button 
            onClick={connectWallet} 
            className="connect-wallet-btn"
          >
            Connect Wallet
          </button>
        )}
      </div>
    </div>
  );
};

export default NetworkSelector; 