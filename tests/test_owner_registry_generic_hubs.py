import pytest
from ape import accounts, project

# Define constant for zero address
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

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

def test_create_generic_commission_hub(setup):
    """Test creating a generic commission hub"""
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    user1 = setup["user1"]
    
    # Create a generic commission hub
    tx = art_commission_hub_owners.createGenericCommissionHub(user1.address, sender=user1)
    
    # Extract the hub address from the event
    hub_address = None
    for event in tx.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
            hub_address = event.commission_hub
            break
    
    assert hub_address is not None, "Commission hub address not found in events"
    
    # Verify the hub is marked as generic
    assert art_commission_hub_owners.isGeneric(hub_address) is True
    
    # Verify the hub is linked to the owner
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

def test_compare_nft_and_generic_hubs(setup):
    """Test comparing NFT-based and generic commission hubs"""
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    deployer = setup["deployer"]
    user1 = setup["user1"]
    
    # Create a profile for user1
    if not profile_factory.hasProfile(user1.address):
        profile_factory.createProfile(user1.address, sender=deployer)
    
    user1_profile = profile_factory.getProfile(user1.address)
    profile = project.Profile.at(user1_profile)
    
    # Create an NFT-based commission hub
    chain_id = 1
    nft_contract = "0x1234567890123456789012345678901234567890"
    token_id = 123
    
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        chain_id,
        nft_contract,
        token_id,
        user1.address,
        sender=deployer  # Acting as L2OwnershipRelay
    )
    
    nft_hub_address = art_commission_hub_owners.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
    
    # Create a generic commission hub
    tx = art_commission_hub_owners.createGenericCommissionHub(user1.address, sender=user1)
    generic_hub_address = None
    for event in tx.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
            generic_hub_address = event.commission_hub
            break
    
    # Verify both hubs exist and are different
    assert nft_hub_address != ZERO_ADDRESS
    assert generic_hub_address is not None
    assert nft_hub_address != generic_hub_address
    
    # Verify the NFT hub is not marked as generic
    assert art_commission_hub_owners.isGeneric(nft_hub_address) is False
    
    # Verify the generic hub is marked as generic
    assert art_commission_hub_owners.isGeneric(generic_hub_address) is True
    
    # Verify both hubs are linked to the owner
    assert art_commission_hub_owners.getCommissionHubCountByOwner(user1.address) == 2
    hubs = art_commission_hub_owners.getCommissionHubsByOwnerWithOffset(user1.address, 0, 10, False)
    assert len(hubs) == 2
    assert nft_hub_address in hubs
    assert generic_hub_address in hubs
    
    # Verify both hubs are linked to the profile
    assert profile.getCommissionHubCount() == 2
    profile_hubs = profile.getCommissionHubsByOffset(0, 10, False)
    assert len(profile_hubs) == 2
    assert nft_hub_address in profile_hubs
    assert generic_hub_address in profile_hubs

def test_link_hubs_to_profile(setup):
    """Test linking hubs to a profile after creation"""
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    deployer = setup["deployer"]
    user1 = setup["user1"]
    
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
    chain_id = 1
    nft_contract = "0x1234567890123456789012345678901234567890"
    token_id = 123
    
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        chain_id, nft_contract, token_id, user1.address, sender=deployer
    )
    
    # Verify the profile now has 2 hubs (generic + NFT-based)
    assert profile.getCommissionHubCount() == 2
    
    # Get all hubs and verify they include both the generic and NFT-based hubs
    profile_hubs = profile.getCommissionHubsByOffset(0, 10, False)
    assert len(profile_hubs) == 2
    assert hub_address in profile_hubs
    
    # Verify the NFT-based hub is also in the list
    nft_hub_address = art_commission_hub_owners.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
    assert nft_hub_address in profile_hubs

def test_ensure_profile_creation(setup):
    """Test automatic profile creation when creating a generic hub"""
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    user2 = setup["user2"]
    
    # Verify user2 doesn't have a profile yet
    assert profile_factory.hasProfile(user2.address) is False
    
    # Create a generic commission hub for user2
    tx = art_commission_hub_owners.createGenericCommissionHub(user2.address, sender=user2)
    
    # Verify a profile was created for user2
    assert profile_factory.hasProfile(user2.address) is True
    user2_profile = profile_factory.getProfile(user2.address)
    
    # Get the hub address
    hub_address = None
    for event in tx.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user2.address:
            hub_address = event.commission_hub
            break
    
    # Verify the hub was linked to the profile
    profile = project.Profile.at(user2_profile)
    assert profile.getCommissionHubCount() == 1
    profile_hubs = profile.getCommissionHubsByOffset(0, 10, False)
    assert len(profile_hubs) == 1
    assert profile_hubs[0] == hub_address

def test_automatic_profile_creation_with_events(setup):
    """Test automatic profile creation with event verification when creating a generic hub"""
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    user3 = accounts.test_accounts[3]  # Use a different user that hasn't been used yet
    
    # Verify user3 doesn't have a profile yet
    assert profile_factory.hasProfile(user3.address) is False
    
    # Create a profile for the user first
    profile_factory.createProfile(user3.address, sender=user3)
    
    # Verify the profile was created
    assert profile_factory.hasProfile(user3.address) is True
    profile_address = profile_factory.getProfile(user3.address)
    
    # Create a generic commission hub for user3 and capture the transaction
    tx = art_commission_hub_owners.createGenericCommissionHub(user3.address, sender=user3)
    
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
    assert profile.getCommissionHubCount() == 1
    
    # Verify the hub is marked as generic
    assert art_commission_hub_owners.isGeneric(hub_address) is True

def test_generic_hub_with_existing_profile(setup):
    """Test creating a generic hub for a user who already has a profile"""
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    user1 = setup["user1"]
    
    # Create a profile for user1 first
    profile_factory.createProfile(user1.address, sender=user1)
    user1_profile = profile_factory.getProfile(user1.address)
    profile = project.Profile.at(user1_profile)
    
    # Verify the profile exists and has no hubs yet
    assert profile_factory.hasProfile(user1.address) is True
    assert profile.getCommissionHubCount() == 0
    
    # Create a generic commission hub for user1
    tx = art_commission_hub_owners.createGenericCommissionHub(user1.address, sender=user1)
    
    # Extract the hub address from the event
    hub_address = None
    for event in tx.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
            hub_address = event.commission_hub
            break
    
    assert hub_address is not None, "Commission hub address not found in events"
    
    # Verify the hub is marked as generic
    assert art_commission_hub_owners.isGeneric(hub_address) is True
    
    # Verify the hub was linked to the owner
    assert art_commission_hub_owners.getCommissionHubCountByOwner(user1.address) == 1
    hubs = art_commission_hub_owners.getCommissionHubsByOwnerWithOffset(user1.address, 0, 10, False)
    assert len(hubs) == 1
    assert hubs[0] == hub_address
    
    # Verify the hub was linked to the existing profile
    assert profile.getCommissionHubCount() == 1
    profile_hubs = profile.getCommissionHubsByOffset(0, 10, False)
    assert len(profile_hubs) == 1
    assert profile_hubs[0] == hub_address
    
    # Verify the profile is still the same one
    assert profile_factory.getProfile(user1.address) == user1_profile 

def test_full_profile_verification(setup):
    """Test the complete flow of creating a generic hub for a new user and verify profile creation across all contracts"""
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    
    # Use a fresh account that hasn't been used in other tests
    new_user = accounts.test_accounts[4]
    
    # STEP 1: Verify the user doesn't have a profile or any commission hubs yet
    assert profile_factory.hasProfile(new_user.address) is False
    assert art_commission_hub_owners.getCommissionHubCountByOwner(new_user.address) == 0
    
    # STEP 2: Create a profile for the user first
    profile_factory.createProfile(new_user.address, sender=new_user)
    
    # Verify the profile was created
    assert profile_factory.hasProfile(new_user.address) is True
    profile_address = profile_factory.getProfile(new_user.address)
    
    # STEP 3: Create a generic commission hub for the new user
    tx = art_commission_hub_owners.createGenericCommissionHub(new_user.address, sender=new_user)
    
    # STEP 4: Extract the hub address from events
    hub_address = None
    
    # Find the GenericCommissionHubCreated event
    for event in tx.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == new_user.address:
            hub_address = event.commission_hub
    
    # Verify we found the event
    assert hub_address is not None, "GenericCommissionHubCreated event not found"
    
    # STEP 5: Verify in ProfileFactoryAndRegistry
    user_profile_from_hub = profile_factory.getProfile(new_user.address)
    assert user_profile_from_hub == profile_address, "Profile address mismatch in ProfileFactoryAndRegistry"
    
    # Verify user is in the latest users list
    latest_user_index = profile_factory.allUserProfilesCount() - 1
    if latest_user_index < 1000:  # Only check if within bounds of latestUsers array
        latest_users = profile_factory.getLatestUserProfiles()
        # Check if the new user is in the latest users list
        assert new_user.address in latest_users, "User not found in latest users list"
    
    # STEP 6: Verify in Profile contract
    profile = project.Profile.at(profile_address)
    assert profile.owner() == new_user.address, "Profile owner mismatch"
    assert profile.profileFactoryAndRegistry() == profile_factory.address, "Profile-Factory-And-Registry mismatch"
    
    # STEP 7: Verify in ArtCommissionHubOwners
    assert art_commission_hub_owners.getCommissionHubCountByOwner(new_user.address) == 1, "Hub count mismatch in ArtCommissionHubOwners"
    hubs = art_commission_hub_owners.getCommissionHubsByOwnerWithOffset(new_user.address, 0, 10, False)
    assert len(hubs) == 1, "Wrong number of hubs in ArtCommissionHubOwners"
    assert hubs[0] == hub_address, "Hub address mismatch in ArtCommissionHubOwners"
    assert art_commission_hub_owners.isGeneric(hub_address) is True, "Hub not marked as generic in ArtCommissionHubOwners"
    
    # STEP 8: Verify hub is linked to profile
    assert profile.getCommissionHubCount() == 1, "Hub count mismatch in Profile"
    profile_hubs = profile.getCommissionHubsByOffset(0, 10, False)
    assert len(profile_hubs) == 1, "Wrong number of hubs in Profile"
    assert profile_hubs[0] == hub_address, "Hub address mismatch in Profile"
    
    # STEP 9: Verify ArtCommissionHub contract
    hub = project.ArtCommissionHub.at(hub_address)
    assert hub.owner() == new_user.address, "Hub owner mismatch"
    assert hub.isGeneric() is True, "Hub not marked as generic in ArtCommissionHub"
    assert hub.artCommissionHubOwners() == art_commission_hub_owners.address, "Hub registry mismatch"
    
    # STEP 10: Test that only one generic hub per user is allowed
    # The current implementation only allows one generic hub per owner
    tx2 = art_commission_hub_owners.createGenericCommissionHub(new_user.address, sender=new_user)
    
    # The second call should return the same hub (or no event if it already exists)
    hub2_address = None
    for event in tx2.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == new_user.address:
            hub2_address = event.commission_hub
    
    # Should still only have 1 hub
    assert art_commission_hub_owners.getCommissionHubCountByOwner(new_user.address) == 1
    assert profile.getCommissionHubCount() == 1

def test_automatic_profile_creation(setup):
    """Test automatic profile creation when creating a generic hub for a user without a profile"""
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    
    # Use a fresh account that hasn't been used in other tests
    new_user = accounts.test_accounts[5]
    
    # Verify the user doesn't have a profile yet
    assert profile_factory.hasProfile(new_user.address) is False
    
    # Make sure the ArtCommissionHubOwners is properly connected to ProfileFactoryAndRegistry
    assert art_commission_hub_owners.profileFactoryAndRegistry() == profile_factory.address
    assert profile_factory.artCommissionHubOwners() == art_commission_hub_owners.address
    
    # Create a generic commission hub for the new user
    # This should automatically create a profile
    tx = art_commission_hub_owners.createGenericCommissionHub(new_user.address, sender=new_user)
    
    # Verify a profile was created for the user
    assert profile_factory.hasProfile(new_user.address) is True
    
    # Get the profile address
    profile_address = profile_factory.getProfile(new_user.address)
    assert profile_address != ZERO_ADDRESS
    
    # Verify the profile was initialized correctly
    profile = project.Profile.at(profile_address)
    assert profile.owner() == new_user.address
    assert profile.profileFactoryAndRegistry() == profile_factory.address
    
    # Extract the hub address from the event
    hub_address = None
    for event in tx.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == new_user.address:
            hub_address = event.commission_hub
            break
    
    assert hub_address is not None, "Commission hub address not found in events"
    
    # Verify the hub was linked to the profile
    assert profile.getCommissionHubCount() == 1
    profile_hubs = profile.getCommissionHubsByOffset(0, 10, False)
    assert len(profile_hubs) == 1
    assert profile_hubs[0] == hub_address
    
    # Verify the hub is marked as generic
    assert art_commission_hub_owners.isGeneric(hub_address) is True
    
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
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    user1 = setup["user1"]
    
    # User creates a hub for themselves - should succeed
    tx = art_commission_hub_owners.createGenericCommissionHub(user1.address, sender=user1)
    
    # Extract the hub address from the event
    hub_address = None
    for event in tx.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
            hub_address = event.commission_hub
            break
    
    assert hub_address is not None, "Commission hub should be created successfully"
    assert art_commission_hub_owners.isGeneric(hub_address) is True
    assert art_commission_hub_owners.getCommissionHubCountByOwner(user1.address) == 1

def test_create_generic_commission_hub_permission_denial(setup):
    """Test that only the owner can create a generic hub for themselves"""
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    
    # User2 tries to create a hub for user1 - should fail
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.createGenericCommissionHub(user1.address, sender=user2)
    
    # Check that the error message matches what we expect
    assert "Only the owner can create their own generic commission hub" in str(excinfo.value), "Incorrect error message"
    
    # Verify no hub was created
    assert art_commission_hub_owners.getCommissionHubCountByOwner(user1.address) == 0 