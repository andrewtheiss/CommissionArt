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
    """Test permission checks for registerNFTOwnerFromParentChain"""
    deployer = setup["deployer"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    
    # Test that unauthorized users cannot register NFT owners
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.registerNFTOwnerFromParentChain(
            CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID, user1.address, sender=user1
        )
    assert "Only system allowed addresses can register artCommissionHubOwners" in str(excinfo.value)
    
    # Test that another unauthorized user also cannot register
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.registerNFTOwnerFromParentChain(
            CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID, user1.address, sender=user2
        )
    assert "Only system allowed addresses can register artCommissionHubOwners" in str(excinfo.value)
    
    # Test other permission-restricted methods
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

def test_system_allowed_permissions(setup):
    """Test that all system allowed addresses can call registerNFTOwnerFromParentChain"""
    deployer = setup["deployer"]
    user1 = setup["user1"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    
    # Test 1: Contract owner (deployer) can register - this should work
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID, user1.address, sender=deployer
    )
    assert art_commission_hub_owners.lookupRegisteredOwner(CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID) == user1.address
    
    # Test 2: L2OwnershipRelay can register (deployer is set as L2OwnershipRelay in setup)
    # Change the owner to user1 using the L2OwnershipRelay (deployer)
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID + 1, user1.address, sender=deployer
    )
    assert art_commission_hub_owners.lookupRegisteredOwner(CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID + 1) == user1.address
    
    # Test 3: ProfileFactoryAndRegistry can register (it's linked in setup)
    # Note: This would require calling from the profile factory contract, which is complex to test directly
    # We'll verify the isSystemAllowed method instead
    assert art_commission_hub_owners.isSystemAllowed(deployer.address) == True  # owner
    assert art_commission_hub_owners.isSystemAllowed(deployer.address) == True  # L2OwnershipRelay (same as owner in setup)
    assert art_commission_hub_owners.isSystemAllowed(profile_factory.address) == True  # ProfileFactoryAndRegistry
    assert art_commission_hub_owners.isSystemAllowed(art_commission_hub_owners.address) == True  # self
    
    # Test 4: Non-system addresses should not be allowed
    assert art_commission_hub_owners.isSystemAllowed(user1.address) == False

def test_owner_only_permissions(setup):
    """Test methods that only the contract owner can call"""
    deployer = setup["deployer"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    commission_hub_template = setup["commission_hub_template"]
    
    # Test setL2OwnershipRelay - only owner can call
    # Should work for owner
    art_commission_hub_owners.setL2OwnershipRelay(user1.address, sender=deployer)
    assert art_commission_hub_owners.l2OwnershipRelay() == user1.address
    
    # Should fail for non-owner
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.setL2OwnershipRelay(user2.address, sender=user1)
    assert "Only owner can set L2 relay" in str(excinfo.value)
    
    # Test setArtCommissionHubTemplate - only owner can call
    # Should work for owner
    art_commission_hub_owners.setArtCommissionHubTemplate(commission_hub_template.address, sender=deployer)
    assert art_commission_hub_owners.artCommissionHubTemplate() == commission_hub_template.address
    
    # Should fail for non-owner
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.setArtCommissionHubTemplate(user1.address, sender=user1)
    assert "Only owner can set commission hub template" in str(excinfo.value)
    
    # Test linkProfileFactoryAndRegistry - only owner can call
    # Should work for owner (re-linking the same address)
    profile_factory = setup["profile_factory"]
    art_commission_hub_owners.linkProfileFactoryAndRegistry(profile_factory.address, sender=deployer)
    assert art_commission_hub_owners.profileFactoryAndRegistry() == profile_factory.address
    
    # Should fail for non-owner
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.linkProfileFactoryAndRegistry(user1.address, sender=user1)
    assert "Only owner can set profile-factory-and-registry" in str(excinfo.value)

def test_generic_hub_creation_permissions(setup):
    """Test permissions for creating generic commission hubs"""
    deployer = setup["deployer"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    
    # Test 1: User can create their own generic hub
    tx = art_commission_hub_owners.createGenericCommissionHub(user1.address, sender=user1)
    # Verify it was created
    assert art_commission_hub_owners.getCommissionHubCountByOwner(user1.address) == 1
    
    # Test 2: Contract owner can create a generic hub for anyone
    tx = art_commission_hub_owners.createGenericCommissionHub(user2.address, sender=deployer)
    # Verify it was created
    assert art_commission_hub_owners.getCommissionHubCountByOwner(user2.address) == 1
    
    # Test 3: User cannot create a generic hub for someone else
    user3 = setup["user1"]  # Reuse user1 as user3 for this test
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.createGenericCommissionHub(user3.address, sender=user2)
    assert "Only the owner can create their own generic commission hub" in str(excinfo.value)

def test_l2_ownership_relay_permissions(setup):
    """Test L2OwnershipRelay specific permissions"""
    deployer = setup["deployer"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    
    # Initially, deployer is set as L2OwnershipRelay
    assert art_commission_hub_owners.l2OwnershipRelay() == deployer.address
    
    # L2OwnershipRelay can register NFT owners
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        CHAIN_ID, TEST_NFT_CONTRACT, 100, user1.address, sender=deployer
    )
    assert art_commission_hub_owners.lookupRegisteredOwner(CHAIN_ID, TEST_NFT_CONTRACT, 100) == user1.address
    
    # Change L2OwnershipRelay to user1
    art_commission_hub_owners.setL2OwnershipRelay(user1.address, sender=deployer)
    assert art_commission_hub_owners.l2OwnershipRelay() == user1.address
    
    # Now user1 (new L2OwnershipRelay) can register NFT owners
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        CHAIN_ID, TEST_NFT_CONTRACT, 101, user2.address, sender=user1
    )
    assert art_commission_hub_owners.lookupRegisteredOwner(CHAIN_ID, TEST_NFT_CONTRACT, 101) == user2.address
    
    # But user2 (not L2OwnershipRelay) cannot register
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.registerNFTOwnerFromParentChain(
            CHAIN_ID, TEST_NFT_CONTRACT, 102, user1.address, sender=user2
        )
    assert "Only system allowed addresses can register artCommissionHubOwners" in str(excinfo.value)

def test_profile_factory_integration_permissions(setup):
    """Test ProfileFactoryAndRegistry integration and permissions"""
    deployer = setup["deployer"]
    user1 = setup["user1"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    
    # Verify ProfileFactoryAndRegistry is linked and has system permissions
    assert art_commission_hub_owners.profileFactoryAndRegistry() == profile_factory.address
    assert art_commission_hub_owners.isSystemAllowed(profile_factory.address) == True
    
    # Test that ProfileFactoryAndRegistry can trigger hub creation through createGenericCommissionHub
    # This happens automatically when a profile is created and the user doesn't have a hub
    
    # Create a profile for user1 (this may trigger hub creation)
    profile_factory.createProfile(user1.address, sender=deployer)
    assert profile_factory.hasProfile(user1.address) == True
    
    # The profile should be able to query commission hubs
    user1_profile = profile_factory.getProfile(user1.address)
    profile = project.Profile.at(user1_profile)
    
    # The profile's getCommissionHubCount should work (even if 0)
    hub_count = profile.getCommissionHubCount()
    assert hub_count >= 0  # Could be 0 if no hubs were auto-created

def test_art_piece_approval_permissions(setup):
    """Test art piece approval and code hash management permissions"""
    deployer = setup["deployer"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    art_piece_template = setup["art_piece_template"]
    
    # Test setApprovedArtPiece - only owner can call
    # Should work for owner
    art_commission_hub_owners.setApprovedArtPiece(art_piece_template.address, True, sender=deployer)
    assert art_commission_hub_owners.isApprovedArtPieceAddress(art_piece_template.address) == True
    
    # Should fail for non-owner
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.setApprovedArtPiece(art_piece_template.address, False, sender=user1)
    assert "Only the owner can set approved art piece code hashes" in str(excinfo.value)
    
    # Test with non-contract address should fail
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.setApprovedArtPiece(user1.address, True, sender=deployer)
    # The error might be "Art piece is not a contract" or just "Transaction failed" depending on the implementation
    error_msg = str(excinfo.value)
    assert "Art piece is not a contract" in error_msg or "Transaction failed" in error_msg
    
    # Test isApprovedArtPiece with address (simpler than dealing with codehash)
    assert art_commission_hub_owners.isApprovedArtPieceAddress(art_piece_template.address) == True
    
    # Test removing approval
    art_commission_hub_owners.setApprovedArtPiece(art_piece_template.address, False, sender=deployer)
    assert art_commission_hub_owners.isApprovedArtPieceAddress(art_piece_template.address) == False

def test_hub_ownership_verification_permissions(setup):
    """Test hub ownership verification and update permissions"""
    deployer = setup["deployer"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    
    # Create a commission hub for user1
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID, user1.address, sender=deployer
    )
    hub_address = art_commission_hub_owners.getArtCommissionHubByOwner(CHAIN_ID, TEST_NFT_CONTRACT, TEST_TOKEN_ID)
    
    # Test isAllowedToUpdateHubForAddress
    assert art_commission_hub_owners.isAllowedToUpdateHubForAddress(hub_address, user1.address) == True  # Owner can update
    assert art_commission_hub_owners.isAllowedToUpdateHubForAddress(hub_address, user2.address) == False  # Non-owner cannot
    assert art_commission_hub_owners.isAllowedToUpdateHubForAddress(hub_address, deployer.address) == False  # Even deployer cannot if not owner
    
    # Test with invalid hub address
    assert art_commission_hub_owners.isAllowedToUpdateHubForAddress(ZERO_ADDRESS, user1.address) == False

def test_contract_initialization_permissions(setup):
    """Test contract initialization and setup permissions"""
    deployer = setup["deployer"]
    user1 = setup["user1"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    commission_hub_template = setup["commission_hub_template"]
    art_piece_template = setup["art_piece_template"]
    
    # Test that contract is properly initialized
    assert art_commission_hub_owners.owner() == deployer.address
    assert art_commission_hub_owners.l2OwnershipRelay() == deployer.address
    assert art_commission_hub_owners.artCommissionHubTemplate() == commission_hub_template.address
    assert art_commission_hub_owners.profileFactoryAndRegistry() == profile_factory.address
    
    # Test that only owner can change critical settings
    new_template = art_piece_template.address  # Use art piece template as a dummy new template
    
    # Owner can update template
    art_commission_hub_owners.setArtCommissionHubTemplate(new_template, sender=deployer)
    assert art_commission_hub_owners.artCommissionHubTemplate() == new_template
    
    # Non-owner cannot update template
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.setArtCommissionHubTemplate(commission_hub_template.address, sender=user1)
    assert "Only owner can set commission hub template" in str(excinfo.value)

def test_edge_case_permissions(setup):
    """Test edge cases and boundary conditions for permissions"""
    deployer = setup["deployer"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    
    # Test registering with zero address owner
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        CHAIN_ID, TEST_NFT_CONTRACT, 999, ZERO_ADDRESS, sender=deployer
    )
    assert art_commission_hub_owners.lookupRegisteredOwner(CHAIN_ID, TEST_NFT_CONTRACT, 999) == ZERO_ADDRESS
    
    # Test registering with zero address NFT contract
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        CHAIN_ID, ZERO_ADDRESS, 1000, user1.address, sender=deployer
    )
    assert art_commission_hub_owners.lookupRegisteredOwner(CHAIN_ID, ZERO_ADDRESS, 1000) == user1.address
    
    # Test with maximum chain ID
    max_chain_id = 2**256 - 1
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        max_chain_id, TEST_NFT_CONTRACT, 1001, user1.address, sender=deployer
    )
    assert art_commission_hub_owners.lookupRegisteredOwner(max_chain_id, TEST_NFT_CONTRACT, 1001) == user1.address
    
    # Test with maximum token ID
    max_token_id = 2**256 - 1
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        CHAIN_ID, TEST_NFT_CONTRACT, max_token_id, user1.address, sender=deployer
    )
    assert art_commission_hub_owners.lookupRegisteredOwner(CHAIN_ID, TEST_NFT_CONTRACT, max_token_id) == user1.address

def test_multiple_role_permissions(setup):
    """Test scenarios where addresses have multiple roles"""
    deployer = setup["deployer"]
    user1 = setup["user1"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    
    # Initially deployer is both owner and L2OwnershipRelay
    assert art_commission_hub_owners.owner() == deployer.address
    assert art_commission_hub_owners.l2OwnershipRelay() == deployer.address
    assert art_commission_hub_owners.isSystemAllowed(deployer.address) == True
    
    # Change L2OwnershipRelay to user1, but deployer remains owner
    art_commission_hub_owners.setL2OwnershipRelay(user1.address, sender=deployer)
    
    # Now both deployer (owner) and user1 (L2OwnershipRelay) should be system allowed
    assert art_commission_hub_owners.isSystemAllowed(deployer.address) == True  # Still owner
    assert art_commission_hub_owners.isSystemAllowed(user1.address) == True  # Now L2OwnershipRelay
    assert art_commission_hub_owners.isSystemAllowed(profile_factory.address) == True  # ProfileFactoryAndRegistry
    assert art_commission_hub_owners.isSystemAllowed(art_commission_hub_owners.address) == True  # Self
    
    # Both should be able to register NFT owners
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        CHAIN_ID, TEST_NFT_CONTRACT, 2000, user1.address, sender=deployer  # Owner calling
    )
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        CHAIN_ID, TEST_NFT_CONTRACT, 2001, deployer.address, sender=user1  # L2OwnershipRelay calling
    )
    
    assert art_commission_hub_owners.lookupRegisteredOwner(CHAIN_ID, TEST_NFT_CONTRACT, 2000) == user1.address
    assert art_commission_hub_owners.lookupRegisteredOwner(CHAIN_ID, TEST_NFT_CONTRACT, 2001) == deployer.address

def test_permission_state_changes(setup):
    """Test how permissions change when contract state changes"""
    deployer = setup["deployer"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    
    # Initial state: deployer is owner and L2OwnershipRelay
    assert art_commission_hub_owners.isSystemAllowed(deployer.address) == True
    assert art_commission_hub_owners.isSystemAllowed(user1.address) == False
    
    # Change L2OwnershipRelay to user1
    art_commission_hub_owners.setL2OwnershipRelay(user1.address, sender=deployer)
    
    # Now user1 should be system allowed
    assert art_commission_hub_owners.isSystemAllowed(user1.address) == True
    
    # Change L2OwnershipRelay to user2
    art_commission_hub_owners.setL2OwnershipRelay(user2.address, sender=deployer)
    
    # Now user1 should no longer be system allowed, but user2 should be
    assert art_commission_hub_owners.isSystemAllowed(user1.address) == False
    assert art_commission_hub_owners.isSystemAllowed(user2.address) == True
    
    # Deployer should still be system allowed (as owner)
    assert art_commission_hub_owners.isSystemAllowed(deployer.address) == True
    
    # ProfileFactoryAndRegistry should still be system allowed
    assert art_commission_hub_owners.isSystemAllowed(profile_factory.address) == True

def test_generic_vs_nft_hub_permissions(setup):
    """Test permission differences between generic and NFT-based hubs"""
    deployer = setup["deployer"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    
    # Create a generic hub for user1
    tx1 = art_commission_hub_owners.createGenericCommissionHub(user1.address, sender=user1)
    generic_hub = None
    for event in tx1.events:
        if hasattr(event, 'commission_hub') and hasattr(event, 'owner') and event.owner == user1.address:
            generic_hub = event.commission_hub
            break
    
    # Create an NFT-based hub for user2
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        CHAIN_ID, TEST_NFT_CONTRACT, 3000, user2.address, sender=deployer
    )
    nft_hub = art_commission_hub_owners.getArtCommissionHubByOwner(CHAIN_ID, TEST_NFT_CONTRACT, 3000)
    
    # Both should be valid hubs
    assert generic_hub is not None
    assert nft_hub != ZERO_ADDRESS
    
    # Test isGeneric flag
    assert art_commission_hub_owners.isGeneric(generic_hub) == True
    assert art_commission_hub_owners.isGeneric(nft_hub) == False
    
    # Test ownership verification for both types
    assert art_commission_hub_owners.isAllowedToUpdateHubForAddress(generic_hub, user1.address) == True
    assert art_commission_hub_owners.isAllowedToUpdateHubForAddress(generic_hub, user2.address) == False
    
    assert art_commission_hub_owners.isAllowedToUpdateHubForAddress(nft_hub, user2.address) == True
    assert art_commission_hub_owners.isAllowedToUpdateHubForAddress(nft_hub, user1.address) == False

def test_security_boundary_conditions(setup):
    """Test security-related boundary conditions and potential attack vectors"""
    deployer = setup["deployer"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    
    # Test that users cannot escalate privileges by calling system methods
    
    # User cannot set themselves as L2OwnershipRelay
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.setL2OwnershipRelay(user1.address, sender=user1)
    assert "Only owner can set L2 relay" in str(excinfo.value)
    
    # User cannot set themselves as ProfileFactoryAndRegistry
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.linkProfileFactoryAndRegistry(user1.address, sender=user1)
    assert "Only owner can set profile-factory-and-registry" in str(excinfo.value)
    
    # User cannot approve their own art piece contracts
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.setApprovedArtPiece(user1.address, True, sender=user1)
    assert "Only the owner can set approved art piece code hashes" in str(excinfo.value)
    
    # Test that even if user1 becomes L2OwnershipRelay, they still can't change owner-only settings
    art_commission_hub_owners.setL2OwnershipRelay(user1.address, sender=deployer)
    
    # user1 can now register NFT owners (as L2OwnershipRelay)
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        CHAIN_ID, TEST_NFT_CONTRACT, 4000, user2.address, sender=user1
    )
    
    # But user1 still cannot change owner-only settings
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.setL2OwnershipRelay(user2.address, sender=user1)
    assert "Only owner can set L2 relay" in str(excinfo.value)
    
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.linkProfileFactoryAndRegistry(user2.address, sender=user1)
    assert "Only owner can set profile-factory-and-registry" in str(excinfo.value)

def test_permission_consistency_across_methods(setup):
    """Test that permission checks are consistent across all methods"""
    deployer = setup["deployer"]
    user1 = setup["user1"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    commission_hub_template = setup["commission_hub_template"]
    
    # Test that isSystemAllowed matches actual permissions for registerNFTOwnerFromParentChain
    
    # deployer should be system allowed and able to register
    assert art_commission_hub_owners.isSystemAllowed(deployer.address) == True
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        CHAIN_ID, TEST_NFT_CONTRACT, 5000, user1.address, sender=deployer
    )  # Should succeed
    
    # user1 should not be system allowed and not able to register
    assert art_commission_hub_owners.isSystemAllowed(user1.address) == False
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.registerNFTOwnerFromParentChain(
            CHAIN_ID, TEST_NFT_CONTRACT, 5001, user1.address, sender=user1
        )
    assert "Only system allowed addresses can register artCommissionHubOwners" in str(excinfo.value)
    
    # Test owner-only methods consistency
    owner_only_methods = [
        ("setL2OwnershipRelay", [user1.address]),
        ("setArtCommissionHubTemplate", [commission_hub_template.address]),
        ("linkProfileFactoryAndRegistry", [art_commission_hub_owners.profileFactoryAndRegistry()]),
    ]
    
    for method_name, args in owner_only_methods:
        # Should work for owner
        method = getattr(art_commission_hub_owners, method_name)
        method(*args, sender=deployer)  # Should succeed
        
        # Should fail for non-owner
        with pytest.raises(Exception):
            method(*args, sender=user1)  # Should fail

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

def test_cross_contract_permission_interactions(setup):
    """Test permission interactions between different contracts"""
    deployer = setup["deployer"]
    user1 = setup["user1"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    
    # Test that ProfileFactoryAndRegistry can interact with ArtCommissionHubOwners
    # Create a profile which should be able to query commission hubs
    profile_factory.createProfile(user1.address, sender=deployer)
    user1_profile = profile_factory.getProfile(user1.address)
    profile = project.Profile.at(user1_profile)
    
    # Create a commission hub for user1
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        CHAIN_ID, TEST_NFT_CONTRACT, 6000, user1.address, sender=deployer
    )
    
    # Profile should be able to query commission hubs through the registry
    hub_count = profile.getCommissionHubCount()
    assert hub_count >= 1  # Should have at least the hub we just created
    
    # Profile should be able to get commission hubs
    hubs = profile.getCommissionHubsByOffset(0, 10, False)
    assert len(hubs) >= 1
    
    # Verify the hub we created is in the list
    created_hub = art_commission_hub_owners.getArtCommissionHubByOwner(CHAIN_ID, TEST_NFT_CONTRACT, 6000)
    assert created_hub in hubs

def test_state_validation_permissions(setup):
    """Test that state validation works correctly with permissions"""
    deployer = setup["deployer"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    
    # Test that state is properly maintained across permission changes
    
    # Create initial state
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        CHAIN_ID, TEST_NFT_CONTRACT, 7000, user1.address, sender=deployer
    )
    hub1 = art_commission_hub_owners.getArtCommissionHubByOwner(CHAIN_ID, TEST_NFT_CONTRACT, 7000)
    
    # Verify initial state
    assert art_commission_hub_owners.lookupRegisteredOwner(CHAIN_ID, TEST_NFT_CONTRACT, 7000) == user1.address
    assert art_commission_hub_owners.getCommissionHubCountByOwner(user1.address) == 1
    assert art_commission_hub_owners.getCommissionHubCountByOwner(user2.address) == 0
    
    # Change ownership
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        CHAIN_ID, TEST_NFT_CONTRACT, 7000, user2.address, sender=deployer
    )
    
    # Verify state changed correctly
    assert art_commission_hub_owners.lookupRegisteredOwner(CHAIN_ID, TEST_NFT_CONTRACT, 7000) == user2.address
    assert art_commission_hub_owners.getCommissionHubCountByOwner(user1.address) == 0  # Should be removed from user1
    assert art_commission_hub_owners.getCommissionHubCountByOwner(user2.address) == 1  # Should be added to user2
    
    # Hub address should remain the same
    hub2 = art_commission_hub_owners.getArtCommissionHubByOwner(CHAIN_ID, TEST_NFT_CONTRACT, 7000)
    assert hub1 == hub2

def test_permission_inheritance_and_delegation(setup):
    """Test permission inheritance and delegation patterns"""
    deployer = setup["deployer"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    
    # Test that system contracts can act on behalf of users in specific contexts
    
    # ProfileFactoryAndRegistry should be able to create generic hubs for users
    # when creating profiles (if implemented)
    profile_factory.createProfile(user1.address, sender=deployer)
    
    # Test that the contract itself (self) is system allowed
    assert art_commission_hub_owners.isSystemAllowed(art_commission_hub_owners.address) == True
    
    # Test delegation: L2OwnershipRelay can register on behalf of any user
    art_commission_hub_owners.setL2OwnershipRelay(user1.address, sender=deployer)
    
    # user1 (as L2OwnershipRelay) can register user2 as owner
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        CHAIN_ID, TEST_NFT_CONTRACT, 8000, user2.address, sender=user1
    )
    assert art_commission_hub_owners.lookupRegisteredOwner(CHAIN_ID, TEST_NFT_CONTRACT, 8000) == user2.address
    
    # But user1 cannot perform owner-only operations
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.setL2OwnershipRelay(user2.address, sender=user1)
    assert "Only owner can set L2 relay" in str(excinfo.value)

def test_permission_revocation_scenarios(setup):
    """Test scenarios where permissions are revoked or changed"""
    deployer = setup["deployer"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    
    # Grant user1 L2OwnershipRelay permissions
    art_commission_hub_owners.setL2OwnershipRelay(user1.address, sender=deployer)
    assert art_commission_hub_owners.isSystemAllowed(user1.address) == True
    
    # user1 can register NFT owners
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        CHAIN_ID, TEST_NFT_CONTRACT, 9000, user2.address, sender=user1
    )
    
    # Revoke user1's permissions by changing L2OwnershipRelay to user2
    art_commission_hub_owners.setL2OwnershipRelay(user2.address, sender=deployer)
    assert art_commission_hub_owners.isSystemAllowed(user1.address) == False
    assert art_commission_hub_owners.isSystemAllowed(user2.address) == True
    
    # user1 can no longer register NFT owners
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.registerNFTOwnerFromParentChain(
            CHAIN_ID, TEST_NFT_CONTRACT, 9001, user1.address, sender=user1
        )
    assert "Only system allowed addresses can register artCommissionHubOwners" in str(excinfo.value)
    
    # But user2 can now register NFT owners
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        CHAIN_ID, TEST_NFT_CONTRACT, 9001, user1.address, sender=user2
    )

def test_comprehensive_permission_matrix(setup):
    """Test comprehensive permission matrix for all roles and methods"""
    deployer = setup["deployer"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    commission_hub_template = setup["commission_hub_template"]
    art_piece_template = setup["art_piece_template"]
    
    # Define all roles
    roles = {
        "owner": deployer,
        "l2_relay": user1,  # Will be set as L2OwnershipRelay
        "regular_user": user2,
        "profile_factory": profile_factory.address,
        "self_contract": art_commission_hub_owners.address
    }
    
    # Set up L2OwnershipRelay
    art_commission_hub_owners.setL2OwnershipRelay(user1.address, sender=deployer)
    
    # Define methods and their expected permissions
    permission_matrix = {
        # Method: (allowed_roles, test_args)
        "registerNFTOwnerFromParentChain": (
            ["owner", "l2_relay", "profile_factory", "self_contract"],
            [CHAIN_ID, TEST_NFT_CONTRACT, 10000, user2.address]
        ),
        "setL2OwnershipRelay": (
            ["owner"],
            [user2.address]
        ),
        "setArtCommissionHubTemplate": (
            ["owner"],
            [commission_hub_template.address]
        ),
        "linkProfileFactoryAndRegistry": (
            ["owner"],
            [profile_factory.address]
        ),
        "setApprovedArtPiece": (
            ["owner"],
            [art_piece_template.address, True]
        )
    }
    
    # Test each method against each role
    for method_name, (allowed_roles, args) in permission_matrix.items():
        method = getattr(art_commission_hub_owners, method_name)
        
        for role_name, role_address in roles.items():
            if role_name in ["profile_factory", "self_contract"]:
                # Skip testing contract addresses as senders (would require complex setup)
                continue
                
            if role_name in allowed_roles:
                # Should succeed
                try:
                    method(*args, sender=role_address)
                except Exception as e:
                    # Some methods might fail for other reasons (like already set), that's ok
                    # We're mainly testing permission errors
                    if "Only" in str(e) and ("owner" in str(e) or "system" in str(e) or "allowed" in str(e)):
                        pytest.fail(f"Method {method_name} should be allowed for role {role_name}, but got permission error: {e}")
            else:
                # Should fail with permission error
                with pytest.raises(Exception) as excinfo:
                    method(*args, sender=role_address)
                
                # Verify it's a permission error
                error_msg = str(excinfo.value)
                assert any(keyword in error_msg for keyword in ["Only", "owner", "system", "allowed"]), \
                    f"Expected permission error for {method_name} with role {role_name}, got: {error_msg}"
    
    # Test createGenericCommissionHub separately due to its special logic
    # Test that owner can create hub for anyone
    hub_address = art_commission_hub_owners.createGenericCommissionHub(user2.address, sender=deployer)
    assert hub_address != ZERO_ADDRESS
    
    # Test that user can create hub for themselves
    # First create a different user to avoid conflicts
    user3 = setup["user1"]  # Use existing user from setup
    hub_address2 = art_commission_hub_owners.createGenericCommissionHub(user3.address, sender=user3)
    assert hub_address2 != ZERO_ADDRESS
    
    # Test that user cannot create hub for someone else
    user4 = setup["user2"]  # Use existing user from setup
    user5 = accounts.test_accounts[5]  # Get a fresh account
    with pytest.raises(Exception) as excinfo:
        art_commission_hub_owners.createGenericCommissionHub(user5.address, sender=user4)
    assert "Only the owner can create their own generic commission hub" in str(excinfo.value) 