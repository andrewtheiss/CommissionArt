import React from 'react';
import CommissionedArt from './CommissionedArt';
import CommissionHubModal from './CommissionHubModal';
import './CommissionHub.css';

const CommissionHub: React.FC = () => {
  return (
    <div className="commission-hub-container">
      <CommissionedArt />
    </div>
  );
};

export default CommissionHub;
export { CommissionedArt, CommissionHubModal }; 