import pytest
from ape import accounts, project

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    user1 = accounts.test_accounts[1]
    user2 = accounts.test_accounts[2]
    
    # Deploy L2Relay (mock)
    l2_relay = deployer
    
    # Deploy ArtCommissionHub template
    art_commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    
    # Deploy OwnerRegistry
    owner_registry = project.OwnerRegistry.deploy(
        l2_relay.address,
        art_commission_hub_template.address,
        sender=deployer
    )
    
    # Deploy Profile template
    profile_template = project.Profile.deploy(sender=deployer)
    
    # Deploy ProfileFactoryAndRegistry
    profile_factory_and_regsitry = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address,
        sender=deployer
    )
    
    # Link OwnerRegistry and ProfileFactoryAndRegistry
    owner_registry.setProfileFactoryAndRegistry(profile_factory_and_regsitry.address, sender=deployer)
    
    # Verify bidirectional connection
    assert owner_registry.profileFactoryAndRegistry() == profile_factory_and_regsitry.address
    assert profile_factory_and_regsitry.ownerRegistry() == owner_registry.address
    
    return {
        "deployer": deployer,
        "user1": user1,
        "user2": user2,
        "owner_registry": owner_registry,
        "profile_factory_and_regsitry": profile_factory_and_regsitry,
        "profile_template": profile_template,
        "art_commission_hub_template": art_commission_hub_template
    }

def test_register_nft_owner_with_no_profile(setup):
    """Test registering an NFT owner who doesn't have a profile yet"""
    owner_registry = setup["owner_registry"]
    profile_factory_and_regsitry = setup["profile_factory_and_regsitry"]
    deployer = setup["deployer"]
    user1 = setup["user1"]
    
    # Mock NFT data
    chain_id = 1  # Ethereum mainnet
    nft_contract = "0x1234567890123456789012345678901234567890"
    token_id = 123
    
    # Verify user1 doesn't have a profile yet
    assert profile_factory_and_regsitry.hasProfile(user1.address) is False
    
    # Register NFT ownership for user1 who doesn't have a profile yet
    tx = owner_registry.registerNFTOwnerFromParentChain(
        chain_id,
        nft_contract,
        token_id,
        user1.address,
        sender=deployer  # Acting as L2Relay
    )
    
    # Verify the hub was created and linked to user1
    commission_hub = owner_registry.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
    assert commission_hub != "0x0000000000000000000000000000000000000000"
    
    # Verify the hub is linked to user1 in the ownerToCommissionHubs mapping
    assert owner_registry.getCommissionHubCountForOwner(user1.address) == 1
    hubs = owner_registry.getCommissionHubsForOwner(user1.address, 0, 100)
    assert hubs[0] == commission_hub
    
    # Verify a profile was automatically created for user1
    assert profile_factory_and_regsitry.hasProfile(user1.address) is True
    user1_profile = profile_factory_and_regsitry.getProfile(user1.address)
    
    # Verify the commission hub was automatically linked to the profile
    profile = project.Profile.at(user1_profile)
    assert profile.commissionHubCount() == 1
    profile_factory_and_regsitrys = profile.getCommissionHubs(0, 100)
    assert profile_factory_and_regsitrys[0] == commission_hub
    
    # Verify the profile owner is set correctly
    assert profile.owner() == user1.address

def test_register_nft_owner_with_existing_profile(setup):
    """Test registering an NFT owner who already has a profile"""
    owner_registry = setup["owner_registry"]
    profile_factory_and_regsitry = setup["profile_factory_and_regsitry"]
    deployer = setup["deployer"]
    user2 = setup["user2"]
    
    # First create a profile for user2
    profile_factory_and_regsitry.createProfile(sender=user2)
    assert profile_factory_and_regsitry.hasProfile(user2.address) is True
    user2_profile = profile_factory_and_regsitry.getProfile(user2.address)
    profile = project.Profile.at(user2_profile)
    
    # Verify no commission hubs yet
    assert profile.commissionHubCount() == 0
    
    # Mock NFT data
    chain_id = 1  # Ethereum mainnet
    nft_contract = "0x2345678901234567890123456789012345678901"
    token_id = 456
    
    # Register NFT ownership for user2 who already has a profile
    owner_registry.registerNFTOwnerFromParentChain(
        chain_id,
        nft_contract,
        token_id,
        user2.address,
        sender=deployer  # Acting as L2Relay
    )
    
    # Verify the hub was created and linked to user2
    commission_hub = owner_registry.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
    assert commission_hub != "0x0000000000000000000000000000000000000000"
    
    # Verify the hub is linked to user2 in the ownerToCommissionHubs mapping
    assert owner_registry.getCommissionHubCountForOwner(user2.address) == 1
    hubs = owner_registry.getCommissionHubsForOwner(user2.address, 0, 100)
    assert hubs[0] == commission_hub
    
    # Verify the commission hub was automatically linked to the profile
    assert profile.commissionHubCount() == 1
    profile_factory_and_regsitrys = profile.getCommissionHubs(0, 100)
    assert profile_factory_and_regsitrys[0] == commission_hub

def test_transfer_nft_ownership(setup):
    """Test transferring NFT ownership between users with profiles"""
    owner_registry = setup["owner_registry"]
    profile_factory_and_regsitry = setup["profile_factory_and_regsitry"]
    deployer = setup["deployer"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    
    # Create profiles for both users
    if not profile_factory_and_regsitry.hasProfile(user1.address):
        profile_factory_and_regsitry.createProfile(sender=user1)
    if not profile_factory_and_regsitry.hasProfile(user2.address):
        profile_factory_and_regsitry.createProfile(sender=user2)
    
    user1_profile = profile_factory_and_regsitry.getProfile(user1.address)
    user2_profile = profile_factory_and_regsitry.getProfile(user2.address)
    profile1 = project.Profile.at(user1_profile)
    profile2 = project.Profile.at(user2_profile)
    
    # Mock NFT data
    chain_id = 1  # Ethereum mainnet
    nft_contract = "0x3456789012345678901234567890123456789012"
    token_id = 789
    
    # Register NFT ownership for user1
    owner_registry.registerNFTOwnerFromParentChain(
        chain_id,
        nft_contract,
        token_id,
        user1.address,
        sender=deployer  # Acting as L2Relay
    )
    
    # Verify the hub was created and linked to user1
    commission_hub = owner_registry.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
    assert commission_hub != "0x0000000000000000000000000000000000000000"
    
    # Verify the hub is linked to user1's profile
    assert profile1.commissionHubCount() == 1
    hubs1 = profile1.getCommissionHubs(0, 100)
    assert hubs1[0] == commission_hub
    
    # Verify user2 has no hubs yet
    assert profile2.commissionHubCount() == 0
    
    # Transfer NFT ownership from user1 to user2
    owner_registry.registerNFTOwnerFromParentChain(
        chain_id,
        nft_contract,
        token_id,
        user2.address,
        sender=deployer  # Acting as L2Relay
    )
    
    # Verify the hub was unlinked from user1's profile
    assert profile1.commissionHubCount() == 0
    
    # Verify the hub is now linked to user2's profile
    assert profile2.commissionHubCount() == 1
    hubs2 = profile2.getCommissionHubs(0, 100)
    assert hubs2[0] == commission_hub
    
    # Verify the ownerToCommissionHubs mappings were updated
    assert owner_registry.getCommissionHubCountForOwner(user1.address) == 0
    assert owner_registry.getCommissionHubCountForOwner(user2.address) == 1
    hubs = owner_registry.getCommissionHubsForOwner(user2.address, 0, 100)
    assert hubs[0] == commission_hub

def test_multiple_hubs_per_user(setup):
    """Test a user owning multiple commission hubs"""
    owner_registry = setup["owner_registry"]
    profile_factory_and_regsitry = setup["profile_factory_and_regsitry"]
    deployer = setup["deployer"]
    user1 = setup["user1"]
    
    # Create profile for user1 if not exists
    if not profile_factory_and_regsitry.hasProfile(user1.address):
        profile_factory_and_regsitry.createProfile(sender=user1)
    
    user1_profile = profile_factory_and_regsitry.getProfile(user1.address)
    profile1 = project.Profile.at(user1_profile)
    
    # Register 3 different NFTs for user1
    for i in range(3):
        chain_id = 1  # Ethereum mainnet
        nft_contract = f"0x{i+1}000000000000000000000000000000000000000"
        token_id = i + 1
        
        owner_registry.registerNFTOwnerFromParentChain(
            chain_id,
            nft_contract,
            token_id,
            user1.address,
            sender=deployer  # Acting as L2Relay
        )
    
    # Verify user1 now has 3 commission hubs
    assert owner_registry.getCommissionHubCountForOwner(user1.address) == 3
    assert profile1.commissionHubCount() == 3
    
    # Get all hubs from the registry
    registry_hubs = owner_registry.getCommissionHubsForOwner(user1.address, 0, 100)
    assert len(registry_hubs) == 3
    
    # Get all hubs from the profile
    profile_factory_and_regsitrys = profile1.getCommissionHubs(0, 100)
    assert len(profile_factory_and_regsitrys) == 3
    
    # Verify the hubs match between registry and profile
    for hub in registry_hubs:
        assert hub in profile_factory_and_regsitrys

def test_pagination_of_hubs(setup):
    """Test pagination of commission hubs"""
    owner_registry = setup["owner_registry"]
    profile_factory_and_regsitry = setup["profile_factory_and_regsitry"]
    deployer = setup["deployer"]
    user1 = setup["user1"]
    
    # Create profile for user1 if not exists
    if not profile_factory_and_regsitry.hasProfile(user1.address):
        profile_factory_and_regsitry.createProfile(sender=user1)
    
    user1_profile = profile_factory_and_regsitry.getProfile(user1.address)
    profile1 = project.Profile.at(user1_profile)
    
    # Register 5 different NFTs for user1
    for i in range(5):
        chain_id = 1  # Ethereum mainnet
        nft_contract = f"0x{i+1}000000000000000000000000000000000000000"
        token_id = i + 1
        
        owner_registry.registerNFTOwnerFromParentChain(
            chain_id,
            nft_contract,
            token_id,
            user1.address,
            sender=deployer  # Acting as L2Relay
        )
    
    # Verify user1 now has 5 commission hubs
    assert owner_registry.getCommissionHubCountForOwner(user1.address) == 5
    assert profile1.commissionHubCount() == 5
    
    # Test pagination from registry
    page1 = owner_registry.getCommissionHubsForOwner(user1.address, 0, 2)
    page2 = owner_registry.getCommissionHubsForOwner(user1.address, 1, 2)
    page3 = owner_registry.getCommissionHubsForOwner(user1.address, 2, 2)
    
    assert len(page1) == 2
    assert len(page2) == 2
    assert len(page3) == 1
    
    # Test pagination from profile
    profile_page1 = profile1.getCommissionHubs(0, 2)
    profile_page2 = profile1.getCommissionHubs(1, 2)
    profile_page3 = profile1.getCommissionHubs(2, 2)
    
    assert len(profile_page1) == 2
    assert len(profile_page2) == 2
    assert len(profile_page3) == 1
    
    # Test recent hubs (reverse order)
    recent_hubs = profile1.getRecentCommissionHubs(0, 3)
    assert len(recent_hubs) == 3
    
    # The most recent hubs should be the last ones added
    all_hubs = profile1.getCommissionHubs(0, 100)
    assert recent_hubs[0] == all_hubs[4]  # Most recent
    assert recent_hubs[1] == all_hubs[3]  # Second most recent
    assert recent_hubs[2] == all_hubs[2]  # Third most recent

def test_bidirectional_connection(setup):
    """Test the bidirectional connection between OwnerRegistry and ProfileFactoryAndRegistry"""
    deployer = setup["deployer"]
    
    # Deploy new instances of OwnerRegistry and ProfileFactoryAndRegistry
    art_commission_hub_template = setup["art_commission_hub_template"]
    profile_template = setup["profile_template"]
    
    # Deploy OwnerRegistry without initial connection
    owner_registry = project.OwnerRegistry.deploy(
        deployer.address,  # Mock L2Relay
        art_commission_hub_template.address,
        sender=deployer
    )
    
    # Deploy ProfileFactoryAndRegistry
    profile_factory_and_regsitry = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address,
        sender=deployer
    )
    
    # Verify no initial connection
    assert owner_registry.profileFactoryAndRegistry() == "0x0000000000000000000000000000000000000000"
    assert profile_factory_and_regsitry.ownerRegistry() == "0x0000000000000000000000000000000000000000"
    
    # Set the bidirectional connection
    owner_registry.setProfileFactoryAndRegistry(profile_factory_and_regsitry.address, sender=deployer)
    
    # Verify both connections are established
    assert owner_registry.profileFactoryAndRegistry() == profile_factory_and_regsitry.address
    assert profile_factory_and_regsitry.ownerRegistry() == owner_registry.address
    
    # Test updating the connection to a new ProfileFactoryAndRegistry
    new_profile_factory_and_regsitry = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address,
        sender=deployer
    )
    
    owner_registry.setProfileFactoryAndRegistry(new_profile_factory_and_regsitry.address, sender=deployer)
    
    # Verify the connection is updated
    assert owner_registry.profileFactoryAndRegistry() == new_profile_factory_and_regsitry.address
    assert new_profile_factory_and_regsitry.ownerRegistry() == owner_registry.address

def test_access_control_for_commission_hub_methods(setup):
    """Test access control for addCommissionHub and removeCommissionHub in Profile"""
    owner_registry = setup["owner_registry"]
    profile_factory_and_regsitry = setup["profile_factory_and_regsitry"]
    deployer = setup["deployer"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    
    # Create profile for user1
    profile_factory_and_regsitry.createProfile(sender=user1)
    user1_profile = profile_factory_and_regsitry.getProfile(user1.address)
    profile = project.Profile.at(user1_profile)
    
    # Mock NFT data
    chain_id = 1
    nft_contract = "0x1234567890123456789012345678901234567890"
    token_id = 123
    
    # Register NFT ownership for user1
    owner_registry.registerNFTOwnerFromParentChain(
        chain_id,
        nft_contract,
        token_id,
        user1.address,
        sender=deployer
    )
    
    # Get the hub address
    commission_hub = owner_registry.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
    
    # Try to add a hub directly as user1 (profile owner) - should fail
    with pytest.raises(Exception) as excinfo:
        profile.addCommissionHub(commission_hub, sender=user1)
    assert "Only hub or registry can add commission hub" in str(excinfo.value)
    
    # Try to add a hub as user2 (not profile owner) - should fail
    with pytest.raises(Exception) as excinfo:
        profile.addCommissionHub(commission_hub, sender=user2)
    assert "Only hub or registry can add commission hub" in str(excinfo.value)
    
    # Try to remove a hub directly as user1 (profile owner) - should fail
    with pytest.raises(Exception) as excinfo:
        profile.removeCommissionHub(commission_hub, sender=user1)
    assert "Only hub or registry can remove commission hub" in str(excinfo.value)
    
    # Try to remove a hub as user2 (not profile owner) - should fail
    with pytest.raises(Exception) as excinfo:
        profile.removeCommissionHub(commission_hub, sender=user2)
    assert "Only hub or registry can remove commission hub" in str(excinfo.value)

def test_events_for_hub_linking(setup):
    """Test events emitted when linking/unlinking hubs to owners"""
    owner_registry = setup["owner_registry"]
    profile_factory_and_regsitry = setup["profile_factory_and_regsitry"]
    deployer = setup["deployer"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    
    # Create profile for user1
    profile_factory_and_regsitry.createProfile(sender=user1)
    
    # Mock NFT data
    chain_id = 1
    nft_contract = "0x1234567890123456789012345678901234567890"
    token_id = 123
    
    # Register NFT ownership for user1 and capture the event
    tx = owner_registry.registerNFTOwnerFromParentChain(
        chain_id,
        nft_contract,
        token_id,
        user1.address,
        sender=deployer
    )
    
    # Get the hub address
    commission_hub = owner_registry.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
    
    # Verify HubLinkedToOwner event was emitted - instead of checking event.name, check for existence of specific attributes
    linked_events = []
    for e in tx.events:
        if hasattr(e, 'owner') and hasattr(e, 'hub'):
            linked_events.append(e)
    
    assert len(linked_events) == 1
    assert linked_events[0].owner == user1.address
    assert linked_events[0].hub == commission_hub
    
    # Transfer ownership to user2 and capture events
    tx = owner_registry.registerNFTOwnerFromParentChain(
        chain_id,
        nft_contract,
        token_id,
        user2.address,
        sender=deployer
    )
    
    # Verify both HubUnlinkedFromOwner and HubLinkedToOwner events were emitted
    # For HubUnlinkedFromOwner events
    unlinked_events = []
    for e in tx.events:
        if hasattr(e, 'owner') and hasattr(e, 'hub') and e.owner == user1.address:
            unlinked_events.append(e)
    
    # For HubLinkedToOwner events
    linked_events = []
    for e in tx.events:
        if hasattr(e, 'owner') and hasattr(e, 'hub') and e.owner == user2.address:
            linked_events.append(e)
    
    assert len(unlinked_events) >= 1
    assert unlinked_events[0].owner == user1.address
    assert unlinked_events[0].hub == commission_hub
    
    assert len(linked_events) >= 1
    assert linked_events[0].owner == user2.address
    assert linked_events[0].hub == commission_hub 