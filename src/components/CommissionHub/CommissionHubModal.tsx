import React, { useState, useEffect } from 'react';
import { ethers } from 'ethers';
import { useBlockchain } from '../../utils/BlockchainContext';

// ABI fragments for CommissionHub contract
const COMMISSION_HUB_ABI = [
  'function chainId() view returns (uint256)',
  'function nftContract() view returns (address)',
  'function tokenId() view returns (uint256)',
  'function owner() view returns (address)',
  'function registry() view returns (address)',
  'function getVerifiedArts(uint256, uint256) view returns (address[])',
  'function artCount() view returns (uint256)',
  'function lastVerifiedArts(uint256) view returns (address)',
  'function gradeArt(address, uint8) nonpayable'
];

interface CommissionHubDetails {
  chainId: string;
  nftContract: string;
  tokenId: string;
  owner: string;
  registry: string;
  verifiedArts: string[];
}

interface VerifiedArtGrade {
  [key: string]: number | undefined;
}

interface CommissionHubModalProps {
  isOpen: boolean;
  onClose: () => void;
  hubAddress: string;
}

const CommissionHubModal: React.FC<CommissionHubModalProps> = ({ isOpen, onClose, hubAddress }) => {
  const { isConnected, connectWallet } = useBlockchain();
  const [hubDetails, setHubDetails] = useState<CommissionHubDetails | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [grades, setGrades] = useState<VerifiedArtGrade>({});
  const [submitting, setSubmitting] = useState<{ [key: string]: boolean }>({});

  useEffect(() => {
    if (isOpen && hubAddress) {
      fetchHubDetails();
    }
  }, [isOpen, hubAddress]);

  const fetchHubDetails = async () => {
    if (!ethers.isAddress(hubAddress)) {
      setError('Invalid CommissionHub address');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      if (!isConnected) {
        await connectWallet();
      }

      if (!window.ethereum) {
        throw new Error('MetaMask is not installed');
      }

      const provider = new ethers.BrowserProvider(window.ethereum);
      const commissionHub = new ethers.Contract(
        hubAddress,
        COMMISSION_HUB_ABI,
        provider
      );

      // Fetch basic details
      const [chainId, nftContract, tokenId, owner, registry, artCount] = await Promise.all([
        commissionHub.chainId(),
        commissionHub.nftContract(),
        commissionHub.tokenId(),
        commissionHub.owner(),
        commissionHub.registry(),
        commissionHub.artCount()
      ]);

      // Get the last 5 verified arts (or fewer if there aren't that many)
      const count = Math.min(Number(artCount), 5);
      const verifiedArts: string[] = [];

      for (let i = 0; i < count; i++) {
        const artAddress = await commissionHub.lastVerifiedArts(i);
        if (artAddress && artAddress !== ethers.ZeroAddress) {
          verifiedArts.push(artAddress);
        }
      }

      setHubDetails({
        chainId: chainId.toString(),
        nftContract,
        tokenId: tokenId.toString(),
        owner,
        registry,
        verifiedArts
      });
    } catch (err: any) {
      console.error('Error fetching CommissionHub details:', err);
      setError(err.message || 'An error occurred while fetching CommissionHub details');
    } finally {
      setLoading(false);
    }
  };

  const handleGradeChange = (artAddress: string, grade: string) => {
    const gradeNum = parseInt(grade);
    if (!isNaN(gradeNum) && gradeNum >= 0 && gradeNum <= 10) {
      setGrades(prev => ({
        ...prev,
        [artAddress]: gradeNum
      }));
    }
  };

  const submitGrade = async (artAddress: string) => {
    const grade = grades[artAddress];
    
    if (grade === undefined || grade < 0 || grade > 10) {
      setError('Grade must be between 0 and 10');
      return;
    }

    try {
      setSubmitting(prev => ({ ...prev, [artAddress]: true }));
      
      if (!window.ethereum) {
        throw new Error('MetaMask is not installed');
      }

      const provider = new ethers.BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();
      const commissionHub = new ethers.Contract(
        hubAddress,
        COMMISSION_HUB_ABI,
        signer
      );

      const tx = await commissionHub.gradeArt(artAddress, grade);
      await tx.wait();

      // Reset the grade for this art after successful submission
      setGrades(prev => {
        const newGrades = { ...prev };
        delete newGrades[artAddress];
        return newGrades;
      });

      setError(null);
    } catch (err: any) {
      console.error('Error submitting grade:', err);
      setError(err.message || 'An error occurred while submitting the grade');
    } finally {
      setSubmitting(prev => ({ ...prev, [artAddress]: false }));
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <button className="modal-close-button" onClick={onClose}>×</button>
        <h2 className="modal-title">CommissionHub Details</h2>
        
        {loading ? (
          <p>Loading CommissionHub details...</p>
        ) : error ? (
          <div className="error-message">{error}</div>
        ) : hubDetails ? (
          <>
            <div className="hub-details">
              <div className="hub-details-item">
                <span className="hub-details-label">Hub Address:</span>
                <span className="hub-details-value">{hubAddress}</span>
              </div>
              <div className="hub-details-item">
                <span className="hub-details-label">Chain ID:</span>
                <span className="hub-details-value">{hubDetails.chainId}</span>
              </div>
              <div className="hub-details-item">
                <span className="hub-details-label">NFT Contract:</span>
                <span className="hub-details-value">{hubDetails.nftContract}</span>
              </div>
              <div className="hub-details-item">
                <span className="hub-details-label">Token ID:</span>
                <span className="hub-details-value">{hubDetails.tokenId}</span>
              </div>
              <div className="hub-details-item">
                <span className="hub-details-label">Owner:</span>
                <span className="hub-details-value">{hubDetails.owner}</span>
              </div>
              <div className="hub-details-item">
                <span className="hub-details-label">Registry:</span>
                <span className="hub-details-value">{hubDetails.registry}</span>
              </div>
            </div>

            {hubDetails.verifiedArts.length > 0 && (
              <div className="verified-arts-section">
                <h3 className="verified-arts-title">Last Verified Arts</h3>
                {hubDetails.verifiedArts.map((artAddress, index) => (
                  <div key={index} className="verified-art-item">
                    <div className="verified-art-id">
                      <span className="hub-details-label">Art Address:</span>
                      <span className="hub-details-value">{artAddress}</span>
                    </div>
                    <div className="grade-form">
                      <input
                        type="number"
                        min="0"
                        max="10"
                        placeholder="Grade (0-10)"
                        className="grade-input"
                        value={grades[artAddress] !== undefined ? grades[artAddress] : ''}
                        onChange={(e) => handleGradeChange(artAddress, e.target.value)}
                      />
                      <button
                        className="grade-button"
                        disabled={grades[artAddress] === undefined || submitting[artAddress]}
                        onClick={() => submitGrade(artAddress)}
                      >
                        {submitting[artAddress] ? 'Submitting...' : 'Submit Grade'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        ) : (
          <p>No details available. Please enter a valid CommissionHub address.</p>
        )}
      </div>
    </div>
  );
};

export default CommissionHubModal; 