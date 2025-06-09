import React, { useState } from 'react';
import { useBlockchain } from '../../utils/BlockchainContext';
import ComprehensiveUpload from '../ComprehensiveUpload/ComprehensiveUpload';
import './NFTRegistration.css';

const NFTRegistration: React.FC = () => {
  const [userType, setUserType] = useState<'artist' | 'commissioner' | null>(null);
  const { isConnected, connectWallet, walletAddress, networkType } = useBlockchain();

  const isTrulyConnected = isConnected && !!walletAddress;

  const handleUserTypeSelection = (type: 'artist' | 'commissioner') => {
    setUserType(type);
  };

  const handleDisconnect = () => {
    if (window.ethereum && window.ethereum.removeAllListeners) {
      try {
        window.ethereum.removeAllListeners();
      } catch (err) {
        console.error("Failed to remove ethereum listeners:", err);
      }
    }
    localStorage.setItem('active_tab', 'registration');
    localStorage.setItem('wallet_disconnect_requested', 'true');
    window.location.reload();
  };

  const ConnectionBar = () => (
    <div className="connection-bar">
      <div className={`connection-status ${isTrulyConnected ? 'connected' : 'disconnected'}`}>
        <span className="status-icon"></span>
        <div className="connection-details">
          {isTrulyConnected ? (
            <>
              <span className="status-text">
                Connected <span className="network-name">{networkType}</span>
              </span>
              <span className="wallet-address">{walletAddress}</span>
            </>
          ) : (
            <span className="status-text">Not Connected</span>
          )}
        </div>
      </div>
      {isTrulyConnected ? (
        <button className="disconnect-wallet-button" onClick={handleDisconnect}>
          Disconnect
        </button>
      ) : (
        <button className="connect-wallet-button" onClick={() => connectWallet()}>
          Connect Wallet
        </button>
      )}
      {isTrulyConnected && networkType !== 'animechain' && (
        <div className="connection-error-message">
          <p><strong>Wrong Network!</strong> Please switch to AnimeChain to register artwork.</p>
        </div>
      )}
    </div>
  );

  const renderContent = () => {
    if (userType === null) {
      return (
        <div className="user-type-selection">
          <p className="selection-prompt">I'm a:</p>
          <div className="selection-buttons">
            <button className="selection-button artist-button" onClick={() => handleUserTypeSelection('artist')}>
              Artist
            </button>
            <button className="selection-button commissioner-button" onClick={() => handleUserTypeSelection('commissioner')}>
              Commissioner
            </button>
          </div>
        </div>
      );
    } else if (userType === 'artist') {
      return <ComprehensiveUpload onBack={() => setUserType(null)} userType="artist" />;
    } else {
      return <ComprehensiveUpload onBack={() => setUserType(null)} userType="commissioner" />;
    }
  };

  return (
    <div className="nft-registration-container">
      <h2>Commission Art</h2>
      <ConnectionBar />
      {renderContent()}
    </div>
  );
};

export default NFTRegistration;