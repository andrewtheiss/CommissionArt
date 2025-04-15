import React, { useState, useEffect } from 'react';
import { useBlockchain } from '../utils/BlockchainContext';
import './NFTRegistration.css';

const NFTRegistration: React.FC = () => {
  const [userType, setUserType] = useState<'none' | 'artist' | 'commissioner'>('none');
  const { isConnected, connectWallet, walletAddress, networkType } = useBlockchain();
  
  // Consider a wallet truly connected only when we have both isConnected flag AND a wallet address
  const isTrulyConnected = isConnected && !!walletAddress;

  // Reset form when component unmounts
  useEffect(() => {
    return () => {
      setUserType('none');
    };
  }, []);

  const handleUserTypeSelection = (type: 'artist' | 'commissioner') => {
    setUserType(type);
  };

  // Since we don't have a built-in disconnect method in our context,
  // we'll handle it by clearing state and forcing a reload
  const handleDisconnect = () => {
    // For future improvement: This should ideally be moved to the BlockchainContext
    if (window.ethereum && window.ethereum.removeAllListeners) {
      try {
        window.ethereum.removeAllListeners();
      } catch (err) {
        console.error("Failed to remove ethereum listeners:", err);
      }
    }
    
    // Store the current tab before refresh
    localStorage.setItem('active_tab', 'registration');
    
    // Use localStorage to indicate we want to disconnect on reload
    localStorage.setItem('wallet_disconnect_requested', 'true');
    
    // Force a proper wallet disconnect by clearing any cached provider state
    if (window.localStorage) {
      // Clear any wallet-related cached data
      const keysToRemove = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && (
            key.includes('wallet') || 
            key.includes('metamask') || 
            key.includes('ethereum') ||
            key.includes('connectedWallet') ||
            key.includes('connect') ||
            key.includes('walletconnect')
        )) {
          keysToRemove.push(key);
        }
      }
      
      // Remove the keys we found
      keysToRemove.forEach(key => {
        localStorage.removeItem(key);
      });
    }
    
    // Reload the page to clear the connection state
    window.location.reload();
  };

  // On component mount, check if we have a disconnect request in localStorage
  useEffect(() => {
    if (localStorage.getItem('wallet_disconnect_requested') === 'true') {
      // Clear the flag
      localStorage.removeItem('wallet_disconnect_requested');
      console.log("Wallet disconnected as requested");
      
      // If we're on this tab after a disconnect, let's manually disconnect from the wallet
      if (window.ethereum) {
        try {
          // Force the wallet UI to show as disconnected
          console.log("Clearing wallet connection after disconnect request");
          
          // Forcibly clear any provider and wallet state
          if (window.ethereum._state && window.ethereum._state.accounts) {
            window.ethereum._state.accounts = [];
          }
        } catch (err) {
          console.error("Error forcing wallet disconnect:", err);
        }
      }
    }
  }, []);

  // Connection Bar Component
  const ConnectionBar = () => (
    <div className="connection-bar">
      {!isTrulyConnected ? (
        <>
          <div className="connection-status disconnected">
            <span className="status-icon"></span>
            <span className="status-text">Wallet Not Connected</span>
          </div>
          <button 
            className="connect-wallet-button" 
            onClick={connectWallet}
          >
            Connect Wallet
          </button>
          
          {isConnected && !walletAddress && (
            <div className="connection-error-message">
              <p>Connection detected but no wallet address available. Please try reconnecting.</p>
            </div>
          )}
        </>
      ) : (
        <>
          <div className="connection-status connected">
            <span className="status-icon"></span>
            <div className="connection-details">
              <span className="status-text">Connected to: <span className="network-name">
                {networkType === 'arbitrum_testnet' ? 'L3 (Arbitrum Sepolia)' : networkType}
              </span></span>
              <span className="wallet-address">{walletAddress ? `${walletAddress.substring(0, 6)}...${walletAddress.substring(walletAddress.length - 4)}` : 'Not connected'}</span>
            </div>
          </div>
          <button 
            className="disconnect-wallet-button" 
            onClick={handleDisconnect}
          >
            Disconnect
          </button>
        </>
      )}
    </div>
  );

  // Artist form that adapts based on connection status
  const ArtistForm = () => {
    return (
      <div className="registration-form">
        <h3>Artist Registration</h3>
        <div className="form-instructions">
          <p>
            As an artist, you'll be able to create and register your artwork on-chain.
          </p>
          {!isTrulyConnected && (
            <p className="connect-reminder">
              <span className="highlight">Please connect your wallet</span> to access the full artist registration features.
            </p>
          )}
        </div>
        <form>
          {isTrulyConnected ? (
            // Connected artist form
            <div className="form-content">
              <div className="form-group">
                <label>Artist form coming soon...</label>
                <p>Your wallet is connected and you can register as an artist.</p>
              </div>
            </div>
          ) : (
            // Not connected artist form
            <div className="form-content disabled">
              <div className="form-group">
                <label>Artist features will be available once connected</label>
                <div className="placeholder-content"></div>
              </div>
            </div>
          )}
          <button type="button" className="form-back-button" onClick={() => setUserType('none')}>
            Back
          </button>
        </form>
      </div>
    );
  };

  // Commissioner form that adapts based on connection status
  const CommissionerForm = () => {
    return (
      <div className="registration-form">
        <h3>Commissioner Registration</h3>
        <div className="form-instructions">
          <p>
            As a commissioner, you can request and fund new commissioned artworks.
          </p>
          {!isTrulyConnected && (
            <p className="connect-reminder">
              <span className="highlight">Please connect your wallet</span> to access the full commissioner registration features.
            </p>
          )}
        </div>
        <form>
          {isTrulyConnected ? (
            // Connected commissioner form
            <div className="form-content">
              <div className="form-group">
                <label>Commissioner form coming soon...</label>
                <p>Your wallet is connected and you can register as a commissioner.</p>
              </div>
            </div>
          ) : (
            // Not connected commissioner form
            <div className="form-content disabled">
              <div className="form-group">
                <label>Commissioner features will be available once connected</label>
                <div className="placeholder-content"></div>
              </div>
            </div>
          )}
          <button type="button" className="form-back-button" onClick={() => setUserType('none')}>
            Back
          </button>
        </form>
      </div>
    );
  };

  return (
    <div className="nft-registration-container">
      <h2>Commission Art</h2>
      
      {/* Always show the connection bar at the top */}
      <ConnectionBar />
      
      {/* Always show the user type selection or corresponding form */}
      {userType === 'none' ? (
        <div className="user-type-selection">
          <p className="selection-prompt">I'm a:</p>
          <div className="selection-buttons">
            <button 
              className="selection-button artist-button"
              onClick={() => handleUserTypeSelection('artist')}
            >
              Artist
            </button>
            <button 
              className="selection-button commissioner-button"
              onClick={() => handleUserTypeSelection('commissioner')}
            >
              Commissioner
            </button>
          </div>
        </div>
      ) : userType === 'artist' ? (
        <ArtistForm />
      ) : (
        <CommissionerForm />
      )}
    </div>
  );
};

export default NFTRegistration; 