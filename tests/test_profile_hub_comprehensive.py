import pytest
from ape import accounts, project
import time

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
    
    # Deploy CommissionHub for art piece registration
    commission_hub = project.CommissionHub.deploy(sender=deployer)
    
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
    image_data = b"user's first art piece" * 100  # Larger test case
    title = "My First Artwork"
    description = b"This is my first ever uploaded art piece"
    is_artist = True  # User is the artist of their own work
    
    # Act - Create profile and art piece in one transaction
    result = profile_hub.createNewArtPieceAndRegisterProfile(
        art_piece_template.address,
        image_data,
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
    assert art_piece.getImageData() == image_data
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
    image_data = b"commission placeholder" * 50
    title = "Art Commission Request"
    description = b"I'd like to commission a fantasy landscape"
    is_artist = False  # Commissioner is not the artist
    
    # Create profile and commission in one transaction
    result = profile_hub.createNewArtPieceAndRegisterProfile(
        art_piece_template.address,
        image_data,
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
    assert art_piece.getImageData() == image_data
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
    image_data = b"artist portfolio art" * 75
    title = "Portfolio Showcase Piece"
    description = b"My best work to demonstrate my skills"
    is_artist = True  # Artist is the creator
    
    # Create profile and portfolio piece in one transaction
    result = profile_hub.createNewArtPieceAndRegisterProfile(
        art_piece_template.address,
        image_data,
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
    assert art_piece.getImageData() == image_data
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
        image_data = f"test art for user {i}".encode() * 40
        title = titles[i]
        description = f"Description for {title}".encode()
        is_artist = True  # All users are artists of their own work in this test
        
        # Create profile and art
        profile_hub.createNewArtPieceAndRegisterProfile(
            art_piece_template.address,
            image_data,
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
    Test creating a profile with large size art data.
    """
    user = setup["user"]
    profile_hub = setup["profile_hub"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Skip if user already has a profile
    if profile_hub.hasProfile(user.address):
        # Create a different user for testing
        temp_user = accounts.test_accounts[5]
        assert profile_hub.hasProfile(temp_user.address) == False
        user = temp_user
    
    # Create large size image data (but not at the absolute max to avoid gas issues)
    # 20,000 bytes is large enough to test the functionality
    large_image_data = b"X" * 20000
    title = "Large Size Art Test"
    description = b"Testing with large image size"
    
    # Create profile and art
    profile_hub.createNewArtPieceAndRegisterProfile(
        art_piece_template.address,
        large_image_data,
        title,
        description,
        True,  # Is artist
        empty_address_value(),
        commission_hub.address,
        False,
        sender=user
    )
    
    # Verify profile and art created
    assert profile_hub.hasProfile(user.address) == True
    
    profile_address = profile_hub.getProfile(user.address)
    profile = project.Profile.at(profile_address)
    
    assert profile.myArtCount() == 1
    
    # Verify art piece with large data
    art_pieces = profile.getLatestArtPieces()
    art_piece = project.ArtPiece.at(art_pieces[0])
    
    assert len(art_piece.getImageData()) == 20000
    assert art_piece.getTitle() == title

def test_ai_generated_art_flag(setup):
    """
    Test creating a profile with AI-generated art.
    """
    # Use a new account for this test
    ai_artist = accounts.test_accounts[6]
    profile_hub = setup["profile_hub"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Verify user doesn't have a profile
    assert profile_hub.hasProfile(ai_artist.address) == False
    
    # Create AI art
    image_data = b"AI generated artwork" * 50
    title = "AI Masterpiece"
    description = b"This was created using an AI art generator"
    
    # Create profile with AI art
    profile_hub.createNewArtPieceAndRegisterProfile(
        art_piece_template.address,
        image_data,
        title,
        description,
        True,  # Is artist
        empty_address_value(),
        commission_hub.address,
        True,  # AI generated flag set to true
        sender=ai_artist
    )
    
    # Verify profile created
    assert profile_hub.hasProfile(ai_artist.address) == True
    
    # Verify AI flag set correctly
    profile_address = profile_hub.getProfile(ai_artist.address)
    profile = project.Profile.at(profile_address)
    
    art_pieces = profile.getLatestArtPieces()
    art_piece = project.ArtPiece.at(art_pieces[0])
    
    assert art_piece.getAIGenerated() == True

def test_error_profile_exists_already(setup):
    """
    Test the error case when trying to create a profile and art piece
    when the profile already exists.
    """
    artist = setup["artist"]
    profile_hub = setup["profile_hub"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Create a profile first
    if not profile_hub.hasProfile(artist.address):
        profile_hub.createProfile(sender=artist)
    
    # Verify profile exists
    assert profile_hub.hasProfile(artist.address) == True
    
    # Try to create a profile and art piece when profile already exists
    image_data = b"art data" * 20
    title = "Should Fail"
    description = b"This should fail because profile exists"
    
    # This should fail with "Profile already exists"
    with pytest.raises(Exception) as excinfo:
        profile_hub.createNewArtPieceAndRegisterProfile(
            art_piece_template.address,
            image_data,
            title,
            description,
            True,
            empty_address_value(),
            commission_hub.address,
            False,
            sender=artist
        )
    
    # Verify the error message contains "Profile already exists"
    assert "Profile already exists" in str(excinfo.value)

def empty_address_value():
    """Helper function to return the zero address"""
    return "0x" + "0" * 40

def test_special_characters_in_title_and_description(setup):
    """
    Test creating a profile and art piece with special characters
    in title and description.
    """
    # Use a different account to avoid profile already exists errors
    special_user = accounts.test_accounts[7]
    profile_hub = setup["profile_hub"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Verify user doesn't have a profile
    assert profile_hub.hasProfile(special_user.address) == False
    
    # Create art data with special characters
    image_data = b"special characters test" * 25
    title = "Special Chars: !@#$%^&*()-+=[]{}|;:',.<>/?`~"
    description = b"Testing with \x01\x02 binary data and Unicode \xe2\x9c\x85 \xe2\x9c\xa8 characters"
    
    # Create profile and art with special characters
    profile_hub.createNewArtPieceAndRegisterProfile(
        art_piece_template.address,
        image_data,
        title,
        description,
        True,  # Is artist
        empty_address_value(),
        commission_hub.address,
        False,
        sender=special_user
    )
    
    # Verify profile created
    assert profile_hub.hasProfile(special_user.address) == True
    
    # Verify art piece with special characters
    profile_address = profile_hub.getProfile(special_user.address)
    profile = project.Profile.at(profile_address)
    
    art_pieces = profile.getLatestArtPieces()
    art_piece = project.ArtPiece.at(art_pieces[0])
    
    assert art_piece.getTitle() == title
    assert art_piece.getDescription() == description

def test_create_profile_with_empty_description(setup):
    """
    Test creating a profile and art piece with empty description.
    """
    # Use a different account
    empty_desc_user = accounts.test_accounts[8]
    profile_hub = setup["profile_hub"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Verify user doesn't have a profile
    assert profile_hub.hasProfile(empty_desc_user.address) == False
    
    # Create art data with empty description
    image_data = b"empty description test" * 25
    title = "Empty Description Test"
    description = b""  # Empty description
    
    # Create profile and art with empty description
    profile_hub.createNewArtPieceAndRegisterProfile(
        art_piece_template.address,
        image_data,
        title,
        description,
        True,  # Is artist
        empty_address_value(),
        commission_hub.address,
        False,
        sender=empty_desc_user
    )
    
    # Verify profile created
    assert profile_hub.hasProfile(empty_desc_user.address) == True
    
    # Verify art piece with empty description
    profile_address = profile_hub.getProfile(empty_desc_user.address)
    profile = project.Profile.at(profile_address)
    
    art_pieces = profile.getLatestArtPieces()
    art_piece = project.ArtPiece.at(art_pieces[0])
    
    assert art_piece.getTitle() == title
    assert art_piece.getDescription() == description
    assert len(art_piece.getDescription()) == 0

def test_create_art_for_another_party(setup):
    """
    Test creating a profile and art piece where another party is specified.
    This tests the commission case where the artist creates art for someone else.
    """
    # Use different accounts
    artist_user = accounts.test_accounts[9]
    other_party = accounts.test_accounts[1]  # Use an existing account as the other party
    profile_hub = setup["profile_hub"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Skip if artist already has a profile
    if profile_hub.hasProfile(artist_user.address):
        return
    
    # Create art data for commission
    image_data = b"commission for other party" * 25
    title = "Commission For Other Party"
    description = b"This art piece is created for another user"
    
    # Create profile and art with other party specified
    profile_hub.createNewArtPieceAndRegisterProfile(
        art_piece_template.address,
        image_data,
        title,
        description,
        True,  # Artist is creating
        other_party.address,  # Other party will be the owner
        commission_hub.address,
        False,
        sender=artist_user
    )
    
    # Verify profile created for artist
    assert profile_hub.hasProfile(artist_user.address) == True
    
    # Verify art piece ownership and attributes
    profile_address = profile_hub.getProfile(artist_user.address)
    profile = project.Profile.at(profile_address)
    
    art_pieces = profile.getLatestArtPieces()
    art_piece = project.ArtPiece.at(art_pieces[0])
    
    assert art_piece.getTitle() == title
    assert art_piece.getArtist() == artist_user.address  # Artist created it
    assert art_piece.getOwner() == other_party.address  # But other party owns it 