import pytest
from ape import accounts, project

@pytest.fixture
def setup():
    # Get local accounts for testing
    deployer = accounts.test_accounts[0]
    owner = accounts.test_accounts[1]
    artist = accounts.test_accounts[2]
    
    # Sample image data (just a placeholder)
    sample_image_data = b"sample image data"
    
    # Deploy the contract
    contract = project.CommissionedArt.deploy(
        sample_image_data,
        owner.address,
        artist.address,
        sender=deployer
    )
    
    return contract, owner, artist

def test_initialization(setup):
    """Test that the contract initializes with correct values"""
    contract, owner, artist = setup
    
    # Check if the owner is set correctly
    assert contract.get_owner() == owner.address
    
    # Check if the artist is set correctly
    assert contract.get_artist() == artist.address
    
    # Check if the image data is set correctly
    assert contract.get_image_data() == b"sample image data"

def test_transfer_ownership(setup):
    """Test the transferOwnership method"""
    contract, owner, artist = setup
    new_owner = accounts.test_accounts[3]
    
    # Transfer ownership
    contract.transferOwnership(new_owner.address, sender=owner)
    
    # Check if ownership was transferred correctly
    assert contract.get_owner() == new_owner.address 