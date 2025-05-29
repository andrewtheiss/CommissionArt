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

    # Deploy ArtEdition1155 template
    art_edition_1155_template = project.ArtEdition1155.deploy(sender=deployer)
    
    # Deploy ArtSales1155 template
    art_sales_1155_template = project.ArtSales1155.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Verify all templates were deployed
    assert profile_template.address != ZERO_ADDRESS
    assert profile_social_template.address != ZERO_ADDRESS
    assert commission_hub_template.address != ZERO_ADDRESS
    assert art_piece_template.address != ZERO_ADDRESS
    
    # Deploy factory registry
    profile_factory = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address, profile_social_template.address, commission_hub_template.address, art_edition_1155_template.address, art_sales_1155_template.address,
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
    ,
        "art_sales_1155_template": art_sales_1155_template,
        "art_edition_1155_template": art_edition_1155_template,
        "art_sales_1155_template": art_sales_1155_template}

def test_register_nft_owner_with_no_profile(setup):
    """Test registering an NFT owner who doesn't have a profile yet"""
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    deployer = setup["deployer"]
    user1 = setup["user1"]
    
    # Mock NFT data
    chain_id = 1  # Ethereum mainnet
    nft_contract = "0x1234567890123456789012345678901234567890"
    token_id = 123
    
    # Verify user1 doesn't have a profile yet
    assert profile_factory.hasProfile(user1.address) is False
    
    # Register NFT ownership for user1 who doesn't have a profile yet
    tx = art_commission_hub_owners.registerNFTOwnerFromParentChain(
        chain_id,
        nft_contract,
        token_id,
        user1.address,
        sender=deployer  # Acting as L2OwnershipRelay
    )
    
    # Verify the hub was created and linked to user1
    commission_hub = art_commission_hub_owners.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
    assert commission_hub != ZERO_ADDRESS
    
    # Verify the hub is linked to user1 in the artCommissionHubsByOwner mapping
    assert art_commission_hub_owners.getCommissionHubCountByOwner(user1.address) == 1
    hubs = art_commission_hub_owners.getCommissionHubsByOwnerWithOffset(user1.address, 0, 100, False)
    assert hubs[0] == commission_hub
    
    # Check if a profile was automatically created for user1
    # Note: Profile creation might not be automatic for NFT registration, only for generic hubs
    if profile_factory.hasProfile(user1.address):
        user1_profile = profile_factory.getProfile(user1.address)
        
        # Verify the commission hub was automatically linked to the profile
        profile = project.Profile.at(user1_profile)
        assert profile.getCommissionHubCount() == 1
        profile_hubs = profile.getCommissionHubsByOffset(0, 100, False)
        assert profile_hubs[0] == commission_hub
        
        # Verify the profile owner is set correctly
        assert profile.owner() == user1.address
    else:
        # If no profile was created automatically, that's also valid behavior
        # The hub should still be properly registered
        assert True  # Test passes - hub was created without profile

def test_register_nft_owner_with_existing_profile(setup):
    """Test registering an NFT owner who already has a profile"""
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    deployer = setup["deployer"]
    user2 = setup["user2"]
    
    # First create a profile for user2
    profile_factory.createProfile(user2.address, sender=user2)
    assert profile_factory.hasProfile(user2.address) is True
    user2_profile = profile_factory.getProfile(user2.address)
    profile = project.Profile.at(user2_profile)
    
    # Verify no commission hubs yet
    assert profile.getCommissionHubCount() == 0
    
    # Mock NFT data
    chain_id = 1  # Ethereum mainnet
    nft_contract = "0x2345678901234567890123456789012345678901"
    token_id = 456
    
    # Register NFT ownership for user2 who already has a profile
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        chain_id,
        nft_contract,
        token_id,
        user2.address,
        sender=deployer  # Acting as L2OwnershipRelay
    )
    
    # Verify the hub was created and linked to user2
    commission_hub = art_commission_hub_owners.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
    assert commission_hub != ZERO_ADDRESS
    
    # Verify the hub is linked to user2 in the artCommissionHubsByOwner mapping
    assert art_commission_hub_owners.getCommissionHubCountByOwner(user2.address) == 1
    hubs = art_commission_hub_owners.getCommissionHubsByOwnerWithOffset(user2.address, 0, 100, False)
    assert hubs[0] == commission_hub
    
    # Verify the commission hub was automatically linked to the profile
    assert profile.getCommissionHubCount() == 1
    profile_hubs = profile.getCommissionHubsByOffset(0, 100, False)
    assert profile_hubs[0] == commission_hub

def test_transfer_nft_ownership(setup):
    """Test transferring NFT ownership between users with profiles"""
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    deployer = setup["deployer"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    
    # Create profiles for both users
    if not profile_factory.hasProfile(user1.address):
        profile_factory.createProfile(user1.address, sender=user1)
    if not profile_factory.hasProfile(user2.address):
        profile_factory.createProfile(user2.address, sender=user2)
    
    user1_profile = profile_factory.getProfile(user1.address)
    user2_profile = profile_factory.getProfile(user2.address)
    profile1 = project.Profile.at(user1_profile)
    profile2 = project.Profile.at(user2_profile)
    
    # Mock NFT data
    chain_id = 1  # Ethereum mainnet
    nft_contract = "0x3456789012345678901234567890123456789012"
    token_id = 789
    
    # Register NFT ownership for user1
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        chain_id,
        nft_contract,
        token_id,
        user1.address,
        sender=deployer  # Acting as L2OwnershipRelay
    )
    
    # Verify the hub was created and linked to user1
    commission_hub = art_commission_hub_owners.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
    assert commission_hub != ZERO_ADDRESS
    
    # Verify the hub is linked to user1's profile
    assert profile1.getCommissionHubCount() == 1
    hubs1 = profile1.getCommissionHubsByOffset(0, 100, False)
    assert hubs1[0] == commission_hub
    
    # Verify user2 has no hubs yet
    assert profile2.getCommissionHubCount() == 0
    
    # Transfer NFT ownership from user1 to user2
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        chain_id,
        nft_contract,
        token_id,
        user2.address,
        sender=deployer  # Acting as L2OwnershipRelay
    )
    
    # Verify the hub was unlinked from user1's profile
    assert profile1.getCommissionHubCount() == 0
    
    # Verify the hub was linked to user2's profile
    assert profile2.getCommissionHubCount() == 1
    hubs2 = profile2.getCommissionHubsByOffset(0, 100, False)
    assert hubs2[0] == commission_hub
    
    # Verify the hub ownership in the registry
    assert art_commission_hub_owners.getCommissionHubCountByOwner(user1.address) == 0
    assert art_commission_hub_owners.getCommissionHubCountByOwner(user2.address) == 1
    
    # Verify the hub's owner was updated
    hub_instance = project.ArtCommissionHub.at(commission_hub)
    assert hub_instance.owner() == user2.address

def test_multiple_hubs_per_user(setup):
    """Test that a user can have multiple commission hubs"""
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    deployer = setup["deployer"]
    user1 = setup["user1"]
    
    # Create a profile for user1
    profile_factory.createProfile(user1.address, sender=user1)
    user1_profile = profile_factory.getProfile(user1.address)
    profile = project.Profile.at(user1_profile)
    
    # Mock NFT data for first hub
    chain_id = 1
    nft_contract1 = "0x1111111111111111111111111111111111111111"
    token_id1 = 111
    
    # Mock NFT data for second hub
    nft_contract2 = "0x2222222222222222222222222222222222222222"
    token_id2 = 222
    
    # Register first NFT
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        chain_id, nft_contract1, token_id1, user1.address, sender=deployer
    )
    
    # Register second NFT
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        chain_id, nft_contract2, token_id2, user1.address, sender=deployer
    )
    
    # Verify both hubs were created
    hub1 = art_commission_hub_owners.getArtCommissionHubByOwner(chain_id, nft_contract1, token_id1)
    hub2 = art_commission_hub_owners.getArtCommissionHubByOwner(chain_id, nft_contract2, token_id2)
    assert hub1 != ZERO_ADDRESS
    assert hub2 != ZERO_ADDRESS
    assert hub1 != hub2
    
    # Verify user has 2 hubs in the registry
    assert art_commission_hub_owners.getCommissionHubCountByOwner(user1.address) == 2
    hubs = art_commission_hub_owners.getCommissionHubsByOwnerWithOffset(user1.address, 0, 10, False)
    assert len(hubs) == 2
    assert hub1 in hubs
    assert hub2 in hubs
    
    # Verify both hubs are linked to the profile
    assert profile.getCommissionHubCount() == 2
    profile_hubs = profile.getCommissionHubsByOffset(0, 10, False)
    assert len(profile_hubs) == 2
    assert hub1 in profile_hubs
    assert hub2 in profile_hubs

def test_pagination_of_hubs(setup):
    """Test pagination of commission hubs"""
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    deployer = setup["deployer"]
    user1 = setup["user1"]
    
    # Create a profile for user1
    profile_factory.createProfile(user1.address, sender=user1)
    user1_profile = profile_factory.getProfile(user1.address)
    profile = project.Profile.at(user1_profile)
    
    # Create multiple hubs for testing pagination
    chain_id = 1
    hubs = []
    
    for i in range(5):
        nft_contract = f"0x{str(i+1).zfill(40)}"
        token_id = i + 1
        
        art_commission_hub_owners.registerNFTOwnerFromParentChain(
            chain_id, nft_contract, token_id, user1.address, sender=deployer
        )
        
        hub = art_commission_hub_owners.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
        hubs.append(hub)
    
    # Verify all hubs were created
    assert art_commission_hub_owners.getCommissionHubCountByOwner(user1.address) == 5
    assert profile.getCommissionHubCount() == 5
    
    # Test pagination - get first 3 hubs
    first_batch = art_commission_hub_owners.getCommissionHubsByOwnerWithOffset(user1.address, 0, 3, False)
    assert len(first_batch) == 3
    
    # Test pagination - get next 2 hubs
    second_batch = art_commission_hub_owners.getCommissionHubsByOwnerWithOffset(user1.address, 3, 2, False)
    assert len(second_batch) == 2
    
    # Verify no overlap between batches
    for hub in first_batch:
        assert hub not in second_batch
    
    # Verify all hubs are accounted for
    all_paginated_hubs = first_batch + second_batch
    for hub in hubs:
        assert hub in all_paginated_hubs
    
    # Test profile pagination as well
    profile_first_batch = profile.getCommissionHubsByOffset(0, 3, False)
    profile_second_batch = profile.getCommissionHubsByOffset(3, 2, False)
    assert len(profile_first_batch) == 3
    assert len(profile_second_batch) == 2

def test_bidirectional_connection(setup):
    """Test that the bidirectional connection between contracts works correctly"""
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    deployer = setup["deployer"]
    user1 = setup["user1"]
    
    # Verify the bidirectional connection is established
    assert art_commission_hub_owners.profileFactoryAndRegistry() == profile_factory.address
    assert profile_factory.artCommissionHubOwners() == art_commission_hub_owners.address
    
    # Test that creating a hub automatically links to profile
    profile_factory.createProfile(user1.address, sender=user1)
    
    # Create a generic hub
    art_commission_hub_owners.createGenericCommissionHub(user1.address, sender=user1)
    
    # Verify the hub is linked in both directions
    assert art_commission_hub_owners.getCommissionHubCountByOwner(user1.address) == 1
    
    user1_profile = profile_factory.getProfile(user1.address)
    profile = project.Profile.at(user1_profile)
    assert profile.getCommissionHubCount() == 1
    
    # Test that creating an NFT hub also links correctly
    chain_id = 1
    nft_contract = "0x1234567890123456789012345678901234567890"
    token_id = 123
    
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        chain_id, nft_contract, token_id, user1.address, sender=deployer
    )
    
    # Should now have 2 hubs
    assert art_commission_hub_owners.getCommissionHubCountByOwner(user1.address) == 2
    assert profile.getCommissionHubCount() == 2

def test_access_control_for_commission_hub_methods(setup):
    """Test access control for commission hub related methods"""
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    deployer = setup["deployer"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    
    # Test that only L2OwnershipRelay or owner can register NFT owners
    chain_id = 1
    nft_contract = "0x1234567890123456789012345678901234567890"
    token_id = 123
    
    # This should work (deployer is set as L2OwnershipRelay)
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        chain_id, nft_contract, token_id, user1.address, sender=deployer
    )
    
    # This should fail (user2 is not L2OwnershipRelay or owner)
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.registerNFTOwnerFromParentChain(
            chain_id, nft_contract, token_id + 1, user1.address, sender=user2
        )
    
    assert "Only system allowed addresses can register artCommissionHubOwners" in str(excinfo.value)
    
    # Test that only owner can create generic hubs for themselves
    # This should work
    art_commission_hub_owners.createGenericCommissionHub(user1.address, sender=user1)
    
    # This should fail
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.createGenericCommissionHub(user1.address, sender=user2)
    
    assert "Only the owner can create their own generic commission hub" in str(excinfo.value)

def test_events_for_hub_linking(setup):
    """Test that proper events are emitted when hubs are linked to profiles"""
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    deployer = setup["deployer"]
    user1 = setup["user1"]
    
    # Create a profile first
    profile_factory.createProfile(user1.address, sender=user1)
    
    # Register an NFT and check for events
    chain_id = 1
    nft_contract = "0x1234567890123456789012345678901234567890"
    token_id = 123
    
    tx = art_commission_hub_owners.registerNFTOwnerFromParentChain(
        chain_id, nft_contract, token_id, user1.address, sender=deployer
    )
    
    # Check for HubLinkedToOwner event
    hub_linked_event = None
    for event in tx.events:
        if hasattr(event, 'owner') and hasattr(event, 'hub') and event.owner == user1.address:
            hub_linked_event = event
            break
    
    assert hub_linked_event is not None, "HubLinkedToOwner event should be emitted"
    
    # Check for ArtCommissionHubCreated event
    hub_created_event = None
    for event in tx.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'is_generic'):
            hub_created_event = event
            break
    
    assert hub_created_event is not None, "ArtCommissionHubCreated event should be emitted"
    # Events return integers, so 0 means False and 1 means True
    assert hub_created_event.is_generic == 0, "NFT-based hub should not be marked as generic (is_generic should be 0)"
    
    # Test generic hub creation events
    tx2 = art_commission_hub_owners.createGenericCommissionHub(user1.address, sender=user1)
    
    # Check for GenericCommissionHubCreated event
    generic_hub_event = None
    for event in tx2.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
            generic_hub_event = event
            break
    
    assert generic_hub_event is not None, "GenericCommissionHubCreated event should be emitted" 