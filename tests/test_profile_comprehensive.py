import pytest
from ape import accounts, project
import time

@pytest.fixture
def setup():
    """Setup test environment with deployed contracts and user accounts"""
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    user = accounts.test_accounts[1]
    artist = accounts.test_accounts[2]
    commissioner = accounts.test_accounts[3]
    other_user = accounts.test_accounts[4]
    
    # Deploy Profile template
    profile_template = project.Profile.deploy(sender=deployer)
    
    # Deploy ProfileHub with the template
    profile_hub = project.ProfileHub.deploy(profile_template.address, sender=deployer)
    
    # Deploy ArtPiece template for art piece creation
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy ArtCommissionHub for art piece registration
    commission_hub = project.ArtCommissionHub.deploy(sender=deployer)
    
    return {
        "deployer": deployer,
        "user": user,
        "artist": artist,
        "commissioner": commissioner,
        "other_user": other_user,
        "profile_template": profile_template,
        "profile_hub": profile_hub,
        "art_piece_template": art_piece_template,
        "commission_hub": commission_hub
    }

def test_profile_creation(setup):
    """Test creating a profile through the profile hub"""
    profile_hub = setup["profile_hub"]
    user = setup["user"]
    
    # Create a profile for the user
    tx = profile_hub.createProfile(sender=user)
    
    # Verify profile was created
    assert profile_hub.hasProfile(user.address) is True
    profile_address = profile_hub.getProfile(user.address)
    assert profile_address != "0x0000000000000000000000000000000000000000"
    
    # Verify profile initialization
    profile = project.Profile.at(profile_address)
    assert profile.owner() == user.address
    assert profile.isArtist() is False
    assert profile.myArtCount() == 0
    assert profile.allowUnverifiedCommissions() is True

def test_create_and_update_artist_profile(setup):
    """Test creating an artist profile and updating its settings""" 
    profile_hub = setup["profile_hub"]
    artist = setup["artist"]
    other_user = setup["other_user"]
    
    # Create a profile for the artist
    profile_hub.createProfile(sender=artist)
    profile_address = profile_hub.getProfile(artist.address)
    profile = project.Profile.at(profile_address)
    
    # Initial profile state
    assert profile.isArtist() is False
    assert profile.artistProceedsAddress() == artist.address
    
    # Update artist status
    profile.setIsArtist(True, sender=artist)
    assert profile.isArtist() is True
    
    # Set profile image (using address instead of string data)
    profile_image_address = "0x1111111111111111111111111111111111111111"
    profile.setProfileImage(profile_image_address, sender=artist)
    assert profile.profileImage() == profile_image_address
    
    # Set proceeds address 
    profile.setProceedsAddress(other_user.address, sender=artist)
    assert profile.artistProceedsAddress() == other_user.address
    
    # Disable unverified commissions
    profile.setAllowUnverifiedCommissions(False, sender=artist)
    assert profile.allowUnverifiedCommissions() is False
    
    # Add to whitelist and blacklist
    profile.addToWhitelist(other_user.address, sender=artist)
    assert profile.whitelist(other_user.address) is True
    
    profile.addToBlacklist(setup["commissioner"].address, sender=artist)
    assert profile.blacklist(setup["commissioner"].address) is True
    
    # Remove from whitelist and blacklist
    profile.removeFromWhitelist(other_user.address, sender=artist)
    assert profile.whitelist(other_user.address) is False
    
    profile.removeFromBlacklist(setup["commissioner"].address, sender=artist)
    assert profile.blacklist(setup["commissioner"].address) is False

def test_profile_permission_restrictions(setup):
    """Test that profile functions have proper permission restrictions"""
    profile_hub = setup["profile_hub"]
    user = setup["user"]
    other_user = setup["other_user"]
    
    # Create a profile for the user
    profile_hub.createProfile(sender=user)
    profile_address = profile_hub.getProfile(user.address)
    profile = project.Profile.at(profile_address)
    
    # Attempt operations with non-owner account
    with pytest.raises(Exception) as excinfo:
        profile.setIsArtist(True, sender=other_user)
    assert "Only owner" in str(excinfo.value)
    
    with pytest.raises(Exception) as excinfo:
        profile.setProfileImage("0x1111111111111111111111111111111111111111", sender=other_user)
    assert "Only owner" in str(excinfo.value)
    
    with pytest.raises(Exception) as excinfo:
        profile.setAllowUnverifiedCommissions(False, sender=other_user)
    assert "Only owner" in str(excinfo.value)
    
    with pytest.raises(Exception) as excinfo:
        profile.addToWhitelist(other_user.address, sender=other_user)
    assert "Only owner" in str(excinfo.value)
    
    with pytest.raises(Exception) as excinfo:
        profile.removeFromWhitelist(other_user.address, sender=other_user)
    assert "Only owner" in str(excinfo.value)

def test_profile_social_features(setup):
    """Test profile social features like liking and linking other profiles"""
    profile_hub = setup["profile_hub"]
    user = setup["user"]
    other_user = setup["other_user"]
    artist = setup["artist"]
    
    # Create profiles
    profile_hub.createProfile(sender=user)
    profile_hub.createProfile(sender=other_user)
    profile_hub.createProfile(sender=artist)
    
    user_profile = project.Profile.at(profile_hub.getProfile(user.address))
    other_profile_address = profile_hub.getProfile(other_user.address)
    artist_profile_address = profile_hub.getProfile(artist.address)
    
    # Like other profiles
    user_profile.addLikedProfile(other_profile_address, sender=user)
    user_profile.addLikedProfile(artist_profile_address, sender=user)
    
    # Check liked profiles
    assert user_profile.likedProfileCount() == 2
    liked_profiles = user_profile.getLikedProfiles(0, 10)
    
    # Check if the addresses are in the liked profiles list
    # Convert the addresses to strings for comparison
    liked_profiles_str = [str(addr) for addr in liked_profiles]
    assert str(other_profile_address) in liked_profiles_str
    assert str(artist_profile_address) in liked_profiles_str
    
    # Link profiles
    user_profile.linkProfile(other_profile_address, sender=user)
    assert user_profile.linkedProfileCount() == 1
    linked_profiles = user_profile.getLinkedProfiles(0, 10)
    linked_profiles_str = [str(addr) for addr in linked_profiles]
    assert str(other_profile_address) in linked_profiles_str
    
    # Remove linked profile
    user_profile.removeLinkedProfile(other_profile_address, sender=user)
    assert user_profile.linkedProfileCount() == 0
    
    # Remove liked profile
    user_profile.removeLikedProfile(other_profile_address, sender=user)
    assert user_profile.likedProfileCount() == 1
    liked_profiles = user_profile.getLikedProfiles(0, 10)
    liked_profiles_str = [str(addr) for addr in liked_profiles]
    assert str(other_profile_address) not in liked_profiles_str
    assert str(artist_profile_address) in liked_profiles_str

def test_create_art_piece_on_profile(setup):
    """Test creating an art piece through a profile"""
    profile_hub = setup["profile_hub"]
    user = setup["user"]
    artist = setup["artist"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Create a profile for the user
    profile_hub.createProfile(sender=user)
    profile_address = profile_hub.getProfile(user.address)
    profile = project.Profile.at(profile_address)
    
    # Test data for art piece
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiVGVzdCBBcnR3b3JrIiwiZGVzY3JpcHRpb24iOiJUaGlzIGlzIGEgdGVzdCBkZXNjcmlwdGlvbiBmb3IgdGhlIGFydHdvcmsiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFBM3BKUkVGVUNOZGovQThEQUFBTkFQOS9oWllhQUFBQUFFbEZUa1N1UW1DQyJ9"
    title = "My First Artwork"
    description = "This is a description of my artwork"
    
    # Create art piece as a commissioner (not an artist)
    # Store the transaction result
    transaction = profile.createArtPiece(
        art_piece_template.address,
        token_uri_data,
        "avif",
        title,
        description,
        False,  # Not as artist
        artist.address,  # Artist address
        commission_hub.address,
        False,  # Not AI generated
        sender=user
    )
    
    # Verify art piece was created
    assert profile.myArtCount() == 1
    
    # Get the art piece using multiple methods for redundancy
    # Method 1: From getLatestArtPieces
    latest_art_pieces = profile.getLatestArtPieces()
    assert len(latest_art_pieces) > 0
    
    # Method 2: From getArtPieces(0, 10) - paginated
    all_art_pieces = profile.getArtPieces(0, 10)
    assert len(all_art_pieces) > 0
    
    # Method 3: Using direct index
    first_art_piece_address = profile.getArtPieceAtIndex(0)
    
    # Verify all methods return the same art piece
    assert first_art_piece_address == latest_art_pieces[0]
    assert first_art_piece_address == all_art_pieces[0]
    
    # Access the art piece
    art_piece = project.ArtPiece.at(first_art_piece_address)
    
    # Verify art piece properties
    assert art_piece.getTitle() == title
    assert art_piece.getTokenURIData() == token_uri_data
    assert art_piece.getDescription() == description
    assert art_piece.getOwner() == user.address  # User is owner
    assert art_piece.getArtist() == artist.address  # Artist as specified
    assert art_piece.getAIGenerated() is False

def test_create_art_piece_as_artist(setup):
    """Test creating an art piece as an artist through a profile"""
    profile_hub = setup["profile_hub"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Create a profile for the artist
    profile_hub.createProfile(sender=artist)
    profile_address = profile_hub.getProfile(artist.address)
    profile = project.Profile.at(profile_address)
    
    # Set as artist
    profile.setIsArtist(True, sender=artist)
    
    # Test data for art piece
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiVGVzdCBBcnR3b3JrIiwiZGVzY3JpcHRpb24iOiJUaGlzIGlzIGEgdGVzdCBkZXNjcmlwdGlvbiBmb3IgdGhlIGFydHdvcmsiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFBM3BKUkVGVUNOZGovQThEQUFBTkFQOS9oWllhQUFBQUFFbEZUa1N1UW1DQyJ9"
    title = "Artist Creation"
    description = "Artwork created by an artist"
    
    # Create art piece as an artist
    transaction = profile.createArtPiece(
        art_piece_template.address,
        token_uri_data,
        "avif",
        title,
        description,
        True,  # As artist
        commissioner.address,  # Commissioner address
        commission_hub.address,
        True,  # AI generated
        sender=artist
    )
    
    # Verify art piece was created
    assert profile.myArtCount() == 1
    
    # Get the art piece by index
    first_art_piece_address = profile.getArtPieceAtIndex(0)
    assert first_art_piece_address != "0x0000000000000000000000000000000000000000"
    
    # Also get the art piece from getLatestArtPieces to verify consistency
    latest_pieces = profile.getLatestArtPieces()
    assert len(latest_pieces) == 1
    assert latest_pieces[0] == first_art_piece_address
    
    # Load the art piece
    art_piece = project.ArtPiece.at(first_art_piece_address)
    
    # Verify art piece properties - note the ownership differences for artist creation
    assert art_piece.getTitle() == title
    assert art_piece.getTokenURIData() == token_uri_data
    assert art_piece.getDescription() == description
    assert art_piece.getOwner() == commissioner.address  # Commissioner is owner
    assert art_piece.getArtist() == artist.address       # Artist is creator
    assert art_piece.getAIGenerated() is True

def test_add_existing_art_piece_to_profile(setup):
    """Test adding an existing art piece to a profile"""
    profile_hub = setup["profile_hub"]
    user = setup["user"]
    artist = setup["artist"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Create profiles
    profile_hub.createProfile(sender=user)
    profile_hub.createProfile(sender=artist)
    
    user_profile = project.Profile.at(profile_hub.getProfile(user.address))
    artist_profile = project.Profile.at(profile_hub.getProfile(artist.address))
    
    # Set artist status
    artist_profile.setIsArtist(True, sender=artist)
    
    # Create an art piece through the user profile
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiVGVzdCBDb21taXNzaW9uIiwiZGVzY3JpcHRpb24iOiJUZXN0IGNvbW1pc3Npb24gZGVzY3JpcHRpb24iLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFBM3BKUkVGVUNOZGovQThEQUFBTkFQOS9oWllhQUFBQUFFbEZUa1N1UW1DQyJ9"
    title = "Shared Artwork"
    description = "Artwork shared across profiles"
    
    # Create art piece through the user's profile
    transaction = user_profile.createArtPiece(
        art_piece_template.address,
        token_uri_data,
        "avif",
        title,
        description,
        False,  # Not as artist
        artist.address,
        commission_hub.address,
        False,
        sender=user
    )
    
    # Verify art piece was created
    assert user_profile.myArtCount() == 1
    
    # Get the art piece address directly
    art_piece_address = user_profile.getArtPieceAtIndex(0)
    
    # Verify the art piece properties
    user_art_piece = project.ArtPiece.at(art_piece_address)
    assert user_art_piece.getTitle() == title
    assert user_art_piece.getTokenURIData() == token_uri_data
    assert user_art_piece.getDescription() == description
    
    # Artist adds the same art piece to their profile
    artist_profile.addArtPiece(art_piece_address, sender=artist)
    
    # Verify both profiles have the art piece
    assert user_profile.myArtCount() == 1
    assert artist_profile.myArtCount() == 1
    
    # Get art piece from both profiles
    user_art_piece_address = user_profile.getArtPieceAtIndex(0)
    artist_art_piece_address = artist_profile.getArtPieceAtIndex(0)
    
    # Verify they're the same art piece
    assert user_art_piece_address == artist_art_piece_address
    assert user_art_piece_address == art_piece_address

def test_remove_art_piece_from_profile(setup):
    """Test removing an art piece from a profile"""
    profile_hub = setup["profile_hub"]
    user = setup["user"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Create a profile
    profile_hub.createProfile(sender=user)
    profile = project.Profile.at(profile_hub.getProfile(user.address))
    
    # Create first art piece
    first_image = b"data:application/json;base64,eyJuYW1lIjoiVGVzdCBDb21taXNzaW9uIiwiZGVzY3JpcHRpb24iOiJUZXN0IGNvbW1pc3Npb24gZGVzY3JpcHRpb24iLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFBM3BKUkVGVUNOZGovQThEQUFBTkFQOS9oWllhQUFBQUFFbEZUa1N1UW1DQyJ9"
    first_title = "First Art"
    profile.createArtPiece(
        art_piece_template.address,
        first_image,
        "avif",
        first_title,
        "First art description",
        False,
        setup["artist"].address,
        commission_hub.address,
        False,
        sender=user
    )
    
    # Create second art piece
    second_image = b"data:application/json;base64,eyJuYW1lIjoiVGVzdCBDb21taXNzaW9uIiwiZGVzY3JpcHRpb24iOiJUZXN0IGNvbW1pc3Npb24gZGVzY3JpcHRpb24iLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFBM3BKUkVGVUNOZGovQThEQUFBTkFQOS9oWllhQUFBQUFFbEZUa1N1UW1DQyJ9"
    second_title = "Second Art"
    profile.createArtPiece(
        art_piece_template.address,
        second_image,
        "avif",
        second_title,
        "Second art description",
        False,
        setup["artist"].address,
        commission_hub.address,
        False,
        sender=user
    )
    
    # Verify both art pieces were created
    assert profile.myArtCount() == 2
    
    # Get the art piece addresses
    art_piece1_addr = profile.getArtPieceAtIndex(0)
    art_piece2_addr = profile.getArtPieceAtIndex(1)
    
    # Verify they're different art pieces
    assert art_piece1_addr != art_piece2_addr
    
    # Load the art pieces and verify their properties
    art_piece1 = project.ArtPiece.at(art_piece1_addr)
    art_piece2 = project.ArtPiece.at(art_piece2_addr)
    
    # Verify the art piece properties
    assert art_piece1.getTitle() == first_title
    assert art_piece2.getTitle() == second_title
    
    # Remove the first art piece
    profile.removeArtPiece(art_piece1_addr, sender=user)
    
    # Verify it was removed
    assert profile.myArtCount() == 1
    
    # The remaining art piece should be the second one
    remaining_art_piece_addr = profile.getArtPieceAtIndex(0)
    assert remaining_art_piece_addr == art_piece2_addr
    assert remaining_art_piece_addr != art_piece1_addr

def test_profile_hub_combined_creation(setup):
    """Test creating a profile and art piece in a workflow similar to the combined creation method"""
    profile_hub = setup["profile_hub"]
    user = setup["user"]
    artist = setup["artist"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Initially user has no profile
    assert profile_hub.hasProfile(user.address) is False
    
    # First create a profile
    profile_hub.createProfile(sender=user)
    profile_address = profile_hub.getProfile(user.address)
    profile = project.Profile.at(profile_address)
    
    # Verify profile was created
    assert profile_hub.hasProfile(user.address) is True
    
    # Define art piece data
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiVGVzdCBDb21taXNzaW9uIiwiZGVzY3JpcHRpb24iOiJUZXN0IGNvbW1pc3Npb24gZGVzY3JpcHRpb24iLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFBM3BKUkVGVUNOZGovQThEQUFBTkFQOS9oWllhQUFBQUFFbEZUa1N1UW1DQyJ9"
    title = "Combined Creation"
    description = "Created in a workflow"
    
    # Create an art piece on the profile
    profile.createArtPiece(
        art_piece_template.address,
        token_uri_data,
        "avif",
        title,
        description,
        False,  # Not as artist
        artist.address,  # Artist address
        commission_hub.address,
        False,  # Not AI generated
        sender=user
    )
    
    # Verify art piece was created
    assert profile.myArtCount() == 1
    
    # Get and verify the art piece
    art_piece_addr = profile.getArtPieceAtIndex(0)
    assert art_piece_addr != "0x0000000000000000000000000000000000000000"
    
    # Load and verify the art piece
    art_piece = project.ArtPiece.at(art_piece_addr)
    assert art_piece.getTitle() == title
    assert art_piece.getTokenURIData() == token_uri_data
    assert art_piece.getDescription() == description
    assert art_piece.getOwner() == user.address
    assert art_piece.getArtist() == artist.address 