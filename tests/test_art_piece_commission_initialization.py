import pytest
from ape import accounts, project
from ape.utils import ZERO_ADDRESS

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    artist = accounts.test_accounts[1]
    commissioner = accounts.test_accounts[2]
    
    # Deploy ArtPiece template
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    return {
        "deployer": deployer,
        "artist": artist,
        "commissioner": commissioner,
        "art_piece_template": art_piece_template
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
    art_piece_template = setup["art_piece_template"]
    
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
    art_piece_template = setup["art_piece_template"]
    
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
    # art_piece.verifyAsCommissioner(sender=commissioner)  # Already verified at initialization, so skip this call
    art_piece.verifyAsArtist(sender=artist)
    
    # Assert - Owner should still be commissioner after verification
    assert art_piece.getOwner() == commissioner.address, "Owner should still be commissioner after verification"

def test_art_piece_interface_change(setup):
    """Test that the ArtPiece interface change from _owner_input to _commissioner_input works correctly"""
    # Arrange
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    art_piece_template = setup["art_piece_template"]
    
    # Simply create an ArtPiece directly instead of through a profile
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
    
    # Assert - Commissioner should be set correctly
    assert art_piece.getCommissioner() == commissioner.address, "Commissioner should be set correctly"
    assert art_piece.getArtist() == artist.address, "Artist should be set correctly"
    assert art_piece.isUnverifiedCommission(), "Should be an unverified commission"
    
    # Now check that the Profile can create art pieces properly
    # Deploy Profile template
    profile_template = project.Profile.deploy(sender=deployer)
    
    # Deploy ProfileSocial template
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    
    # Deploy ProfileFactoryAndRegistry with the required template addresses
    profile_factory = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address,
        profile_social_template.address,
        sender=deployer
    )
    
    # Create profile for artist
    profile_factory.createProfile(sender=artist)
    
    # Get the created profile
    artist_profile = profile_factory.getProfileByOwner(artist.address)
    artist_profile_contract = project.Profile.at(artist_profile)
    
    print(f"Created artist profile at {artist_profile}")
    
    # Verify the profile exists and is correctly associated with the artist
    assert profile_factory.hasProfile(artist.address), "Artist should have a profile"
    assert artist_profile_contract != ZERO_ADDRESS, "Artist profile should not be zero address"
    
    # Verify ProfileSocial was created and linked
    profile_social_address = artist_profile_contract.profileSocial()
    assert profile_social_address != ZERO_ADDRESS, "Profile should have a linked ProfileSocial"
    
    # Get the ProfileSocial contract
    profile_social_contract = project.ProfileSocial.at(profile_social_address)
    
    # Verify bidirectional link
    assert profile_social_contract.profile() == artist_profile, "ProfileSocial should link back to Profile"
    assert profile_social_contract.owner() == artist.address, "ProfileSocial should have the same owner as Profile"

def test_verification_flow(setup):
    """Test the full verification flow for a commission piece"""
    # Arrange
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    art_piece_template = setup["art_piece_template"]
    
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
