# @version 0.4.1

import pytest
from ape import accounts, project
import time

# Test data
TEST_TOKEN_URI_DATA = b"data:application/json;base64,eyJuYW1lIjoiVGVzdCBBcnR3b3JrIiwiZGVzY3JpcHRpb24iOiJUaGlzIGlzIGEgdGVzdCBkZXNjcmlwdGlvbiBmb3IgdGhlIGFydHdvcmsiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFCM1JKVFVVSDVBb1NEdUZvQ0FBQUFBMUpSRUZVZU5xVEVFRUFBQUE1VVBBRHhpVXFJVzRBQUFBQlNVVk9SSzVDWUlJPSJ9"
TEST_TITLE = "Test Artwork"
TEST_DESCRIPTION = "This is a test description for the artwork"
TEST_TOKEN_URI_DATA_FORMAT = "avif"
TEST_AI_GENERATED = False
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    user = accounts.test_accounts[1]
    artist = accounts.test_accounts[2]
    
    # Deploy all templates
    profile_template = project.Profile.deploy(sender=deployer)
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy ProfileFactoryAndRegistry with all templates
    profile_factory_and_registry = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address,
        profile_social_template.address,
        commission_hub_template.address,
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
    profile_factory_and_registry.linkArtCommissionHubOwnersContract(art_commission_hub_owners.address, sender=deployer)
    art_commission_hub_owners.linkProfileFactoryAndRegistry(profile_factory_and_registry.address, sender=deployer)
    
    # Create profiles for test accounts
    profile_factory_and_registry.createProfile(user.address, sender=deployer)
    profile_factory_and_registry.createProfile(artist.address, sender=deployer)
    
    # Get profile addresses and instances
    user_profile_address = profile_factory_and_registry.getProfile(user.address)
    artist_profile_address = profile_factory_and_registry.getProfile(artist.address)
    user_profile = project.Profile.at(user_profile_address)
    artist_profile = project.Profile.at(artist_profile_address)
    
    # Set artist status for the artist profile
    artist_profile.setIsArtist(True, sender=artist)
    
    return {
        "deployer": deployer,
        "user": user,
        "artist": artist,
        "profile_template": profile_template,
        "profile_social_template": profile_social_template,
        "commission_hub_template": commission_hub_template,
        "art_piece_template": art_piece_template,
        "profile_factory_and_registry": profile_factory_and_registry,
        "art_commission_hub_owners": art_commission_hub_owners,
        "user_profile": user_profile,
        "artist_profile": artist_profile
    }

def test_create_single_art_piece_and_get_latest(setup):
    """Test creating a single art piece and getting the latest art pieces"""
    user = setup["user"]
    user_profile = setup["user_profile"]
    art_piece_template = setup["art_piece_template"]
    
    # Initial check - no art pieces yet
    initial_art_pieces = user_profile.getArtPiecesByOffset(0, 5, True)
    assert len(initial_art_pieces) == 0
    
    # Create a single art piece (personal piece)
    tx_receipt = user_profile.createArtPiece(
        art_piece_template.address,
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        "Art Piece 1",
        "Description for Art Piece 1",
        True,  # As artist (creating their own art)
        user.address,  # Other party is also user (personal piece)
        False,  # Not AI generated
        ZERO_ADDRESS,  # No commission hub
        False,  # Not profile art
        sender=user
    )
    
    # Verify art piece was added to user's collection
    assert user_profile.myArtCount() == 1
    
    # Get the latest art pieces
    latest_art_pieces = user_profile.getArtPiecesByOffset(0, 5, True)
    assert len(latest_art_pieces) == 1
    
    # Verify the art piece properties using the address we got back
    art_piece = project.ArtPiece.at(latest_art_pieces[0])
    assert art_piece.getOwner() == user.address
    assert art_piece.getArtist() == user.address
    assert art_piece.getTokenURIData() == TEST_TOKEN_URI_DATA

def test_create_multiple_art_pieces_and_get_latest(setup):
    """Test creating multiple art pieces and getting the latest art pieces"""
    user = setup["user"]
    user_profile = setup["user_profile"]
    art_piece_template = setup["art_piece_template"]
    
    # Create 7 art pieces (personal pieces)
    for i in range(7):
        tx_receipt = user_profile.createArtPiece(
            art_piece_template.address,
            TEST_TOKEN_URI_DATA,
            TEST_TOKEN_URI_DATA_FORMAT,
            f"Art Piece {i+1}",
            f"Description for Art Piece {i+1}",
            True,  # As artist (creating their own art)
            user.address,  # Other party is also user (personal piece)
            False,  # Not AI generated
            ZERO_ADDRESS,  # No commission hub
            False,  # Not profile art
            sender=user
        )
    
    # Verify all art pieces were created
    assert user_profile.myArtCount() == 7
    
    # Get the latest art pieces (should return at most 5)
    latest_art_pieces = user_profile.getArtPiecesByOffset(0, 5, True)
    
    # Should return at most 5 art pieces
    assert len(latest_art_pieces) == 5
    
    # Verify the last art piece in the array is valid
    last_art_piece = project.ArtPiece.at(latest_art_pieces[0])
    assert last_art_piece.getOwner() == user.address
    assert last_art_piece.getArtist() == user.address
    
    # Get individual art pieces and check their titles to verify ordering
    # Most recent should have higher index numbers
    recent_pieces = []
    for addr in latest_art_pieces:
        art = project.ArtPiece.at(addr)
        recent_pieces.append(art.getTitle())
    
    # Verify descending order (newest first)
    for i in range(len(recent_pieces) - 1):
        current_piece_num = int(recent_pieces[i].split()[2])
        next_piece_num = int(recent_pieces[i+1].split()[2])
        assert current_piece_num > next_piece_num, f"Expected {current_piece_num} > {next_piece_num}"

def test_create_fewer_than_five_art_pieces(setup):
    """Test creating fewer than 5 art pieces and getting the latest art pieces"""
    user = setup["user"]
    user_profile = setup["user_profile"]
    art_piece_template = setup["art_piece_template"]
    
    # Create 3 art pieces (personal pieces)
    for i in range(3):
        tx_receipt = user_profile.createArtPiece(
            art_piece_template.address,
            TEST_TOKEN_URI_DATA,
            TEST_TOKEN_URI_DATA_FORMAT,
            f"Art Piece {i+1}",
            f"Description for Art Piece {i+1}",
            True,  # As artist (creating their own art)
            user.address,  # Other party is also user (personal piece)
            False,  # Not AI generated
            ZERO_ADDRESS,  # No commission hub
            False,  # Not profile art
            sender=user
        )
    
    # Verify art pieces were created
    assert user_profile.myArtCount() == 3
    
    # Get the latest art pieces
    latest_art_pieces = user_profile.getArtPiecesByOffset(0, 5, True)
    
    # Should return all 3 art pieces
    assert len(latest_art_pieces) == 3
    
    # Get individual art pieces and check their titles to verify ordering
    recent_pieces = []
    for addr in latest_art_pieces:
        art = project.ArtPiece.at(addr)
        recent_pieces.append(art.getTitle())
    
    # Verify descending order (newest first)
    for i in range(len(recent_pieces) - 1):
        current_piece_num = int(recent_pieces[i].split()[2])
        next_piece_num = int(recent_pieces[i+1].split()[2])
        assert current_piece_num > next_piece_num, f"Expected {current_piece_num} > {next_piece_num}"

def test_artist_creating_art_pieces(setup):
    """Test an artist creating art pieces and getting latest art pieces"""
    artist = setup["artist"]
    artist_profile = setup["artist_profile"]
    art_piece_template = setup["art_piece_template"]
    
    # Create 4 art pieces as an artist (personal pieces)
    for i in range(4):
        tx_receipt = artist_profile.createArtPiece(
            art_piece_template.address,
            TEST_TOKEN_URI_DATA,
            TEST_TOKEN_URI_DATA_FORMAT,
            f"Artist Piece {i+1}",
            f"Description for Artist Piece {i+1}",
            True,  # As artist
            artist.address,  # Other party is also artist (personal piece)
            i % 2 == 0,  # Alternate AI generated flag
            ZERO_ADDRESS,  # No commission hub
            False,  # Not profile art
            sender=artist
        )
    
    # Verify art pieces were created
    assert artist_profile.myArtCount() == 4
    
    # Get the latest art pieces
    latest_art_pieces = artist_profile.getArtPiecesByOffset(0, 5, True)
    
    # Should return all 4 art pieces
    assert len(latest_art_pieces) == 4
    
    # Get individual art pieces and check their titles to verify ordering
    recent_pieces = []
    for addr in latest_art_pieces:
        art = project.ArtPiece.at(addr)
        recent_pieces.append(art.getTitle())
    
    # Verify descending order (newest first)
    for i in range(len(recent_pieces) - 1):
        current_piece_num = int(recent_pieces[i].split()[2])
        next_piece_num = int(recent_pieces[i+1].split()[2])
        assert current_piece_num > next_piece_num, f"Expected {current_piece_num} > {next_piece_num}"
    
    # Verify the properties of one of the art pieces
    art_piece = project.ArtPiece.at(latest_art_pieces[0])
    assert art_piece.getOwner() == artist.address
    assert art_piece.getArtist() == artist.address

def test_create_art_pieces_across_profiles(setup):
    """Test creating art pieces across different profiles and checking latest art pieces"""
    user = setup["user"]
    artist = setup["artist"]
    user_profile = setup["user_profile"]
    artist_profile = setup["artist_profile"]
    art_piece_template = setup["art_piece_template"]
    
    # Create art piece through the user profile (personal pieces)
    for i in range(3):
        tx_receipt = user_profile.createArtPiece(
            art_piece_template.address,
            TEST_TOKEN_URI_DATA,
            TEST_TOKEN_URI_DATA_FORMAT,
            f"User Art {i+1}",
            f"Description for User Art {i+1}",
            True,  # As artist (creating their own art)
            user.address,  # Other party is also user (personal piece)
            False,  # Not AI generated
            ZERO_ADDRESS,  # No commission hub
            False,  # Not profile art
            sender=user
        )
    
    # Create art piece through the artist profile (personal pieces)
    for i in range(2):
        tx_receipt = artist_profile.createArtPiece(
            art_piece_template.address,
            TEST_TOKEN_URI_DATA,
            TEST_TOKEN_URI_DATA_FORMAT,
            f"Artist Art {i+1}",
            f"Description for Artist Art {i+1}",
            True,  # As artist
            artist.address,  # Other party is also artist (personal piece)
            True,  # AI generated
            ZERO_ADDRESS,  # No commission hub
            False,  # Not profile art
            sender=artist
        )
    
    # Verify art pieces were created
    assert user_profile.myArtCount() == 3
    assert artist_profile.myArtCount() == 2
    
    # Get the latest art pieces from both profiles
    user_latest = user_profile.getArtPiecesByOffset(0, 5, True)
    artist_latest = artist_profile.getArtPiecesByOffset(0, 5, True)
    
    # Should return all art pieces from each profile
    assert len(user_latest) == 3
    assert len(artist_latest) == 2
    
    # Verify ordering for user art pieces
    user_pieces = []
    for addr in user_latest:
        art = project.ArtPiece.at(addr)
        user_pieces.append(art.getTitle())
    
    for i in range(len(user_pieces) - 1):
        current_piece_num = int(user_pieces[i].split()[2])
        next_piece_num = int(user_pieces[i+1].split()[2])
        assert current_piece_num > next_piece_num, f"Expected user piece {current_piece_num} > {next_piece_num}"
    
    # Verify ordering for artist art pieces
    artist_pieces = []
    for addr in artist_latest:
        art = project.ArtPiece.at(addr)
        artist_pieces.append(art.getTitle())
    
    for i in range(len(artist_pieces) - 1):
        current_piece_num = int(artist_pieces[i].split()[2])
        next_piece_num = int(artist_pieces[i+1].split()[2])
        assert current_piece_num > next_piece_num, f"Expected artist piece {current_piece_num} > {next_piece_num}"
    
    # Verify the collections are separate
    assert set(user_latest) != set(artist_latest) 