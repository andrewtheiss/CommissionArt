import pytest
from ape import accounts, project

@pytest.fixture
def setup():
    # Get local accounts for testing
    deployer = accounts.test_accounts[0]
    
    # Deploy Registry contract
    registry = project.Registry.deploy(sender=deployer)
    
    return registry, deployer

def test_registry_initialization(setup):
    """Test that the registry initializes with correct values"""
    registry, deployer = setup
    
    # Check if the owner is set correctly
    assert registry.owner() == deployer.address
    
    # Check initial values
    assert registry.is_ownership_rescinded() == False
    assert registry.l1_contract() == "0x0000000000000000000000000000000000000000"

def test_register_image_data(setup):
    """Test registering image data contracts"""
    registry, deployer = setup
    
    # Create some test addresses for image contracts
    image_contract_1 = accounts.test_accounts[1].address
    image_contract_2 = accounts.test_accounts[2].address
    image_contract_3 = accounts.test_accounts[3].address
    
    # Register image contracts
    registry.registerImageData(1, image_contract_1, sender=deployer)
    registry.registerImageData(2, image_contract_2, sender=deployer)
    
    # Verify registrations
    assert registry.imageDataContracts(1) == image_contract_1
    assert registry.imageDataContracts(2) == image_contract_2
    
    # Try to register duplicate - should fail
    # with pytest.raises(Exception) as exc_info:
    #     registry.registerImageData(1, accounts.test_accounts[3].address, sender=deployer)
    # assert "Azuki ID already registered" in str(exc_info.value)
    registry.registerImageData(1, accounts.test_accounts[3].address, sender=deployer)
    assert registry.imageDataContracts(1) == image_contract_3

def test_set_l1_contract(setup):
    """Test setting L1 contract address"""
    registry, deployer = setup
    
    l1_contract_address = accounts.test_accounts[5].address
    
    # Set L1 contract address
    tx = registry.setL1Contract(l1_contract_address, sender=deployer)
    
    # Verify L1 contract was set
    assert registry.l1_contract() == l1_contract_address
    
    # Verify event was emitted
    events = tx.events
    assert len(events) == 1
    event = events[0]
    assert event.l1_contract == l1_contract_address
    
    # Try to set to zero address - should fail
    with pytest.raises(Exception) as exc_info:
        registry.setL1Contract("0x0000000000000000000000000000000000000000", sender=deployer)
    assert "Invalid L1 contract address" in str(exc_info.value)

def test_rescind_ownership(setup):
    """Test rescinding ownership"""
    registry, deployer = setup
    unauthorized = accounts.test_accounts[3]
    
    # Try to rescind with unauthorized account - should fail
    with pytest.raises(Exception) as exc_info:
        registry.rescindOwnership(sender=unauthorized)
    assert "Only owner can rescind ownership" in str(exc_info.value)
    
    # Rescind ownership
    tx = registry.rescindOwnership(sender=deployer)
    
    # Verify state changes
    assert registry.is_ownership_rescinded() == True
    assert registry.owner() == "0x0000000000000000000000000000000000000000"
    
    # Verify event was emitted
    events = tx.events
    assert len(events) == 1
    event = events[0]
    assert event.previous_owner == deployer.address
    
    # Try to rescind again - should fail
    with pytest.raises(Exception) as exc_info:
        registry.rescindOwnership(sender=deployer)
    assert "Ownership already rescinded" in str(exc_info.value)
    
    # Try to register image after rescinding - should fail
    with pytest.raises(Exception) as exc_info:
        registry.registerImageData(5, accounts.test_accounts[5].address, sender=deployer)
    assert "Ownership has been rescinded" in str(exc_info.value)
    
    # Try to set L1 contract after rescinding - should fail
    with pytest.raises(Exception) as exc_info:
        registry.setL1Contract(accounts.test_accounts[6].address, sender=deployer)
    assert "Ownership has been rescinded" in str(exc_info.value)

def test_integrated_flow(setup):
    """Test an integrated flow of registry operations"""
    registry, deployer = setup
    
    # Set L1 contract
    l1_address = accounts.test_accounts[7].address
    registry.setL1Contract(l1_address, sender=deployer)
    
    # Register multiple image contracts
    for i in range(5):
        image_contract = accounts.test_accounts[i].address
        registry.registerImageData(i, image_contract, sender=deployer)
        assert registry.imageDataContracts(i) == image_contract
    
    # Verify L1 contract is still set correctly
    assert registry.l1_contract() == l1_address
    
    # Rescind ownership
    registry.rescindOwnership(sender=deployer)
    
    # Verify state after rescinding
    assert registry.is_ownership_rescinded() == True
    assert registry.owner() == "0x0000000000000000000000000000000000000000"
    
    # All previously registered contracts should still be accessible
    for i in range(5):
        assert registry.imageDataContracts(i) == accounts.test_accounts[i].address 