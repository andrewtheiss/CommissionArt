import pytest
from ape import accounts, project

@pytest.fixture
def setup():
    # Get local accounts for testing
    deployer = accounts.test_accounts[0]
    owner = accounts.test_accounts[1]
    artist = accounts.test_accounts[2]
    
    # Sample image data (smaller size for testing)
    sample_image_data = b"sample image data" * 10  # Still well under 1000 bytes
    
    # Deploy the contract with increased gas limit
    contract = project.CommissionedArt.deploy(
        sample_image_data,
        owner.address,
        artist.address,
        sender=deployer,
        gas_limit=2000000  # Explicitly set gas limit
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
    assert contract.get_image_data() == b"sample image data" * 10

def test_transfer_ownership(setup):
    """Test the transferOwnership method"""
    contract, owner, artist = setup
    new_owner = accounts.test_accounts[3]
    
    # Transfer ownership
    contract.transferOwnership(new_owner.address, sender=owner, gas_limit=200000)
    
    # Check if ownership was transferred correctly
    assert contract.get_owner() == new_owner.address 

def test_large_image_data_and_multiple_transfers(setup):
    """Test contract with larger image data and multiple ownership transfers"""
    contract, owner, artist = setup
    new_owner1 = accounts.test_accounts[3]
    new_owner2 = accounts.test_accounts[4]
    
    # Create a larger image data (5KB) - more reasonable size for testing
    large_image_data = b"large image data " * 312  # 5KB of data
    
    # Deploy a new contract with larger image data
    large_contract = project.CommissionedArt.deploy(
        large_image_data,
        owner.address,
        artist.address,
        sender=owner,
        gas_limit=25000000  # Adjusted gas limit for 5KB data
    )
    
    # Verify large image data was stored correctly
    assert large_contract.get_image_data() == large_image_data
    
    # Perform multiple ownership transfers with adjusted gas limits
    large_contract.transferOwnership(new_owner1.address, sender=owner, gas_limit=200000)
    assert large_contract.get_owner() == new_owner1.address
    
    large_contract.transferOwnership(new_owner2.address, sender=new_owner1, gas_limit=200000)
    assert large_contract.get_owner() == new_owner2.address
    
    # Verify all state remains correct after transfers
    assert large_contract.get_image_data() == large_image_data
    assert large_contract.get_artist() == artist.address

def test_ownership_transfer_events_and_error_conditions(setup):
    """Test ownership transfer events and error conditions"""
    contract, owner, artist = setup
    new_owner = accounts.test_accounts[3]
    unauthorized_account = accounts.test_accounts[5]
    
    # Test that unauthorized account cannot transfer ownership
    with pytest.raises(Exception) as exc_info:
        contract.transferOwnership(new_owner.address, sender=unauthorized_account, gas_limit=200000)
    assert "Only the owner can transfer ownership" in str(exc_info.value)
    
    # Test ownership transfer to zero address
    with pytest.raises(Exception) as exc_info:
        contract.transferOwnership("0x0000000000000000000000000000000000000000", sender=owner, gas_limit=100000)
    assert "Invalid new owner address" in str(exc_info.value)
    
    # Test successful ownership transfer and verify event
    tx = contract.transferOwnership(new_owner.address, sender=owner, gas_limit=100000)
    events = tx.events
    
    # Verify OwnershipTransferred event
    assert len(events) == 1
    event = events[0]
    assert event.from_owner == owner.address
    assert event.to_owner == new_owner.address
    
    # Verify final state
    assert contract.get_owner() == new_owner.address
    assert contract.get_artist() == artist.address 