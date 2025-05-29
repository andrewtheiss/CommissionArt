import pytest
from ape import accounts, project
from ape.utils import ZERO_ADDRESS

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    artist = accounts.test_accounts[1]
    commissioner = accounts.test_accounts[2]
    
    # Deploy all necessary templates
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
    
    # Create profiles for test accounts
    profile_factory.createProfile(artist.address, sender=deployer)
    profile_factory.createProfile(commissioner.address, sender=deployer)
    profile_factory.createProfile(deployer.address, sender=deployer)
    
    return {
        "deployer": deployer,
        "artist": artist,
        "commissioner": commissioner,
        "art_piece_template": art_piece_template,
        "profile_factory": profile_factory
    ,
        "art_sales_1155_template": art_sales_1155_template,
        "art_edition_1155_template": art_edition_1155_template,
        "art_sales_1155_template": art_sales_1155_template}

def test_is_commission_determination(setup):
    """Test that isUnverifiedCommission is correctly determined based on commissioner_input != artist_input"""
    # Arrange
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    profile_factory = setup["profile_factory"]
    
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
        artist.address,  # original_uploader
        profile_factory.address,  # profile_factory_address
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
        artist.address,  # original_uploader
        profile_factory.address,  # profile_factory_address
        sender=deployer
    )
    
    # Assert - Should not be an unverified commission
    assert not non_commission_art_piece.isUnverifiedCommission(), "Should not be an unverified commission when commissioner == artist"

def test_verification_status_initialization(setup):
    """Test that verification status is correctly initialized based on commissioner vs artist"""
    # Arrange
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    profile_factory = setup["profile_factory"]
    
    # Act - Create art piece with different commissioner and artist
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
        artist.address,  # original_uploader
        profile_factory.address,  # profile_factory_address
        sender=deployer
    )
    
    # Assert - Neither side should be verified initially for commission pieces
    assert not commission_piece.commissionerVerified(), "Commissioner side should not be verified initially"
    assert not commission_piece.artistVerified(), "Artist side should not be verified initially"
    assert not commission_piece.isFullyVerifiedCommission(), "Commission should not be fully verified yet"
    
    # Act - Create art piece with same commissioner and artist (non-commission)
    non_commission_piece = project.ArtPiece.deploy(sender=deployer)
    non_commission_piece.initialize(
        b"test_data",
        "avif",
        "Non-Commission Piece",
        "Test Description",
        artist.address,  # commissioner_input (same as artist)
        artist.address,  # artist_input
        ZERO_ADDRESS,  # commission_hub
        False,  # ai_generated
        artist.address,  # original_uploader
        profile_factory.address,  # profile_factory_address
        sender=deployer
    )
    
    # Assert - Both sides should be verified (non-commission piece)
    assert non_commission_piece.commissionerVerified(), "Commissioner side should be verified for non-commission piece"
    assert non_commission_piece.artistVerified(), "Artist side should be verified for non-commission piece"
    assert non_commission_piece.isFullyVerifiedCommission(), "Non-commission piece should be fully verified"

def test_commissioner_stored_separately(setup):
    """Test that the commissioner is stored separately from the owner"""
    # Arrange
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    profile_factory = setup["profile_factory"]
    
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
        artist.address,  # original_uploader
        profile_factory.address,  # profile_factory_address
        sender=deployer
    )
    
    # Assert - Commissioner should be stored correctly
    assert art_piece.getCommissioner() == commissioner.address, "Commissioner should be stored correctly"
    
    # Assert - Owner should be original uploader initially (before verification)
    assert art_piece.getOwner() == artist.address, "Owner should be original uploader initially"

def test_art_piece_interface_change(setup):
    """Test that the ArtPiece interface change from _owner_input to _commissioner_input works correctly"""
    # Arrange
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    profile_factory = setup["profile_factory"]
    
    # Simply create an ArtPiece directly
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
        artist.address,        # original_uploader
        profile_factory.address,  # profile_factory_address
        sender=deployer
    )
    
    # Assert - Commissioner should be set correctly
    assert art_piece.getCommissioner() == commissioner.address, "Commissioner should be set correctly"
    assert art_piece.getArtist() == artist.address, "Artist should be set correctly"
    assert art_piece.isUnverifiedCommission(), "Should be an unverified commission"
    
    # Verify the profile exists and is correctly associated with the artist
    assert profile_factory.hasProfile(artist.address), "Artist should have a profile"
    
    # Get the created profile
    artist_profile_address = profile_factory.getProfile(artist.address)
    artist_profile_contract = project.Profile.at(artist_profile_address)
    
    assert artist_profile_contract.address != ZERO_ADDRESS, "Artist profile should not be zero address"
    
    # Verify ProfileSocial was created and linked
    profile_social_address = artist_profile_contract.profileSocial()
    assert profile_social_address != ZERO_ADDRESS, "Profile should have a linked ProfileSocial"
    
    # Get the ProfileSocial contract
    profile_social_contract = project.ProfileSocial.at(profile_social_address)
    
    # Verify bidirectional link
    assert profile_social_contract.profile() == artist_profile_address, "ProfileSocial should link back to Profile"
    assert profile_social_contract.owner() == artist.address, "ProfileSocial should have the same owner as Profile"

def test_verification_flow(setup):
    """Test the full verification flow for a commission piece"""
    # Arrange
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    profile_factory = setup["profile_factory"]
    
    # Create art piece with artist as uploader (non-commission)
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
        b"test_data",
        "avif",
        "Verification Flow Test",
        "Test Description",
        artist.address,  # commissioner_input (same as artist)
        artist.address,  # artist_input
        ZERO_ADDRESS,  # commission_hub
        False,  # ai_generated
        artist.address,  # original_uploader
        profile_factory.address,  # profile_factory_address
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
        commissioner.address,  # commissioner_input (different from artist)
        artist.address,  # artist_input
        ZERO_ADDRESS,  # commission_hub
        False,  # ai_generated
        artist.address,  # original_uploader
        profile_factory.address,  # profile_factory_address
        sender=deployer
    )
    
    # Assert initial state for commission piece
    assert commission_piece.isUnverifiedCommission(), "Should be an unverified commission"
    assert not commission_piece.commissionerVerified(), "Commissioner side should not be verified initially"
    assert not commission_piece.artistVerified(), "Artist side should not be verified initially"
    assert not commission_piece.isFullyVerifiedCommission(), "Commission should not be fully verified yet"
