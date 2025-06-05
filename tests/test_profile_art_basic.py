import pytest
from ape import accounts, project

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
    artist = accounts.test_accounts[1]
    owner = accounts.test_accounts[2]
    tagged_person = accounts.test_accounts[3]
    commissioner = accounts.test_accounts[4]
    xtra1 = accounts.test_accounts[5]
    xtra2 = accounts.test_accounts[6]
    xtra3 = accounts.test_accounts[7]
    xtra4 = accounts.test_accounts[8]
    xtra5 = accounts.test_accounts[9]
    
    # Deploy all templates
    profile_template = project.Profile.deploy(sender=deployer)
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)

    # Deploy ArtEdition1155 template
    art_edition_1155_template = project.ArtEdition1155.deploy(sender=deployer)
    
    # Deploy ArtSales1155 template
    art_sales_1155_template = project.ArtSales1155.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy ProfileFactoryAndRegistry with all templates
    profile_factory_and_registry = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address, profile_social_template.address, commission_hub_template.address, art_edition_1155_template.address, art_sales_1155_template.address,
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
    profile_factory_and_registry.createProfile(owner.address, sender=deployer)
    profile_factory_and_registry.createProfile(artist.address, sender=deployer)
    
    # Get profile addresses and instances
    owner_profile_address = profile_factory_and_registry.getProfile(owner.address)
    artist_profile_address = profile_factory_and_registry.getProfile(artist.address)
    owner_profile = project.Profile.at(owner_profile_address)
    artist_profile = project.Profile.at(artist_profile_address)
    
    # Get profile social addresses and instances
    owner_profile_social_address = profile_factory_and_registry.getProfileSocial(owner.address)
    artist_profile_social_address = profile_factory_and_registry.getProfileSocial(artist.address)
    owner_profile_social = project.ProfileSocial.at(owner_profile_social_address)
    artist_profile_social = project.ProfileSocial.at(artist_profile_social_address)
    
    # Set artist status for the artist profile
    artist_profile.setIsArtist(True, sender=artist)
    
    return {
        "deployer": deployer,
        "artist": artist,
        "owner": owner,
        "tagged_person": tagged_person,
        "commissioner": commissioner,
        "profile_template": profile_template,
        "profile_social_template": profile_social_template,
        "commission_hub_template": commission_hub_template,
        "art_piece_template": art_piece_template,
        "profile_factory_and_registry": profile_factory_and_registry,
        "art_commission_hub_owners": art_commission_hub_owners,
        "owner_profile": owner_profile,
        "artist_profile": artist_profile,
        "owner_profile_social": owner_profile_social,
        "artist_profile_social": artist_profile_social,
        "xtra1": xtra1,
        "xtra2": xtra2,
        "xtra3": xtra3,
        "xtra4": xtra4,
        "xtra5": xtra5
    ,
        "art_sales_1155_template": art_sales_1155_template,
        "art_edition_1155_template": art_edition_1155_template,
        "art_sales_1155_template": art_sales_1155_template}

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
    """Test basic social features with ProfileSocial contract"""
    owner = setup["owner"]
    artist = setup["artist"]
    owner_profile_social = setup["owner_profile_social"]
    artist_profile_address = setup["artist_profile"].address
    
    # Owner likes artist profile
    owner_profile_social.addLikedProfile(artist_profile_address, sender=owner)
    
    # Check liked profile count
    assert owner_profile_social.likedProfileCount() == 1
    
    # Get liked profiles
    liked_profiles = owner_profile_social.getLikedProfiles(0, 10)
    assert len(liked_profiles) == 1
    assert liked_profiles[0] == artist_profile_address

def test_create_art_piece_owner(setup):
    """Test creating an art piece through a profile as an owner (personal piece)"""
    owner = setup["owner"]
    owner_profile = setup["owner_profile"]
    art_piece_template = setup["art_piece_template"]
    
    # Test data for art piece
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiT3duZXIgQXJ0IFBpZWNlIiwiZGVzY3JpcHRpb24iOiJEZXNjcmlwdGlvbiBmb3Igb3duZXIgYXJ0IHBpZWNlIiwiaW1hZ2UiOiJkYXRhOmltYWdlL3BuZztiYXNlNjQsaVZCT1J3MEtHZ29BQUFBTlNVaEVVZ0FBQUFRQUFBQUVDQUlBQUFCQ05DdkRBQUFBQjNSSlRVVUg1QW9WRnQ4c0FVSUFBQUFPU1VSQlZBalhZOFFCQW1JQW5JRUIzZ0FBQUFCSlJVNUVya0pnZ2c9PSJ9"
    token_uri_data_format = "avif"
    title = "Owner Art Piece"
    description = "Description for owner art piece"
    
    # Initial art count
    initial_count = owner_profile.myArtCount()
    
    # Create art piece as a personal piece (owner is both artist and commissioner)
    tx_receipt = owner_profile.createArtPiece(
        art_piece_template.address,
        token_uri_data,
        token_uri_data_format,
        title,
        description,
        True,  # As artist (owner is creating their own art)
        owner.address,  # Other party is also owner (personal piece)
        False,  # Not AI generated
        ZERO_ADDRESS,  # Not linked to a commission hub
        False,  # Not profile art
        sender=owner
    )
    
    # Verify art piece was created and added to profile
    assert owner_profile.myArtCount() == initial_count + 1
    
    # Get the art piece address from the profile's recent art pieces
    art_pieces = owner_profile.getArtPiecesByOffset(0, 1, True)
    assert len(art_pieces) > 0, "No art pieces found in the owner's profile"
    art_piece_address = art_pieces[0]
    
    # Check art piece properties
    art_piece = project.ArtPiece.at(art_piece_address)
    assert art_piece.getOwner() == owner.address
    assert art_piece.getArtist() == owner.address
    assert art_piece.getTitle() == title

def test_create_art_piece_artist(setup):
    """Test creating an art piece as an artist (personal piece)"""
    artist = setup["artist"]
    artist_profile = setup["artist_profile"]
    art_piece_template = setup["art_piece_template"]
    
    # Test data for art piece
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiQXJ0aXN0IENyZWF0aW9uIiwiZGVzY3JpcHRpb24iOiJBcnR3b3JrIGNyZWF0ZWQgYnkgYW4gYXJ0aXN0IiwiaW1hZ2UiOiJkYXRhOmltYWdlL3BuZztiYXNlNjQsaVZCT1J3MEtHZ29BQUFBTlNVaEVVZ0FBQUFRQUFBQUVDQUlBQUFCQ05DdkRBQUFBQjNSSlRVVUg1QW9WRnQ5djhIRUFBQUFNU1VSQlZBalhZOFFCQWxvQWtXOEIzd0FBQUFCSLVVRK9Sa0pnZ2c9PSJ9"
    token_uri_data_format = "avif"
    title = "Artist Creation"
    description = "Artwork created by an artist"
    
    # Initial art count
    initial_count = artist_profile.myArtCount()
    
    # Create art piece as an artist (personal piece)
    tx_receipt = artist_profile.createArtPiece(
        art_piece_template.address,
        token_uri_data,
        token_uri_data_format,
        title,
        description,
        True,  # As artist
        artist.address,  # Other party is also artist (personal piece)
        True,  # AI generated
        ZERO_ADDRESS,  # Not linked to a commission hub
        False,  # Not profile art
        sender=artist
    )
    
    # Verify art piece was created and added to profile
    assert artist_profile.myArtCount() == initial_count + 1
    
    # Get the art piece address from the profile's recent art pieces
    art_pieces = artist_profile.getArtPiecesByOffset(0, 1, True)
    assert len(art_pieces) > 0, "No art pieces found in the artist's profile"
    art_piece_address = art_pieces[0]
    
    # Check art piece properties
    art_piece = project.ArtPiece.at(art_piece_address)
    assert art_piece.getOwner() == artist.address
    assert art_piece.getArtist() == artist.address
    assert art_piece.getTitle() == title
    assert art_piece.getAIGenerated() is True

def test_direct_profile_creation_and_art(setup):
    """Test creating a new profile directly and then creating art piece"""
    profile_factory_and_registry = setup["profile_factory_and_registry"]
    commissioner = setup["commissioner"]
    art_piece_template = setup["art_piece_template"]
    
    # Initially commissioner has no profile
    assert profile_factory_and_registry.hasProfile(commissioner.address) is False
    
    # First create a profile for the commissioner
    profile_factory_and_registry.createProfile(commissioner.address, sender=commissioner)
    
    # Verify profile was created
    assert profile_factory_and_registry.hasProfile(commissioner.address) is True
    
    # Get the profile address and interface
    profile_address = profile_factory_and_registry.getProfile(commissioner.address)
    profile = project.Profile.at(profile_address)
    
    # Now create an art piece through the profile (personal piece)
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
        True,  # As artist (creating their own art)
        commissioner.address,  # Other party is also commissioner (personal piece)
        False,  # Not AI generated
        ZERO_ADDRESS,  # No commission hub
        False,  # Not profile art
        sender=commissioner
    )
    
    # Verify art piece was created and added to profile
    assert profile.myArtCount() == 1
    
    # Get the art piece address from the profile's recent art pieces
    art_pieces = profile.getArtPiecesByOffset(0, 1, True)
    assert len(art_pieces) > 0, "No art pieces found in the commissioner's profile"
    art_piece_address = art_pieces[0]
    
    # Check art piece properties
    art_piece = project.ArtPiece.at(art_piece_address)
    assert art_piece.getTitle() == title
    assert art_piece.getOwner() == commissioner.address
    assert art_piece.getArtist() == commissioner.address

def test_get_art_piece_at_index_single(setup):
    """Test getting a single art piece by index"""
    owner = setup["owner"]
    owner_profile = setup["owner_profile"]
    art_piece_template = setup["art_piece_template"]
    
    # Test data for art piece
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiU2luZ2xlIEFydCBQaWVjZSIsImRlc2NyaXB0aW9uIjoiRGVzY3JpcHRpb24gZm9yIHNpbmdsZSBhcnQgcGllY2UiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFCM1JKVFVVSDVBb1ZGdDlQOVFFQUFBQUxTVVJCVkFqWFk4UUJBa3dBbUlRQjVnQUFBQUJKUlU1RXJrSmdnZz09In0="
    token_uri_data_format = "avif"
    title = "Single Art Piece"
    description = "Description for single art piece"
    
    # Create art piece (personal piece)
    tx_receipt = owner_profile.createArtPiece(
        art_piece_template.address,
        token_uri_data,
        token_uri_data_format,
        title,
        description,
        True,  # As artist (creating their own art)
        owner.address,  # Other party is also owner (personal piece)
        False,  # Not AI generated
        ZERO_ADDRESS,  # No commission hub
        False,  # Not profile art
        sender=owner
    )
    
    # Verify art piece was created
    assert owner_profile.myArtCount() == 1
    
    # Get the art piece address using getArtPieceAtIndex
    retrieved_art_piece_address = owner_profile.getArtPieceAtIndex(0)
    
    # Get the art piece address from the profile's recent art pieces for comparison
    art_pieces = owner_profile.getArtPiecesByOffset(0, 1, True)
    assert len(art_pieces) > 0, "No art pieces found in the owner's profile"
    art_piece_address = art_pieces[0]
    
    # Verify it matches what we created
    assert retrieved_art_piece_address == art_piece_address
    
    # Check art piece properties
    art_piece = project.ArtPiece.at(retrieved_art_piece_address)
    assert art_piece.getTitle() == title
    assert art_piece.getOwner() == owner.address
    assert art_piece.getArtist() == owner.address

def test_get_art_piece_at_index_multiple(setup):
    """Test getting multiple art pieces by index"""
    owner = setup["owner"]
    owner_profile = setup["owner_profile"]
    art_piece_template = setup["art_piece_template"]
    
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
        # Create art piece (personal piece)
        tx_receipt = owner_profile.createArtPiece(
            art_piece_template.address,
            token_uri_data_templates[i],
            token_uri_data_format,
            title,
            f"Description for art piece {i+1}",
            True,  # As artist (creating their own art)
            owner.address,  # Other party is also owner (personal piece)
            False,  # Not AI generated
            ZERO_ADDRESS,  # No commission hub
            False,  # Not profile art
            sender=owner
        )
        
        # Get the art piece address from the profile's recent art pieces
        art_pieces = owner_profile.getArtPiecesByOffset(0, 1, True)
        assert len(art_pieces) > 0, f"No art pieces found in the owner's profile after creating piece {i+1}"
        art_piece_address = art_pieces[0]
        
        # Add created address to our list for verification
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
    """Test the array slice functionality through liked profiles in ProfileSocial"""
    owner = setup["owner"]
    profile_factory_and_registry = setup["profile_factory_and_registry"]
    owner_profile_social = setup["owner_profile_social"]
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
    profiles_to_like.append(setup["artist_profile"].address)
    
    # Then add the test accounts' profiles
    for account in test_accounts:
        profile_factory_and_registry.createProfile(account.address, sender=account)
        profile_address = profile_factory_and_registry.getProfile(account.address)
        profiles_to_like.append(profile_address)
    
    # Like all the profiles
    for profile in profiles_to_like:
        owner_profile_social.addLikedProfile(profile, sender=owner)
    
    # Verify we have the expected number of liked profiles (6 total)
    assert owner_profile_social.likedProfileCount() == 6
    
    # Test page 0 with size 3 (should return first 3 profiles)
    page_0 = owner_profile_social.getLikedProfiles(0, 3)
    assert len(page_0) == 3
    for i in range(3):
        assert page_0[i] == profiles_to_like[i]
    
    # Test page 1 with size 3 (should return profiles 3-5)
    page_1 = owner_profile_social.getLikedProfiles(1, 3)
    assert len(page_1) == 3
    for i in range(3):
        assert page_1[i] == profiles_to_like[i + 3]
    
    # Test page 2 with size 3 (should return empty array - out of bounds)
    page_2 = owner_profile_social.getLikedProfiles(2, 3)
    assert len(page_2) == 0
    
    # Test with larger page size (should respect array bounds)
    large_page = owner_profile_social.getLikedProfiles(0, 10)
    assert len(large_page) == 6  # Only 6 items exist

def test_array_slice_reverse_functionality(setup):
    """Test the reverse array slice functionality through recent liked profiles in ProfileSocial"""
    owner = setup["owner"]
    profile_factory_and_registry = setup["profile_factory_and_registry"]
    owner_profile_social = setup["owner_profile_social"]
    xtra1 = setup["xtra1"]
    xtra2 = setup["xtra2"]
    xtra3 = setup["xtra3"]
    xtra4 = setup["xtra4"]
    xtra5 = setup["xtra5"]
    
    # Use a subset of accounts for testing
    test_accounts = [xtra1, xtra2, xtra3, xtra4, xtra5]
    
    profiles_to_like = []
    for account in test_accounts:
        profile_factory_and_registry.createProfile(account.address, sender=account)
        profile_address = profile_factory_and_registry.getProfile(account.address)
        profiles_to_like.append(profile_address)
    
    # Like all the profiles
    for profile in profiles_to_like:
        owner_profile_social.addLikedProfile(profile, sender=owner)
    
    # Verify we have the expected number of liked profiles
    assert owner_profile_social.likedProfileCount() == 5
    
    # Test page 0 with size 2 (should return last 2 profiles in reverse)
    page_0 = owner_profile_social.getRecentLikedProfiles(0, 2)
    assert len(page_0) == 2
    assert page_0[0] == profiles_to_like[4]  # Most recent first
    assert page_0[1] == profiles_to_like[3]
    
    # Test page 1 with size 2 (should return profiles 2-1 in reverse)
    page_1 = owner_profile_social.getRecentLikedProfiles(1, 2)
    assert len(page_1) == 2
    assert page_1[0] == profiles_to_like[2]
    assert page_1[1] == profiles_to_like[1]
    
    # Test page 2 with size 2 (should return profile 0)
    page_2 = owner_profile_social.getRecentLikedProfiles(2, 2)
    assert len(page_2) == 1
    assert page_2[0] == profiles_to_like[0]
    
    # Test page 3 with size 2 (should return empty array - out of bounds)
    page_3 = owner_profile_social.getRecentLikedProfiles(3, 2)
    assert len(page_3) == 0

def test_remove_from_array_functionality(setup):
    """Test the remove from array functionality through liked profiles in ProfileSocial"""
    owner = setup["owner"]
    profile_factory_and_registry = setup["profile_factory_and_registry"]
    owner_profile_social = setup["owner_profile_social"]
    xtra1 = setup["xtra1"]
    xtra2 = setup["xtra2"]
    xtra3 = setup["xtra3"]
    
    # Use a smaller subset
    test_accounts = [xtra1, xtra2, xtra3]
    
    # Create profiles to like
    profiles_to_like = []
    for account in test_accounts:
        profile_factory_and_registry.createProfile(account.address, sender=account)
        profile_address = profile_factory_and_registry.getProfile(account.address)
        profiles_to_like.append(profile_address)
    
    # Like all the profiles
    for profile in profiles_to_like:
        owner_profile_social.addLikedProfile(profile, sender=owner)
    
    # Verify we have the expected number of liked profiles
    assert owner_profile_social.likedProfileCount() == 3
    
    # Get initial profiles array
    initial_profiles = owner_profile_social.getLikedProfiles(0, 10)
    assert len(initial_profiles) == 3
    
    # 1. Remove an item and verify count decreased
    first_item = profiles_to_like[0]
    owner_profile_social.removeLikedProfile(first_item, sender=owner)
    assert owner_profile_social.likedProfileCount() == 2
    
    # Get the updated array
    remaining_profiles = owner_profile_social.getLikedProfiles(0, 10)
    assert len(remaining_profiles) == 2
    
    # Verify the removed item is not in the array
    assert first_item not in remaining_profiles
    
    # 2. Remove another item and verify count decreased again
    second_item = profiles_to_like[1]
    owner_profile_social.removeLikedProfile(second_item, sender=owner)
    assert owner_profile_social.likedProfileCount() == 1
    
    # Get the updated array
    remaining_profiles = owner_profile_social.getLikedProfiles(0, 10)
    assert len(remaining_profiles) == 1
    assert remaining_profiles[0] == profiles_to_like[2], "Only the third item should remain"
    
    # 3. Remove the last item and verify array is empty
    last_item = profiles_to_like[2]
    owner_profile_social.removeLikedProfile(last_item, sender=owner)
    assert owner_profile_social.likedProfileCount() == 0
    
    # Check that the array is now empty
    final_profiles = owner_profile_social.getLikedProfiles(0, 10)
    assert len(final_profiles) == 0
    
    # 4. Try to remove an item that doesn't exist (should revert)
    non_existent_profile = "0x0000000000000000000000000000000000001234"
    with pytest.raises(Exception):
        owner_profile_social.removeLikedProfile(non_existent_profile, sender=owner)

def test_complex_array_operations(setup):
    """Test a combination of array operations in sequence using ProfileSocial"""
    owner = setup["owner"]
    profile_factory_and_registry = setup["profile_factory_and_registry"]
    owner_profile_social = setup["owner_profile_social"]
    xtra1 = setup["xtra1"]
    xtra2 = setup["xtra2"]
    xtra3 = setup["xtra3"]
    xtra4 = setup["xtra4"]
    xtra5 = setup["xtra5"]
    
    # Start with a clean state
    assert owner_profile_social.likedProfileCount() == 0
    
    # Use available accounts
    test_accounts = [xtra1, xtra2, xtra3, xtra4, xtra5]
    
    # Create profiles
    profiles = []
    for account in test_accounts:
        profile_factory_and_registry.createProfile(account.address, sender=account)
        profile_address = profile_factory_and_registry.getProfile(account.address)
        profiles.append(profile_address)
    
    # Phase 1: Add first 3 profiles
    for i in range(3):
        owner_profile_social.addLikedProfile(profiles[i], sender=owner)
    
    # Verify count and content
    assert owner_profile_social.likedProfileCount() == 3
    page = owner_profile_social.getLikedProfiles(0, 10)
    assert len(page) == 3
    recent = owner_profile_social.getRecentLikedProfiles(0, 10)
    assert len(recent) == 3
    
    # Most recent should be the last one added
    assert recent[0] == profiles[2]
    
    # Phase 2: Remove middle profile
    owner_profile_social.removeLikedProfile(profiles[1], sender=owner)
    
    # Get updated state
    page = owner_profile_social.getLikedProfiles(0, 10)
    
    # Verify count
    assert owner_profile_social.likedProfileCount() == 2
    assert len(page) == 2
    
    # Verify correct items remain
    remaining_profiles = set(page)
    expected_remaining = {profiles[0], profiles[2]}
    assert remaining_profiles == expected_remaining
    
    # Phase 3: Add 2 more profiles
    for i in range(3, 5):
        owner_profile_social.addLikedProfile(profiles[i], sender=owner)
    
    # Verify count and content
    assert owner_profile_social.likedProfileCount() == 4
    page = owner_profile_social.getLikedProfiles(0, 10)
    assert len(page) == 4
    
    # Phase 4: Test reverse ordering - most recent first
    recent = owner_profile_social.getRecentLikedProfiles(0, 10)
    assert len(recent) == 4
    
    # Check the first 2 items match the most recently added
    assert recent[0] == profiles[4]
    assert recent[1] == profiles[3]
    
    # Phase 5: Test pagination
    recent_0 = owner_profile_social.getRecentLikedProfiles(0, 2)
    recent_1 = owner_profile_social.getRecentLikedProfiles(1, 2)
    
    assert len(recent_0) == 2
    assert len(recent_1) == 2
    
    # Most recent 2 items should be profiles[4] and profiles[3]
    assert recent_0[0] == profiles[4]
    assert recent_0[1] == profiles[3]
    
    # Next 2 items should be the remaining profiles
    assert recent_1[0] in [profiles[0], profiles[2]]
    assert recent_1[1] in [profiles[0], profiles[2]]
    assert recent_1[0] != recent_1[1]  # Make sure they're different 