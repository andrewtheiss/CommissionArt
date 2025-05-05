import pytest
from ape import accounts, project

# Test data
TEST_TOKEN_URI_DATA = "data:application/json;base64,eyJuYW1lIjoiVGVzdCBBcnR3b3JrIiwiZGVzY3JpcHRpb24iOiJUaGlzIGlzIGEgdGVzdCBkZXNjcmlwdGlvbiBmb3IgdGhlIGFydHdvcmsiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFCM1JKVFVVSDVBb1NEdUZvQ0FBQUFBMUpSRUZVZU5xVEVFRUFBQUE1VVBBRHhpVXFJVzRBQUFBQlNVVk9SSzVDWUlJPSJ9"
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
    xtra1 = accounts.test_accounts[5]
    xtra2 = accounts.test_accounts[6]
    xtra3 = accounts.test_accounts[7]
    xtra4 = accounts.test_accounts[8]
    xtra5 = accounts.test_accounts[9]
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
        "artist_profile": artist_profile,
        "xtra1": xtra1,
        "xtra2": xtra2,
        "xtra3": xtra3,
        "xtra4": xtra4,
        "xtra5": xtra5
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
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiT3duZXIgQ29tbWlzc2lvbiIsImRlc2NyaXB0aW9uIjoiRGVzY3JpcHRpb24gZm9yIG93bmVyIGNvbW1pc3Npb24iLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFCM1JKVFVVSDVBb1ZGdDhzQVVJQUFBQU9TVVJCVkFqWFk4UUJBbUlBbklFQjVnQUFBQUJKUlU1RXJrSmdnZz09In0="
    token_uri_data_format = "avif"
    title = "Owner Commission"
    description = "Description for owner commission"
    
    # Initial art count
    initial_count = owner_profile.myArtCount()
    
    # Create art piece as a commissioner (not an artist)
    tx_receipt = owner_profile.createArtPiece(
        art_piece_template.address,
        token_uri_data,
        token_uri_data_format,
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
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiQXJ0aXN0IENyZWF0aW9uIiwiZGVzY3JpcHRpb24iOiJBcnR3b3JrIGNyZWF0ZWQgYnkgYW4gYXJ0aXN0IiwiaW1hZ2UiOiJkYXRhOmltYWdlL3BuZztiYXNlNjQsaVZCT1J3MEtHZ29BQUFBTlNVaEVVZ0FBQUFRQUFBQUVDQUlBQUFCQ05DdkRBQUFBQjNSSlRVVUg1QW9WRnQ5djhIRUFBQUFNU1VSQlZBalhZOFFCQWxvQWtXOEIzd0FBQUFCSLVVRK9Sa0pnZ2c9PSJ9"
    token_uri_data_format = "avif"
    title = "Artist Creation"
    description = "Artwork created by an artist"
    
    # Initial art count
    initial_count = artist_profile.myArtCount()
    
    # Create art piece as an artist
    tx_receipt = artist_profile.createArtPiece(
        art_piece_template.address,
        token_uri_data,
        token_uri_data_format,
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
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiQ29tbWlzc2lvbmVyIENyZWF0aW9uIiwiZGVzY3JpcHRpb24iOiJBcnQgY3JlYXRlZCBieSBjb21taXNzaW9uZXIiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFCM1JKVFVVSDVBb1ZGdDlOTFhFQUFBQVFTVVJCVkFqWFk4UUJBbFFBbjRrQzl3QUFBQUJKUlU1RXJrSmdnZz09In0="
    token_uri_data_format = "avif"
    title = "Commissioner Creation"
    description = "Art created by commissioner"
    
    tx_receipt = profile.createArtPiece(
        art_piece_template.address,
        token_uri_data,
        token_uri_data_format,
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
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiU2luZ2xlIEFydCBQaWVjZSIsImRlc2NyaXB0aW9uIjoiRGVzY3JpcHRpb24gZm9yIHNpbmdsZSBhcnQgcGllY2UiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFCM1JKVFVVSDVBb1ZGdDlQOVFFQUFBQUxTVVJCVkFqWFk4UUJBa3dBbUlRQjVnQUFBQUJKUlU1RXJrSmdnZz09In0="
    token_uri_data_format = "avif"
    title = "Single Art Piece"
    description = "Description for single art piece"
    
    # Create art piece
    tx_receipt = owner_profile.createArtPiece(
        art_piece_template.address,
        token_uri_data,
        token_uri_data_format,
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
    token_uri_data_templates = [
        b"data:application/json;base64,eyJuYW1lIjoiRmlyc3QgQXJ0IFBpZWNlIiwiZGVzY3JpcHRpb24iOiJEZXNjcmlwdGlvbiBmb3IgYXJ0IHBpZWNlIDEiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFCM1JKVFVVSDVBb1ZGdDlhUDJFQUFBQU1TVVJCVkFqWFk4UUJBbGdBb0lJQjVBQUFBQUJKUlU1RXJrSmdnZz09In0=",
        b"data:application/json;base64,eyJuYW1lIjoiU2Vjb25kIEFydCBQaWVjZSIsImRlc2NyaXB0aW9uIjoiRGVzY3JpcHRpb24gZm9yIGFydCBwaWVjZSAyIiwiaW1hZ2UiOiJkYXRhOmltYWdlL3BuZztiYXNlNjQsaVZCT1J3MEtHZ29BQUFBTlNVaEVVZ0FBQUFRQUFBQUVDQUlBQUFCQ05DdkRBQUFBQjNSSlRVVUg1QW9WRnQ5blFGc0FBQUFNU1VSQlZBalhZOFFCQW1BQW1vUUI2QUFBQUFCSlJVNUVya0pnZ2c9PSJ9",
        b"data:application/json;base64,eyJuYW1lIjoiVGhpcmQgQXJ0IFBpZWNlIiwiZGVzY3JpcHRpb24iOiJEZXNjcmlwdGlvbiBmb3IgYXJ0IHBpZWNlIDMiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFCM1JKVFVVSDVBb1ZGdDhTSnpNQUFBQU1TVVJCVkFqWFk4UUJBbmdBbm9jQ0FBQUFBQUJKUlU1RXJrSmdnZz09In0="
    ]
    token_uri_data_format = "avif"
    created_addresses = []
    
    for i, title in enumerate(art_titles):
        # Create art piece
        tx_receipt = owner_profile.createArtPiece(
            art_piece_template.address,
            token_uri_data_templates[i],
            token_uri_data_format,
            title,
            f"Description for art piece {i+1}",
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

def test_array_slice_functionality(setup):
    """Test the _getArraySlice functionality through liked profiles"""
    owner = setup["owner"]
    profile_hub = setup["profile_hub"]
    owner_profile = setup["owner_profile"]
    xtra1 = setup["xtra1"]
    xtra2 = setup["xtra2"]
    xtra3 = setup["xtra3"]
    xtra4 = setup["xtra4"]
    xtra5 = setup["xtra5"]
    
    # Create a limited set of profiles to test with
    test_accounts = [xtra1, xtra2, xtra3, xtra4, xtra5]
    artist = setup["artist"]  # Already has a profile
    
    profiles_to_like = []
    # First add the existing artist profile
    profiles_to_like.append(profile_hub.getProfile(artist.address))
    
    # Then add the test accounts' profiles
    for account in test_accounts:
        profile_hub.createProfile(sender=account)
        profile_address = profile_hub.getProfile(account.address)
        profiles_to_like.append(profile_address)
    
    # Like all the profiles
    for profile in profiles_to_like:
        owner_profile.addLikedProfile(profile, sender=owner)
    
    # Verify we have the expected number of liked profiles (6 total)
    assert owner_profile.likedProfileCount() == 6
    
    # Test page 0 with size 3 (should return first 3 profiles)
    page_0 = owner_profile.getLikedProfiles(0, 3)
    assert len(page_0) == 3
    for i in range(3):
        assert page_0[i] == profiles_to_like[i]
    
    # Test page 1 with size 3 (should return profiles 3-5)
    page_1 = owner_profile.getLikedProfiles(1, 3)
    assert len(page_1) == 3
    for i in range(3):
        assert page_1[i] == profiles_to_like[i + 3]
    
    # Test page 2 with size 3 (should return empty array - out of bounds)
    page_2 = owner_profile.getLikedProfiles(2, 3)
    assert len(page_2) == 0
    
    # Test with larger page size (should respect array bounds)
    large_page = owner_profile.getLikedProfiles(0, 10)
    assert len(large_page) == 6  # Only 6 items exist
    
    # Test with smaller page size
    small_pages_total = []
    for i in range(6):  # Get 6 pages of size 1
        page = owner_profile.getLikedProfiles(i, 1)
        small_pages_total.extend(page)
    
    assert len(small_pages_total) == 6  # Should have retrieved all 6 items
    
    # Test partial page
    partial_page = owner_profile.getLikedProfiles(1, 5)  # 6 total items, page 1 with size 5 should just return the 6th item
    assert len(partial_page) == 1
    assert partial_page[0] == profiles_to_like[5]

def test_array_slice_reverse_functionality(setup):
    """Test the _getArraySliceReverse functionality through liked profiles"""
    owner = setup["owner"]
    profile_hub = setup["profile_hub"]
    owner_profile = setup["owner_profile"]
    xtra1 = setup["xtra1"]
    xtra2 = setup["xtra2"]
    xtra3 = setup["xtra3"]
    xtra4 = setup["xtra4"]
    xtra5 = setup["xtra5"]
    
    # Use a subset of accounts for testing
    test_accounts = [xtra1, xtra2, xtra3, xtra4, xtra5]
    
    profiles_to_like = []
    for account in test_accounts:
        profile_hub.createProfile(sender=account)
        profile_address = profile_hub.getProfile(account.address)
        profiles_to_like.append(profile_address)
    
    # Like all the profiles
    for profile in profiles_to_like:
        owner_profile.addLikedProfile(profile, sender=owner)
    
    # Verify we have the expected number of liked profiles
    assert owner_profile.likedProfileCount() == 5
    
    # Test page 0 with size 2 (should return last 2 profiles in reverse)
    page_0 = owner_profile.getRecentLikedProfiles(0, 2)
    assert len(page_0) == 2
    assert page_0[0] == profiles_to_like[4]  # Most recent first
    assert page_0[1] == profiles_to_like[3]
    
    # Test page 1 with size 2 (should return profiles 2-1 in reverse)
    page_1 = owner_profile.getRecentLikedProfiles(1, 2)
    assert len(page_1) == 2
    assert page_1[0] == profiles_to_like[2]
    assert page_1[1] == profiles_to_like[1]
    
    # Test page 2 with size 2 (should return profile 0)
    page_2 = owner_profile.getRecentLikedProfiles(2, 2)
    assert len(page_2) == 1
    assert page_2[0] == profiles_to_like[0]
    
    # Test page 3 with size 2 (should return empty array - out of bounds)
    page_3 = owner_profile.getRecentLikedProfiles(3, 2)
    assert len(page_3) == 0
    
    # Test with larger page size (should respect array bounds and return in reverse)
    large_page = owner_profile.getRecentLikedProfiles(0, 10)
    assert len(large_page) == 5  # Only 5 items exist
    for i in range(5):
        assert large_page[i] == profiles_to_like[4 - i]  # Reverse order

def test_remove_from_array_functionality(setup):
    """Test the _removeFromArray functionality through liked profiles"""
    owner = setup["owner"]
    profile_hub = setup["profile_hub"]
    owner_profile = setup["owner_profile"]
    xtra1 = setup["xtra1"]
    xtra2 = setup["xtra2"]
    xtra3 = setup["xtra3"]
    
    # Use a smaller subset
    test_accounts = [xtra1, xtra2, xtra3]
    
    # Create profiles to like
    profiles_to_like = []
    for account in test_accounts:
        profile_hub.createProfile(sender=account)
        profile_address = profile_hub.getProfile(account.address)
        profiles_to_like.append(profile_address)
    
    # Like all the profiles
    for profile in profiles_to_like:
        owner_profile.addLikedProfile(profile, sender=owner)
    
    # Verify we have the expected number of liked profiles
    assert owner_profile.likedProfileCount() == 3
    
    # Get initial profiles array
    initial_profiles = owner_profile.getLikedProfiles(0, 10)
    assert len(initial_profiles) == 3
    
    # 1. Remove an item and verify count decreased
    first_item = profiles_to_like[0]
    owner_profile.removeLikedProfile(first_item, sender=owner)
    assert owner_profile.likedProfileCount() == 2
    
    # Get the updated array
    remaining_profiles = owner_profile.getLikedProfiles(0, 10)
    assert len(remaining_profiles) == 2
    
    # Count occurrences of the removed item (should be 0)
    removed_item_count = sum(1 for profile in remaining_profiles if profile == first_item)
    assert removed_item_count == 0, f"Removed item {first_item} still found in the array"
    
    # 2. Remove another item and verify count decreased again
    second_item = profiles_to_like[1]
    owner_profile.removeLikedProfile(second_item, sender=owner)
    assert owner_profile.likedProfileCount() == 1
    
    # Get the updated array
    remaining_profiles = owner_profile.getLikedProfiles(0, 10)
    assert len(remaining_profiles) == 1
    assert remaining_profiles[0] == profiles_to_like[2], "Only the third item should remain"
    
    # 3. Remove the last item and verify array is empty
    last_item = profiles_to_like[2]
    owner_profile.removeLikedProfile(last_item, sender=owner)
    assert owner_profile.likedProfileCount() == 0
    
    # Check that the array is now empty
    final_profiles = owner_profile.getLikedProfiles(0, 10)
    assert len(final_profiles) == 0
    
    # 4. Try to remove an item that doesn't exist (should revert)
    non_existent_profile = "0x0000000000000000000000000000000000001234"
    with pytest.raises(Exception):
        owner_profile.removeLikedProfile(non_existent_profile, sender=owner)

def test_complex_array_operations(setup):
    """Test a combination of array operations in sequence"""
    owner = setup["owner"]
    profile_hub = setup["profile_hub"]
    owner_profile = setup["owner_profile"]
    xtra1 = setup["xtra1"]
    xtra2 = setup["xtra2"]
    xtra3 = setup["xtra3"]
    xtra4 = setup["xtra4"]
    xtra5 = setup["xtra5"]
    
    # Start with a clean state - remove any existing liked profiles
    existing_profiles = owner_profile.getLikedProfiles(0, 20)
    for profile in existing_profiles:
        try:
            owner_profile.removeLikedProfile(profile, sender=owner)
        except:
            pass
    
    # Verify clean state
    assert owner_profile.likedProfileCount() == 0
    
    # Use available accounts
    test_accounts = [xtra1, xtra2, xtra3, xtra4, xtra5]
    
    # Create profiles
    profiles = []
    for account in test_accounts:
        profile_hub.createProfile(sender=account)
        profile_address = profile_hub.getProfile(account.address)
        profiles.append(profile_address)
    
    # Phase 1: Add first 3 profiles
    for i in range(3):
        owner_profile.addLikedProfile(profiles[i], sender=owner)
    
    # Verify count and content
    assert owner_profile.likedProfileCount() == 3
    page = owner_profile.getLikedProfiles(0, 10)
    assert len(page) == 3
    recent = owner_profile.getRecentLikedProfiles(0, 10)
    assert len(recent) == 3
    
    # Most recent should be the last one added
    assert recent[0] == profiles[2]
    
    # Phase 2: Remove middle profile
    owner_profile.removeLikedProfile(profiles[1], sender=owner)
    
    # Get updated state
    page = owner_profile.getLikedProfiles(0, 10)
    
    # Verify count
    assert owner_profile.likedProfileCount() == 2, f"Expected 2 profiles, got {owner_profile.likedProfileCount()}"
    assert len(page) == 2, f"Expected 2 profiles, got {len(page)}"
    
    # Verify correct items remain
    remaining_profiles = set(page)
    expected_remaining = {profiles[0], profiles[2]}
    assert remaining_profiles == expected_remaining, f"Remaining profiles {remaining_profiles} don't match expected {expected_remaining}"
    
    # Phase 3: Add 2 more profiles
    for i in range(3, 5):
        owner_profile.addLikedProfile(profiles[i], sender=owner)
    
    # Verify count and content
    assert owner_profile.likedProfileCount() == 4
    page = owner_profile.getLikedProfiles(0, 10)
    assert len(page) == 4
    
    # Phase 4: Test reverse ordering - most recent first
    recent = owner_profile.getRecentLikedProfiles(0, 10)
    assert len(recent) == 4
    
    # Check the first 2 items match the most recently added
    assert recent[0] == profiles[4], f"Expected most recent to be profiles[4], got {recent[0]}"
    assert recent[1] == profiles[3], f"Expected second most recent to be profiles[3], got {recent[1]}"
    
    # Phase 5: Test pagination
    recent_0 = owner_profile.getRecentLikedProfiles(0, 2)
    recent_1 = owner_profile.getRecentLikedProfiles(1, 2)
    
    assert len(recent_0) == 2
    assert len(recent_1) == 2
    
    # Most recent 2 items should be profiles[4] and profiles[3]
    assert recent_0[0] == profiles[4]
    assert recent_0[1] == profiles[3]
    
    # Next 2 items should be the remaining profiles
    # We can't guarantee the exact order because of the swap-to-remove algorithm
    # Just verify they're in the list
    assert recent_1[0] in [profiles[0], profiles[2]]
    assert recent_1[1] in [profiles[0], profiles[2]]
    assert recent_1[0] != recent_1[1]  # Make sure they're different 