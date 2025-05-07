import React, { useState, useEffect } from 'react';
import { useBlockchain } from '../utils/BlockchainContext';

interface ProfileEnvironmentToggleProps {
  className?: string;
}

const ProfileEnvironmentToggle: React.FC<ProfileEnvironmentToggleProps> = ({ className = '' }) => {
  const { switchToLayer } = useBlockchain();
  const [useL2Testnet, setUseL2Testnet] = useState<boolean>(() => {
    // Get the saved preference or default to false (L3)
    const saved = localStorage.getItem('profile-use-l2-testnet');
    return saved ? JSON.parse(saved) : false;
  });

  // Save preference to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('profile-use-l2-testnet', JSON.stringify(useL2Testnet));
  }, [useL2Testnet]);

  const handleToggle = () => {
    const newValue = !useL2Testnet;
    setUseL2Testnet(newValue);
    
    // Switch network layer based on toggle selection
    if (newValue) {
      // Switch to L2 testnet for profiles
      switchToLayer('l2', 'testnet');
    } else {
      // Switch to L3 for profiles (default)
      switchToLayer('l3', 'mainnet');
    }
    
    // Dispatch custom event to notify components of the change
    window.dispatchEvent(new Event('profile-layer-changed'));
  };

  return (
    <div className={`profile-environment-toggle ${className}`}>
      <div className="toggle-container">
        <span className="toggle-label">Profile Environment:</span>
        <label className="toggle-switch">
          <input 
            type="checkbox" 
            checked={useL2Testnet} 
            onChange={handleToggle} 
          />
          <span className="toggle-slider"></span>
        </label>
        <span className="toggle-value">
          {useL2Testnet ? 'L2 Testnet' : 'L3 AnimeChain'}
        </span>
      </div>
    </div>
  );
};

export default ProfileEnvironmentToggle;