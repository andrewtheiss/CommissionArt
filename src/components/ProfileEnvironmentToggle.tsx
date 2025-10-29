import React, { useState, useEffect } from 'react';
import { useBlockchain } from '../utils/BlockchainContext';

interface ProfileEnvironmentToggleProps {
  className?: string;
}

// Three-option environment selector: Mainnet (L3), Testnet (L2 Sepolia), Arbitrum (L2 Mainnet)
const ProfileEnvironmentToggle: React.FC<ProfileEnvironmentToggleProps> = ({ className = '' }) => {
  const { switchToLayer } = useBlockchain();
  const [selectedEnv, setSelectedEnv] = useState<'mainnet' | 'testnet' | 'arbitrum'>(() => {
    const saved = localStorage.getItem('profile-env-selection') as 'mainnet' | 'testnet' | 'arbitrum' | null;
    if (saved === 'mainnet' || saved === 'testnet' || saved === 'arbitrum') {
      return saved;
    }
    const legacy = localStorage.getItem('profile-use-testnet');
    const legacyBool = legacy ? JSON.parse(legacy) : false;
    return legacyBool ? 'testnet' : 'mainnet';
  });
  const [isSwitching, setIsSwitching] = useState<boolean>(false);

  useEffect(() => {
    // Persist selection and maintain legacy key for compatibility
    localStorage.setItem('profile-env-selection', selectedEnv);
    localStorage.setItem('profile-use-testnet', JSON.stringify(selectedEnv === 'testnet'));
  }, [selectedEnv]);

  const performSwitch = async (target: 'mainnet' | 'testnet' | 'arbitrum') => {
    if (target === selectedEnv) return;
    setIsSwitching(true);
    try {
      if (target === 'mainnet') {
        console.log('[ProfileEnvironmentToggle] switchToLayer(l3, mainnet)');
        await switchToLayer('l3', 'mainnet');
      } else if (target === 'testnet') {
        // Keep existing behavior: Testnet maps to Arbitrum Sepolia (L2)
        console.log('[ProfileEnvironmentToggle] switchToLayer(l2, testnet)');
        await switchToLayer('l2', 'testnet');
      } else {
        // Arbitrum (L2 mainnet)
        console.log('[ProfileEnvironmentToggle] switchToLayer(l2, mainnet)');
        await switchToLayer('l2', 'mainnet');
      }
      setSelectedEnv(target);
      window.dispatchEvent(new Event('profile-environment-changed'));
    } catch (error) {
      console.error('[ProfileEnvironmentToggle] Failed to switch network:', error);
      alert(`Failed to switch network: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsSwitching(false);
    }
  };

  return (
    <div className={`profile-environment-toggle ${className}`}>
      <div className="toggle-container">
        <span className="toggle-label">Environment:</span>
        <div className="env-segmented">
          <button
            type="button"
            className={`env-btn ${selectedEnv === 'mainnet' ? 'active' : ''}`}
            onClick={() => performSwitch('mainnet')}
            disabled={isSwitching}
            title="AnimeChain L3"
          >
            Mainnet
          </button>
          <button
            type="button"
            className={`env-btn ${selectedEnv === 'testnet' ? 'active' : ''}`}
            onClick={() => performSwitch('testnet')}
            disabled={isSwitching}
            title="Arbitrum Sepolia (L2)"
          >
            Testnet
          </button>
          <button
            type="button"
            className={`env-btn ${selectedEnv === 'arbitrum' ? 'active' : ''}`}
            onClick={() => performSwitch('arbitrum')}
            disabled={isSwitching}
            title="Arbitrum One (L2)"
          >
            Arbitrum (L2)
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProfileEnvironmentToggle;