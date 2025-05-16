import pytest
from ape import accounts, project
import time
from eth_utils import to_checksum_address

# Define constant for zero address
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    user = accounts.test_accounts[1]
    
    # Deploy Profile template
    profile_template = project.Profile.deploy(sender=deployer)
    
    # Deploy ProfileFactoryAndRegistry with the template
    # Deploy ProfileSocial template
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)


    # Deploy ProfileFactoryAndRegistry with both templates
    profile_factory_and_regsitry = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address,
        profile_social_template.address,
        sender=deployer
    )
    
    # Deploy L2Relay and ArtCommissionHub template for OwnerRegistry
    l2_relay = project.L2Relay.deploy(sender=deployer)
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    
    # Deploy OwnerRegistry with the required parameters
    owner_registry = project.OwnerRegistry.deploy(l2_relay.address, commission_hub_template.address, sender=deployer)
    
    # Set OwnerRegistry in ProfileFactoryAndRegistry
    profile_factory_and_regsitry.setOwnerRegistry(owner_registry.address, sender=deployer)
    
    # Set L2Relay to the deployer for testing purposes
    owner_registry.setL2Relay(deployer.address, sender=deployer)
    
    # Create a profile for the user
    profile_factory_and_regsitry.createProfile(sender=user)
    user_profile_address = profile_factory_and_regsitry.getProfile(user.address)
    user_profile = project.Profile.at(user_profile_address)
    
    # Deploy multiple commission hubs for testing pagination
    commission_hubs = []
    for i in range(25):  # Create 25 commission hubs
        # Use a different NFT contract address for each - use deployer's address with different indices
        nft_contract = deployer.address  # Use a valid address that already exists
        token_id = i + 1
        
        # Register NFT ownership - now the deployer is authorized as L2Relay
        owner_registry.registerNFTOwnerFromParentChain(1, nft_contract, token_id, user.address, sender=deployer)
        
        # Get the created commission hub address
        commission_hub_address = owner_registry.getArtCommissionHubByOwner(1, nft_contract, token_id)
        commission_hubs.append(commission_hub_address)
    
    return {
        "deployer": deployer,
        "user": user,
        "profile_factory_and_regsitry": profile_factory_and_regsitry,
        "owner_registry": owner_registry,
        "user_profile": user_profile,
        "commission_hubs": commission_hubs
    }

def test_get_commission_hubs_for_owner_different_page_sizes(setup):
    """
    Test retrieving commission hubs with different page sizes
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
    
    # Test page size 10
    page_size = 10
    total_pages = (len(commission_hubs) + page_size - 1) // page_size
    
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
    
    # Test page size 20
    page_size = 20
    total_pages = (len(commission_hubs) + page_size - 1) // page_size
    
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
    
    # Test page size 100 (larger than total)
    page_size = 100
    hubs = owner_registry.getCommissionHubsForOwner(user.address, 0, page_size)
    
    # Verify all hubs returned in a single page
    assert len(hubs) == len(commission_hubs)
    for hub in commission_hubs:
        assert hub in hubs

def test_get_commission_hubs_for_owner_empty_pages(setup):
    """
    Test retrieving commission hubs with page numbers beyond available data
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

def test_get_commission_hubs_for_owner_count(setup):
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

def test_get_commission_hubs_for_nonexistent_owner(setup):
    """
    Test retrieving commission hubs for a user with no hubs
    """
    # Arrange
    deployer = setup["deployer"]  # Use deployer as a user with no hubs
    owner_registry = setup["owner_registry"]
    
    # Get hubs for user with no hubs - use a different account that has no hubs
    no_hub_user = accounts.test_accounts[2]
    hubs = owner_registry.getCommissionHubsForOwner(no_hub_user.address, 0, 10)
    
    # Verify empty array returned
    assert len(hubs) == 0
    
    # Verify count is 0
    hub_count = owner_registry.getCommissionHubCountForOwner(no_hub_user.address)
    assert hub_count == 0 