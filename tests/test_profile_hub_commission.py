import pytest
from ape import accounts, project
import time

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    user = accounts.test_accounts[1]
    artist = accounts.test_accounts[2]
    
    # Deploy Profile template
    profile_template = project.Profile.deploy(sender=deployer)
    
    # Deploy ProfileHub with the template
    profile_hub = project.ProfileHub.deploy(profile_template.address, sender=deployer)
    
    # Deploy ArtPiece template for createArtPiece tests
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy CommissionHub for art piece registration
    commission_hub = project.CommissionHub.deploy(sender=deployer)
    
    return {
        "deployer": deployer,
        "user": user,
        "artist": artist,
        "profile_template": profile_template,
        "profile_hub": profile_hub,
        "art_piece_template": art_piece_template,
        "commission_hub": commission_hub
    }

def test_create_new_commission_and_register_profile(setup):
    """Test creating a profile and art piece in one transaction"""
    user = setup["user"]
    artist = setup["artist"]
    profile_hub = setup["profile_hub"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Verify user doesn't have a profile yet
    assert profile_hub.hasProfile(user.address) == False
    
    # Sample art piece data
    image_data = b"sample art piece image data" * 10
    title = "First Commission"
    description = b"Description for first commission"
    is_artist = False  # User is not the artist
    
    # Create profile and commission in one transaction
    profile_address, art_piece_address = profile_hub.createNewArtPieceAndRegisterProfile(
        art_piece_template.address,
        image_data,
        title,
        description,
        is_artist,
        artist.address,  # Artist is the other party
        commission_hub.address,
        False,  # Not AI generated
        sender=user
    )
    
    # Verify profile was created and registered
    assert profile_hub.hasProfile(user.address) == True
    assert profile_hub.getProfile(user.address) == profile_address
    
    # Load the profile contract
    profile = project.Profile.at(profile_address)
    
    # Verify the profile owner is set correctly
    assert profile.owner() == user.address
    
    # Verify art piece count and access
    assert profile.myArtCount() == 1
    
    # Get the latest art pieces and verify
    latest_art_pieces = profile.getLatestArtPieces()
    assert len(latest_art_pieces) == 1
    assert latest_art_pieces[0] == art_piece_address
    
    # Load and verify the art piece properties
    art_piece = project.ArtPiece.at(art_piece_address)
    assert art_piece.getOwner() == user.address
    assert art_piece.getArtist() == artist.address
    assert art_piece.getImageData() == image_data
    assert art_piece.getTitle() == title
    assert art_piece.getDescription() == description

def test_create_new_commission_when_profile_exists_should_fail(setup):
    """Test that creating a commission with an existing profile fails"""
    user = setup["user"]
    artist = setup["artist"]
    profile_hub = setup["profile_hub"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # First create a profile the normal way
    profile_hub.createProfile(sender=user)
    
    # Verify user now has a profile
    assert profile_hub.hasProfile(user.address) == True
    
    # Sample art piece data
    image_data = b"sample art piece image data" * 10
    title = "Should Fail Commission"
    description = b"Description for failing commission"
    
    # Attempt to create profile and commission when profile already exists
    # This should fail
    with pytest.raises(Exception):
        profile_hub.createNewArtPieceAndRegisterProfile(
            art_piece_template.address,
            image_data,
            title,
            description,
            False,  # Not an artist
            artist.address,
            commission_hub.address,
            False,  # Not AI generated
            sender=user
        )

def test_artist_creates_commission_for_user(setup):
    """Test an artist creating a commission and profile in one transaction"""
    user = setup["user"]
    artist = setup["artist"]
    profile_hub = setup["profile_hub"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Verify artist doesn't have a profile yet
    assert profile_hub.hasProfile(artist.address) == False
    
    # Sample art piece data
    image_data = b"artist created commission" * 10
    title = "Artist Commission"
    description = b"Commission created by artist"
    is_artist = True  # Artist is creating the commission
    
    # Create profile and commission in one transaction
    profile_address, art_piece_address = profile_hub.createNewArtPieceAndRegisterProfile(
        art_piece_template.address,
        image_data,
        title,
        description,
        is_artist,
        user.address,  # User is the other party (owner)
        commission_hub.address,
        True,  # AI generated
        sender=artist
    )
    
    # Verify profile was created and registered
    assert profile_hub.hasProfile(artist.address) == True
    assert profile_hub.getProfile(artist.address) == profile_address
    
    # Load the profile contract
    profile = project.Profile.at(profile_address)
    
    # Verify the profile owner is set correctly
    assert profile.owner() == artist.address
    
    # Verify art piece count and access
    assert profile.myArtCount() == 1
    
    # Get the latest art pieces and verify
    latest_art_pieces = profile.getLatestArtPieces()
    assert len(latest_art_pieces) == 1
    assert latest_art_pieces[0] == art_piece_address
    
    # Load and verify the art piece properties
    art_piece = project.ArtPiece.at(art_piece_address)
    assert art_piece.getOwner() == user.address  # User owns the art
    assert art_piece.getArtist() == artist.address  # Artist created it
    assert art_piece.getImageData() == image_data
    assert art_piece.getTitle() == title
    assert art_piece.getDescription() == description
    assert art_piece.getAIGenerated() == True 