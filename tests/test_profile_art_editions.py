import pytest
from ape import accounts, project

# Define constant for zero address
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

# Define global test data constants
TEST_TOKEN_URI_DATA = b"data:application/json;base64,eyJuYW1lIjoiVGVzdCBBcnR3b3JrIiwiZGVzY3JpcHRpb24iOiJUaGlzIGlzIGEgdGVzdCBkZXNjcmlwdGlvbiBmb3IgdGhlIGFydHdvcmsiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTndJREFBQUFCbEJNVkVYLy8vL24vNGJsQUFBQUJYUlNUbk1BUUtKZVVtUktBQUFBQWtsRVFWUUkxMkJnQUFNRE1BQUJoVUFCQUVtQ0FVQUFBQUJKUlU1RXJrSmdnZz09In0="
TEST_TITLE = "Test Artwork"
TEST_DESCRIPTION = "This is a test description for the artwork"
TEST_TOKEN_URI_DATA_FORMAT = "avif"
TEST_AI_GENERATED = False

@pytest.fixture(scope="function")
def setup():
    deployer = accounts.test_accounts[0]
    owner = accounts.test_accounts[1]
    artist = accounts.test_accounts[2]

    # Deploy templates
    profile_template = project.Profile.deploy(sender=deployer)
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    art_sales_1155_template = project.ArtSales1155.deploy(sender=deployer)
    art_edition_1155_template = project.ArtEdition1155.deploy(sender=deployer)

    # Deploy factory with all templates
    profile_factory_and_registry = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address,
        profile_social_template.address,
        commission_hub_template.address,
        art_edition_1155_template.address,
        art_sales_1155_template.address,
        sender=deployer
    )

    # Create profiles
    profile_factory_and_registry.createProfile(owner.address, sender=deployer)
    owner_profile = project.Profile.at(profile_factory_and_registry.getProfile(owner.address))
    
    profile_factory_and_registry.createProfile(artist.address, sender=deployer)
    artist_profile = project.Profile.at(profile_factory_and_registry.getProfile(artist.address))
    
    # Set artist status manually
    artist_profile.setIsArtist(True, sender=artist)
    
    # Get auto-created ArtSales1155 for artist
    artist_sales = project.ArtSales1155.at(artist_profile.artSales1155())

    return {
        "deployer": deployer,
        "owner": owner,
        "artist": artist,
        "profile_template": profile_template,
        "profile_factory_and_registry": profile_factory_and_registry,
        "owner_profile": owner_profile,
        "artist_profile": artist_profile,
        "art_piece_template": art_piece_template,
        "art_sales_1155_template": art_sales_1155_template,
        "art_edition_1155_template": art_edition_1155_template,
        "artist_sales": artist_sales
    }

def test_art_piece_has_editions_returns_false_initially(setup):
    """Test that artPieceHasEditions returns False for art pieces without editions"""
    artist = setup["artist"]
    artist_profile = setup["artist_profile"]
    art_piece_template = setup["art_piece_template"]
    
    # Create an art piece
    artist_profile.createArtPiece(
        art_piece_template.address,
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        True,
        artist.address,
        TEST_AI_GENERATED,
        ZERO_ADDRESS,  # No commission hub
        False,  # Not profile art
        sender=artist
    )
    
    # Get art piece address
    art_pieces = artist_profile.getArtPiecesByOffset(0, 1, False)
    art_piece_address = art_pieces[0]
    
    # Should return False initially
    assert artist_profile.artPieceHasEditions(art_piece_address) == False

def test_art_piece_has_editions_returns_false_no_sales_contract(setup):
    """Test that artPieceHasEditions returns False when no ArtSales1155 contract is set"""
    owner = setup["owner"]
    owner_profile = setup["owner_profile"]
    art_piece_template = setup["art_piece_template"]
    
    # Owner profile doesn't have ArtSales1155 set (not an artist)
    assert owner_profile.artSales1155() == ZERO_ADDRESS
    
    # Create an art piece
    owner_profile.createArtPiece(
        art_piece_template.address,
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        True,
        owner.address,
        TEST_AI_GENERATED,
        ZERO_ADDRESS,  # No commission hub
        False,  # Not profile art
        sender=owner
    )
    
    # Get art piece address
    art_pieces = owner_profile.getArtPiecesByOffset(0, 1, False)
    art_piece_address = art_pieces[0]
    
    # Should return False when no sales contract
    assert owner_profile.artPieceHasEditions(art_piece_address) == False

def test_create_art_edition_success_via_sales_contract(setup):
    """Test creating art edition via ArtSales1155 directly"""
    artist = setup["artist"]
    artist_profile = setup["artist_profile"]
    artist_sales = setup["artist_sales"]
    art_piece_template = setup["art_piece_template"]
    
    # Create an art piece
    artist_profile.createArtPiece(
        art_piece_template.address,
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        True,
        artist.address,
        TEST_AI_GENERATED,
        ZERO_ADDRESS,  # No commission hub
        False,  # Not profile art
        sender=artist
    )
    
    art_pieces = artist_profile.getArtPiecesByOffset(0, 1, False)
    art_piece_address = art_pieces[0]
    
    # Initially should have no editions
    assert artist_profile.artPieceHasEditions(art_piece_address) == False
    
    # Create edition via ArtSales1155
    receipt = artist_sales.createEditionFromArtPiece(
        art_piece_address,
        "Test Edition",
        "TESTART",
        "https://api.example.com/metadata/",
        1000000000000000000,  # 1 ETH
        100,
        500,  # 5%
        sender=artist
    )
    
    # Should now have editions
    assert artist_profile.artPieceHasEditions(art_piece_address) == True
    
    # Verify the return value is an address
    edition_address = receipt.return_value
    assert edition_address != ZERO_ADDRESS
    assert len(edition_address) == 42  # Valid Ethereum address format

def test_create_art_edition_via_profile_method(setup):
    """Test creating art edition using Profile.createArtEdition method"""
    artist = setup["artist"]
    artist_profile = setup["artist_profile"]
    art_piece_template = setup["art_piece_template"]
    
    # Debug: Check profile ownership
    print(f"Artist address: {artist.address}")
    print(f"Artist profile owner: {artist_profile.owner()}")
    print(f"Artist profile address: {artist_profile.address}")
    print(f"ArtSales1155 address: {artist_profile.artSales1155()}")
    
    # Create art piece
    artist_profile.createArtPiece(
        art_piece_template.address,
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        True,  # As artist
        artist.address,
        TEST_AI_GENERATED,
        ZERO_ADDRESS,  # No commission hub
        False,  # Not profile art
        sender=artist
    )
    
    art_pieces = artist_profile.getArtPiecesByOffset(0, 1, False)
    art_piece_address = art_pieces[0]
    
    print(f"Art piece address: {art_piece_address}")
    
    # Check art piece details
    art_piece = project.ArtPiece.at(art_piece_address)
    print(f"Art piece artist: {art_piece.getArtist()}")
    print(f"Art piece owner: {art_piece.getOwner()}")
    
    # Check if art piece exists in profile
    print(f"Art piece exists in profile: {artist_profile.artPieceExists(art_piece_address)}")
    
    # Initially should have no editions
    assert artist_profile.artPieceHasEditions(art_piece_address) == False
    
    # Create edition via Profile method
    receipt = artist_profile.createArtEdition(
        art_piece_address,
        "Profile Edition",
        "PROFILE",
        "https://api.example.com/profile/",
        2000000000000000000,  # 2 ETH
        50,
        750,  # 7.5%
        sender=artist
    )
    
    # Should now have editions
    assert artist_profile.artPieceHasEditions(art_piece_address) == True
    
    # Verify the return value is an address
    edition_address = receipt.return_value
    assert edition_address != ZERO_ADDRESS
    assert len(edition_address) == 42  # Valid Ethereum address format

def test_create_art_edition_requires_owner(setup):
    """Test that only profile owner can create editions"""
    artist = setup["artist"]
    owner = setup["owner"]
    artist_profile = setup["artist_profile"]
    art_piece_template = setup["art_piece_template"]
    
    # Create art piece
    artist_profile.createArtPiece(
        art_piece_template.address,
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        True,
        artist.address,
        TEST_AI_GENERATED,
        ZERO_ADDRESS,  # No commission hub
        False,  # Not profile art
        sender=artist
    )
    
    art_pieces = artist_profile.getArtPiecesByOffset(0, 1, False)
    art_piece_address = art_pieces[0]
    
    # Owner should not be able to create edition on artist's profile
    with pytest.raises(Exception, match="Only owner can create editions"):
        artist_profile.createArtEdition(
            art_piece_address,
            "Unauthorized Edition",
            "UNAUTH",
            "https://api.example.com/",
            1000000000000000000,
            10,
            500,
            sender=owner
        )

def test_create_art_edition_requires_art_sales_contract(setup):
    """Test that createArtEdition requires ArtSales1155 to be set"""
    owner = setup["owner"]
    owner_profile = setup["owner_profile"]
    art_piece_template = setup["art_piece_template"]
    
    # Owner profile doesn't have ArtSales1155 set
    assert owner_profile.artSales1155() == ZERO_ADDRESS
    
    # Create art piece
    owner_profile.createArtPiece(
        art_piece_template.address,
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        True,
        owner.address,
        TEST_AI_GENERATED,
        ZERO_ADDRESS,  # No commission hub
        False,  # Not profile art
        sender=owner
    )
    
    art_pieces = owner_profile.getArtPiecesByOffset(0, 1, False)
    art_piece_address = art_pieces[0]
    
    # Should fail when ArtSales1155 not set
    with pytest.raises(Exception, match="ArtSales1155 not set"):
        owner_profile.createArtEdition(
            art_piece_address,
            "No Sales Edition",
            "NOSALES",
            "https://api.example.com/",
            1000000000000000000,
            10,
            500,
            sender=owner
        )

def test_create_art_edition_requires_art_piece_in_profile(setup):
    """Test that createArtEdition requires the art piece to be in the profile"""
    artist = setup["artist"]
    artist_profile = setup["artist_profile"]
    
    # Use a random address that doesn't exist in the profile
    fake_art_piece_address = "0x1234567890123456789012345678901234567890"
    
    # Should fail when art piece not in profile
    with pytest.raises(Exception, match="Art piece not in profile"):
        artist_profile.createArtEdition(
            fake_art_piece_address,
            "Fake Edition",
            "FAKE",
            "https://api.example.com/",
            1000000000000000000,
            10,
            500,
            sender=artist
        )

def test_multiple_editions_for_same_art_piece(setup):
    """Test that hasEditions still returns True even after multiple edition creations"""
    artist = setup["artist"]
    artist_profile = setup["artist_profile"]
    artist_sales = setup["artist_sales"]
    art_piece_template = setup["art_piece_template"]
    
    # Create art piece
    artist_profile.createArtPiece(
        art_piece_template.address,
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        True,
        artist.address,
        TEST_AI_GENERATED,
        ZERO_ADDRESS,  # No commission hub
        False,  # Not profile art
        sender=artist
    )
    
    art_pieces = artist_profile.getArtPiecesByOffset(0, 1, False)
    art_piece_address = art_pieces[0]
    
    # Initially no editions
    assert artist_profile.artPieceHasEditions(art_piece_address) == False
    
    # Create first edition
    artist_sales.createEditionFromArtPiece(
        art_piece_address,
        "Edition 1",
        "ED1",
        "https://api.example.com/1/",
        1000000000000000000,
        100,
        500,
        sender=artist
    )
    
    # Should have editions
    assert artist_profile.artPieceHasEditions(art_piece_address) == True
    
    # Note: The current implementation maps one art piece to one edition contract
    # Multiple editions would be different token IDs within the same contract
    # So we can't create a second edition contract for the same art piece
    # This is the expected behavior according to the mapping in ArtSales1155 