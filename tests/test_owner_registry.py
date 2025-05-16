import pytest
from ape import accounts, project, reverts
from eth_utils import to_checksum_address

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
CHAIN_ID = 1  # Ethereum mainnet
TEST_NFT_CONTRACT = "0x1111111111111111111111111111111111111111"
TEST_TOKEN_ID = 123

@pytest.fixture
def deployer():
    return accounts.test_accounts[0]

@pytest.fixture
def l2_relay(deployer):
    return project.L2Relay.deploy(sender=deployer)

@pytest.fixture
def user1():
    return accounts.test_accounts[1]

@pytest.fixture
def user2():
    return accounts.test_accounts[2]

@pytest.fixture
def art_commission_hub_template(deployer):
    return project.ArtCommissionHub.deploy(sender=deployer)

@pytest.fixture
def profile_template(deployer):
    return project.Profile.deploy(sender=deployer)

@pytest.fixture
def profile_social_template(deployer):
    return project.ProfileSocial.deploy(sender=deployer)

@pytest.fixture
def profile_factory_and_regsitry(deployer, profile_template, profile_social_template):
    hub = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address,
        profile_social_template.address,
        sender=deployer
    )
    return hub

@pytest.fixture
def owner_registry(deployer, l2_relay, art_commission_hub_template):
    # Deploy the OwnerRegistry contract
    registry = project.OwnerRegistry.deploy(l2_relay.address, art_commission_hub_template.address, sender=deployer)
    return registry

# Test initialization
def test_initialization(owner_registry, l2_relay, art_commission_hub_template, deployer):
    assert owner_registry.l2Relay() == l2_relay.address
    assert owner_registry.artCommissionHubTemplate() == art_commission_hub_template.address
    assert owner_registry.owner() == deployer.address
    assert owner_registry.profileFactoryAndRegistry() == ZERO_ADDRESS

# Test NFT owner registration
def test_register_nft_owner(owner_registry, l2_relay, user1, deployer):
    # Set L2Relay to the deployer for testing
    owner_registry.setL2Relay(deployer.address, sender=deployer)
    
    # Register an NFT owner
    owner_registry.registerNFTOwnerFromParentChain(
        CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID, user1.address, sender=deployer
    )
    
    # Verify the owner was registered
    assert owner_registry.lookupRegisteredOwner(CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID) == user1.address
    assert owner_registry.lookupEthereumRegisteredOwner(TEST_NFT_CONTRACT, TEST_TOKEN_ID) == user1.address
    
    # Verify a timestamp was recorded
    assert owner_registry.getLastUpdated(CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID) > 0
    assert owner_registry.getEthereumLastUpdated(TEST_NFT_CONTRACT, TEST_TOKEN_ID) > 0
    
    # Verify a commission hub was created
    hub_address = owner_registry.getArtCommissionHubByOwner(CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID)
    assert hub_address != ZERO_ADDRESS
    assert owner_registry.getEthereumArtCommissionHubByOwner(TEST_NFT_CONTRACT, TEST_TOKEN_ID) == hub_address
    
    # Verify the hub is not generic
    assert not owner_registry.isGeneric(hub_address)
    
    # Verify the hub was linked to the owner
    assert owner_registry.getCommissionHubCountForOwner(user1.address) == 1
    hubs = owner_registry.getCommissionHubsForOwner(user1.address, 0, 10)
    assert len(hubs) == 1
    assert hubs[0] == hub_address

# Test NFT owner update
def test_update_nft_owner(owner_registry, l2_relay, user1, user2, deployer):
    # Set L2Relay to the deployer for testing
    owner_registry.setL2Relay(deployer.address, sender=deployer)
    
    # Register an NFT owner
    owner_registry.registerNFTOwnerFromParentChain(
        CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID, user1.address, sender=deployer
    )
    
    # Get the hub address
    hub_address = owner_registry.getArtCommissionHubByOwner(CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID)
    
    # Update the owner
    owner_registry.registerNFTOwnerFromParentChain(
        CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID, user2.address, sender=deployer
    )
    
    # Verify the owner was updated
    assert owner_registry.lookupRegisteredOwner(CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID) == user2.address
    
    # Verify the hub was unlinked from user1 and linked to user2
    assert owner_registry.getCommissionHubCountForOwner(user1.address) == 0
    assert owner_registry.getCommissionHubCountForOwner(user2.address) == 1
    hubs = owner_registry.getCommissionHubsForOwner(user2.address, 0, 10)
    assert len(hubs) == 1
    assert hubs[0] == hub_address

# Test generic commission hub creation
def test_create_generic_commission_hub(owner_registry, user1):
    # Create a generic commission hub
    tx = owner_registry.createGenericCommissionHub(CHAIN_ID, user1.address, sender=user1)
    
    # Get the hub address from the event
    hub_address = None
    for event in tx.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
            hub_address = event.commission_hub
            break
    
    assert hub_address is not None
    
    # Verify the hub is generic
    assert owner_registry.isGeneric(hub_address)
    
    # Verify the hub was linked to the owner
    assert owner_registry.getCommissionHubCountForOwner(user1.address) == 1
    hubs = owner_registry.getCommissionHubsForOwner(user1.address, 0, 10)
    assert len(hubs) == 1
    assert hubs[0] == hub_address

# Test profile integration
def test_profile_integration(owner_registry, profile_factory_and_regsitry, deployer, user1):
    # Set the profile-factory-and-registry
    owner_registry.setProfileFactoryAndRegistry(profile_factory_and_regsitry.address, sender=deployer)
    profile_factory_and_regsitry.setOwnerRegistry(owner_registry.address, sender=deployer)
    assert owner_registry.profileFactoryAndRegistry() == profile_factory_and_regsitry.address
    
    # Create a profile for user1
    profile_factory_and_regsitry.createProfile(sender=user1)
    user1_profile = profile_factory_and_regsitry.getProfile(user1.address)
    
    # Create a generic commission hub
    tx = owner_registry.createGenericCommissionHub(CHAIN_ID, user1.address, sender=user1)
    
    # Get the hub address from the event
    hub_address = None
    for event in tx.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
            hub_address = event.commission_hub
            break
    
    # Verify the hub was linked to the profile
    profile = project.Profile.at(user1_profile)
    assert profile.commissionHubCount() == 1
    profile_factory_and_regsitrys = profile.getCommissionHubs(0, 10)
    assert len(profile_factory_and_regsitrys) == 1
    assert profile_factory_and_regsitrys[0] == hub_address

# Test profile creation
def test_profile_creation(owner_registry, profile_factory_and_regsitry, deployer, user1):
    # Set the profile-factory-and-registry
    owner_registry.setProfileFactoryAndRegistry(profile_factory_and_regsitry.address, sender=deployer)
    profile_factory_and_regsitry.setOwnerRegistry(owner_registry.address, sender=deployer)
    
    # Set L2Relay to the deployer for testing purposes
    owner_registry.setL2Relay(deployer.address, sender=deployer)
    
    # Verify user1 doesn't have a profile yet
    assert profile_factory_and_regsitry.hasProfile(user1.address) is False
    
    # Create a profile for user1 first
    profile_factory_and_regsitry.createProfile(sender=user1)
    
    # Verify profile was created
    assert profile_factory_and_regsitry.hasProfile(user1.address) is True
    user1_profile = profile_factory_and_regsitry.getProfile(user1.address)
    
    # Create a generic commission hub
    tx = owner_registry.createGenericCommissionHub(CHAIN_ID, user1.address, sender=user1)
    
    # Get the hub address from the event
    hub_address = None
    for event in tx.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
            hub_address = event.commission_hub
            break
    
    # Verify the hub was linked to the profile
    profile = project.Profile.at(user1_profile)
    assert profile.commissionHubCount() == 1
    profile_factory_and_regsitrys = profile.getCommissionHubs(0, 10)
    assert len(profile_factory_and_regsitrys) == 1
    assert profile_factory_and_regsitrys[0] == hub_address

# Test linking hubs to profile
def test_link_hubs_to_profile(owner_registry, profile_factory_and_regsitry, deployer, user1):
    # Create a generic commission hub (without profile integration)
    tx = owner_registry.createGenericCommissionHub(CHAIN_ID, user1.address, sender=user1)
    
    # Get the hub address from the event
    hub_address = None
    for event in tx.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
            hub_address = event.commission_hub
            break
    
    # Set the profile-factory-and-registry
    owner_registry.setProfileFactoryAndRegistry(profile_factory_and_regsitry.address, sender=deployer)
    profile_factory_and_regsitry.setOwnerRegistry(owner_registry.address, sender=deployer)
    
    # Create a profile for user1
    profile_factory_and_regsitry.createProfile(sender=user1)
    user1_profile = profile_factory_and_regsitry.getProfile(user1.address)
    profile = project.Profile.at(user1_profile)
    
    # Link hubs to profile
    owner_registry.linkHubsToProfile(user1.address, sender=user1)
    
    # Verify the hub was linked to the profile
    assert profile.commissionHubCount() == 1
    profile_factory_and_regsitrys = profile.getCommissionHubs(0, 10)
    assert len(profile_factory_and_regsitrys) == 1
    assert profile_factory_and_regsitrys[0] == hub_address

# Test multiple generic hubs for the same owner
def test_multiple_generic_hubs(owner_registry, user1):
    # Create first generic commission hub
    tx1 = owner_registry.createGenericCommissionHub(CHAIN_ID, user1.address, sender=user1)
    hub1 = None
    for event in tx1.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
            hub1 = event.commission_hub
            break
    
    # Create second generic commission hub on a different chain
    tx2 = owner_registry.createGenericCommissionHub(CHAIN_ID + 1, user1.address, sender=user1)
    hub2 = None
    for event in tx2.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
            hub2 = event.commission_hub
            break
    
    # Verify both hubs exist and are different
    assert hub1 is not None
    assert hub2 is not None
    assert hub1 != hub2
    
    # Verify both hubs are linked to the owner
    assert owner_registry.getCommissionHubCountForOwner(user1.address) == 2
    hubs = owner_registry.getCommissionHubsForOwner(user1.address, 0, 10)
    assert len(hubs) == 2
    assert hub1 in hubs
    assert hub2 in hubs

# Test permission checks
def test_permissions(owner_registry, deployer, user1, l2_relay):
    # Only L2Relay can register NFT owners
    with reverts("Only L2Relay can register NFT owners"):
        owner_registry.registerNFTOwnerFromParentChain(
            CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID, user1.address, sender=user1
        )
    
    # Only owner can set L2Relay
    with reverts("Only owner can set L2 relay"):
        owner_registry.setL2Relay(user1.address, sender=user1)
    
    # Only owner can set commission hub template
    with reverts("Only owner can set commission hub template"):
        owner_registry.setArtCommissionHubTemplate(user1.address, sender=user1)
    
    # Only owner can set profile-factory-and-registry
    with reverts("Only owner can set profile-factory-and-registry"):
        owner_registry.setProfileFactoryAndRegistry(user1.address, sender=user1)

# Test pagination of commission hubs
def test_commission_hub_pagination(owner_registry, user1):
    # Create multiple generic commission hubs
    hubs = []
    for i in range(5):
        tx = owner_registry.createGenericCommissionHub(CHAIN_ID + i, user1.address, sender=user1)
        for event in tx.events:
            if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
                hubs.append(event.commission_hub)
                break
    
    # Test pagination
    assert owner_registry.getCommissionHubCountForOwner(user1.address) == 5
    
    # Page 0, size 2
    page0 = owner_registry.getCommissionHubsForOwner(user1.address, 0, 2)
    assert len(page0) == 2
    assert page0[0] == hubs[0]
    assert page0[1] == hubs[1]
    
    # Page 1, size 2
    page1 = owner_registry.getCommissionHubsForOwner(user1.address, 1, 2)
    assert len(page1) == 2
    assert page1[0] == hubs[2]
    assert page1[1] == hubs[3]
    
    # Page 2, size 2
    page2 = owner_registry.getCommissionHubsForOwner(user1.address, 2, 2)
    assert len(page2) == 1
    assert page2[0] == hubs[4]
    
    # Page 3, size 2 (empty)
    page3 = owner_registry.getCommissionHubsForOwner(user1.address, 3, 2)
    assert len(page3) == 0 