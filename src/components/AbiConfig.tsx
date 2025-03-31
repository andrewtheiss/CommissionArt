import React, { useState, useEffect } from 'react';
import './AbiConfig.css';

interface ContractConfig {
  name: string;
  abi: any[];
  addresses: {
    [chainId: string]: string;
  };
}

const AbiConfig: React.FC = () => {
  const [contracts, setContracts] = useState<ContractConfig[]>([]);
  const [selectedContract, setSelectedContract] = useState<ContractConfig | null>(null);
  const [newAddress, setNewAddress] = useState<{ chainId: string; address: string }>({
    chainId: '',
    address: '',
  });

  useEffect(() => {
    // TODO: Load contracts from storage or API
    const loadContracts = async () => {
      try {
        const response = await fetch('/api/contracts');
        const data = await response.json();
        setContracts(data);
      } catch (error) {
        console.error('Failed to load contracts:', error);
      }
    };
    loadContracts();
  }, []);

  const handleAddAddress = () => {
    if (!selectedContract || !newAddress.chainId || !newAddress.address) return;

    const updatedContracts = contracts.map(contract => {
      if (contract.name === selectedContract.name) {
        return {
          ...contract,
          addresses: {
            ...contract.addresses,
            [newAddress.chainId]: newAddress.address,
          },
        };
      }
      return contract;
    });

    setContracts(updatedContracts);
    setSelectedContract(updatedContracts.find(c => c.name === selectedContract.name) || null);
    setNewAddress({ chainId: '', address: '' });
  };

  const handleRemoveAddress = (chainId: string) => {
    if (!selectedContract) return;

    const updatedContracts = contracts.map(contract => {
      if (contract.name === selectedContract.name) {
        const { [chainId]: removed, ...remaining } = contract.addresses;
        return {
          ...contract,
          addresses: remaining,
        };
      }
      return contract;
    });

    setContracts(updatedContracts);
    setSelectedContract(updatedContracts.find(c => c.name === selectedContract.name) || null);
  };

  return (
    <div className="abi-config">
      <h2>ABI Configuration</h2>
      
      <div className="contracts-list">
        <h3>Available Contracts</h3>
        <div className="contracts-grid">
          {contracts.map((contract) => (
            <div
              key={contract.name}
              className={`contract-card ${selectedContract?.name === contract.name ? 'selected' : ''}`}
              onClick={() => setSelectedContract(contract)}
            >
              <h4>{contract.name}</h4>
              <div className="contract-addresses">
                {Object.entries(contract.addresses).map(([chainId, address]) => (
                  <div key={chainId} className="address-item">
                    <span className="chain-id">Chain {chainId}:</span>
                    <span className="address">{address}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {selectedContract && (
        <div className="contract-details">
          <h3>{selectedContract.name} Details</h3>
          <div className="abi-preview">
            <h4>ABI Preview</h4>
            <pre>{JSON.stringify(selectedContract.abi, null, 2)}</pre>
          </div>

          <div className="add-address">
            <h4>Add New Contract Address</h4>
            <div className="input-group">
              <input
                type="text"
                placeholder="Chain ID"
                value={newAddress.chainId}
                onChange={(e) => setNewAddress({ ...newAddress, chainId: e.target.value })}
              />
              <input
                type="text"
                placeholder="Contract Address"
                value={newAddress.address}
                onChange={(e) => setNewAddress({ ...newAddress, address: e.target.value })}
              />
              <button onClick={handleAddAddress}>Add Address</button>
            </div>
          </div>

          <div className="addresses-list">
            <h4>Contract Addresses</h4>
            {Object.entries(selectedContract.addresses).map(([chainId, address]) => (
              <div key={chainId} className="address-item">
                <span className="chain-id">Chain {chainId}:</span>
                <span className="address">{address}</span>
                <button onClick={() => handleRemoveAddress(chainId)}>Remove</button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default AbiConfig; 