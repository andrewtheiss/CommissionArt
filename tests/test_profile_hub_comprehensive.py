import pytest
from ape import accounts, project
import time
import base64
import json

@pytest.fixture
def setup():
    # Get accounts for testing - create more test accounts for comprehensive testing
    deployer = accounts.test_accounts[0]
    user = accounts.test_accounts[1]
    artist = accounts.test_accounts[2]
    commissioner = accounts.test_accounts[3]
    other_artist = accounts.test_accounts[4]
    
    # Deploy Profile template
    profile_template = project.Profile.deploy(sender=deployer)
    
    # Deploy ProfileHub with the template
    profile_hub = project.ProfileHub.deploy(profile_template.address, sender=deployer)
    
    # Deploy ArtPiece template for createArtPiece tests
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy ArtCommissionHub for art piece registration
    commission_hub = project.ArtCommissionHub.deploy(sender=deployer)
    
    return {
        "deployer": deployer,
        "user": user,
        "artist": artist,
        "commissioner": commissioner,
        "other_artist": other_artist,
        "profile_template": profile_template,
        "profile_hub": profile_hub,
        "art_piece_template": art_piece_template,
        "commission_hub": commission_hub
    }

def test_user_first_upload_creates_profile_and_art(setup):
    """
    Test a user's first art upload creates both a profile and art piece in one transaction.
    This is the main user flow we want to ensure works correctly.
    """
    # Arrange
    user = setup["user"]
    artist = setup["artist"]
    profile_hub = setup["profile_hub"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Verify user doesn't have a profile yet
    assert profile_hub.hasProfile(user.address) == False
    
    # Sample art piece data for first upload
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiTXkgRmlyc3QgQXJ0d29yayIsImRlc2NyaXB0aW9uIjoiVGhpcyBpcyBteSBmaXJzdCBldmVyIHVwbG9hZGVkIGFydCBwaWVjZSIsImltYWdlIjoiZGF0YTppbWFnZS9wbmc7YmFzZTY0LGlWQk9SdzBLR2dvQUFBQU5TVWhFVWdBQUFBUUFBQUFFQ0FJQUFBQENOQ3ZEQUFBQUF4cEpSRUZVQ05kai9BOERBQUFqQVA5L2c0dWFBQUFBQUVsRlRrU3VRbUNDIn0="
    # Parse base64 data to extract title and description
    base64_data = token_uri_data.replace(b"data:application/json;base64,", b"")
    json_data = json.loads(base64.b64decode(base64_data).decode("utf-8"))
    title = json_data["name"]
    description = json_data["description"]
    is_artist = True  # User is the artist of their own work
    
    # Act - Create profile and art piece in one transaction
    result = profile_hub.createNewArtPieceAndRegisterProfile(
        art_piece_template.address,
        token_uri_data,
        "avif",
        title,
        description,
        is_artist,
        empty_address_value(),  # No other party
        commission_hub.address,
        False,  # Not AI generated
        sender=user
    )
    
    # Get profile address
    profile_address = profile_hub.getProfile(user.address)
    
    # Assert - Verify profile was created and registered
    assert profile_hub.hasProfile(user.address) == True
    
    # Load the profile contract
    profile = project.Profile.at(profile_address)
    
    # Verify the profile owner is set correctly
    assert profile.owner() == user.address
    
    # Verify art piece count and access
    assert profile.myArtCount() == 1
    
    # Get the latest art pieces and verify
    latest_art_pieces = profile.getLatestArtPieces()
    assert len(latest_art_pieces) == 1
    art_piece_address = latest_art_pieces[0]
    
    # Load and verify the art piece properties
    art_piece = project.ArtPiece.at(art_piece_address)
    assert art_piece.getOwner() == user.address
    assert art_piece.getArtist() == user.address  # User is both owner and artist
    assert art_piece.getTokenURIData() == token_uri_data
    assert art_piece.getTitle() == title
    assert art_piece.getDescription() == description

def test_commissioner_creates_profile_and_commission(setup):
    """
    Test a commissioner creating a profile and commissioning art in one transaction.
    """
    commissioner = setup["commissioner"]
    artist = setup["artist"]
    profile_hub = setup["profile_hub"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Verify commissioner doesn't have a profile yet
    assert profile_hub.hasProfile(commissioner.address) == False
    
    # Sample commission data
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiQXJ0IENvbW1pc3Npb24gUmVxdWVzdCIsImRlc2NyaXB0aW9uIjoiSSdkIGxpa2UgdG8gY29tbWlzc2lvbiBhIGZhbnRhc3kgbGFuZHNjYXBlIiwiaW1hZ2UiOiJkYXRhOmltYWdlL3BuZztiYXNlNjQsaVZCT1J3MEtHZ29BQUFBTlNVaEVVZ0FBQUFRQUFBQUVDQUlBQUFCQ05DdkRBQUFBQXhwSlJFRlVDTmRqL0E4REFBQU5BUDgvaFpZYUFBQUFBRWxGVGtTdVFtQ0MifQ=="
    # Parse base64 data to extract title and description
    base64_data = token_uri_data.replace(b"data:application/json;base64,", b"")
    json_data = json.loads(base64.b64decode(base64_data).decode("utf-8"))
    title = json_data["name"]
    description = json_data["description"]
    is_artist = False  # Commissioner is not the artist
    
    # Create profile and commission in one transaction
    result = profile_hub.createNewArtPieceAndRegisterProfile(
        art_piece_template.address,
        token_uri_data,
        "avif",
        title,
        description,
        is_artist,
        artist.address,  # Artist is the other party
        commission_hub.address,
        False,  # Not AI generated
        sender=commissioner
    )
    
    # Get profile address
    profile_address = profile_hub.getProfile(commissioner.address)
    
    # Verify profile was created
    assert profile_hub.hasProfile(commissioner.address) == True
    
    # Load the profile contract
    profile = project.Profile.at(profile_address)
    
    # Verify the profile owner is set correctly
    assert profile.owner() == commissioner.address
    
    # Verify art piece count
    assert profile.myArtCount() == 1
    
    # Get the art piece
    latest_art_pieces = profile.getLatestArtPieces()
    assert len(latest_art_pieces) == 1
    art_piece_address = latest_art_pieces[0]
    
    # Load and verify the art piece properties
    art_piece = project.ArtPiece.at(art_piece_address)
    assert art_piece.getOwner() == commissioner.address
    assert art_piece.getArtist() == artist.address
    assert art_piece.getTokenURIData() == token_uri_data
    assert art_piece.getTitle() == title
    assert art_piece.getDescription() == description

def test_artist_creates_profile_with_portfolio_piece(setup):
    """
    Test an artist creating a profile and portfolio piece in one transaction.
    """
    other_artist = setup["other_artist"]
    profile_hub = setup["profile_hub"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Verify artist doesn't have a profile yet
    assert profile_hub.hasProfile(other_artist.address) == False
    
    # Sample portfolio piece data
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiUG9ydGZvbGlvIFNob3djYXNlIFBpZWNlIiwiZGVzY3JpcHRpb24iOiJNeSBiZXN0IHdvcmsgdG8gZGVtb25zdHJhdGUgbXkgc2tpbGxzIiwiaW1hZ2UiOiJkYXRhOmltYWdlL3BuZztiYXNlNjQsaVZCT1J3MEtHZ29BQUFBTlNVaEVVZ0FBQUFRQUFBQUVDQUlBQUFCQ05DdkRBQUFBQXhwSlJFRlVDTmRqL0E4REFBQU5BUDkvaFpZYUFBQUFBRWxGVGtTdVFtQ0MifQ=="
    # Parse base64 data for title and description
    base64_data = token_uri_data.replace(b"data:application/json;base64,", b"")
    json_data = json.loads(base64.b64decode(base64_data).decode("utf-8"))
    title = json_data["name"]
    description = json_data["description"]
    is_artist = True  # Artist is the creator
    
    # Create profile and portfolio piece in one transaction
    result = profile_hub.createNewArtPieceAndRegisterProfile(
        art_piece_template.address,
        token_uri_data,
        "avif",
        title,
        description,
        is_artist,
        empty_address_value(),  # No other party for portfolio piece
        commission_hub.address,
        False,  # Not AI generated
        sender=other_artist
    )
    
    # Get profile address
    profile_address = profile_hub.getProfile(other_artist.address)
    
    # Verify profile was created
    assert profile_hub.hasProfile(other_artist.address) == True
    
    # Load profile and set as artist
    profile = project.Profile.at(profile_address)
    profile.setIsArtist(True, sender=other_artist)
    
    # Verify the profile owner and artist status
    assert profile.owner() == other_artist.address
    assert profile.isArtist() == True
    
    # Verify art piece count
    assert profile.myArtCount() == 1
    
    # Get the art piece
    latest_art_pieces = profile.getLatestArtPieces()
    assert len(latest_art_pieces) == 1
    art_piece_address = latest_art_pieces[0]
    
    # Verify art piece properties
    art_piece = project.ArtPiece.at(art_piece_address)
    assert art_piece.getOwner() == other_artist.address
    assert art_piece.getArtist() == other_artist.address
    assert art_piece.getTokenURIData() == token_uri_data
    assert art_piece.getTitle() == title
    assert art_piece.getDescription() == description

def test_multiple_users_create_profiles_with_art(setup):
    """
    Test multiple users creating profiles with art pieces.
    """
    user = setup["user"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    other_artist = setup["other_artist"]
    profile_hub = setup["profile_hub"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Create profiles with art for multiple users
    users = [user, artist, commissioner, other_artist]
    titles = ["User Art", "Artist Portfolio", "Commissioner Request", "Other Artist Work"]
    
    for i, current_user in enumerate(users):
        # Skip if profile exists
        if profile_hub.hasProfile(current_user.address):
            continue
            
        # Create art data
        token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiVXNlciAxIEFydHdvcmsiLCJkZXNjcmlwdGlvbiI6IkFydHdvcmsgYnkgdXNlciAxIiwiaW1hZ2UiOiJkYXRhOmltYWdlL3BuZztiYXNlNjQsaVZCT1J3MEtHZ29BQUFBTlNVaEVVZ0FBQUFRQUFBQUVDQUlBQUFCQ05DdkRBQUFBQXhwSlJFRlVDTmRqL0E4REFBQU5BUDkvaFpZYUFBQUFBRWxGVGtTdVFtQ0MifQ=="
        title = titles[i]
        description = f"Description for {title}"  # Changed from byte string to regular string
        is_artist = True  # All users are artists of their own work in this test
        
        # Create profile and art
        profile_hub.createNewArtPieceAndRegisterProfile(
            art_piece_template.address,
            token_uri_data,
            "avif",
            title,
            description,
            is_artist,
            empty_address_value(),
            commission_hub.address,
            False,  # Not AI generated
            sender=current_user
        )
        
        # Verify profile created
        assert profile_hub.hasProfile(current_user.address) == True
        
        # Verify art piece created
        profile_address = profile_hub.getProfile(current_user.address)
        profile = project.Profile.at(profile_address)
        assert profile.myArtCount() == 1
        
        # Get and verify art piece
        latest_art = profile.getLatestArtPieces()
        assert len(latest_art) == 1
        
        art_piece = project.ArtPiece.at(latest_art[0])
        assert art_piece.getTitle() == title
        assert art_piece.getOwner() == current_user.address
        assert art_piece.getArtist() == current_user.address

def test_edge_case_max_size_art(setup):
    """
    Test uploading a large art piece close to the maximum size limit.
    """
    user = setup["user"]
    profile_hub = setup["profile_hub"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Skip if profile already exists
    if profile_hub.hasProfile(user.address):
        return
    
    # Create large size image data (but not at the absolute max to avoid gas issues)
    # 20,000 bytes is large enough to test the functionality
    # Use a long tokenURI format string for the test
    large_token_uri_data = b"data:application/json;base64," + b"A" * 20000
    title = "Large Size Art Test"
    description = "Testing with large image size"  # Changed from byte string to regular string
    is_artist = True
    
    # Create profile and large art piece
    profile_hub.createNewArtPieceAndRegisterProfile(
        art_piece_template.address,
        large_token_uri_data,
        "avif",
        title,
        description,
        is_artist,
        empty_address_value(),
        commission_hub.address,
        False,  # Not AI generated
        sender=user
    )
    
    # Verify profile created
    assert profile_hub.hasProfile(user.address) == True
    
    # Verify art piece created with large token URI
    profile_address = profile_hub.getProfile(user.address)
    profile = project.Profile.at(profile_address)
    
    art_pieces = profile.getLatestArtPieces()
    art_piece = project.ArtPiece.at(art_pieces[0])
    
    # Verify the token URI data was stored correctly
    token_uri = art_piece.getTokenURIData()
    assert len(token_uri) > 20000  # Base64 prefix + 20000 chars
    assert art_piece.getTitle() == title

def test_ai_generated_art_flag(setup):
    """
    Test creating AI generated art with the flag properly set.
    """
    user = setup["user"]
    profile_hub = setup["profile_hub"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Skip if profile already exists
    if profile_hub.hasProfile(user.address):
        return
    
    # Create AI art
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiQUkgR2VuZXJhdGVkIEFydCIsImRlc2NyaXB0aW9uIjoiVGhpcyB3YXMgY3JlYXRlZCB3aXRoIHRoZSBoZWxwIG9mIEFJIiwiaW1hZ2UiOiJkYXRhOmltYWdlL3BuZztiYXNlNjQsaVZCT1J3MEtHZ29BQUFBTlNVaEVVZ0FBQUFRQUFBQUVDQUlBQUFCQ05DdkRBQUFBQXhwSlJFRlVDTmRqL0E4REFBQU5BUDkvaFpZYUFBQUFBRWxGVGtTdVFtQ0MifQ=="
    # Parse base64 data for title and description
    base64_data = token_uri_data.replace(b"data:application/json;base64,", b"")
    json_data = json.loads(base64.b64decode(base64_data).decode("utf-8"))
    title = json_data["name"]
    description = json_data["description"]
    is_artist = True
    
    # Act - create profile and art piece with AI generated flag
    profile_hub.createNewArtPieceAndRegisterProfile(
        art_piece_template.address,
        token_uri_data,
        "avif",
        title,
        description,
        is_artist,
        empty_address_value(),
        commission_hub.address,
        True,  # AI generated
        sender=user
    )

def test_error_profile_exists_already(setup):
    """
    Test that an error is thrown when trying to create a profile that already exists.
    """
    user = setup["user"]
    profile_hub = setup["profile_hub"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # First, create a profile if one doesn't exist
    if not profile_hub.hasProfile(user.address):
        token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiSW5pdGlhbCBBcnQiLCJkZXNjcmlwdGlvbiI6IkZpcnN0IGFydCBwaWVjZSIsImltYWdlIjoiZGF0YTppbWFnZS9wbmc7YmFzZTY0LGlWQk9SdzBLR2dvQUFBQU5TVWhFVWdBQUFBUUFBQUFFQ0FJQUFBQENOQ3ZEQUFBQUF4cEpSRUZVQ05kai9BOERBQUFqQVA5L2c0dWFBQUFBQUVsRlRrU3VRbUNDIn0="
        # Parse base64 data for title and description
        base64_data = token_uri_data.replace(b"data:application/json;base64,", b"")
        json_data = json.loads(base64.b64decode(base64_data).decode("utf-8"))
        title = json_data["name"]
        description = json_data["description"]
        profile_hub.createNewArtPieceAndRegisterProfile(
            art_piece_template.address,
            token_uri_data,
            "avif",
            title,
            description,
            True,
            empty_address_value(),
            commission_hub.address,
            False,
            sender=user
        )
    
    # Try to create a profile and art piece when profile already exists
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiU2hvdWxkIEZhaWwiLCJkZXNjcmlwdGlvbiI6IlRoaXMgc2hvdWxkIGZhaWwgYmVjYXVzZSBwcm9maWxlIGV4aXN0cyIsImltYWdlIjoiZGF0YTppbWFnZS9wbmc7YmFzZTY0LGlWQk9SdzBLR2dvQUFBQU5TVWhFVWdBQUFBUUFBQUFFQ0FJQUFBQENOQ3ZEQUFBQUF4cEpSRUZVQ05kai9BOERBQUFqQVA5L2c0dWFBQUFBQUVsRlRrU3VRbUNDIn0="
    # Parse base64 data for title and description 
    base64_data = token_uri_data.replace(b"data:application/json;base64,", b"")
    json_data = json.loads(base64.b64decode(base64_data).decode("utf-8"))
    title = json_data["name"]
    description = json_data["description"]
    
    # Act & Assert - This should throw an exception
    with pytest.raises(Exception) as excinfo:
        profile_hub.createNewArtPieceAndRegisterProfile(
            art_piece_template.address,
            token_uri_data,
            "avif",
            title,
            description,
            True,
            empty_address_value(),
            commission_hub.address,
            False,
            sender=user
        )
    
    # Verify the error message
    assert "Profile already exists" in str(excinfo.value)

def empty_address_value():
    """Helper function to return empty address value for tests"""
    return "0x0000000000000000000000000000000000000000"

def test_special_characters_in_title_and_description(setup):
    """
    Test creating art with special characters in title and description.
    """
    # Create a temporary user for this test
    temp_user = accounts.test_accounts[6]
    profile_hub = setup["profile_hub"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Skip if profile already exists
    if profile_hub.hasProfile(temp_user.address):
        return
    
    # Create art data with special characters
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiU3BlY2lhbCBUaXRsZTogIUAjJCVeJiooKV8re318Ojw+P35gLT1bXVxcOycsLi9cIiIsImRlc2NyaXB0aW9uIjoiU3BlY2lhbCBEZXNjcmlwdGlvbjogIUAjJCVeJiooKV8re318Ojw+P35gLT1bXVxcOycsLi9cIiIsImltYWdlIjoiZGF0YTppbWFnZS9wbmc7YmFzZTY0LGlWQk9SdzBLR2dvQUFBQU5TVWhFVWdBQUFBUUFBQUFFQ0FJQUFBQENOQ3ZEQUFBQUF4cEpSRUZVQ05kai9BOERBQUFqQVA5L2c0dWFBQUFBQUVsRlRrU3VRbUNDIn0="
    title = "Special Title: !@#$%^&*()_+{}|:<>?~`-=[]\\;',./\""
    description = "Special Description: !@#$%^&*()_+{}|:<>?~`-=[]\\;',./\""
    
    # Act - create profile and art piece with special characters
    profile_hub.createNewArtPieceAndRegisterProfile(
        art_piece_template.address,
        token_uri_data,
        "avif",
        title,
        description,
        True,
        empty_address_value(),
        commission_hub.address,
        False,
        sender=temp_user
    )

def test_create_profile_with_empty_description(setup):
    """
    Test creating a profile with art piece that has an empty description.
    """
    # Create a temporary user for this test
    temp_user = accounts.test_accounts[7]
    profile_hub = setup["profile_hub"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Skip if profile already exists
    if profile_hub.hasProfile(temp_user.address):
        return
    
    # Create art data with empty description
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiVGl0bGUgV2l0aCBFbXB0eSBEZXNjcmlwdGlvbiIsImRlc2NyaXB0aW9uIjoiIiwiaW1hZ2UiOiJkYXRhOmltYWdlL3BuZztiYXNlNjQsaVZCT1J3MEtHZ29BQUFBTlNVaEVVZ0FBQUFRQUFBQUVDQUlBQUFCQ05DdkRBQUFBQXhwSlJFRlVDTmRqL0E4REFBQU5BUDkvaFpZYUFBQUFBRWxGVGtTdVFtQ0MifQ=="
    title = "Empty Description Test"
    description = ""  # Empty description as string instead of bytes
    
    # Act - create profile and art piece with empty description
    profile_hub.createNewArtPieceAndRegisterProfile(
        art_piece_template.address,
        token_uri_data,
        "avif",
        title,
        description,
        True,
        empty_address_value(),
        commission_hub.address,
        False,
        sender=temp_user
    )

def test_create_art_for_another_party(setup):
    """
    Test creating art for another party (commissioner or artist).
    """
    # Get a new test account
    commissioner = accounts.test_accounts[8]
    artist = accounts.test_accounts[9]
    profile_hub = setup["profile_hub"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Skip if profiles already exist
    if profile_hub.hasProfile(commissioner.address):
        return
    
    # Create art data for commission
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiQXJ0IGZvciBBbm90aGVyIFBhcnR5IiwiZGVzY3JpcHRpb24iOiJBcnQgcGllY2UgZGVkaWNhdGVkIHRvIGFub3RoZXIgdXNlciIsImltYWdlIjoiZGF0YTppbWFnZS9wbmc7YmFzZTY0LGlWQk9SdzBLR2dvQUFBQU5TVWhFVWdBQUFBUUFBQUFFQ0FJQUFBQENOQ3ZEQUFBQUF4cEpSRUZVQ05kai9BOERBQUFqQVA5L2c0dWFBQUFBQUVsRlRrU3VRbUNDIn0="
    # Parse base64 data for title and description
    base64_data = token_uri_data.replace(b"data:application/json;base64,", b"")
    json_data = json.loads(base64.b64decode(base64_data).decode("utf-8"))
    title = json_data["name"]
    description = json_data["description"]
    
    # Act - create profile and art piece for another party
    profile_hub.createNewArtPieceAndRegisterProfile(
        art_piece_template.address,
        token_uri_data,
        "avif",
        title,
        description,
        False,  # Not the artist
        artist.address,  # The other party is the artist
        commission_hub.address,
        False,
        sender=commissioner
    ) 