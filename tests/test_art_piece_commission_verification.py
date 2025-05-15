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
    
    # Deploy ArtPiece template
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy ArtCommissionHub
    commission_hub = project.ArtCommissionHub.deploy(sender=deployer)
    
    # Initialize the hub with hub_owner
    chain_id = 1
    nft_contract = deployer.address
    token_id = 1
    commission_hub.initialize(chain_id, nft_contract, token_id, hub_owner.address, sender=deployer)
    
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
    """Test that the commissioner is stored separately from the owner"""
    # Arrange
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    
    # Act - Create art piece
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
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
    
    # Assert - Commissioner should be stored correctly
    assert art_piece.getCommissioner() == commissioner.address, "Commissioner should be stored correctly"
    
    # Assert - Owner should be commissioner initially (before verification)
    assert art_piece.getOwner() == commissioner.address, "Owner should be commissioner initially"
    
    # Act - Verify as both parties
    art_piece.verifyAsCommissioner(sender=commissioner)
    art_piece.verifyAsArtist(sender=artist)
    
    # Assert - Owner should still be commissioner after verification
    assert art_piece.getOwner() == commissioner.address, "Owner should still be commissioner after verification"

def test_verification_flow(setup):
    """Test the full verification flow for a commission piece"""
    # Arrange
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    
    # Create art piece with artist as uploader
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
    
    # Create a commission piece with artist as uploader
    commission_piece = project.ArtPiece.deploy(sender=deployer)
    commission_piece.initialize(
        b"test_data",
        "avif",
        "Commission Verification Flow",
        "Test Description",
        artist.address,  # commissioner_input (artist is uploader)
        commissioner.address,  # artist_input (different from uploader)
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
    commission_piece.verifyAsArtist(sender=commissioner)
    
    # Assert final state
    assert commission_piece.artistVerified(), "Artist side should now be verified"
    assert commission_piece.isFullyVerifiedCommission(), "Commission should now be fully verified"

def test_hub_attached_commission_verification(setup):
    """Test verification of a commission piece attached to a hub"""
    # Arrange
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    hub_owner = setup["hub_owner"]
    commission_hub = setup["commission_hub"]
    
    # Create a commission piece attached to a hub
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
        b"test_data",
        "avif",
        "Hub Commission",
        "Test Description",
        artist.address,  # commissioner_input (artist is uploader)
        commissioner.address,  # artist_input
        commission_hub.address,  # commission_hub
        False,  # ai_generated
        sender=deployer
    )
    
    # Assert initial state
    assert art_piece.isUnverifiedCommission(), "Should be an unverified commission"
    assert art_piece.commissionerVerified(), "Commissioner side should be verified (uploader)"
    assert not art_piece.artistVerified(), "Artist side should not be verified yet"
    assert not art_piece.isFullyVerifiedCommission(), "Commission should not be fully verified yet"
    assert art_piece.attachedToArtCommissionHub(), "Should be attached to hub"
    assert art_piece.getArtCommissionHubAddress() == commission_hub.address, "Should have correct hub address"
    
    # Act - Complete verification
    art_piece.verifyAsArtist(sender=commissioner)
    
    # Assert final state
    assert art_piece.artistVerified(), "Artist side should now be verified"
    assert art_piece.isFullyVerifiedCommission(), "Commission should now be fully verified"
    
    # Check that the owner is the hub owner
    assert art_piece.getOwner() == hub_owner.address, "Owner should be the hub owner"

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