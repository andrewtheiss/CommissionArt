import React, { useState } from 'react';
import { ethers } from 'ethers';
import ethersService from '../../utils/ethers-service';
import abiLoader from '../../utils/abiLoader';

interface CrossChainWhitelistFormProps {
  editionAddress: string;
}

const CrossChainWhitelistForm: React.FC<CrossChainWhitelistFormProps> = ({ editionAddress }) => {
  const [inputAddress, setInputAddress] = useState<string>('');
  const [aliasedAddress, setAliasedAddress] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [whitelisting, setWhitelisting] = useState<boolean>(false);
  const [currentBypassAddress, setCurrentBypassAddress] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');

  // Load current bypass address on component mount
  React.useEffect(() => {
    loadCurrentBypassAddress();
  }, [editionAddress]);

  const loadCurrentBypassAddress = async () => {
    if (!editionAddress) return;
    
    try {
      const provider = ethersService.getProvider();
      if (!provider) return;

      const artEditionAbi = abiLoader.loadABI('ArtEdition1155');
      if (!artEditionAbi) return;

      const editionContract = new ethers.Contract(editionAddress, artEditionAbi, provider);
      const bypassAddr = await editionContract.getBypassAddress();
      setCurrentBypassAddress(bypassAddr || '0x0000000000000000000000000000000000000000');
    } catch (err) {
      console.error('Error loading bypass address:', err);
    }
  };

  const handleGetAliasedAddress = async () => {
    if (!inputAddress.trim()) {
      setError('Please enter an address');
      return;
    }

    if (!ethers.isAddress(inputAddress.trim())) {
      setError('Please enter a valid Ethereum address');
      return;
    }

    try {
      setLoading(true);
      setError('');
      setSuccess('');

      const provider = ethersService.getProvider();
      if (!provider) {
        throw new Error('No provider available');
      }

      const artEditionAbi = abiLoader.loadABI('ArtEdition1155');
      if (!artEditionAbi) {
        throw new Error('ArtEdition1155 ABI not found');
      }

      const editionContract = new ethers.Contract(editionAddress, artEditionAbi, provider);
      const aliased = await editionContract.getAliasedAddress(inputAddress.trim());
      
      setAliasedAddress(aliased);
      setSuccess('Aliased address generated successfully!');
    } catch (err: any) {
      console.error('Error getting aliased address:', err);
      setError(`Failed to get aliased address: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleWhitelistAddress = async () => {
    if (!aliasedAddress) {
      setError('Please generate an aliased address first');
      return;
    }

    try {
      setWhitelisting(true);
      setError('');
      setSuccess('');

      const signer = await ethersService.getSigner();
      if (!signer) {
        throw new Error('Wallet not connected');
      }

      const artEditionAbi = abiLoader.loadABI('ArtEdition1155');
      if (!artEditionAbi) {
        throw new Error('ArtEdition1155 ABI not found');
      }

      const editionContract = new ethers.Contract(editionAddress, artEditionAbi, signer);
      
      console.log('Whitelisting address for cross-chain update:', aliasedAddress);
      const tx = await editionContract.whitelistForCrossChainUpdate(aliasedAddress);
      console.log('Whitelist transaction:', tx.hash);
      
      // Wait for transaction confirmation
      await tx.wait();
      console.log('Whitelist transaction confirmed');
      
      setSuccess(`Address ${aliasedAddress} has been whitelisted for cross-chain updates!`);
      
      // Reload the current bypass address
      loadCurrentBypassAddress();
      
    } catch (err: any) {
      console.error('Error whitelisting address:', err);
      if (err.message?.includes('Only owner')) {
        setError('Only the contract owner can whitelist addresses');
      } else {
        setError(`Failed to whitelist address: ${err.message}`);
      }
    } finally {
      setWhitelisting(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setInputAddress(value);
    
    // Clear aliased address when input changes
    if (aliasedAddress) {
      setAliasedAddress('');
    }
    
    // Clear messages
    setError('');
    setSuccess('');
  };

  const formatAddress = (address: string): string => {
    if (!address || address === '0x0000000000000000000000000000000000000000') {
      return 'None set';
    }
    return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
  };

  return (
    <div className="cross-chain-whitelist-form">
      <div style={{marginBottom: '16px'}}>
        <div><strong>Current Bypass Address:</strong></div>
        <div style={{
          fontFamily: 'monospace', 
          fontSize: '0.9em', 
          color: 'var(--text-secondary)', 
          padding: '4px 8px', 
          backgroundColor: 'var(--background-secondary)', 
          borderRadius: '4px', 
          margin: '4px 0'
        }}>
          {currentBypassAddress === '0x0000000000000000000000000000000000000000' ? 'None set' : currentBypassAddress}
        </div>
      </div>

      <div style={{marginBottom: '16px'}}>
        <label htmlFor="l1-address" style={{display: 'block', marginBottom: '8px', fontWeight: 'bold'}}>
          L1 Address to Whitelist:
        </label>
        <input
          id="l1-address"
          type="text"
          value={inputAddress}
          onChange={handleInputChange}
          placeholder="0x1234567890123456789012345678901234567890"
          style={{
            width: '100%',
            padding: '8px 12px',
            border: '1px solid var(--border-primary)',
            borderRadius: '4px',
            fontSize: '0.9em',
            fontFamily: 'monospace',
            backgroundColor: 'var(--input-background)',
            color: 'var(--text-primary)'
          }}
          disabled={loading || whitelisting}
        />
      </div>

      <div style={{marginBottom: '16px'}}>
        <label style={{display: 'block', marginBottom: '8px', fontWeight: 'bold'}}>
          Aliased Address (Auto-generated):
        </label>
        <input
          type="text"
          value={aliasedAddress}
          readOnly
          placeholder="Generated aliased address will appear here"
          style={{
            width: '100%',
            padding: '8px 12px',
            border: '1px solid var(--border-secondary)',
            borderRadius: '4px',
            fontSize: '0.9em',
            fontFamily: 'monospace',
            backgroundColor: 'var(--background-secondary)',
            color: 'var(--text-secondary)',
            cursor: 'not-allowed'
          }}
        />
      </div>

      <div style={{display: 'flex', gap: '12px', marginBottom: '16px'}}>
        <button
          onClick={handleGetAliasedAddress}
          disabled={loading || whitelisting || !inputAddress.trim()}
          style={{
            flex: 1,
            padding: '10px 16px',
            backgroundColor: loading ? 'var(--button-disabled)' : 'var(--button-secondary)',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            fontSize: '0.9em',
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading || !inputAddress.trim() ? 0.6 : 1
          }}
        >
          {loading ? 'Generating...' : 'Get Aliased Address'}
        </button>

        <button
          onClick={handleWhitelistAddress}
          disabled={whitelisting || !aliasedAddress}
          style={{
            flex: 1,
            padding: '10px 16px',
            backgroundColor: whitelisting || !aliasedAddress ? 'var(--button-disabled)' : 'var(--button-primary)',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            fontSize: '0.9em',
            cursor: whitelisting || !aliasedAddress ? 'not-allowed' : 'pointer',
            opacity: whitelisting || !aliasedAddress ? 0.6 : 1
          }}
        >
          {whitelisting ? 'Whitelisting...' : 'Whitelist Address'}
        </button>
      </div>

      {error && (
        <div style={{
          padding: '12px',
          backgroundColor: 'rgba(255, 0, 0, 0.1)',
          border: '1px solid rgba(255, 0, 0, 0.3)',
          borderRadius: '4px',
          color: 'red',
          fontSize: '0.9em',
          marginBottom: '12px'
        }}>
          {error}
        </div>
      )}

      {success && (
        <div style={{
          padding: '12px',
          backgroundColor: 'rgba(0, 255, 0, 0.1)',
          border: '1px solid rgba(0, 255, 0, 0.3)',
          borderRadius: '4px',
          color: 'green',
          fontSize: '0.9em',
          marginBottom: '12px'
        }}>
          {success}
        </div>
      )}

      <div style={{
        fontSize: '0.8em',
        color: 'var(--text-secondary)',
        lineHeight: '1.4',
        padding: '12px',
        backgroundColor: 'var(--background-tertiary)',
        borderRadius: '4px',
        border: '1px solid var(--border-secondary)'
      }}>
        <div style={{fontWeight: 'bold', marginBottom: '8px'}}>ℹ️ Cross-Chain Instructions:</div>
        <div>1. Enter the L1 address you want to whitelist for cross-chain operations</div>
        <div>2. Click "Get Aliased Address" to generate the L2 alias</div>
        <div>3. Click "Whitelist Address" to authorize the aliased address for cross-chain updates</div>
        <div style={{marginTop: '8px', fontStyle: 'italic'}}>
          Only the contract owner can whitelist addresses for cross-chain functionality.
        </div>
      </div>
    </div>
  );
};

export default CrossChainWhitelistForm; 