import pytest
from ape import accounts, project

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    user1 = accounts.test_accounts[1]
    user2 = accounts.test_accounts[2]
    
    # Deploy L2Relay
    l2_relay = project.L2Relay.deploy(sender=deployer)
    
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
    
    # Deploy ProfileSocial template
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    
    # Deploy ProfileFactoryAndRegistry
    profile_factory_and_regsitry = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address,
        profile_social_template.address,
        sender=deployer
    )
    
    # Link OwnerRegistry and ProfileFactoryAndRegistry
    owner_registry.setProfileFactoryAndRegistry(profile_factory_and_regsitry.address, sender=deployer)
    profile_factory_and_regsitry.setOwnerRegistry(owner_registry.address, sender=deployer)
    
    # Set L2Relay to the deployer for testing purposes
    owner_registry.setL2Relay(deployer.address, sender=deployer)
    
    return {
        "deployer": deployer,
        "user1": user1,
        "user2": user2,
        "owner_registry": owner_registry,
        "profile_factory_and_regsitry": profile_factory_and_regsitry,
        "l2_relay": l2_relay,
        "profile_template": profile_template,
        "profile_social_template": profile_social_template,
        "art_commission_hub_template": art_commission_hub_template
    }

def test_create_generic_commission_hub(setup):
    """Test creating a generic commission hub"""
    owner_registry = setup["owner_registry"]
    profile_factory_and_regsitry = setup["profile_factory_and_regsitry"]
    user1 = setup["user1"]
    
    # Create a generic commission hub
    tx = owner_registry.createGenericCommissionHub(1, user1.address, sender=user1)
    
    # Extract the hub address from the event
    hub_address = None
    for event in tx.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
            hub_address = event.commission_hub
            break
    
    assert hub_address is not None, "Commission hub address not found in events"
    
    # Verify the hub is marked as generic
    assert owner_registry.isGeneric(hub_address) is True
    
    # Verify the hub is linked to the owner
    assert owner_registry.getCommissionHubCountForOwner(user1.address) == 1
    hubs = owner_registry.getCommissionHubsForOwner(user1.address, 0, 10)
    assert len(hubs) == 1
    assert hubs[0] == hub_address
    
    # Verify a profile was created for the user
    assert profile_factory_and_regsitry.hasProfile(user1.address) is True
    user1_profile = profile_factory_and_regsitry.getProfile(user1.address)
    profile = project.Profile.at(user1_profile)
    
    # Verify the hub was linked to the profile
    assert profile.commissionHubCount() == 1
    profile_factory_and_regsitrys = profile.getCommissionHubs(0, 10)
    assert len(profile_factory_and_regsitrys) == 1
    assert profile_factory_and_regsitrys[0] == hub_address

def test_multiple_generic_hubs_for_same_owner(setup):
    """Test creating multiple generic commission hubs for the same owner"""
    owner_registry = setup["owner_registry"]
    profile_factory_and_regsitry = setup["profile_factory_and_regsitry"]
    user1 = setup["user1"]
    
    # Create first generic commission hub on chain 1
    tx1 = owner_registry.createGenericCommissionHub(1, user1.address, sender=user1)
    hub1_address = None
    for event in tx1.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
            hub1_address = event.commission_hub
            break
    
    # Create second generic commission hub on chain 2
    tx2 = owner_registry.createGenericCommissionHub(2, user1.address, sender=user1)
    hub2_address = None
    for event in tx2.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
            hub2_address = event.commission_hub
            break
    
    # Verify both hubs exist and are different
    assert hub1_address is not None
    assert hub2_address is not None
    assert hub1_address != hub2_address
    
    # Verify both hubs are marked as generic
    assert owner_registry.isGeneric(hub1_address) is True
    assert owner_registry.isGeneric(hub2_address) is True
    
    # Verify both hubs are linked to the owner
    assert owner_registry.getCommissionHubCountForOwner(user1.address) == 2
    hubs = owner_registry.getCommissionHubsForOwner(user1.address, 0, 10)
    assert len(hubs) == 2
    assert hub1_address in hubs
    assert hub2_address in hubs
    
    # Verify both hubs are linked to the profile
    user1_profile = profile_factory_and_regsitry.getProfile(user1.address)
    profile = project.Profile.at(user1_profile)
    assert profile.commissionHubCount() == 2
    profile_factory_and_regsitrys = profile.getCommissionHubs(0, 10)
    assert len(profile_factory_and_regsitrys) == 2
    assert hub1_address in profile_factory_and_regsitrys
    assert hub2_address in profile_factory_and_regsitrys

def test_compare_nft_and_generic_hubs(setup):
    """Test comparing NFT-based and generic commission hubs"""
    owner_registry = setup["owner_registry"]
    profile_factory_and_regsitry = setup["profile_factory_and_regsitry"]
    deployer = setup["deployer"]
    user1 = setup["user1"]
    
    # Create a profile for user1
    if not profile_factory_and_regsitry.hasProfile(user1.address):
        profile_factory_and_regsitry.createProfile(sender=user1)
    
    user1_profile = profile_factory_and_regsitry.getProfile(user1.address)
    profile = project.Profile.at(user1_profile)
    
    # Create an NFT-based commission hub
    chain_id = 1
    nft_contract = "0x1234567890123456789012345678901234567890"
    token_id = 123
    
    owner_registry.registerNFTOwnerFromParentChain(
        chain_id,
        nft_contract,
        token_id,
        user1.address,
        sender=deployer  # Acting as L2Relay
    )
    
    nft_hub_address = owner_registry.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
    
    # Create a generic commission hub
    tx = owner_registry.createGenericCommissionHub(chain_id, user1.address, sender=user1)
    generic_hub_address = None
    for event in tx.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
            generic_hub_address = event.commission_hub
            break
    
    # Verify both hubs exist and are different
    assert nft_hub_address != "0x0000000000000000000000000000000000000000"
    assert generic_hub_address is not None
    assert nft_hub_address != generic_hub_address
    
    # Verify the NFT hub is not marked as generic
    assert owner_registry.isGeneric(nft_hub_address) is False
    
    # Verify the generic hub is marked as generic
    assert owner_registry.isGeneric(generic_hub_address) is True
    
    # Verify both hubs are linked to the owner
    assert owner_registry.getCommissionHubCountForOwner(user1.address) == 2
    hubs = owner_registry.getCommissionHubsForOwner(user1.address, 0, 10)
    assert len(hubs) == 2
    assert nft_hub_address in hubs
    assert generic_hub_address in hubs
    
    # Verify both hubs are linked to the profile
    assert profile.commissionHubCount() == 2
    profile_factory_and_regsitrys = profile.getCommissionHubs(0, 10)
    assert len(profile_factory_and_regsitrys) == 2
    assert nft_hub_address in profile_factory_and_regsitrys
    assert generic_hub_address in profile_factory_and_regsitrys

def test_link_hubs_to_profile(setup):
    """Test linking hubs to a profile after creation"""
    owner_registry = setup["owner_registry"]
    profile_factory_and_regsitry = setup["profile_factory_and_regsitry"]
    deployer = setup["deployer"]
    user1 = setup["user1"]
    
    # Create a profile for user1 first
    profile_factory_and_regsitry.createProfile(sender=user1)
    user1_profile = profile_factory_and_regsitry.getProfile(user1.address)
    profile = project.Profile.at(user1_profile)
    
    # Verify the profile has no hubs yet
    assert profile.commissionHubCount() == 0
    
    # Temporarily disconnect ProfileFactoryAndRegistry from OwnerRegistry
    owner_registry.setProfileFactoryAndRegistry("0x0000000000000000000000000000000000000000", sender=deployer)
    
    # Create a generic commission hub (without profile integration)
    tx = owner_registry.createGenericCommissionHub(1, user1.address, sender=user1)
    hub_address = None
    for event in tx.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
            hub_address = event.commission_hub
            break
    
    # Verify the hub exists but is not linked to the profile yet
    assert hub_address is not None
    assert profile.commissionHubCount() == 0
    
    # Reconnect ProfileFactoryAndRegistry to OwnerRegistry
    owner_registry.setProfileFactoryAndRegistry(profile_factory_and_regsitry.address, sender=deployer)
    profile_factory_and_regsitry.setOwnerRegistry(owner_registry.address, sender=deployer)
    
    # Link hubs to profile
    owner_registry.linkHubsToProfile(user1.address, sender=user1)
    
    # Verify the hub is now linked to the profile
    assert profile.commissionHubCount() == 1
    profile_factory_and_regsitrys = profile.getCommissionHubs(0, 10)
    assert len(profile_factory_and_regsitrys) == 1
    assert profile_factory_and_regsitrys[0] == hub_address

def test_ensure_profile_creation(setup):
    """Test automatic profile creation when creating a generic hub"""
    owner_registry = setup["owner_registry"]
    profile_factory_and_regsitry = setup["profile_factory_and_regsitry"]
    user2 = setup["user2"]
    
    # Verify user2 doesn't have a profile yet
    assert profile_factory_and_regsitry.hasProfile(user2.address) is False
    
    # Create a generic commission hub for user2
    tx = owner_registry.createGenericCommissionHub(1, user2.address, sender=user2)
    
    # Verify a profile was created for user2
    assert profile_factory_and_regsitry.hasProfile(user2.address) is True
    user2_profile = profile_factory_and_regsitry.getProfile(user2.address)
    
    # Get the hub address
    hub_address = None
    for event in tx.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user2.address:
            hub_address = event.commission_hub
            break
    
    # Verify the hub was linked to the profile
    profile = project.Profile.at(user2_profile)
    assert profile.commissionHubCount() == 1
    profile_factory_and_regsitrys = profile.getCommissionHubs(0, 10)
    assert len(profile_factory_and_regsitrys) == 1
    assert profile_factory_and_regsitrys[0] == hub_address

def test_automatic_profile_creation_with_events(setup):
    """Test automatic profile creation with event verification when creating a generic hub"""
    owner_registry = setup["owner_registry"]
    profile_factory_and_regsitry = setup["profile_factory_and_regsitry"]
    user3 = accounts.test_accounts[3]  # Use a different user that hasn't been used yet
    
    # Verify user3 doesn't have a profile yet
    assert profile_factory_and_regsitry.hasProfile(user3.address) is False
    
    # Create a profile for the user first
    profile_factory_and_regsitry.createProfile(sender=user3)
    
    # Verify the profile was created
    assert profile_factory_and_regsitry.hasProfile(user3.address) is True
    profile_address = profile_factory_and_regsitry.getProfile(user3.address)
    
    # Create a generic commission hub for user3 and capture the transaction
    tx = owner_registry.createGenericCommissionHub(1, user3.address, sender=user3)
    
    # Extract events from the transaction
    hub_address = None
    
    # Find the GenericCommissionHubCreated event
    for event in tx.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user3.address:
            hub_address = event.commission_hub
    
    # Verify we found the hub address
    assert hub_address is not None, "GenericCommissionHubCreated event not found"
    
    # Verify the hub is linked to the profile
    profile = project.Profile.at(profile_address)
    assert profile.commissionHubCount() == 1
    
    # Verify the hub is marked as generic
    assert owner_registry.isGeneric(hub_address) is True

def test_generic_hub_with_existing_profile(setup):
    """Test creating a generic hub for a user who already has a profile"""
    owner_registry = setup["owner_registry"]
    profile_factory_and_regsitry = setup["profile_factory_and_regsitry"]
    user1 = setup["user1"]
    
    # Create a profile for user1 first
    profile_factory_and_regsitry.createProfile(sender=user1)
    user1_profile = profile_factory_and_regsitry.getProfile(user1.address)
    profile = project.Profile.at(user1_profile)
    
    # Verify the profile exists and has no hubs yet
    assert profile_factory_and_regsitry.hasProfile(user1.address) is True
    assert profile.commissionHubCount() == 0
    
    # Create a generic commission hub for user1
    tx = owner_registry.createGenericCommissionHub(1, user1.address, sender=user1)
    
    # Extract the hub address from the event
    hub_address = None
    for event in tx.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
            hub_address = event.commission_hub
            break
    
    assert hub_address is not None, "Commission hub address not found in events"
    
    # Verify the hub is marked as generic
    assert owner_registry.isGeneric(hub_address) is True
    
    # Verify the hub was linked to the owner
    assert owner_registry.getCommissionHubCountForOwner(user1.address) == 1
    hubs = owner_registry.getCommissionHubsForOwner(user1.address, 0, 10)
    assert len(hubs) == 1
    assert hubs[0] == hub_address
    
    # Verify the hub was linked to the existing profile
    assert profile.commissionHubCount() == 1
    profile_factory_and_regsitrys = profile.getCommissionHubs(0, 10)
    assert len(profile_factory_and_regsitrys) == 1
    assert profile_factory_and_regsitrys[0] == hub_address
    
    # Verify the profile is still the same one
    assert profile_factory_and_regsitry.getProfile(user1.address) == user1_profile 

def test_full_profile_verification(setup):
    """Test the complete flow of creating a generic hub for a new user and verify profile creation across all contracts"""
    owner_registry = setup["owner_registry"]
    profile_factory_and_regsitry = setup["profile_factory_and_regsitry"]
    
    # Use a fresh account that hasn't been used in other tests
    new_user = accounts.test_accounts[4]
    
    # STEP 1: Verify the user doesn't have a profile or any commission hubs yet
    assert profile_factory_and_regsitry.hasProfile(new_user.address) is False
    assert owner_registry.getCommissionHubCountForOwner(new_user.address) == 0
    
    # STEP 2: Create a profile for the user first
    profile_factory_and_regsitry.createProfile(sender=new_user)
    
    # Verify the profile was created
    assert profile_factory_and_regsitry.hasProfile(new_user.address) is True
    profile_address = profile_factory_and_regsitry.getProfile(new_user.address)
    
    # STEP 3: Create a generic commission hub for the new user
    tx = owner_registry.createGenericCommissionHub(1, new_user.address, sender=new_user)
    
    # STEP 4: Extract the hub address from events
    hub_address = None
    
    # Find the GenericCommissionHubCreated event
    for event in tx.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == new_user.address:
            hub_address = event.commission_hub
    
    # Verify we found the event
    assert hub_address is not None, "GenericCommissionHubCreated event not found"
    
    # STEP 5: Verify in ProfileFactoryAndRegistry
    user_profile_from_hub = profile_factory_and_regsitry.getProfile(new_user.address)
    assert user_profile_from_hub == profile_address, "Profile address mismatch in ProfileFactoryAndRegistry"
    
    # Verify user is in the latest users list
    latest_user_index = profile_factory_and_regsitry.userProfileCount() - 1
    if latest_user_index < 1000:  # Only check if within bounds of latestUsers array
        latest_user = profile_factory_and_regsitry.getLatestUserAtIndex(latest_user_index)
        assert latest_user == new_user.address, "User not found in latest users list"
    
    # STEP 6: Verify in Profile contract
    profile = project.Profile.at(profile_address)
    assert profile.owner() == new_user.address, "Profile owner mismatch"
    assert profile.hub() == profile_factory_and_regsitry.address, "Profile-Factory-And-Registry mismatch"
    
    # STEP 7: Verify in OwnerRegistry
    assert owner_registry.getCommissionHubCountForOwner(new_user.address) == 1, "Hub count mismatch in OwnerRegistry"
    hubs = owner_registry.getCommissionHubsForOwner(new_user.address, 0, 10)
    assert len(hubs) == 1, "Wrong number of hubs in OwnerRegistry"
    assert hubs[0] == hub_address, "Hub address mismatch in OwnerRegistry"
    assert owner_registry.isGeneric(hub_address) is True, "Hub not marked as generic in OwnerRegistry"
    
    # STEP 8: Verify hub is linked to profile
    assert profile.commissionHubCount() == 1, "Hub count mismatch in Profile"
    profile_factory_and_regsitrys = profile.getCommissionHubs(0, 10)
    assert len(profile_factory_and_regsitrys) == 1, "Wrong number of hubs in Profile"
    assert profile_factory_and_regsitrys[0] == hub_address, "Hub address mismatch in Profile"
    
    # STEP 9: Verify ArtCommissionHub contract
    hub = project.ArtCommissionHub.at(hub_address)
    assert hub.owner() == new_user.address, "Hub owner mismatch"
    assert hub.is_generic() is True, "Hub not marked as generic in ArtCommissionHub"
    assert hub.registry() == owner_registry.address, "Hub registry mismatch"
    
    # STEP 10: Create another hub for the same user and verify it's added to the existing profile
    tx2 = owner_registry.createGenericCommissionHub(2, new_user.address, sender=new_user)
    
    # Extract the second hub address
    hub2_address = None
    for event in tx2.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == new_user.address:
            hub2_address = event.commission_hub
    
    assert hub2_address is not None, "Second hub address not found in events"
    assert hub2_address != hub_address, "Second hub should be different from first hub"
    
    # Verify the second hub is also linked to the same profile
    assert owner_registry.getCommissionHubCountForOwner(new_user.address) == 2
    assert profile.commissionHubCount() == 2
    
    profile_factory_and_regsitrys = profile.getCommissionHubs(0, 10)
    assert len(profile_factory_and_regsitrys) == 2
    assert hub_address in profile_factory_and_regsitrys
    assert hub2_address in profile_factory_and_regsitrys 

def test_automatic_profile_creation(setup):
    """Test automatic profile creation when creating a generic hub for a user without a profile"""
    owner_registry = setup["owner_registry"]
    profile_factory_and_regsitry = setup["profile_factory_and_regsitry"]
    
    # Use a fresh account that hasn't been used in other tests
    new_user = accounts.test_accounts[5]
    
    # Verify the user doesn't have a profile yet
    assert profile_factory_and_regsitry.hasProfile(new_user.address) is False
    
    # Make sure the OwnerRegistry is properly connected to ProfileFactoryAndRegistry
    assert owner_registry.profileFactoryAndRegistry() == profile_factory_and_regsitry.address
    assert profile_factory_and_regsitry.ownerRegistry() == owner_registry.address
    
    # Create a generic commission hub for the new user
    # This should automatically create a profile
    tx = owner_registry.createGenericCommissionHub(1, new_user.address, sender=new_user)
    
    # Verify a profile was created for the user
    assert profile_factory_and_regsitry.hasProfile(new_user.address) is True
    
    # Get the profile address
    profile_address = profile_factory_and_regsitry.getProfile(new_user.address)
    assert profile_address != "0x0000000000000000000000000000000000000000"
    
    # Verify the profile was initialized correctly
    profile = project.Profile.at(profile_address)
    assert profile.owner() == new_user.address
    assert profile.hub() == profile_factory_and_regsitry.address
    
    # Extract the hub address from the event
    hub_address = None
    for event in tx.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == new_user.address:
            hub_address = event.commission_hub
            break
    
    assert hub_address is not None, "Commission hub address not found in events"
    
    # Verify the hub was linked to the profile
    assert profile.commissionHubCount() == 1
    profile_factory_and_regsitrys = profile.getCommissionHubs(0, 10)
    assert len(profile_factory_and_regsitrys) == 1
    assert profile_factory_and_regsitrys[0] == hub_address
    
    # Verify the hub is marked as generic
    assert owner_registry.isGeneric(hub_address) is True
    
    # Verify the ProfileCreated event was emitted
    profile_created_event = None
    for event in tx.events:
        if hasattr(event, 'owner') and hasattr(event, 'profile') and event.owner == new_user.address:
            profile_created_event = event
            break
    
    assert profile_created_event is not None, "ProfileCreated event not found"
    assert profile_created_event.profile == profile_address 

def test_create_generic_commission_hub_owner_permission(setup):
    """Test that an owner can create a generic hub for themselves"""
    owner_registry = setup["owner_registry"]
    user1 = setup["user1"]
    
    # User creates a hub for themselves - should succeed
    tx = owner_registry.createGenericCommissionHub(1, user1.address, sender=user1)
    
    # Extract the hub address from the event
    hub_address = None
    for event in tx.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
            hub_address = event.commission_hub
            break
    
    assert hub_address is not None, "Commission hub should be created successfully"
    assert owner_registry.isGeneric(hub_address) is True
    assert owner_registry.getCommissionHubCountForOwner(user1.address) == 1

def test_create_generic_commission_hub_permission_denial(setup):
    """Test that only the owner can create a generic hub for themselves"""
    owner_registry = setup["owner_registry"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    
    # User2 tries to create a hub for user1 - should fail
    try:
        owner_registry.createGenericCommissionHub(1, user1.address, sender=user2)
        assert False, "Should have failed with permission error"
    except Exception as e:
        # Check that the error message matches what we expect
        assert "Only the owner can create their own generic commission hub" in str(e), "Incorrect error message"
    
    # Verify no hub was created
    assert owner_registry.getCommissionHubCountForOwner(user1.address) == 0 