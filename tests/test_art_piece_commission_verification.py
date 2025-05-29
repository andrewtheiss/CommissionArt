import pytest
from ape import accounts, project

# Test data
TEST_TOKEN_URI_DATA = b"data:application/json;base64,eyJuYW1lIjoiVGVzdCBBcnR3b3JrIiwiZGVzY3JpcHRpb24iOiJUaGlzIGlzIGEgdGVzdCBkZXNjcmlwdGlvbiBmb3IgdGhlIGFydHdvcmsiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJCTndJREFBQUFCbEJNVkVYLy8vL24vNGJsQUFBQUJYUlNUbk1BUUtKZVVtUktBQUFBQWtsRVFWUUkxMkJnQUFNRE1BQUJoVUFCQUVtQ0FVQUFBQUJKUlU1RXJrSmdnZz09In0="
TEST_TITLE = "Test Artwork"
TEST_DESCRIPTION = "This is a test description for the artwork"
TEST_TOKEN_URI_DATA_FORMAT = "avif"
TEST_AI_GENERATED = False
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

@pytest.fixture
def setup():
    """Setup function that deploys and initializes all contracts needed for testing"""
    deployer = accounts.test_accounts[0]
    artist = accounts.test_accounts[1]
    commissioner = accounts.test_accounts[2]
    hub_owner = accounts.test_accounts[3]
    
    # Deploy all templates
    profile_template = project.Profile.deploy(sender=deployer)
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)

    # Deploy ArtEdition1155 template
    art_edition_1155_template = project.ArtEdition1155.deploy(sender=deployer)
    
    # Deploy ArtSales1155 template
    art_sales_1155_template = project.ArtSales1155.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy factory registry
    profile_factory = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address, profile_social_template.address, commission_hub_template.address, art_edition_1155_template.address, art_sales_1155_template.address,
        sender=deployer
    )
    
    # Deploy ArtCommissionHubOwners
    art_commission_hub_owners = project.ArtCommissionHubOwners.deploy(
        deployer.address,  # L2OwnershipRelay
        commission_hub_template.address,
        art_piece_template.address,
        sender=deployer
    )
    
    # Link factory and hub owners
    profile_factory.linkArtCommissionHubOwnersContract(art_commission_hub_owners.address, sender=deployer)
    art_commission_hub_owners.linkProfileFactoryAndRegistry(profile_factory.address, sender=deployer)
    
    # Create profiles for test accounts
    profile_factory.createProfile(artist.address, sender=deployer)
    profile_factory.createProfile(commissioner.address, sender=deployer)
    profile_factory.createProfile(hub_owner.address, sender=deployer)
    profile_factory.createProfile(deployer.address, sender=deployer)
    
    # Create a commission hub for testing
    art_commission_hub_owners.createGenericCommissionHub(hub_owner.address, sender=deployer)
    
    # Get the hub address
    hubs_list = art_commission_hub_owners.getCommissionHubsByOwnerWithOffset(hub_owner.address, 0, 1, False)
    hub_address = hubs_list[0]
    commission_hub = project.ArtCommissionHub.at(hub_address)
    
    return {
        "deployer": deployer,
        "artist": artist,
        "commissioner": commissioner,
        "hub_owner": hub_owner,
        "profile_factory": profile_factory,
        "art_commission_hub_owners": art_commission_hub_owners,
        "commission_hub": commission_hub,
        "art_edition_1155_template": art_edition_1155_template,
        "art_sales_1155_template": art_sales_1155_template,
        "art_piece_template": art_piece_template
    }

def test_is_commission_determination(setup):
    """Test that isUnverifiedCommission is correctly determined based on commissioner_input != artist_input"""
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    profile_factory = setup["profile_factory"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    
    # Create art piece with different commissioner and artist
    commission_art_piece = project.ArtPiece.deploy(sender=deployer)
    commission_art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        "Test Commission",
        TEST_DESCRIPTION,
        commissioner.address,  # commissioner_input
        artist.address,  # artist_input
        ZERO_ADDRESS,  # commission_hub
        TEST_AI_GENERATED,
        artist.address,  # original_uploader
        profile_factory.address,  # profile_factory_address
        sender=deployer
    )
    
    # Approve the art piece
    art_commission_hub_owners.setApprovedArtPiece(commission_art_piece.address, True, sender=deployer)
    
    # Should be an unverified commission
    assert commission_art_piece.isUnverifiedCommission(), "Should be an unverified commission when commissioner != artist"
    
    # Create art piece with same commissioner and artist
    non_commission_art_piece = project.ArtPiece.deploy(sender=deployer)
    non_commission_art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        "Test Non-Commission",
        TEST_DESCRIPTION,
        artist.address,  # commissioner_input (same as artist)
        artist.address,  # artist_input
        ZERO_ADDRESS,  # commission_hub
        TEST_AI_GENERATED,
        artist.address,  # original_uploader
        profile_factory.address,  # profile_factory_address
        sender=deployer
    )
    
    # Approve the art piece
    art_commission_hub_owners.setApprovedArtPiece(non_commission_art_piece.address, True, sender=deployer)
    
    # Should not be an unverified commission
    assert not non_commission_art_piece.isUnverifiedCommission(), "Should not be an unverified commission when commissioner == artist"

def test_verification_status_initialization(setup):
    """Test that verification status is correctly initialized based on commissioner vs artist"""
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    profile_factory = setup["profile_factory"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    
    # Create art piece with different commissioner and artist
    commission_piece = project.ArtPiece.deploy(sender=deployer)
    commission_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        "Commission Piece",
        TEST_DESCRIPTION,
        commissioner.address,  # commissioner_input
        artist.address,  # artist_input
        ZERO_ADDRESS,  # commission_hub
        TEST_AI_GENERATED,
        artist.address,  # original_uploader
        profile_factory.address,  # profile_factory_address
        sender=deployer
    )
    
    # Approve the art piece
    art_commission_hub_owners.setApprovedArtPiece(commission_piece.address, True, sender=deployer)
    
    # Neither side should be verified initially for commission pieces
    assert not commission_piece.commissionerVerified(), "Commissioner side should not be verified initially"
    assert not commission_piece.artistVerified(), "Artist side should not be verified initially"
    assert not commission_piece.isFullyVerifiedCommission(), "Commission should not be fully verified yet"
    
    # Create art piece with same commissioner and artist (non-commission)
    non_commission_piece = project.ArtPiece.deploy(sender=deployer)
    non_commission_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        "Non-Commission Piece",
        TEST_DESCRIPTION,
        artist.address,  # commissioner_input (same as artist)
        artist.address,  # artist_input
        ZERO_ADDRESS,  # commission_hub
        TEST_AI_GENERATED,
        artist.address,  # original_uploader
        profile_factory.address,  # profile_factory_address
        sender=deployer
    )
    
    # Approve the art piece
    art_commission_hub_owners.setApprovedArtPiece(non_commission_piece.address, True, sender=deployer)
    
    # Both sides should be verified (non-commission piece)
    assert non_commission_piece.commissionerVerified(), "Commissioner side should be verified for non-commission piece"
    assert non_commission_piece.artistVerified(), "Artist side should be verified for non-commission piece"
    assert non_commission_piece.isFullyVerifiedCommission(), "Non-commission piece should be fully verified"

def test_commissioner_stored_separately(setup):
    """Test that the commissioner is stored separately from the owner"""
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    profile_factory = setup["profile_factory"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    
    # Create art piece
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        "Test Commission",
        TEST_DESCRIPTION,
        commissioner.address,  # commissioner_input
        artist.address,  # artist_input
        ZERO_ADDRESS,  # commission_hub
        TEST_AI_GENERATED,
        artist.address,  # original_uploader
        profile_factory.address,  # profile_factory_address
        sender=deployer
    )
    
    # Approve the art piece
    art_commission_hub_owners.setApprovedArtPiece(art_piece.address, True, sender=deployer)
    
    # Commissioner should be stored correctly
    assert art_piece.getCommissioner() == commissioner.address, "Commissioner should be stored correctly"
    
    # Owner should be original uploader initially (before verification)
    assert art_piece.getOwner() == artist.address, "Owner should be original uploader initially"

def test_verification_flow(setup):
    """Test the full verification flow for a commission piece"""
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    profile_factory = setup["profile_factory"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    
    # Create art piece with artist as uploader (non-commission)
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        "Verification Flow Test",
        TEST_DESCRIPTION,
        artist.address,  # commissioner_input (same as artist)
        artist.address,  # artist_input
        ZERO_ADDRESS,  # commission_hub
        TEST_AI_GENERATED,
        artist.address,  # original_uploader
        profile_factory.address,  # profile_factory_address
        sender=deployer
    )
    
    # Approve the art piece
    art_commission_hub_owners.setApprovedArtPiece(art_piece.address, True, sender=deployer)
    
    # Initial state for non-commission piece
    assert not art_piece.isUnverifiedCommission(), "Should not be an unverified commission"
    assert art_piece.isFullyVerifiedCommission(), "Non-commission piece should be verified automatically"
    
    # Create a commission piece with artist as uploader
    commission_piece = project.ArtPiece.deploy(sender=deployer)
    commission_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        "Commission Verification Flow",
        TEST_DESCRIPTION,
        commissioner.address,  # commissioner_input (different from artist)
        artist.address,  # artist_input
        ZERO_ADDRESS,  # commission_hub
        TEST_AI_GENERATED,
        artist.address,  # original_uploader
        profile_factory.address,  # profile_factory_address
        sender=deployer
    )
    
    # Approve the art piece
    art_commission_hub_owners.setApprovedArtPiece(commission_piece.address, True, sender=deployer)
    
    # Initial state for commission piece
    assert commission_piece.isUnverifiedCommission(), "Should be an unverified commission"
    assert not commission_piece.commissionerVerified(), "Commissioner side should not be verified initially"
    assert not commission_piece.artistVerified(), "Artist side should not be verified initially"
    assert not commission_piece.isFullyVerifiedCommission(), "Commission should not be fully verified yet"

def test_hub_attached_commission_verification(setup):
    """Test verification flow for commission attached to a hub"""
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    hub_owner = setup["hub_owner"]
    profile_factory = setup["profile_factory"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    commission_hub = setup["commission_hub"]
    
    # Deploy ArtPiece attached to hub
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        "Hub Commission",
        TEST_DESCRIPTION,
        commissioner.address,
        artist.address,
        commission_hub.address,
        TEST_AI_GENERATED,
        artist.address,  # original_uploader
        profile_factory.address,  # profile_factory_address
        sender=deployer
    )
    
    # Approve the art piece
    art_commission_hub_owners.setApprovedArtPiece(art_piece.address, True, sender=deployer)
    
    assert art_piece.isUnverifiedCommission(), "Should be an unverified commission"
    assert not art_piece.artistVerified(), "Artist side should not be verified yet"
    assert not art_piece.commissionerVerified(), "Commissioner side should not be verified yet"
    assert not art_piece.isFullyVerifiedCommission(), "Commission should not be fully verified yet"
    assert art_piece.getArtCommissionHubAddress() == commission_hub.address, "Should have correct hub address"
    
    # Verify as artist
    art_piece.verifyAsArtist(sender=artist)
    assert art_piece.artistVerified(), "Artist side should now be verified"
    assert not art_piece.isFullyVerifiedCommission(), "Commission should not be fully verified yet"
    
    # Verify as commissioner
    art_piece.verifyAsCommissioner(sender=commissioner)
    assert art_piece.artistVerified(), "Artist side should still be verified"
    assert art_piece.commissionerVerified(), "Commissioner side should now be verified"
    assert art_piece.isFullyVerifiedCommission(), "Commission should now be fully verified"
    
    # Owner should be the hub owner (aliased)
    assert art_piece.getOwner() == commission_hub.owner(), "Owner should be the hub owner (aliased)"

def test_non_commission_always_verified(setup):
    """Test that non-commission pieces are always considered verified"""
    deployer = setup["deployer"]
    artist = setup["artist"]
    profile_factory = setup["profile_factory"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    
    # Create non-commission art piece (artist is both artist and commissioner)
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        "Non-Commission Piece",
        TEST_DESCRIPTION,
        artist.address,  # commissioner_input
        artist.address,  # artist_input
        ZERO_ADDRESS,  # commission_hub
        TEST_AI_GENERATED,
        artist.address,  # original_uploader
        profile_factory.address,  # profile_factory_address
        sender=deployer
    )
    
    # Approve the art piece
    art_commission_hub_owners.setApprovedArtPiece(art_piece.address, True, sender=deployer)
    
    assert not art_piece.isUnverifiedCommission(), "Should not be an unverified commission"
    assert art_piece.isFullyVerifiedCommission(), "Non-commission piece should always be verified"
    assert art_piece.artistVerified(), "Artist side should be verified for non-commission"
    assert art_piece.commissionerVerified(), "Commissioner side should be verified for non-commission"

def test_commission_verification_flow(setup):
    """Test the full verification flow for a commission piece"""
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    profile_factory = setup["profile_factory"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    
    # Create commission piece
    commission_piece = project.ArtPiece.deploy(sender=deployer)
    commission_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        "Commission Piece",
        TEST_DESCRIPTION,
        commissioner.address,  # commissioner_input
        artist.address,  # artist_input
        ZERO_ADDRESS,  # commission_hub
        TEST_AI_GENERATED,
        artist.address,  # original_uploader
        profile_factory.address,  # profile_factory_address
        sender=deployer
    )
    
    # Approve the art piece
    art_commission_hub_owners.setApprovedArtPiece(commission_piece.address, True, sender=deployer)
    
    # Initial state
    assert commission_piece.isUnverifiedCommission(), "Should be an unverified commission"
    assert not commission_piece.isFullyVerifiedCommission(), "Commission should not be verified initially"
    assert not commission_piece.artistVerified(), "Artist should not be verified initially"
    assert not commission_piece.commissionerVerified(), "Commissioner should not be verified initially"

def test_artist_verification(setup):
    """Test that artist can verify their side of a commission"""
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    profile_factory = setup["profile_factory"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    commission_hub = setup["commission_hub"]
    
    # Create commission with hub attached (required for verification)
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        "Artist Verification Test",
        TEST_DESCRIPTION,
        commissioner.address,  # commissioner_input
        artist.address,  # artist_input
        commission_hub.address,  # commission_hub (required for verification)
        TEST_AI_GENERATED,
        artist.address,  # original_uploader
        profile_factory.address,  # profile_factory_address
        sender=deployer
    )
    
    # Approve the art piece
    art_commission_hub_owners.setApprovedArtPiece(art_piece.address, True, sender=deployer)
    
    # Initial state
    assert art_piece.isUnverifiedCommission(), "Should be an unverified commission"
    assert not art_piece.artistVerified(), "Artist should not be verified initially"
    assert not art_piece.commissionerVerified(), "Commissioner should not be verified initially"
    
    # Artist verifies
    art_piece.verifyAsArtist(sender=artist)
    assert art_piece.artistVerified(), "Artist should be verified after calling verifyAsArtist"
    assert not art_piece.commissionerVerified(), "Commissioner should still not be verified"
    assert not art_piece.isFullyVerifiedCommission(), "Should not be fully verified until both parties verify"

# Helper fixture to deploy ArtCommissionHubOwners and ArtCommissionHub template
@pytest.fixture
def registry_and_template():
    deployer = accounts.test_accounts[0]
    l2relay = accounts.test_accounts[9]
    
    # Deploy all templates
    profile_template = project.Profile.deploy(sender=deployer)
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)

    # Deploy ArtEdition1155 template
    art_edition_1155_template = project.ArtEdition1155.deploy(sender=deployer)
    
    # Deploy ArtSales1155 template
    art_sales_1155_template = project.ArtSales1155.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy factory registry
    profile_factory = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address, profile_social_template.address, commission_hub_template.address, art_edition_1155_template.address, art_sales_1155_template.address,
        sender=deployer
    )
    
    # Deploy ArtCommissionHubOwners
    art_collection_ownership_registry = project.ArtCommissionHubOwners.deploy(
        l2relay.address, 
        commission_hub_template.address, 
        art_piece_template.address,
        sender=deployer
    )
    
    # Link factory and hub owners
    profile_factory.linkArtCommissionHubOwnersContract(art_collection_ownership_registry.address, sender=deployer)
    art_collection_ownership_registry.linkProfileFactoryAndRegistry(profile_factory.address, sender=deployer)
    
    return deployer, l2relay, commission_hub_template, art_collection_ownership_registry, profile_factory

# Test creation and initialization of a generic commission hub via ArtCommissionHubOwners
@pytest.mark.usefixtures("registry_and_template")
def test_create_generic_commission_hub(registry_and_template):
    deployer, l2relay, commission_hub_template, art_collection_ownership_registry, profile_factory = registry_and_template
    owner = accounts.test_accounts[1]
    
    # Owner creates a generic commission hub via the registry
    art_collection_ownership_registry.createGenericCommissionHub(owner.address, sender=deployer)
    
    # Get the hub address from the ArtCommissionHubOwners
    hubs = art_collection_ownership_registry.getCommissionHubsByOwnerWithOffset(owner.address, 0, 1, False)
    assert len(hubs) > 0, "No commission hubs found for owner"
    commission_hub_address = hubs[0]  # Get the first hub (should be the one we just created)
    
    commission_hub = project.ArtCommissionHub.at(commission_hub_address)
    
    # Check that the hub is initialized and owned by the correct owner
    assert commission_hub.isInitialized() is True
    assert commission_hub.owner() == owner.address
    assert commission_hub.isGeneric() is True
    assert commission_hub.chainId() == 1

# Test creation and initialization of an NFT-based commission hub via ArtCommissionHubOwners
@pytest.mark.usefixtures("registry_and_template")
def test_create_nft_commission_hub(registry_and_template):
    deployer, l2relay, commission_hub_template, art_collection_ownership_registry, profile_factory = registry_and_template
    nft_owner = accounts.test_accounts[2]
    chain_id = 1
    nft_contract = accounts.test_accounts[3].address  # Use an address as a dummy NFT contract
    token_id = 42
    
    # L2OwnershipRelay registers NFT owner, which creates and initializes the hub
    art_collection_ownership_registry.registerNFTOwnerFromParentChain(chain_id, nft_contract, token_id, nft_owner.address, sender=l2relay)
    commission_hub_address = art_collection_ownership_registry.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
    commission_hub = project.ArtCommissionHub.at(commission_hub_address)
    
    # Check that the hub is initialized and owned by the correct owner
    assert commission_hub.isInitialized() is True
    assert commission_hub.owner() == nft_owner.address
    assert commission_hub.isGeneric() is False
    assert commission_hub.chainId() == chain_id
    assert commission_hub.nftContract() == nft_contract
    assert commission_hub.nftTokenIdOrGenericHubAccount() == token_id

# Test updating the owner of an NFT-based commission hub via ArtCommissionHubOwners
@pytest.mark.usefixtures("registry_and_template")
def test_update_nft_commission_hub_owner(registry_and_template):
    deployer, l2relay, commission_hub_template, art_collection_ownership_registry, profile_factory = registry_and_template
    nft_owner = accounts.test_accounts[2]
    new_owner = accounts.test_accounts[4]
    chain_id = 1
    nft_contract = accounts.test_accounts[3].address
    token_id = 99
    
    # Register initial owner
    art_collection_ownership_registry.registerNFTOwnerFromParentChain(chain_id, nft_contract, token_id, nft_owner.address, sender=l2relay)
    commission_hub_address = art_collection_ownership_registry.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
    commission_hub = project.ArtCommissionHub.at(commission_hub_address)
    assert commission_hub.owner() == nft_owner.address
    
    # Update owner
    art_collection_ownership_registry.registerNFTOwnerFromParentChain(chain_id, nft_contract, token_id, new_owner.address, sender=l2relay)
    assert commission_hub.owner() == new_owner.address

# Test ArtPiece attachment to a hub and correct owner logic after full verification
@pytest.mark.usefixtures("registry_and_template")
def test_art_piece_hub_ownership_flow(registry_and_template):
    deployer, l2relay, commission_hub_template, art_collection_ownership_registry, profile_factory = registry_and_template
    artist = accounts.test_accounts[5]
    commissioner = accounts.test_accounts[6]
    chain_id = 1
    nft_contract = accounts.test_accounts[7].address
    token_id = 123
    
    # Create profiles for test accounts
    profile_factory.createProfile(artist.address, sender=deployer)
    profile_factory.createProfile(commissioner.address, sender=deployer)
    
    # Register NFT owner and get hub
    art_collection_ownership_registry.registerNFTOwnerFromParentChain(chain_id, nft_contract, token_id, commissioner.address, sender=l2relay)
    commission_hub_address = art_collection_ownership_registry.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
    commission_hub = project.ArtCommissionHub.at(commission_hub_address)
    
    # Deploy ArtPiece
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        "Commissioned Art",
        TEST_DESCRIPTION,
        commissioner.address,  # commissioner_input
        artist.address,        # artist_input
        commission_hub_address,
        TEST_AI_GENERATED,
        artist.address,  # original_uploader
        profile_factory.address,  # profile_factory_address
        sender=deployer
    )
    
    # Approve the art piece
    art_collection_ownership_registry.setApprovedArtPiece(art_piece.address, True, sender=deployer)
    
    # Initially, neither party is verified
    assert art_piece.commissionerVerified() is False
    assert art_piece.artistVerified() is False
    assert art_piece.isFullyVerifiedCommission() is False
    
    # Artist verifies
    art_piece.verifyAsArtist(sender=artist)
    assert art_piece.artistVerified() is True
    assert art_piece.commissionerVerified() is False
    assert art_piece.isFullyVerifiedCommission() is False
    
    # Commissioner verifies
    art_piece.verifyAsCommissioner(sender=commissioner)
    assert art_piece.artistVerified() is True
    assert art_piece.commissionerVerified() is True
    assert art_piece.isFullyVerifiedCommission() is True
    
    # Now fully verified, owner should be the hub owner (commissioner)
    assert art_piece.getOwner() == commissioner.address
    
    # Simulate NFT transfer: update hub owner via registry
    new_owner = accounts.test_accounts[8]
    profile_factory.createProfile(new_owner.address, sender=deployer)
    art_collection_ownership_registry.registerNFTOwnerFromParentChain(chain_id, nft_contract, token_id, new_owner.address, sender=l2relay)
    
    # ArtPiece should now report new owner
    assert art_piece.getOwner() == new_owner.address

# Test that only ArtCommissionHubOwners can initialize a hub (negative test)
def test_only_art_collection_ownership_registry_can_initialize(registry_and_template):
    deployer, l2relay, commission_hub_template, art_collection_ownership_registry, profile_factory = registry_and_template
    attacker = accounts.test_accounts[8]
    commission_hub = project.ArtCommissionHub.deploy(sender=deployer)
    
    # First set the parent contract (this is allowed)
    commission_hub.initializeParentCommissionHubOwnerContract(art_collection_ownership_registry.address, sender=deployer)
    
    # Now try to initialize the hub directly as attacker - should fail
    with pytest.raises(Exception) as excinfo:
        commission_hub.initializeForArtCommissionHub(1, attacker.address, 1, sender=attacker)
    
    error_msg = str(excinfo.value).lower()
    assert "not allowed" in error_msg or "system" in error_msg or "auth" in error_msg, f"Expected authorization error, got: {excinfo.value}" 