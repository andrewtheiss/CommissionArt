import React from 'react';
import CommissionedArt from './CommissionedArt';
import ArtCommissionHubModal from './ArtCommissionHubModal';
import './ArtCommissionHub.css';

const ArtCommissionHub: React.FC = () => {
  return (
    <div className="commission-hub-container">
      <CommissionedArt />
    </div>
  );
};

export default ArtCommissionHub;
export { CommissionedArt, ArtCommissionHubModal }; 