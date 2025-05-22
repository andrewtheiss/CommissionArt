import pytest
from ape import accounts, project
from eth_utils import to_checksum_address

# Define constant for zero address
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

# Define global test data constants
TEST_TOKEN_URI_DATA = b"data:application/json;base64,eyJuYW1lIjoiVGVzdCBBcnR3b3JrIiwiZGVzY3JpcHRpb24iOiJUaGlzIGlzIGEgdGVzdCBkZXNjcmlwdGlvbiBmb3IgdGhlIGFydHdvcmsiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTndJREFBQUFCbEJNVkVYLy8vL24vNGJsQUFBQUJYUlNUbk1BUUtKZVVtUktBQUFBQWtsRVFWUUkxMkJnQUFNRE1BQUJoVUFCQUVtQ0FVQUFBQUJKUlU1RXJrSmdnZz09In0="
TEST_TITLE = "Test Artwork"
TEST_DESCRIPTION = "This is a test description for the artwork"
TEST_TOKEN_URI_DATA_FORMAT = "avif"
TEST_AI_GENERATED = False

@pytest.fixture(scope="function")
def setup():
    """Setup function that deploys and initializes all contracts needed for testing"""
    deployer = accounts.test_accounts[0]
    user = accounts.test_accounts[1]
    artist = accounts.test_accounts[2]
    owner = accounts.test_accounts[3]
    
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
    
    # Deploy a commission hub instance
    commission_hub = project.ArtCommissionHub.deploy(sender=deployer)
    
    # Initialize the hub
    commission_hub.initializeParentCommissionHubOwnerContract(art_commission_hub_owners.address, sender=deployer)
    
    # Verify initialization
    assert commission_hub.artCommissionHubOwners() == art_commission_hub_owners.address
    
    # Create profiles for test accounts
    profile_factory.createProfile(user.address, sender=deployer)
    profile_factory.createProfile(owner.address, sender=deployer)
    profile_factory.createProfile(artist.address, sender=deployer)
    
    # Verify profiles were created
    assert profile_factory.hasProfile(user.address) == True
    assert profile_factory.hasProfile(owner.address) == True
    assert profile_factory.hasProfile(artist.address) == True
    
    # Get profile addresses
    user_profile_address = profile_factory.getProfile(user.address)
    owner_profile_address = profile_factory.getProfile(owner.address)
    artist_profile_address = profile_factory.getProfile(artist.address)
    
    # Create references to profiles
    user_profile = project.Profile.at(user_profile_address)
    owner_profile = project.Profile.at(owner_profile_address)
    artist_profile = project.Profile.at(artist_profile_address)
    
    # Deploy and initialize an art piece
    art_piece = project.ArtPiece.deploy(sender=deployer)
    
    art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        owner.address,
        artist.address,
        ZERO_ADDRESS,  # No commission hub needed for this test
        TEST_AI_GENERATED,
        owner.address,  # original uploader
        profile_factory.address,  # Profile factory address
        sender=deployer
    )
    
    # Verify art piece initialization
    assert art_piece.getOwner() == owner.address
    assert art_piece.artist() == artist.address
    assert art_piece.title() == TEST_TITLE
    assert art_piece.description() == TEST_DESCRIPTION
    assert art_piece.aiGenerated() == TEST_AI_GENERATED
    
    # Return all deployed contracts and references for use in tests
    return {
        "deployer": deployer,
        "user": user,
        "artist": artist,
        "owner": owner,
        "profile_template": profile_template,
        "profile_social_template": profile_social_template,
        "commission_hub_template": commission_hub_template,
        "art_piece_template": art_piece_template,
        "profile_factory": profile_factory,
        "art_commission_hub_owners": art_commission_hub_owners,
        "commission_hub": commission_hub,
        "user_profile": user_profile,
        "owner_profile": owner_profile,
        "artist_profile": artist_profile,
        "art_piece": art_piece
    }

# Individual standalone tests - each test is fully independent
def test_00_deploy_basic_contracts(setup):
    """Test deploying basic contracts"""
    # Verify all template contracts are deployed
    assert setup["profile_template"].address != ZERO_ADDRESS
    assert setup["profile_social_template"].address != ZERO_ADDRESS
    assert setup["commission_hub_template"].address != ZERO_ADDRESS
    assert setup["art_piece_template"].address != ZERO_ADDRESS
    
    # Verify factory registry
    profile_factory = setup["profile_factory"]
    assert profile_factory.address != ZERO_ADDRESS
    assert profile_factory.profileTemplate() == setup["profile_template"].address
    assert profile_factory.profileSocialTemplate() == setup["profile_social_template"].address
    assert profile_factory.commissionHubTemplate() == setup["commission_hub_template"].address
    
    # Verify ArtCommissionHubOwners
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    assert art_commission_hub_owners.address != ZERO_ADDRESS
    assert art_commission_hub_owners.l2OwnershipRelay() == setup["deployer"].address
    
    # Verify linking between factory and hub owners
    assert profile_factory.artCommissionHubOwners() == art_commission_hub_owners.address
    assert art_commission_hub_owners.profileFactoryAndRegistry() == profile_factory.address
    
    # Verify profiles were created
    assert profile_factory.hasProfile(setup["user"].address) == True
    assert profile_factory.hasProfile(setup["owner"].address) == True
    assert profile_factory.hasProfile(setup["artist"].address) == True
    
    # Verify art piece initialization
    art_piece = setup["art_piece"]
    assert art_piece.getOwner() == setup["owner"].address
    assert art_piece.artist() == setup["artist"].address
    assert art_piece.title() == TEST_TITLE
    assert art_piece.description() == TEST_DESCRIPTION


def test_01_deploy_commission_hub_template(setup):
    """Test that ArtCommissionHub template can be deployed"""
    deployer = setup["deployer"]
    commission_hub_template = setup["commission_hub_template"]
    
    assert commission_hub_template.address != ZERO_ADDRESS


def test_02_deploy_art_commission_hub_owners():
    """Test that ArtCommissionHubOwners can be deployed"""
    deployer = accounts.test_accounts[0]
    
    # Deploy templates first
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy ArtCommissionHubOwners
    art_commission_hub_owners = project.ArtCommissionHubOwners.deploy(
        deployer.address,  # L2OwnershipRelay
        commission_hub_template.address,
        art_piece_template.address,
        sender=deployer
    )
    
    assert art_commission_hub_owners.address != ZERO_ADDRESS
    assert art_commission_hub_owners.l2OwnershipRelay() == deployer.address


def test_03_create_generic_commission_hub():
    """Test creating a generic commission hub through ArtCommissionHubOwners"""
    deployer = accounts.test_accounts[0]
    user = accounts.test_accounts[1]
    
    # Deploy templates first
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy ArtCommissionHubOwners
    art_commission_hub_owners = project.ArtCommissionHubOwners.deploy(
        deployer.address,  # L2OwnershipRelay
        commission_hub_template.address,
        art_piece_template.address,
        sender=deployer
    )
    
    # Create a generic commission hub for the user
    art_commission_hub_owners.createGenericCommissionHub(
        user.address,  # Owner
        sender=deployer
    )
    
    # Verify hub creation
    hub_count = art_commission_hub_owners.getCommissionHubCountByOwner(user.address)
    assert hub_count == 1, "User should have one commission hub"
    
    # Get the hub address
    hub_address = art_commission_hub_owners.getCommissionHubsByOwner(user.address, 0, 1)[0]
    assert hub_address != ZERO_ADDRESS, "Hub address should not be zero"
    
    # Create a reference to the hub
    commission_hub = project.ArtCommissionHub.at(hub_address)
    
    # Verify hub initialization
    assert commission_hub.isInitialized() is True, "Hub should be initialized"
    assert commission_hub.owner() == user.address, "Hub owner should be the user"


def test_04_register_nft_owner_and_create_hub():
    """Test registering an NFT owner and creating a hub for it"""
    deployer = accounts.test_accounts[0]
    
    # Deploy templates first
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy ArtCommissionHubOwners
    art_commission_hub_owners = project.ArtCommissionHubOwners.deploy(
        deployer.address,  # L2OwnershipRelay
        commission_hub_template.address,
        art_piece_template.address,
        sender=deployer
    )
    
    # Set test parameters
    chain_id = 1
    nft_contract = "0x1234567890123456789012345678901234567890"
    token_id = 123
    owner = accounts.test_accounts[3]
    
    # Register NFT owner
    art_commission_hub_owners.registerNFTOwnerFromParentChain(
        chain_id, 
        nft_contract, 
        token_id, 
        owner.address,
        sender=deployer  # pretending to be L2OwnershipRelay
    )
    
    # Get the hub address
    hub_address = art_commission_hub_owners.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
    assert hub_address != ZERO_ADDRESS, "Hub address should not be zero"
    
    # Create a reference to the hub
    commission_hub = project.ArtCommissionHub.at(hub_address)
    
    # Verify hub initialization
    assert commission_hub.isInitialized() is True, "Hub should be initialized"
    assert commission_hub.owner() == owner.address, "Hub owner should be the NFT owner"


def test_05_submit_commission():
    """Test submitting a commission to a hub"""
    deployer = accounts.test_accounts[0]
    user = accounts.test_accounts[1]
    artist = accounts.test_accounts[2]
    
    # Deploy templates first
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy ArtCommissionHubOwners
    art_commission_hub_owners = project.ArtCommissionHubOwners.deploy(
        deployer.address,  # L2OwnershipRelay
        commission_hub_template.address,
        art_piece_template.address,
        sender=deployer
    )
    
    # Create a generic commission hub for the user
    art_commission_hub_owners.createGenericCommissionHub(
        user.address,  # Owner
        sender=deployer
    )
    
    # Get the hub address
    hub_address = art_commission_hub_owners.getCommissionHubsByOwner(user.address, 0, 1)[0]
    commission_hub = project.ArtCommissionHub.at(hub_address)
    
    # Deploy an art piece for testing
    art_piece = project.ArtPiece.deploy(sender=deployer)
    
    # Approve the ArtPiece template's code hash
    commission_hub.approveArtPieceCodeHash(art_piece.address, True, sender=user)
    
    # Submit a commission
    commission_hub.submitCommission(art_piece.address, sender=artist)
    
    # Verify submission
    assert commission_hub.countUnverifiedCommissions() == 1, "Should have 1 unverified commission"
    assert commission_hub.getUnverifiedCount(artist.address) == 1, "Artist should have 1 unverified commission"
    
    unverified_art_pieces = commission_hub.getUnverifiedArtPieces(0, 10)
    assert len(unverified_art_pieces) == 1, "Should have 1 art piece in unverified list"
    assert unverified_art_pieces[0] == art_piece.address, "Art piece should be in unverified list"


def test_06_verify_commission():
    """Test verifying a commission"""
    deployer = accounts.test_accounts[0]
    user = accounts.test_accounts[1]
    artist = accounts.test_accounts[2]
    
    # Deploy templates first
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy ArtCommissionHubOwners
    art_commission_hub_owners = project.ArtCommissionHubOwners.deploy(
        deployer.address,  # L2OwnershipRelay
        commission_hub_template.address,
        art_piece_template.address,
        sender=deployer
    )
    
    # Create a generic commission hub for the user
    art_commission_hub_owners.createGenericCommissionHub(
        user.address,  # Owner
        sender=deployer
    )
    
    # Get the hub address
    hub_address = art_commission_hub_owners.getCommissionHubsByOwner(user.address, 0, 1)[0]
    commission_hub = project.ArtCommissionHub.at(hub_address)
    
    # Deploy an art piece for testing
    art_piece = project.ArtPiece.deploy(sender=deployer)
    
    # Approve the ArtPiece template's code hash
    commission_hub.approveArtPieceCodeHash(art_piece.address, True, sender=user)
    
    # Submit a commission
    commission_hub.submitCommission(art_piece.address, sender=artist)
    
    # Verify the commission
    commission_hub.verifyCommission(art_piece.address, artist.address, sender=user)
    
    # Check state after verification
    assert commission_hub.countUnverifiedCommissions() == 0, "Should have 0 unverified commissions"
    assert commission_hub.countVerifiedCommissions() == 1, "Should have 1 verified commission"
    assert commission_hub.getUnverifiedCount(artist.address) == 0, "Artist should have 0 unverified commissions"
    
    # Check unverified list - should be empty
    unverified_art_pieces = commission_hub.getUnverifiedArtPieces(0, 10)
    assert len(unverified_art_pieces) == 0, "Unverified list should be empty"
    
    # Check verified list - should contain the art piece
    verified_art_pieces = commission_hub.getVerifiedArtPieces(0, 10)
    assert len(verified_art_pieces) == 1, "Should have 1 art piece in verified list"
    assert verified_art_pieces[0] == art_piece.address, "Art piece should be in verified list"
    
    # Check latest verified art
    latest_verified = commission_hub.getLatestVerifiedArt(1)
    assert len(latest_verified) == 1, "Should have 1 art piece in latest verified"
    assert latest_verified[0] == art_piece.address, "Art piece should be in latest verified"


def test_07_verify_multiple_commissions():
    """Test verifying multiple commissions from the same submitter"""
    deployer = accounts.test_accounts[0]
    user = accounts.test_accounts[1]
    artist = accounts.test_accounts[2]
    
    # Deploy templates first
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy ArtCommissionHubOwners
    art_commission_hub_owners = project.ArtCommissionHubOwners.deploy(
        deployer.address,  # L2OwnershipRelay
        commission_hub_template.address,
        art_piece_template.address,
        sender=deployer
    )
    
    # Create a generic commission hub for the user
    art_commission_hub_owners.createGenericCommissionHub(
        user.address,  # Owner
        sender=deployer
    )
    
    # Get the hub address
    hub_address = art_commission_hub_owners.getCommissionHubsByOwner(user.address, 0, 1)[0]
    commission_hub = project.ArtCommissionHub.at(hub_address)
    
    # Deploy art pieces for testing
    art_piece_1 = project.ArtPiece.deploy(sender=deployer)
    art_piece_2 = project.ArtPiece.deploy(sender=deployer)
    
    # Approve the ArtPiece template's code hash
    commission_hub.approveArtPieceCodeHash(art_piece_1.address, True, sender=user)
    
    # Submit two unverified commissions
    commission_hub.submitCommission(art_piece_1.address, sender=artist)
    commission_hub.submitCommission(art_piece_2.address, sender=artist)
    
    # Check initial state
    assert commission_hub.countUnverifiedCommissions() == 2, "Should have 2 unverified commissions"
    assert commission_hub.getUnverifiedCount(artist.address) == 2, "Artist should have 2 unverified commissions"
    
    # Verify the first commission
    commission_hub.verifyCommission(art_piece_1.address, artist.address, sender=user)
    
    # Check state after first verification
    assert commission_hub.countUnverifiedCommissions() == 1, "Should have 1 unverified commission"
    assert commission_hub.countVerifiedCommissions() == 1, "Should have 1 verified commission"
    assert commission_hub.getUnverifiedCount(artist.address) == 1, "Artist should have 1 unverified commission"
    
    # Check unverified list - should contain second art piece only
    unverified_art_pieces = commission_hub.getUnverifiedArtPieces(0, 10)
    assert len(unverified_art_pieces) == 1, "Should have 1 art piece in unverified list"
    assert unverified_art_pieces[0] == art_piece_2.address, "Art piece 2 should be in unverified list"
    
    # Verify the second commission
    commission_hub.verifyCommission(art_piece_2.address, artist.address, sender=user)
    
    # Check state after second verification
    assert commission_hub.countUnverifiedCommissions() == 0, "Should have 0 unverified commissions"
    assert commission_hub.countVerifiedCommissions() == 2, "Should have 2 verified commissions"
    assert commission_hub.getUnverifiedCount(artist.address) == 0, "Artist should have 0 unverified commissions"


def test_08_unverify_commission():
    """Test unverifying a commission"""
    deployer = accounts.test_accounts[0]
    user = accounts.test_accounts[1]
    artist = accounts.test_accounts[2]
    
    # Deploy templates first
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy ArtCommissionHubOwners
    art_commission_hub_owners = project.ArtCommissionHubOwners.deploy(
        deployer.address,  # L2OwnershipRelay
        commission_hub_template.address,
        art_piece_template.address,
        sender=deployer
    )
    
    # Create a generic commission hub for the user
    art_commission_hub_owners.createGenericCommissionHub(
        user.address,  # Owner
        sender=deployer
    )
    
    # Get the hub address
    hub_address = art_commission_hub_owners.getCommissionHubsByOwner(user.address, 0, 1)[0]
    commission_hub = project.ArtCommissionHub.at(hub_address)
    
    # Deploy an art piece for testing
    art_piece = project.ArtPiece.deploy(sender=deployer)
    
    # Approve the ArtPiece template's code hash
    commission_hub.approveArtPieceCodeHash(art_piece.address, True, sender=user)
    
    # Submit a commission
    commission_hub.submitCommission(art_piece.address, sender=artist)
    
    # Verify the commission
    commission_hub.verifyCommission(art_piece.address, artist.address, sender=user)
    
    # Check initial state
    assert commission_hub.countUnverifiedCommissions() == 0, "Should have 0 unverified commissions"
    assert commission_hub.countVerifiedCommissions() == 1, "Should have 1 verified commission"
    
    # Unverify the commission
    commission_hub.unverifyCommission(art_piece.address, artist.address, sender=user)
    
    # Check state after unverification
    assert commission_hub.countUnverifiedCommissions() == 1, "Should have 1 unverified commission"
    assert commission_hub.countVerifiedCommissions() == 0, "Should have 0 verified commissions"
    assert commission_hub.getUnverifiedCount(artist.address) == 1, "Artist should have 1 unverified commission"
    
    # Check unverified list - should contain the art piece
    unverified_art_pieces = commission_hub.getUnverifiedArtPieces(0, 10)
    assert len(unverified_art_pieces) == 1, "Should have 1 art piece in unverified list"
    assert unverified_art_pieces[0] == art_piece.address, "Art piece should be in unverified list"
    
    # Check verified list - should be empty
    verified_art_pieces = commission_hub.getVerifiedArtPieces(0, 10)
    assert len(verified_art_pieces) == 0, "Verified list should be empty"


def test_09_unverify_commission_permissions():
    """Test that only the owner can unverify commissions"""
    deployer = accounts.test_accounts[0]
    user = accounts.test_accounts[1]
    artist = accounts.test_accounts[2]
    non_owner = accounts.test_accounts[3]
    
    # Deploy templates first
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy ArtCommissionHubOwners
    art_commission_hub_owners = project.ArtCommissionHubOwners.deploy(
        deployer.address,  # L2OwnershipRelay
        commission_hub_template.address,
        art_piece_template.address,
        sender=deployer
    )
    
    # Create a generic commission hub for the user
    art_commission_hub_owners.createGenericCommissionHub(
        user.address,  # Owner
        sender=deployer
    )
    
    # Get the hub address
    hub_address = art_commission_hub_owners.getCommissionHubsByOwner(user.address, 0, 1)[0]
    commission_hub = project.ArtCommissionHub.at(hub_address)
    
    # Deploy an art piece for testing
    art_piece = project.ArtPiece.deploy(sender=deployer)
    
    # Approve the ArtPiece template's code hash
    commission_hub.approveArtPieceCodeHash(art_piece.address, True, sender=user)
    
    # Submit and verify a commission
    commission_hub.submitCommission(art_piece.address, sender=artist)
    commission_hub.verifyCommission(art_piece.address, artist.address, sender=user)
    
    # Non-owner tries to unverify - should fail
    with pytest.raises(Exception) as excinfo:
        commission_hub.unverifyCommission(art_piece.address, artist.address, sender=non_owner)
    
    # Check error message
    error_message = str(excinfo.value).lower()
    assert "not authorized" in error_message or "auth" in error_message, "Error should mention authorization"
    
    # State should remain unchanged
    assert commission_hub.countVerifiedCommissions() == 1, "Should still have 1 verified commission"
    assert commission_hub.countUnverifiedCommissions() == 0, "Should still have 0 unverified commissions"


def test_10_verify_unverify_cycle():
    """Test a full cycle of verify -> unverify -> verify again"""
    deployer = accounts.test_accounts[0]
    user = accounts.test_accounts[1]
    artist = accounts.test_accounts[2]
    
    # Deploy templates first
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy ArtCommissionHubOwners
    art_commission_hub_owners = project.ArtCommissionHubOwners.deploy(
        deployer.address,  # L2OwnershipRelay
        commission_hub_template.address,
        art_piece_template.address,
        sender=deployer
    )
    
    # Create a generic commission hub for the user
    art_commission_hub_owners.createGenericCommissionHub(
        user.address,  # Owner
        sender=deployer
    )
    
    # Get the hub address
    hub_address = art_commission_hub_owners.getCommissionHubsByOwner(user.address, 0, 1)[0]
    commission_hub = project.ArtCommissionHub.at(hub_address)
    
    # Deploy an art piece for testing
    art_piece = project.ArtPiece.deploy(sender=deployer)
    
    # Approve the ArtPiece template's code hash
    commission_hub.approveArtPieceCodeHash(art_piece.address, True, sender=user)
    
    # Submit as unverified
    commission_hub.submitCommission(art_piece.address, sender=artist)
    
    # Initial state
    assert commission_hub.countUnverifiedCommissions() == 1, "Should have 1 unverified commission"
    assert commission_hub.countVerifiedCommissions() == 0, "Should have 0 verified commissions"
    
    # Step 1: Verify the commission
    commission_hub.verifyCommission(art_piece.address, artist.address, sender=user)
    
    # Check state after verification
    assert commission_hub.countUnverifiedCommissions() == 0, "Should have 0 unverified commissions"
    assert commission_hub.countVerifiedCommissions() == 1, "Should have 1 verified commission"
    
    # Step 2: Unverify the commission
    commission_hub.unverifyCommission(art_piece.address, artist.address, sender=user)
    
    # Check state after unverification
    assert commission_hub.countUnverifiedCommissions() == 1, "Should have 1 unverified commission"
    assert commission_hub.countVerifiedCommissions() == 0, "Should have 0 verified commissions"
    
    # Step 3: Verify the commission again
    commission_hub.verifyCommission(art_piece.address, artist.address, sender=user)
    
    # Check final state
    assert commission_hub.countUnverifiedCommissions() == 0, "Should have 0 unverified commissions"
    assert commission_hub.countVerifiedCommissions() == 1, "Should have 1 verified commission"
    
    # Get the art piece from verified list
    verified_art_pieces = commission_hub.getVerifiedArtPieces(0, 10)
    assert len(verified_art_pieces) == 1, "Should have 1 art piece in verified list"
    assert verified_art_pieces[0] == art_piece.address, "Art piece should be in verified list" 