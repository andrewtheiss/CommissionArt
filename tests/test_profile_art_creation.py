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
    
    # Create profiles for the user and artist
    profile_hub.createProfile(sender=user)
    profile_hub.createProfile(sender=artist)
    
    user_profile_address = profile_hub.getProfile(user.address)
    artist_profile_address = profile_hub.getProfile(artist.address)
    
    user_profile = project.Profile.at(user_profile_address)
    artist_profile = project.Profile.at(artist_profile_address)
    
    # Set artist status for the artist profile
    artist_profile.setIsArtist(True, sender=artist)
    
    return {
        "deployer": deployer,
        "user": user,
        "artist": artist,
        "profile_template": profile_template,
        "profile_hub": profile_hub,
        "art_piece_template": art_piece_template,
        "commission_hub": commission_hub,
        "user_profile": user_profile,
        "artist_profile": artist_profile
    }

def test_create_single_art_piece_and_get_latest(setup):
    """Test creating a single art piece and getting the latest art pieces"""
    user = setup["user"]
    artist = setup["artist"]
    user_profile = setup["user_profile"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Initial check - no art pieces yet
    initial_art_pieces = user_profile.getLatestArtPieces()
    assert len(initial_art_pieces) == 0
    
    # Create a single art piece
    image_data = b"art piece 1 image data" * 5
    art_piece_address = user_profile.createArtPiece(
        art_piece_template.address,
        image_data,
        "Art Piece 1",
        b"Description for Art Piece 1",
        False,  # Not an artist
        artist.address,  # Artist address
        commission_hub.address,
        False,  # Not AI generated
        sender=user
    )
    
    # Verify art piece was added to user's collection
    assert user_profile.myArtCount() == 1
    
    # Get the latest art pieces
    latest_art_pieces = user_profile.getLatestArtPieces()
    assert len(latest_art_pieces) == 1
    assert latest_art_pieces[0] == art_piece_address
    
    # Verify the art piece properties
    art_piece = project.ArtPiece.at(art_piece_address)
    assert art_piece.getOwner() == user.address
    assert art_piece.getArtist() == artist.address
    assert art_piece.getImageData() == image_data

def test_create_multiple_art_pieces_and_get_latest(setup):
    """Test creating multiple art pieces and getting the latest art pieces"""
    user = setup["user"]
    artist = setup["artist"]
    user_profile = setup["user_profile"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Create 7 art pieces
    art_piece_addresses = []
    for i in range(7):
        image_data = f"art piece {i+1} image data".encode() * 5
        art_piece_address = user_profile.createArtPiece(
            art_piece_template.address,
            image_data,
            f"Art Piece {i+1}",
            f"Description for Art Piece {i+1}".encode(),
            False,  # Not an artist
            artist.address,  # Artist address
            commission_hub.address,
            False,  # Not AI generated
            sender=user
        )
        art_piece_addresses.append(art_piece_address)
        
        # Add a small delay to ensure art pieces have different timestamps
        time.sleep(0.1)
    
    # Verify all art pieces were created
    assert user_profile.myArtCount() == 7
    
    # Get the latest art pieces
    latest_art_pieces = user_profile.getLatestArtPieces()
    
    # Should return at most 5 art pieces
    assert len(latest_art_pieces) == 5
    
    # The latest art pieces should be the 5 most recently created (in reverse order)
    for i in range(5):
        assert latest_art_pieces[i] == art_piece_addresses[6-i]
    
    # Verify the properties of the last created art piece
    last_art_piece = project.ArtPiece.at(art_piece_addresses[-1])
    assert last_art_piece.getOwner() == user.address
    assert last_art_piece.getArtist() == artist.address
    assert last_art_piece.getImageData() == b"art piece 7 image data" * 5

def test_create_fewer_than_five_art_pieces(setup):
    """Test creating fewer than 5 art pieces and getting the latest art pieces"""
    user = setup["user"]
    artist = setup["artist"]
    user_profile = setup["user_profile"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Create 3 art pieces
    art_piece_addresses = []
    for i in range(3):
        image_data = f"art piece {i+1} image data".encode() * 5
        art_piece_address = user_profile.createArtPiece(
            art_piece_template.address,
            image_data,
            f"Art Piece {i+1}",
            f"Description for Art Piece {i+1}".encode(),
            False,  # Not an artist
            artist.address,  # Artist address
            commission_hub.address,
            False,  # Not AI generated
            sender=user
        )
        art_piece_addresses.append(art_piece_address)
        
        # Add a small delay to ensure art pieces have different timestamps
        time.sleep(0.1)
    
    # Verify art pieces were created
    assert user_profile.myArtCount() == 3
    
    # Get the latest art pieces
    latest_art_pieces = user_profile.getLatestArtPieces()
    
    # Should return all 3 art pieces
    assert len(latest_art_pieces) == 3
    
    # The latest art pieces should be in reverse order of creation
    for i in range(3):
        assert latest_art_pieces[i] == art_piece_addresses[2-i]

def test_artist_creating_art_pieces(setup):
    """Test an artist creating art pieces and getting latest art pieces"""
    user = setup["user"]
    artist = setup["artist"]
    artist_profile = setup["artist_profile"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Create 4 art pieces as an artist
    art_piece_addresses = []
    for i in range(4):
        image_data = f"artist piece {i+1} image data".encode() * 5
        art_piece_address = artist_profile.createArtPiece(
            art_piece_template.address,
            image_data,
            f"Artist Piece {i+1}",
            f"Description for Artist Piece {i+1}".encode(),
            True,  # Is artist
            user.address,  # Commissioner address
            commission_hub.address,
            i % 2 == 0,  # Alternate AI generated flag
            sender=artist
        )
        art_piece_addresses.append(art_piece_address)
        
        # Add a small delay to ensure art pieces have different timestamps
        time.sleep(0.1)
    
    # Verify art pieces were created
    assert artist_profile.myArtCount() == 4
    
    # Get the latest art pieces
    latest_art_pieces = artist_profile.getLatestArtPieces()
    
    # Should return all 4 art pieces
    assert len(latest_art_pieces) == 4
    
    # The latest art pieces should be in reverse order of creation
    for i in range(4):
        assert latest_art_pieces[i] == art_piece_addresses[3-i]
    
    # Verify the properties of one of the art pieces
    art_piece = project.ArtPiece.at(art_piece_addresses[2])
    assert art_piece.getOwner() == user.address
    assert art_piece.getArtist() == artist.address
    assert art_piece.getImageData() == b"artist piece 3 image data" * 5
    assert art_piece.getAIGenerated() == (2 % 2 == 0)  # Check if AI generated flag matches

def test_create_art_pieces_across_profiles(setup):
    """Test creating art pieces across different profiles and checking latest art pieces"""
    user = setup["user"]
    artist = setup["artist"]
    user_profile = setup["user_profile"]
    artist_profile = setup["artist_profile"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Create 2 art pieces for user
    user_art_pieces = []
    for i in range(2):
        image_data = f"user art {i+1}".encode() * 5
        art_piece_address = user_profile.createArtPiece(
            art_piece_template.address,
            image_data,
            f"User Art {i+1}",
            f"User Art Description {i+1}".encode(),
            False,  # Not artist
            artist.address,
            commission_hub.address,
            False,
            sender=user
        )
        user_art_pieces.append(art_piece_address)
        time.sleep(0.1)
    
    # Create 2 art pieces for artist
    artist_art_pieces = []
    for i in range(2):
        image_data = f"artist art {i+1}".encode() * 5
        art_piece_address = artist_profile.createArtPiece(
            art_piece_template.address,
            image_data,
            f"Artist Art {i+1}",
            f"Artist Art Description {i+1}".encode(),
            True,  # Is artist
            user.address,
            commission_hub.address,
            True,
            sender=artist
        )
        artist_art_pieces.append(art_piece_address)
        time.sleep(0.1)
    
    # Check counts for each profile
    assert user_profile.myArtCount() == 2
    assert artist_profile.myArtCount() == 2
    
    # Get latest art pieces for user
    user_latest = user_profile.getLatestArtPieces()
    assert len(user_latest) == 2
    assert user_latest[0] == user_art_pieces[1]
    assert user_latest[1] == user_art_pieces[0]
    
    # Get latest art pieces for artist
    artist_latest = artist_profile.getLatestArtPieces()
    assert len(artist_latest) == 2
    assert artist_latest[0] == artist_art_pieces[1]
    assert artist_latest[1] == artist_art_pieces[0]
    
    # Verify the collections are separate
    assert set(user_latest) != set(artist_latest) 