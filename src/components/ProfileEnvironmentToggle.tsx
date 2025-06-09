import React, { useState, useEffect } from 'react';
import { useBlockchain } from '../utils/BlockchainContext';

interface ProfileEnvironmentToggleProps {
  className?: string;
}

const ProfileEnvironmentToggle: React.FC<ProfileEnvironmentToggleProps> = ({ className = '' }) => {
  const { switchToLayer } = useBlockchain();
  const [useTestnet, setUseTestnet] = useState<boolean>(() => {
    // Get the saved preference or default to false (Mainnet)
    const saved = localStorage.getItem('profile-use-testnet');
    return saved ? JSON.parse(saved) : false;
  });
  const [isSwitching, setIsSwitching] = useState<boolean>(false);

  // Save preference to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('profile-use-testnet', JSON.stringify(useTestnet));
  }, [useTestnet]);

  const handleToggle = async () => {
    const newValue = !useTestnet;
    setIsSwitching(true);
    
    console.log(`[ProfileEnvironmentToggle] Starting network switch: ${!newValue ? 'Mainnet' : 'Testnet'} -> ${newValue ? 'Testnet' : 'Mainnet'}`);
    
    try {
      // Switch network based on toggle selection
      if (newValue) {
        // Switch to Testnet (Arbitrum Sepolia)
        console.log('[ProfileEnvironmentToggle] Calling switchToLayer(l2, testnet)');
        await switchToLayer('l2', 'testnet');
        console.log('[ProfileEnvironmentToggle] Successfully switched to Testnet');
      } else {
        // Switch to Mainnet (AnimeChain)
        console.log('[ProfileEnvironmentToggle] Calling switchToLayer(l3, mainnet)');
        await switchToLayer('l3', 'mainnet');
        console.log('[ProfileEnvironmentToggle] Successfully switched to Mainnet');
      }
      
      // Only update state if network switch was successful
      setUseTestnet(newValue);
      
      // Dispatch custom event to notify components of the change
      window.dispatchEvent(new Event('profile-environment-changed'));
    } catch (error) {
      console.error('[ProfileEnvironmentToggle] Failed to switch network:', error);
      // Don't update the toggle state if network switch failed
      alert(`Failed to switch network: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsSwitching(false);
    }
  };

  return (
    <div className={`profile-environment-toggle ${className}`}>
      <div className="toggle-container">
        <span className="toggle-label">Environment:</span>
        <div className="toggle-wrapper">
          <span className={`toggle-option-label left ${!useTestnet ? 'active' : ''}`}>
            Mainnet
          </span>
          <label className="toggle-switch">
            <input 
              type="checkbox" 
              checked={useTestnet} 
              onChange={handleToggle}
              disabled={isSwitching}
            />
            <span className={`toggle-slider ${isSwitching ? 'switching' : ''}`}>
              {isSwitching && <span className="switching-indicator">⟳</span>}
            </span>
          </label>
          <span className={`toggle-option-label right ${useTestnet ? 'active' : ''}`}>
            Testnet
          </span>
        </div>
      </div>
    </div>
  );
};

export default ProfileEnvironmentToggle;