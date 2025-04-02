import pytest
import os
from pathlib import Path
from ape import accounts, project

@pytest.fixture
def dummy_image_data():
    """Generate dummy image data for testing"""
    # PNG header + some random data
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

@pytest.fixture
def setup(dummy_image_data):
    # Get local accounts for testing
    deployer = accounts.test_accounts[0]
    
    # Deploy Registry contract
    registry = project.Registry.deploy(sender=deployer)
    
    # Create and deploy 5 CommissionedArt contracts with dummy data
    image_contracts = []
    zero_address = "0x0000000000000000000000000000000000000000"
    
    for i in range(5):
        # Add some variation to each image's data for testing
        image_data = dummy_image_data + str(i).encode()
        
        # Deploy CommissionedArt contract
        img_contract = project.CommissionedArt.deploy(
            image_data,
            zero_address,  # Owner is zero address
            zero_address,  # Artist is zero address
            sender=deployer
        )
        
        # Register in Registry
        registry.registerImageData(i, img_contract.address, sender=deployer)
        
        # Store for later use
        image_contracts.append(img_contract)
    
    return registry, image_contracts, deployer

def test_registry_with_images(setup):
    """Test registry with image contracts"""
    registry, image_contracts, deployer = setup
    
    # Check that all images were registered
    for i, img_contract in enumerate(image_contracts):
        registered_address = registry.imageDataContracts(i)
        assert registered_address == img_contract.address
        
        # Verify image data is retrievable 
        image_data = img_contract.get_image_data()
        assert image_data.startswith(b"\x89PNG\r\n\x1a\n")
        assert len(image_data) > 100  # Data has reasonable size
        
        # Verify owner and artist are zero address
        assert img_contract.get_owner() == "0x0000000000000000000000000000000000000000"
        assert img_contract.get_artist() == "0x0000000000000000000000000000000000000000"

def test_set_l1_and_rescind(setup):
    """Test setting L1 contract and rescinding ownership"""
    registry, image_contracts, deployer = setup
    
    # Set L1 contract
    l1_address = accounts.test_accounts[9].address
    registry.setL1Contract(l1_address, sender=deployer)
    assert registry.l1_contract() == l1_address
    
    # Rescind ownership
    registry.rescindOwnership(sender=deployer)
    assert registry.is_ownership_rescinded() == True
    assert registry.owner() == "0x0000000000000000000000000000000000000000"
    
    # Verify we can still access all registered image contracts
    for i, img_contract in enumerate(image_contracts):
        registered_address = registry.imageDataContracts(i)
        assert registered_address == img_contract.address
        
    # But can't register a new one
    with pytest.raises(Exception):
        registry.registerImageData(
            5, 
            accounts.test_accounts[8].address, 
            sender=deployer
        )

def test_full_deployment_simulation(dummy_image_data):
    """Simulate the full deployment process as it would happen in the script"""
    deployer = accounts.test_accounts[0]
    zero_address = "0x0000000000000000000000000000000000000000"
    l1_contract = accounts.test_accounts[9].address
    
    # Step 1: Deploy Registry
    registry = project.Registry.deploy(sender=deployer)
    assert registry.owner() == deployer.address
    
    # Step 2: Set L1 contract
    registry.setL1Contract(l1_contract, sender=deployer)
    assert registry.l1_contract() == l1_contract
    
    # Step 3: Deploy image contracts and register them
    for i in range(5):
        # Simulate different image data for each Azuki
        image_data = dummy_image_data + f"Azuki #{i}".encode()
        
        # Deploy CommissionedArt contract
        img_contract = project.CommissionedArt.deploy(
            image_data,
            zero_address,
            zero_address,
            sender=deployer
        )
        
        # Register in Registry
        registry.registerImageData(i, img_contract.address, sender=deployer)
        
        # Verify registration worked
        assert registry.imageDataContracts(i) == img_contract.address
        
        # Verify image data is intact
        retrieved_image = img_contract.get_image_data()
        assert retrieved_image == image_data
    
    # Step 4: Rescind ownership (final step)
    registry.rescindOwnership(sender=deployer)
    assert registry.is_ownership_rescinded() == True
    assert registry.owner() == zero_address
    
    # Verify we can still access all image data
    for i in range(5):
        img_contract_addr = registry.imageDataContracts(i)
        assert img_contract_addr != zero_address
        
        img_contract = project.CommissionedArt.at(img_contract_addr)
        img_data = img_contract.get_image_data()
        assert f"Azuki #{i}".encode() in img_data 