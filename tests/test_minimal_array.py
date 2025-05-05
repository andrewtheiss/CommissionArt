import pytest
from ape import accounts, project

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    owner = accounts.test_accounts[1]
    
    # Deploy Profile template
    profile_template = project.Profile.deploy(sender=deployer)
    
    # Deploy ProfileHub
    profile_hub = project.ProfileHub.deploy(profile_template.address, sender=deployer)
    
    # Create a profile for testing
    profile_hub.createProfile(sender=owner)
    
    profile_address = profile_hub.getProfile(owner.address)
    profile = project.Profile.at(profile_address)
    
    return {
        "deployer": deployer,
        "owner": owner,
        "profile": profile,
        "profile_hub": profile_hub
    }

def test_minimal_commission_array(setup):
    """Test minimal commission array functionality"""
    owner = setup["owner"]
    profile = setup["profile"]
    
    # Test initial state
    assert profile.commissionCount() == 0
    
    # Test adding a commission
    test_commission = "0x1111111111111111111111111111111111111111"
    profile.addCommission(test_commission, sender=owner)
    
    # Check count was updated
    assert profile.commissionCount() == 1
    
    # Check commission was added
    commissions = profile.getCommissions(0, 10)
    assert len(commissions) == 1
    assert commissions[0] == test_commission
    
    # Test removing the commission
    profile.removeCommission(test_commission, sender=owner)
    
    # Check count was updated
    assert profile.commissionCount() == 0
    
    # Check commission was removed
    commissions = profile.getCommissions(0, 10)
    assert len(commissions) == 0 