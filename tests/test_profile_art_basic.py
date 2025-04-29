import pytest
from ape import accounts, project

# Test data
TEST_IMAGE_DATA = b"Test image data" * 10  # Multiply to make it a bit larger
TEST_TITLE = "Test Artwork"
TEST_DESCRIPTION = b"This is a test description for the artwork"
TEST_AI_GENERATED = False

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    artist = accounts.test_accounts[1]
    owner = accounts.test_accounts[2]
    tagged_person = accounts.test_accounts[3]
    commissioner = accounts.test_accounts[4]
    
    # Deploy CommissionHub
    commission_hub = project.CommissionHub.deploy(sender=deployer)
    
    # Deploy Profile template
    profile_template = project.Profile.deploy(sender=deployer)
    
    # Deploy ProfileHub with the template
    profile_hub = project.ProfileHub.deploy(profile_template.address, sender=deployer)
    
    # Deploy ArtPiece template
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Create a profile for the owner
    profile_hub.createProfile(sender=owner)
    owner_profile_address = profile_hub.getProfile(owner.address)
    owner_profile = project.Profile.at(owner_profile_address)
    
    # Create a profile for the artist
    profile_hub.createProfile(sender=artist)
    artist_profile_address = profile_hub.getProfile(artist.address)
    artist_profile = project.Profile.at(artist_profile_address)
    
    # Set artist status for the artist profile
    artist_profile.setIsArtist(True, sender=artist)
    
    return {
        "deployer": deployer,
        "artist": artist,
        "owner": owner,
        "tagged_person": tagged_person,
        "commissioner": commissioner,
        "commission_hub": commission_hub,
        "profile_template": profile_template,
        "profile_hub": profile_hub,
        "art_piece_template": art_piece_template,
        "owner_profile": owner_profile,
        "artist_profile": artist_profile
    }

def test_profile_basic_info(setup):
    """Test basic profile information"""
    owner_profile = setup["owner_profile"]
    artist_profile = setup["artist_profile"]
    owner = setup["owner"]
    artist = setup["artist"]
    
    # Check owner profile
    assert owner_profile.owner() == owner.address
    assert owner_profile.isArtist() is False
    assert owner_profile.myArtCount() == 0
    
    # Check artist profile
    assert artist_profile.owner() == artist.address
    assert artist_profile.isArtist() is True
    assert artist_profile.myArtCount() == 0

def test_profile_social_features_simple(setup):
    """Test basic social features with a simpler approach"""
    owner_profile = setup["owner_profile"]
    owner = setup["owner"]
    artist = setup["artist"]
    profile_hub = setup["profile_hub"]
    
    # Get artist profile address
    artist_profile_address = profile_hub.getProfile(artist.address)
    
    # Owner likes artist profile
    owner_profile.addLikedProfile(artist_profile_address, sender=owner)
    
    # Check liked profile count
    assert owner_profile.likedProfileCount() == 1

def test_create_art_piece_owner(setup):
    """Test creating an art piece through a profile as an owner/commissioner"""
    owner = setup["owner"]
    artist = setup["artist"]
    owner_profile = setup["owner_profile"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Test data for art piece
    image_data = b"test artwork image data" * 10
    title = "Owner Commission"
    description = b"Description for owner commission"
    
    # Initial art count
    initial_count = owner_profile.myArtCount()
    
    # Create art piece as a commissioner (not an artist)
    tx_receipt = owner_profile.createArtPiece(
        art_piece_template.address,
        image_data,
        title,
        description,
        False,  # Not as artist
        artist.address,  # Artist address
        commission_hub.address,
        False,  # Not AI generated
        sender=owner
    )
    
    # Verify art piece was created and added to profile
    assert owner_profile.myArtCount() == initial_count + 1
    
    # Get the art piece address from the profile's art pieces
    # Since we just created it, it should be the only one or the last one added
    art_pieces = owner_profile.getArtPieces(0, 10)
    # Get the last art piece (most recently added)
    art_piece_address = art_pieces[0]  # assuming we're getting the first one in the array
    
    # Check art piece properties
    art_piece = project.ArtPiece.at(art_piece_address)
    assert art_piece.getOwner() == owner.address
    assert art_piece.getArtist() == artist.address
    assert art_piece.getTitle() == title

def test_create_art_piece_artist(setup):
    """Test creating an art piece as an artist"""
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Test data for art piece
    image_data = b"artist created artwork" * 10
    title = "Artist Creation"
    description = b"Artwork created by an artist"
    
    # Initial art count
    initial_count = artist_profile.myArtCount()
    
    # Create art piece as an artist
    tx_receipt = artist_profile.createArtPiece(
        art_piece_template.address,
        image_data,
        title,
        description,
        True,  # As artist
        commissioner.address,  # Commissioner address
        commission_hub.address,
        True,  # AI generated
        sender=artist
    )
    
    # Verify art piece was created and added to profile
    assert artist_profile.myArtCount() == initial_count + 1
    
    # Get the art piece address from the profile's art pieces
    art_pieces = artist_profile.getLatestArtPieces()
    # Should be the only or first art piece in the latest art pieces
    art_piece_address = art_pieces[0]
    
    # Check art piece properties
    art_piece = project.ArtPiece.at(art_piece_address)
    assert art_piece.getOwner() == commissioner.address
    assert art_piece.getArtist() == artist.address
    assert art_piece.getTitle() == title
    assert art_piece.getAIGenerated() is True

def test_direct_profile_creation_and_art(setup):
    """Test creating a new profile directly and then creating art piece"""
    profile_hub = setup["profile_hub"]
    commissioner = setup["commissioner"]
    artist = setup["artist"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Initially commissioner has no profile
    assert profile_hub.hasProfile(commissioner.address) is False
    
    # First create a profile for the commissioner
    profile_hub.createProfile(sender=commissioner)
    
    # Verify profile was created
    assert profile_hub.hasProfile(commissioner.address) is True
    
    # Get the profile address and interface
    profile_address = profile_hub.getProfile(commissioner.address)
    profile = project.Profile.at(profile_address)
    
    # Now create an art piece through the profile
    image_data = b"commissioner artwork" * 10
    title = "Commissioner Creation"
    description = b"Art created by commissioner"
    
    tx_receipt = profile.createArtPiece(
        art_piece_template.address,
        image_data,
        title,
        description,
        False,  # Not as artist
        artist.address,  # Artist address
        commission_hub.address,
        False,  # Not AI generated
        sender=commissioner
    )
    
    # Verify art piece was created and added to profile
    assert profile.myArtCount() == 1
    
    # Get the art piece address
    art_pieces = profile.getArtPieces(0, 10)
    art_piece_address = art_pieces[0]
    
    # Check art piece properties
    art_piece = project.ArtPiece.at(art_piece_address)
    assert art_piece.getTitle() == title
    assert art_piece.getOwner() == commissioner.address
    assert art_piece.getArtist() == artist.address

def test_get_art_piece_at_index_single(setup):
    """Test getting a single art piece by index"""
    owner = setup["owner"]
    artist = setup["artist"]
    owner_profile = setup["owner_profile"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Test data for art piece
    image_data = b"test artwork for index" * 10
    title = "Single Art Piece"
    description = b"Description for single art piece"
    
    # Create art piece
    tx_receipt = owner_profile.createArtPiece(
        art_piece_template.address,
        image_data,
        title,
        description,
        False,  # Not as artist
        artist.address,  # Artist address
        commission_hub.address,
        False,  # Not AI generated
        sender=owner
    )
    
    # Verify art piece was created
    assert owner_profile.myArtCount() == 1
    
    # Get the art piece address using getArtPieceAtIndex
    art_piece_address = owner_profile.getArtPieceAtIndex(0)
    
    # Verify it's not empty
    assert art_piece_address != "0x0000000000000000000000000000000000000000"
    
    # Check art piece properties
    art_piece = project.ArtPiece.at(art_piece_address)
    assert art_piece.getTitle() == title
    assert art_piece.getOwner() == owner.address
    assert art_piece.getArtist() == artist.address

def test_get_art_piece_at_index_multiple(setup):
    """Test getting multiple art pieces by index"""
    owner = setup["owner"]
    artist = setup["artist"]
    owner_profile = setup["owner_profile"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Create 3 art pieces with different titles
    art_titles = ["First Art Piece", "Second Art Piece", "Third Art Piece"]
    created_addresses = []
    
    for i, title in enumerate(art_titles):
        # Create art piece
        tx_receipt = owner_profile.createArtPiece(
            art_piece_template.address,
            f"test artwork {i+1}".encode() * 10,
            title,
            f"Description for art piece {i+1}".encode(),
            False,  # Not as artist
            artist.address,  # Artist address
            commission_hub.address,
            False,  # Not AI generated
            sender=owner
        )
        
        # Add created address to our list for verification
        art_piece_address = owner_profile.getArtPieceAtIndex(i)
        created_addresses.append(art_piece_address)
    
    # Verify art pieces count
    assert owner_profile.myArtCount() == 3
    
    # Get the first art piece using getArtPieceAtIndex
    first_art_piece_address = owner_profile.getArtPieceAtIndex(0)
    assert first_art_piece_address == created_addresses[0]
    
    # Verify first art piece
    first_art_piece = project.ArtPiece.at(first_art_piece_address)
    assert first_art_piece.getTitle() == art_titles[0]
    
    # Try getting index 2 (third art piece)
    third_art_piece_address = owner_profile.getArtPieceAtIndex(2)
    assert third_art_piece_address == created_addresses[2]
    
    # Verify third art piece
    third_art_piece = project.ArtPiece.at(third_art_piece_address)
    assert third_art_piece.getTitle() == art_titles[2]
    
    # Test with invalid index - should revert
    with pytest.raises(Exception):
        owner_profile.getArtPieceAtIndex(3)  # Index out of bounds 