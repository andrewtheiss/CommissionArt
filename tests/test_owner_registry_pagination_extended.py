import pytest
from ape import accounts, project
import time
from eth_utils import to_checksum_address

# Define constant for zero address
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

@pytest.fixture
def setup():
    # Get accounts for testing - use test_accounts which are available in the test environment
    deployer = accounts.test_accounts[0]
    user = accounts.test_accounts[1]
    
    # Deploy Profile template
    profile_template = project.Profile.deploy(sender=deployer)
    
    # Deploy ProfileHub with the template
    profile_hub = project.ProfileHub.deploy(profile_template.address, sender=deployer)
    
    # Deploy L2Relay and ArtCommissionHub template for OwnerRegistry
    l2_relay = project.L2Relay.deploy(sender=deployer)
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    
    # Deploy OwnerRegistry with the required parameters
    owner_registry = project.OwnerRegistry.deploy(l2_relay.address, commission_hub_template.address, sender=deployer)
    
    # Set OwnerRegistry in ProfileHub
    profile_hub.setOwnerRegistry(owner_registry.address, sender=deployer)
    
    # Set ProfileHub in OwnerRegistry
    owner_registry.setProfileHub(profile_hub.address, sender=deployer)
    
    # Set L2Relay to the deployer for testing purposes
    owner_registry.setL2Relay(deployer.address, sender=deployer)
    
    # Create a profile for the user
    profile_hub.createProfile(sender=user)
    user_profile_address = profile_hub.getProfile(user.address)
    user_profile = project.Profile.at(user_profile_address)
    
    # Deploy multiple commission hubs for testing pagination
    # Using a larger number of hubs (50) to better test different page sizes
    commission_hubs = []
    for i in range(50):  # Create 50 commission hubs
        # Use a valid address for NFT contract
        nft_contract = deployer.address
        token_id = i + 1
        
        # Register the NFT with the owner registry
        # Now the deployer is authorized as L2Relay
        owner_registry.registerNFTOwnerFromParentChain(1, nft_contract, token_id, user.address, sender=deployer)
        
        # Get the commission hub address
        commission_hub_address = owner_registry.getArtCommissionHubByOwner(1, nft_contract, token_id)
        commission_hubs.append(commission_hub_address)
    
    return {
        "deployer": deployer,
        "user": user,
        "profile_hub": profile_hub,
        "owner_registry": owner_registry,
        "user_profile": user_profile,
        "commission_hubs": commission_hubs
    }

def test_get_commission_hubs_with_page_size_5(setup):
    """
    Test retrieving commission hubs with page size 5
    """
    # Arrange
    user = setup["user"]
    owner_registry = setup["owner_registry"]
    commission_hubs = setup["commission_hubs"]
    
    # Test page size 5
    page_size = 5
    total_pages = (len(commission_hubs) + page_size - 1) // page_size  # Ceiling division
    
    all_hubs = []
    for page in range(total_pages):
        hubs = owner_registry.getCommissionHubsForOwner(user.address, page, page_size)
        all_hubs.extend(hubs)
        
        # Verify correct number of hubs returned
        expected_count = min(page_size, len(commission_hubs) - page * page_size)
        assert len(hubs) == expected_count
    
    # Verify we got all hubs
    assert len(all_hubs) == len(commission_hubs)
    for hub in commission_hubs:
        assert hub in all_hubs

def test_get_commission_hubs_with_page_size_10(setup):
    """
    Test retrieving commission hubs with page size 10
    """
    # Arrange
    user = setup["user"]
    owner_registry = setup["owner_registry"]
    commission_hubs = setup["commission_hubs"]
    
    # Test page size 10
    page_size = 10
    total_pages = (len(commission_hubs) + page_size - 1) // page_size  # Ceiling division
    
    all_hubs = []
    for page in range(total_pages):
        hubs = owner_registry.getCommissionHubsForOwner(user.address, page, page_size)
        all_hubs.extend(hubs)
        
        # Verify correct number of hubs returned
        expected_count = min(page_size, len(commission_hubs) - page * page_size)
        assert len(hubs) == expected_count
    
    # Verify we got all hubs
    assert len(all_hubs) == len(commission_hubs)
    for hub in commission_hubs:
        assert hub in all_hubs

def test_get_commission_hubs_with_page_size_20(setup):
    """
    Test retrieving commission hubs with page size 20
    """
    # Arrange
    user = setup["user"]
    owner_registry = setup["owner_registry"]
    commission_hubs = setup["commission_hubs"]
    
    # Test page size 20
    page_size = 20
    total_pages = (len(commission_hubs) + page_size - 1) // page_size  # Ceiling division
    
    all_hubs = []
    for page in range(total_pages):
        hubs = owner_registry.getCommissionHubsForOwner(user.address, page, page_size)
        all_hubs.extend(hubs)
        
        # Verify correct number of hubs returned
        expected_count = min(page_size, len(commission_hubs) - page * page_size)
        assert len(hubs) == expected_count
    
    # Verify we got all hubs
    assert len(all_hubs) == len(commission_hubs)
    for hub in commission_hubs:
        assert hub in all_hubs

def test_get_commission_hubs_with_page_size_100(setup):
    """
    Test retrieving commission hubs with page size 100
    """
    # Arrange
    user = setup["user"]
    owner_registry = setup["owner_registry"]
    commission_hubs = setup["commission_hubs"]
    
    # Test page size 100 (larger than total)
    page_size = 100
    hubs = owner_registry.getCommissionHubsForOwner(user.address, 0, page_size)
    
    # Verify all hubs returned in a single page
    assert len(hubs) == len(commission_hubs)
    for hub in commission_hubs:
        assert hub in hubs

def test_get_commission_hubs_empty_page(setup):
    """
    Test retrieving commission hubs with page number beyond available data
    """
    # Arrange
    user = setup["user"]
    owner_registry = setup["owner_registry"]
    
    # Test requesting a page beyond available data
    page_size = 10
    page = 100  # Far beyond available data
    
    hubs = owner_registry.getCommissionHubsForOwner(user.address, page, page_size)
    
    # Verify empty array returned
    assert len(hubs) == 0

def test_get_commission_hub_count(setup):
    """
    Test getCommissionHubCountForOwner returns the correct count
    """
    # Arrange
    user = setup["user"]
    owner_registry = setup["owner_registry"]
    commission_hubs = setup["commission_hubs"]
    
    # Get the count
    hub_count = owner_registry.getCommissionHubCountForOwner(user.address)
    
    # Verify correct count
    assert hub_count == len(commission_hubs)

@pytest.fixture
def setup_empty_user():
    """
    Setup for testing a user with no hubs
    """
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    user_with_no_hubs = accounts.test_accounts[2]
    
    # Deploy necessary contracts
    profile_template = project.Profile.deploy(sender=deployer)
    profile_hub = project.ProfileHub.deploy(profile_template.address, sender=deployer)
    l2_relay = project.L2Relay.deploy(sender=deployer)
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    owner_registry = project.OwnerRegistry.deploy(l2_relay.address, commission_hub_template.address, sender=deployer)
    
    # Set L2Relay to the deployer for testing purposes
    owner_registry.setL2Relay(deployer.address, sender=deployer)
    
    return {
        "deployer": deployer,
        "user_with_no_hubs": user_with_no_hubs,
        "owner_registry": owner_registry
    }

def test_get_commission_hubs_for_user_with_no_hubs(setup_empty_user):
    """
    Test retrieving commission hubs for a user with no hubs
    """
    # Arrange
    user_with_no_hubs = setup_empty_user["user_with_no_hubs"]
    owner_registry = setup_empty_user["owner_registry"]
    
    # Get hubs for user with no hubs
    hubs = owner_registry.getCommissionHubsForOwner(user_with_no_hubs.address, 0, 10)
    
    # Verify empty array returned
    assert len(hubs) == 0
    
    # Verify count is 0
    hub_count = owner_registry.getCommissionHubCountForOwner(user_with_no_hubs.address)
    assert hub_count == 0 