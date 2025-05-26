import pytest
from ape import accounts, project
from eth_utils import to_checksum_address

# Define constant for zero address
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
CHAIN_ID = 1  # Ethereum mainnet
TEST_NFT_CONTRACT = "0x1111111111111111111111111111111111111111"
TEST_TOKEN_ID = 123

@pytest.fixture(scope="function")
def setup():
    """Setup function that deploys and initializes all contracts needed for testing"""
    deployer = accounts.test_accounts[0]
    user1 = accounts.test_accounts[1]
    user2 = accounts.test_accounts[2]
    
    # Deploy all templates
    profile_template = project.Profile.deploy(sender=deployer)
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Verify all templates were deployed
    assert profile_template.address != ZERO_ADDRESS
    assert profile_social_template.address != ZERO_ADDRESS
    assert commission_hub_template.address != ZERO_ADDRESS
    assert art_piece_template.address != ZERO_ADDRESS
    
    # Deploy factory registry
    profile_factory = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address,
        profile_social_template.address,
        commission_hub_template.address,
        sender=deployer
    )
    
    # Verify factory registry was deployed
    assert profile_factory.address != ZERO_ADDRESS
    assert profile_factory.profileTemplate() == profile_template.address
    assert profile_factory.profileSocialTemplate() == profile_social_template.address
    assert profile_factory.commissionHubTemplate() == commission_hub_template.address
    
    # Deploy ArtCommissionHubOwners
    art_commission_hub_owners = project.ArtCommissionHubOwners.deploy(
        deployer.address,  # L2OwnershipRelay
        commission_hub_template.address,
        art_piece_template.address,
        sender=deployer
    )
    
    # Verify hub owners was deployed
    assert art_commission_hub_owners.address != ZERO_ADDRESS
    assert art_commission_hub_owners.l2OwnershipRelay() == deployer.address
    
    # Link factory and hub owners
    profile_factory.linkArtCommissionHubOwnersContract(art_commission_hub_owners.address, sender=deployer)
    art_commission_hub_owners.linkProfileFactoryAndRegistry(profile_factory.address, sender=deployer)
    
    # Verify the links
    assert profile_factory.artCommissionHubOwners() == art_commission_hub_owners.address
    assert art_commission_hub_owners.profileFactoryAndRegistry() == profile_factory.address
    
    # Return all deployed contracts and references for use in tests
    return {
        "deployer": deployer,
        "user1": user1,
        "user2": user2,
        "profile_template": profile_template,
        "profile_social_template": profile_social_template,
        "commission_hub_template": commission_hub_template,
        "art_piece_template": art_piece_template,
        "profile_factory": profile_factory,
        "art_commission_hub_owners": art_commission_hub_owners
    }

def test_initialization(setup):
    """Test that ArtCommissionHubOwners initializes correctly"""
    deployer = setup["deployer"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    commission_hub_template = setup["commission_hub_template"]
    profile_factory = setup["profile_factory"]
    
    assert art_commission_hub_owners.l2OwnershipRelay() == deployer.address
    assert art_commission_hub_owners.artCommissionHubTemplate() == commission_hub_template.address
    assert art_commission_hub_owners.owner() == deployer.address
    assert art_commission_hub_owners.profileFactoryAndRegistry() == profile_factory.address

def test_register_nft_owner(setup):
    """Test NFT owner registration"""
    deployer = setup["deployer"]
    user1 = setup["user1"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    
    # Register an NFT owner (deployer is set as L2OwnershipRelay in setup)
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID, user1.address, sender=deployer
    )
    
    # Verify the owner was registered
    assert art_commission_hub_owners.lookupRegisteredOwner(CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID) == user1.address
    assert art_commission_hub_owners.lookupEthereumRegisteredOwner(TEST_NFT_CONTRACT, TEST_TOKEN_ID) == user1.address
    
    # Verify a timestamp was recorded
    assert art_commission_hub_owners.getArtCommissionHubLastUpdated(CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID) > 0
    assert art_commission_hub_owners.getEthereumArtCommissionHubLastUpdated(TEST_NFT_CONTRACT, TEST_TOKEN_ID) > 0
    
    # Verify a commission hub was created
    hub_address = art_commission_hub_owners.getArtCommissionHubByOwner(CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID)
    assert hub_address != ZERO_ADDRESS
    assert art_commission_hub_owners.getEthereumArtCommissionHubByOwner(TEST_NFT_CONTRACT, TEST_TOKEN_ID) == hub_address
    
    # Verify the hub is not generic
    assert not art_commission_hub_owners.isGeneric(hub_address)
    
    # Verify the hub was linked to the owner
    assert art_commission_hub_owners.getCommissionHubCountByOwner(user1.address) == 1
    hubs = art_commission_hub_owners.getCommissionHubsByOwnerWithOffset(user1.address, 0, 10, False)
    assert len(hubs) == 1
    assert hubs[0] == hub_address

def test_update_nft_owner(setup):
    """Test NFT owner update"""
    deployer = setup["deployer"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    
    # Register an NFT owner
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID, user1.address, sender=deployer
    )
    
    # Get the hub address
    hub_address = art_commission_hub_owners.getArtCommissionHubByOwner(CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID)
    
    # Update the owner
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID, user2.address, sender=deployer
    )
    
    # Verify the owner was updated
    assert art_commission_hub_owners.lookupRegisteredOwner(CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID) == user2.address
    
    # Verify the hub was unlinked from user1 and linked to user2
    assert art_commission_hub_owners.getCommissionHubCountByOwner(user1.address) == 0
    assert art_commission_hub_owners.getCommissionHubCountByOwner(user2.address) == 1
    hubs = art_commission_hub_owners.getCommissionHubsByOwnerWithOffset(user2.address, 0, 10, False)
    assert len(hubs) == 1
    assert hubs[0] == hub_address

def test_create_generic_commission_hub(setup):
    """Test creating a generic commission hub"""
    user1 = setup["user1"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    
    # Create a generic commission hub
    tx = art_commission_hub_owners.createGenericCommissionHub(user1.address, sender=user1)
    
    # Get the hub address from the event
    hub_address = None
    for event in tx.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
            hub_address = event.commission_hub
            break
    
    assert hub_address is not None
    
    # Verify the hub is generic
    assert art_commission_hub_owners.isGeneric(hub_address)
    
    # Verify the hub was linked to the owner
    assert art_commission_hub_owners.getCommissionHubCountByOwner(user1.address) == 1
    hubs = art_commission_hub_owners.getCommissionHubsByOwnerWithOffset(user1.address, 0, 10, False)
    assert len(hubs) == 1
    assert hubs[0] == hub_address
    
    # Verify a profile was created for the user
    assert profile_factory.hasProfile(user1.address) is True
    user1_profile = profile_factory.getProfile(user1.address)
    profile = project.Profile.at(user1_profile)
    
    # Verify the hub was linked to the profile
    assert profile.getCommissionHubCount() == 1
    profile_hubs = profile.getCommissionHubsByOffset(0, 10, False)
    assert len(profile_hubs) == 1
    assert profile_hubs[0] == hub_address

def test_profile_integration(setup):
    """Test profile integration with commission hubs"""
    deployer = setup["deployer"]
    user1 = setup["user1"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    
    # Create a profile for user1 first
    profile_factory.createProfile(user1.address, sender=deployer)
    user1_profile = profile_factory.getProfile(user1.address)
    
    # Create a generic commission hub
    tx = art_commission_hub_owners.createGenericCommissionHub(user1.address, sender=user1)
    
    # Get the hub address from the event
    hub_address = None
    for event in tx.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
            hub_address = event.commission_hub
            break
    
    # Verify the hub was linked to the profile
    profile = project.Profile.at(user1_profile)
    assert profile.getCommissionHubCount() == 1
    profile_hubs = profile.getCommissionHubsByOffset(0, 10, False)
    assert len(profile_hubs) == 1
    assert profile_hubs[0] == hub_address

def test_profile_creation(setup):
    """Test automatic profile creation when creating a generic hub"""
    user1 = setup["user1"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    
    # Verify user1 doesn't have a profile yet
    assert profile_factory.hasProfile(user1.address) is False
    
    # Create a generic commission hub (should automatically create profile)
    tx = art_commission_hub_owners.createGenericCommissionHub(user1.address, sender=user1)
    
    # Verify profile was created
    assert profile_factory.hasProfile(user1.address) is True
    user1_profile = profile_factory.getProfile(user1.address)
    
    # Get the hub address from the event
    hub_address = None
    for event in tx.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
            hub_address = event.commission_hub
            break
    
    # Verify the hub was linked to the profile
    profile = project.Profile.at(user1_profile)
    assert profile.getCommissionHubCount() == 1
    profile_hubs = profile.getCommissionHubsByOffset(0, 10, False)
    assert len(profile_hubs) == 1
    assert profile_hubs[0] == hub_address

def test_link_hubs_to_profile(setup):
    """Test linking existing hubs to a profile after creation"""
    deployer = setup["deployer"]
    user1 = setup["user1"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    
    # Create a profile for user1 first
    profile_factory.createProfile(user1.address, sender=deployer)
    user1_profile = profile_factory.getProfile(user1.address)
    profile = project.Profile.at(user1_profile)
    
    # Verify the profile has no hubs yet
    assert profile.getCommissionHubCount() == 0
    
    # Create a generic commission hub (with profile integration)
    tx = art_commission_hub_owners.createGenericCommissionHub(user1.address, sender=user1)
    hub_address = None
    for event in tx.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
            hub_address = event.commission_hub
            break
    
    # Verify the hub exists and is linked to the profile
    assert hub_address is not None
    assert profile.getCommissionHubCount() == 1
    
    # Create an NFT-based hub to test multiple hubs
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID, user1.address, sender=deployer
    )
    
    # Verify the profile now has 2 hubs (generic + NFT-based)
    assert profile.getCommissionHubCount() == 2
    
    # Get all hubs and verify they include both the generic and NFT-based hubs
    profile_hubs = profile.getCommissionHubsByOffset(0, 10, False)
    assert len(profile_hubs) == 2
    assert hub_address in profile_hubs
    
    # Verify the NFT-based hub is also in the list
    nft_hub_address = art_commission_hub_owners.getArtCommissionHubByOwner(CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID)
    assert nft_hub_address in profile_hubs

def test_multiple_generic_hubs(setup):
    """Test creating multiple generic hubs for the same owner"""
    user1 = setup["user1"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    
    # Create first generic commission hub
    tx1 = art_commission_hub_owners.createGenericCommissionHub(user1.address, sender=user1)
    hub1 = None
    for event in tx1.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
            hub1 = event.commission_hub
            break
    
    # Note: The current implementation only allows one generic hub per owner
    # So we'll test that trying to create a second one returns the same hub
    tx2 = art_commission_hub_owners.createGenericCommissionHub(user1.address, sender=user1)
    hub2 = None
    for event in tx2.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
            hub2 = event.commission_hub
            break
    
    # The second call should return the same hub (or no event if it already exists)
    if hub2 is not None:
        assert hub1 == hub2, "Should return the same hub for the same owner"
    
    # Verify only one hub is linked to the owner
    assert art_commission_hub_owners.getCommissionHubCountByOwner(user1.address) == 1
    hubs = art_commission_hub_owners.getCommissionHubsByOwnerWithOffset(user1.address, 0, 10, False)
    assert len(hubs) == 1
    assert hubs[0] == hub1

def test_permissions(setup):
    """Test permission checks"""
    deployer = setup["deployer"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    
    # Only L2OwnershipRelay or owner can register NFT owners
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.registerNFTOwnerFromParentChain(
            CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID, user1.address, sender=user1
        )
    assert "Only L2OwnershipRelay or the owner can register" in str(excinfo.value)
    
    # Only owner can set L2OwnershipRelay
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.setL2OwnershipRelay(user1.address, sender=user1)
    assert "Only owner can set L2 relay" in str(excinfo.value)
    
    # Only owner can set commission hub template
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.setArtCommissionHubTemplate(user1.address, sender=user1)
    assert "Only owner can set commission hub template" in str(excinfo.value)
    
    # Only owner can set profile factory and registry
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.linkProfileFactoryAndRegistry(user1.address, sender=user1)
    assert "Only owner can set profile-factory-and-registry" in str(excinfo.value)
    
    # Only the owner can create their own generic commission hub
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.createGenericCommissionHub(user1.address, sender=user2)
    assert "Only the owner can create their own generic commission hub" in str(excinfo.value)

def test_commission_hub_pagination(setup):
    """Test pagination of commission hubs"""
    user1 = setup["user1"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    deployer = setup["deployer"]
    
    # Create multiple NFT-based commission hubs (since generic hubs are limited to one per owner)
    hubs = []
    for i in range(5):
        nft_contract = f"0x{str(i).zfill(40)}"  # Create different NFT contract addresses
        art_commission_hub_owners.registerNFTOwnerFromParentChain(
            CHAIN_ID, nft_contract, i, user1.address, sender=deployer
        )
        hub_address = art_commission_hub_owners.getArtCommissionHubByOwner(CHAIN_ID, nft_contract, i)
        hubs.append(hub_address)
    
    # Test pagination
    assert art_commission_hub_owners.getCommissionHubCountByOwner(user1.address) == 5
    
    # Page 0, size 2 (forward pagination)
    page0 = art_commission_hub_owners.getCommissionHubsByOwnerWithOffset(user1.address, 0, 2, False)
    assert len(page0) == 2
    assert page0[0] == hubs[0]
    assert page0[1] == hubs[1]
    
    # Page with offset 2, size 2 (forward pagination)
    page1 = art_commission_hub_owners.getCommissionHubsByOwnerWithOffset(user1.address, 2, 2, False)
    assert len(page1) == 2
    assert page1[0] == hubs[2]
    assert page1[1] == hubs[3]
    
    # Page with offset 4, size 2 (forward pagination)
    page2 = art_commission_hub_owners.getCommissionHubsByOwnerWithOffset(user1.address, 4, 2, False)
    assert len(page2) == 1
    assert page2[0] == hubs[4]
    
    # Page with offset 5, size 2 (empty)
    page3 = art_commission_hub_owners.getCommissionHubsByOwnerWithOffset(user1.address, 5, 2, False)
    assert len(page3) == 0
    
    # Test reverse pagination
    reverse_page0 = art_commission_hub_owners.getCommissionHubsByOwnerWithOffset(user1.address, 0, 2, True)
    assert len(reverse_page0) == 2
    assert reverse_page0[0] == hubs[4]  # Most recent first
    assert reverse_page0[1] == hubs[3] 