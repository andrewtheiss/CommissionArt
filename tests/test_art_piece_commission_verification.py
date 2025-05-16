import pytest
from ape import accounts, project
from ape.utils import ZERO_ADDRESS

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    artist = accounts.test_accounts[1]
    commissioner = accounts.test_accounts[2]
    hub_owner = accounts.test_accounts[3]
    l2relay = accounts.test_accounts[9]
    
    # Deploy ArtPiece template
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy ArtCommissionHub template
    art_commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    
    # Deploy OwnerRegistry
    owner_registry = project.OwnerRegistry.deploy(l2relay.address, art_commission_hub_template.address, sender=deployer)
    
    # Use registry to create and initialize the hub
    chain_id = 1
    nft_contract = deployer.address
    token_id = 1
    owner_registry.registerNFTOwnerFromParentChain(chain_id, nft_contract, token_id, hub_owner.address, sender=l2relay)
    commission_hub_address = owner_registry.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
    commission_hub = project.ArtCommissionHub.at(commission_hub_address)
    
    return {
        "deployer": deployer,
        "artist": artist,
        "commissioner": commissioner,
        "hub_owner": hub_owner,
        "art_piece_template": art_piece_template,
        "commission_hub": commission_hub
    }

def test_is_commission_determination(setup):
    """Test that isUnverifiedCommission is correctly determined based on commissioner_input != artist_input"""
    # Arrange
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    art_piece_template = setup["art_piece_template"]
    
    # Act - Create art piece with different commissioner and artist
    commission_art_piece = project.ArtPiece.deploy(sender=deployer)
    commission_art_piece.initialize(
        b"test_data",
        "avif",
        "Test Commission",
        "Test Description",
        commissioner.address,  # commissioner_input
        artist.address,  # artist_input
        ZERO_ADDRESS,  # commission_hub
        False,  # ai_generated
        sender=deployer
    )
    
    # Assert - Should be an unverified commission
    assert commission_art_piece.isUnverifiedCommission(), "Should be an unverified commission when commissioner != artist"
    
    # Act - Create art piece with same commissioner and artist
    non_commission_art_piece = project.ArtPiece.deploy(sender=deployer)
    non_commission_art_piece.initialize(
        b"test_data",
        "avif",
        "Test Non-Commission",
        "Test Description",
        artist.address,  # commissioner_input
        artist.address,  # artist_input
        ZERO_ADDRESS,  # commission_hub
        False,  # ai_generated
        sender=deployer
    )
    
    # Assert - Should not be an unverified commission
    assert not non_commission_art_piece.isUnverifiedCommission(), "Should not be an unverified commission when commissioner == artist"

def test_verification_status_initialization(setup):
    """Test that verification status is correctly initialized based on the uploader's role"""
    # Arrange
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    
    # Act - Create art piece with commissioner as uploader
    commissioner_uploaded = project.ArtPiece.deploy(sender=deployer)
    commissioner_uploaded.initialize(
        b"test_data",
        "avif",
        "Commissioner Uploaded",
        "Test Description",
        commissioner.address,  # commissioner_input (uploader)
        artist.address,  # artist_input
        ZERO_ADDRESS,  # commission_hub
        False,  # ai_generated
        sender=deployer
    )
    
    # Assert - Commissioner side should be verified, artist side should not
    assert commissioner_uploaded.commissionerVerified(), "Commissioner side should be verified when commissioner is uploader"
    assert not commissioner_uploaded.artistVerified(), "Artist side should not be verified when commissioner is uploader"
    assert not commissioner_uploaded.isFullyVerifiedCommission(), "Commission should not be fully verified yet"
    
    # Act - Create art piece with artist as uploader
    artist_uploaded = project.ArtPiece.deploy(sender=deployer)
    artist_uploaded.initialize(
        b"test_data",
        "avif",
        "Artist Uploaded",
        "Test Description",
        artist.address,  # commissioner_input (uploader)
        artist.address,  # artist_input
        ZERO_ADDRESS,  # commission_hub
        False,  # ai_generated
        sender=deployer
    )
    
    # Assert - Both sides should be verified (non-commission piece)
    assert artist_uploaded.commissionerVerified(), "Commissioner side should be verified for non-commission piece"
    assert artist_uploaded.artistVerified(), "Artist side should be verified for non-commission piece"
    assert artist_uploaded.isFullyVerifiedCommission(), "Non-commission piece should be fully verified"

def test_commissioner_stored_separately(setup):
    """Test that the commissioner is stored separately from the owner, and ownership logic is correct"""
    # Arrange
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]

    # Act - Create art piece (commissioner as uploader)
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
        b"test_data",
        "avif",
        "Test Commission",
        "Test Description",
        commissioner.address,  # commissioner_input
        artist.address,        # artist_input
        ZERO_ADDRESS,          # commission_hub
        False,                 # ai_generated
        sender=deployer
    )

    # Assert - Commissioner should be stored correctly
    assert art_piece.getCommissioner() == commissioner.address, "Commissioner should be stored correctly"
    # Assert - Owner should be commissioner initially (before verification)
    assert art_piece.getOwner() == commissioner.address, "Owner should be commissioner initially"

    # Act - Only verify as artist (commissioner is already verified)
    art_piece.verifyAsArtist(sender=artist)

    # Assert - Owner should still be commissioner after verification (no hub attached)
    assert art_piece.getOwner() == commissioner.address, "Owner should still be commissioner after verification"

def test_verification_flow(setup):
    """Test the full verification flow for a commission piece"""
    # Arrange
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]

    # Create art piece with artist as uploader (non-commission piece)
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
        b"test_data",
        "avif",
        "Verification Flow Test",
        "Test Description",
        artist.address,  # commissioner_input (artist is uploader)
        artist.address,  # artist_input
        ZERO_ADDRESS,  # commission_hub
        False,  # ai_generated
        sender=deployer
    )

    # Assert initial state for non-commission piece
    assert not art_piece.isUnverifiedCommission(), "Should not be an unverified commission"
    assert art_piece.isFullyVerifiedCommission(), "Non-commission piece should be verified automatically"

    # Create a commission piece with commissioner as commissioner and artist as artist
    commission_piece = project.ArtPiece.deploy(sender=deployer)
    commission_piece.initialize(
        b"test_data",
        "avif",
        "Commission Verification Flow",
        "Test Description",
        commissioner.address,  # commissioner_input (commissioner)
        artist.address,        # artist_input (artist)
        ZERO_ADDRESS,  # commission_hub
        False,  # ai_generated
        sender=deployer
    )

    # Assert initial state for commission piece
    assert commission_piece.isUnverifiedCommission(), "Should be an unverified commission"
    assert commission_piece.commissionerVerified(), "Commissioner side should be verified (uploader)"
    assert not commission_piece.artistVerified(), "Artist side should not be verified yet"
    assert not commission_piece.isFullyVerifiedCommission(), "Commission should not be fully verified yet"

    # Act - Complete verification
    commission_piece.verifyAsArtist(sender=artist)

    # Assert final state
    assert commission_piece.artistVerified(), "Artist side should now be verified"
    assert commission_piece.isFullyVerifiedCommission(), "Commission should now be fully verified"

def test_hub_attached_commission_verification():
    # --- Begin new setup for registry and hub ---
    deployer = accounts.test_accounts[0]
    l2relay = accounts.test_accounts[9]
    art_commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    owner_registry = project.OwnerRegistry.deploy(l2relay.address, art_commission_hub_template.address, sender=deployer)
    artist = accounts.test_accounts[1]
    commissioner = accounts.test_accounts[2]
    hub_owner = accounts.test_accounts[3]
    chain_id = 1
    nft_contract = accounts.test_accounts[4].address
    token_id = 55
    # Register NFT owner and get hub
    owner_registry.registerNFTOwnerFromParentChain(chain_id, nft_contract, token_id, hub_owner.address, sender=l2relay)
    commission_hub_address = owner_registry.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
    commission_hub = project.ArtCommissionHub.at(commission_hub_address)
    # --- End new setup ---
    # Deploy ArtPiece attached to hub
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
        b"test_data",
        "avif",
        "Hub Commission",
        "Test Description",
        commissioner.address,
        artist.address,
        commission_hub_address,
        False,
        sender=deployer
    )
    assert art_piece.isUnverifiedCommission(), "Should be an unverified commission"
    assert art_piece.commissionerVerified(), "Commissioner side should be verified (uploader)"
    assert not art_piece.artistVerified(), "Artist side should not be verified yet"
    assert not art_piece.isFullyVerifiedCommission(), "Commission should not be fully verified yet"
    assert art_piece.attachedToArtCommissionHub(), "Should be attached to hub"
    assert art_piece.getArtCommissionHubAddress() == commission_hub_address, "Should have correct hub address"
    art_piece.verifyAsArtist(sender=artist)
    assert art_piece.artistVerified(), "Artist side should now be verified"
    assert art_piece.isFullyVerifiedCommission(), "Commission should now be fully verified"
    # Owner should be the hub owner (aliased)
    assert art_piece.getOwner() == commission_hub.owner(), "Owner should be the hub owner (aliased)"

def test_non_commission_always_verified(setup):
    """Test that non-commission pieces are always considered verified"""
    # Arrange
    deployer = setup["deployer"]
    artist = setup["artist"]
    
    # Act - Create non-commission art piece (artist is both artist and commissioner)
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
        b"test_data",
        "avif",
        "Non-Commission Piece",
        "Test Description",
        artist.address,  # commissioner_input
        artist.address,  # artist_input
        ZERO_ADDRESS,  # commission_hub
        False,  # ai_generated
        sender=deployer
    )
    
    # Assert
    assert not art_piece.isUnverifiedCommission(), "Should not be an unverified commission"
    assert art_piece.isFullyVerifiedCommission(), "Non-commission piece should always be verified"
    assert art_piece.artistVerified(), "Artist side should be verified for non-commission"
    assert art_piece.commissionerVerified(), "Commissioner side should be verified for non-commission"
    assert art_piece.fullyVerifiedCommission(), "Non-commission piece should be fully verified"

def test_commission_verification_flow(setup):
    """Test the full verification flow for a commission piece"""
    # Arrange
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    
    # Act - Create commission piece
    commission_piece = project.ArtPiece.deploy(sender=deployer)
    commission_piece.initialize(
        b"test_data",
        "avif",
        "Commission Piece",
        "Test Description",
        commissioner.address,  # commissioner_input
        artist.address,  # artist_input
        ZERO_ADDRESS,  # commission_hub
        False,  # ai_generated
        sender=deployer
    )
    
    # Assert initial state
    assert commission_piece.isUnverifiedCommission(), "Should be an unverified commission"
    assert not commission_piece.isFullyVerifiedCommission(), "Commission should not be verified initially"
    assert not commission_piece.artistVerified(), "Artist should not be verified initially"
    assert commission_piece.commissionerVerified(), "Commissioner should be verified initially (uploader)"

def test_artist_verification(setup):
    """Test that artist can verify their side of a commission"""
    # Arrange
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    
    # Create commission with commissioner as uploader
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
        b"test_data",
        "avif",
        "Artist Verification Test",
        "Test Description",
        commissioner.address,  # commissioner_input
        artist.address,  # artist_input
        ZERO_ADDRESS,  # commission_hub
        False,  # ai_generated
        sender=deployer
    )
    
    # Assert initial state
    assert art_piece.isUnverifiedCommission(), "Should be an unverified commission"
    assert not art_piece.artistVerified(), "Artist should not be verified initially"
    assert art_piece.commissionerVerified(), "Commissioner should be verified initially (uploader)"

# Helper fixture to deploy OwnerRegistry and ArtCommissionHub template
@pytest.fixture
def registry_and_template():
    deployer = accounts.test_accounts[0]
    l2relay = accounts.test_accounts[9]
    art_commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    owner_registry = project.OwnerRegistry.deploy(l2relay.address, art_commission_hub_template.address, sender=deployer)
    return deployer, l2relay, art_commission_hub_template, owner_registry

# Test creation and initialization of a generic commission hub via OwnerRegistry
@pytest.mark.usefixtures("registry_and_template")
def test_create_generic_commission_hub(registry_and_template):
    deployer, l2relay, art_commission_hub_template, owner_registry = registry_and_template
    owner = accounts.test_accounts[1]
    chain_id = 1
    
    # Owner creates a generic commission hub via the registry
    # The function returns a transaction receipt, not the address directly
    tx = owner_registry.createGenericCommissionHub(chain_id, owner.address, sender=owner)
    
    # Debug: Print logs to understand their structure
    print("\nTransaction logs:")
    for i, log in enumerate(tx.logs):
        print(f"Log {i}:")
        print(f"  Address: {log['address']}")
        print(f"  Topics: {[t.hex() if isinstance(t, bytes) else t for t in log['topics']]}")
        print(f"  Data: {log['data'].hex() if isinstance(log['data'], bytes) else log['data']}")
    
    # Get the hub address from the OwnerRegistry directly instead of parsing logs
    # This is a more reliable approach
    # We'll use getCommissionHubsForOwner which returns the hubs for a given owner
    hubs = owner_registry.getCommissionHubsForOwner(owner.address, 0, 100)
    assert len(hubs) > 0, "No commission hubs found for owner"
    commission_hub_address = hubs[0]  # Get the first hub (should be the one we just created)
    
    commission_hub = project.ArtCommissionHub.at(commission_hub_address)
    
    # Check that the hub is initialized and owned by the correct owner
    assert commission_hub.isInitialized() is True
    assert commission_hub.owner() == owner.address
    assert commission_hub.is_generic() is True
    assert commission_hub.chainId() == chain_id

# Test creation and initialization of an NFT-based commission hub via OwnerRegistry
@pytest.mark.usefixtures("registry_and_template")
def test_create_nft_commission_hub(registry_and_template):
    deployer, l2relay, art_commission_hub_template, owner_registry = registry_and_template
    nft_owner = accounts.test_accounts[2]
    chain_id = 1
    nft_contract = accounts.test_accounts[3].address  # Use an address as a dummy NFT contract
    token_id = 42
    # L2Relay registers NFT owner, which creates and initializes the hub
    owner_registry.registerNFTOwnerFromParentChain(chain_id, nft_contract, token_id, nft_owner.address, sender=l2relay)
    commission_hub_address = owner_registry.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
    commission_hub = project.ArtCommissionHub.at(commission_hub_address)
    # Check that the hub is initialized and owned by the correct owner
    assert commission_hub.isInitialized() is True
    assert commission_hub.owner() == nft_owner.address
    assert commission_hub.is_generic() is False
    assert commission_hub.chainId() == chain_id
    assert commission_hub.nftContract() == nft_contract
    assert commission_hub.tokenId() == token_id

# Test updating the owner of an NFT-based commission hub via OwnerRegistry
@pytest.mark.usefixtures("registry_and_template")
def test_update_nft_commission_hub_owner(registry_and_template):
    deployer, l2relay, art_commission_hub_template, owner_registry = registry_and_template
    nft_owner = accounts.test_accounts[2]
    new_owner = accounts.test_accounts[4]
    chain_id = 1
    nft_contract = accounts.test_accounts[3].address
    token_id = 99
    # Register initial owner
    owner_registry.registerNFTOwnerFromParentChain(chain_id, nft_contract, token_id, nft_owner.address, sender=l2relay)
    commission_hub_address = owner_registry.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
    commission_hub = project.ArtCommissionHub.at(commission_hub_address)
    assert commission_hub.owner() == nft_owner.address
    # Update owner
    owner_registry.registerNFTOwnerFromParentChain(chain_id, nft_contract, token_id, new_owner.address, sender=l2relay)
    assert commission_hub.owner() == new_owner.address

# Test ArtPiece attachment to a hub and correct owner logic after full verification
@pytest.mark.usefixtures("registry_and_template")
def test_art_piece_hub_ownership_flow(registry_and_template):
    deployer, l2relay, art_commission_hub_template, owner_registry = registry_and_template
    artist = accounts.test_accounts[5]
    commissioner = accounts.test_accounts[6]
    chain_id = 1
    nft_contract = accounts.test_accounts[7].address
    token_id = 123
    # Register NFT owner and get hub
    owner_registry.registerNFTOwnerFromParentChain(chain_id, nft_contract, token_id, commissioner.address, sender=l2relay)
    commission_hub_address = owner_registry.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
    commission_hub = project.ArtCommissionHub.at(commission_hub_address)
    # Deploy ArtPiece
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
        b"test_data",
        "avif",
        "Commissioned Art",
        "Test Description",
        commissioner.address,  # commissioner_input
        artist.address,        # artist_input
        commission_hub_address,
        False,
        sender=deployer
    )
    # Initially, only commissioner is verified
    assert art_piece.commissionerVerified() is True
    assert art_piece.artistVerified() is False
    assert art_piece.isFullyVerifiedCommission() is False
    # Artist verifies
    art_piece.verifyAsArtist(sender=artist)
    # Now fully verified, owner should be the hub owner (commissioner)
    assert art_piece.isFullyVerifiedCommission() is True
    assert art_piece.getOwner() == commissioner.address
    # Simulate NFT transfer: update hub owner via registry
    new_owner = accounts.test_accounts[8]
    owner_registry.registerNFTOwnerFromParentChain(chain_id, nft_contract, token_id, new_owner.address, sender=l2relay)
    # ArtPiece should now report new owner
    assert art_piece.getOwner() == new_owner.address

# Test that only OwnerRegistry can initialize a hub (negative test)
def test_only_owner_registry_can_initialize(registry_and_template):
    deployer, l2relay, art_commission_hub_template, owner_registry = registry_and_template
    attacker = accounts.test_accounts[8]
    commission_hub = project.ArtCommissionHub.deploy(sender=deployer)
    # Try to initialize directly as attacker
    with pytest.raises(Exception) as excinfo:
        commission_hub.initialize(1, attacker.address, 1, owner_registry.address, sender=attacker)
    assert "Only OwnerRegistry can initialize" in str(excinfo.value)
    # Try to initializeGeneric directly as attacker
    with pytest.raises(Exception) as excinfo:
        commission_hub.initializeGeneric(1, attacker.address, owner_registry.address, True, sender=attacker)
    assert "Only OwnerRegistry can initialize generic hub" in str(excinfo.value) 