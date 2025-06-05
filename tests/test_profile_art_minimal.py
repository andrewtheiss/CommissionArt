import pytest
from ape import accounts, project

# Test data
TEST_TOKEN_URI_DATA = b"data:application/json;base64,eyJuYW1lIjoiVGVzdCBBcnR3b3JrIiwiZGVzY3JpcHRpb24iOiJUaGlzIGlzIGEgdGVzdCBkZXNjcmlwdGlvbiBmb3IgdGhlIGFydHdvcmsiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFCM1JKVFVVSDVBb1NEdUZvQ0FBQUFBMUpSRUZVZU5xVEVFRUFBQUE1VVBBRHhpVXFJVzRBQUFBQlNVVk9SSzVDWUlJPSJ9"
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    artist = accounts.test_accounts[1]
    owner = accounts.test_accounts[2]
    
    # Deploy all templates
    profile_template = project.Profile.deploy(sender=deployer)
    print(f"Deployed Profile template at {profile_template.address}")
    
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    print(f"Deployed ProfileSocial template at {profile_social_template.address}")
    
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)

    # Deploy ArtEdition1155 template
    art_edition_1155_template = project.ArtEdition1155.deploy(sender=deployer)
    
    # Deploy ArtSales1155 template
    art_sales_1155_template = project.ArtSales1155.deploy(sender=deployer)
    print(f"Deployed ArtCommissionHub template at {commission_hub_template.address}")
    
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    print(f"Deployed ArtPiece template at {art_piece_template.address}")
    
    # Deploy ProfileFactoryAndRegistry with all templates
    profile_factory_and_registry = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address, profile_social_template.address, commission_hub_template.address, art_edition_1155_template.address, art_sales_1155_template.address,
        sender=deployer
    )
    print(f"Deployed ProfileFactoryAndRegistry at {profile_factory_and_registry.address}")
    
    # Deploy ArtCommissionHubOwners
    art_commission_hub_owners = project.ArtCommissionHubOwners.deploy(
        deployer.address,  # L2OwnershipRelay
        commission_hub_template.address,
        art_piece_template.address,
        sender=deployer
    )
    print(f"Deployed ArtCommissionHubOwners at {art_commission_hub_owners.address}")
    
    # Link factory and hub owners
    profile_factory_and_registry.linkArtCommissionHubOwnersContract(art_commission_hub_owners.address, sender=deployer)
    art_commission_hub_owners.linkProfileFactoryAndRegistry(profile_factory_and_registry.address, sender=deployer)
    
    return {
        "deployer": deployer,
        "artist": artist,
        "owner": owner,
        "profile_template": profile_template,
        "profile_social_template": profile_social_template,
        "commission_hub_template": commission_hub_template,
        "art_piece_template": art_piece_template,
        "profile_factory_and_registry": profile_factory_and_registry,
        "art_commission_hub_owners": art_commission_hub_owners
    ,
        "art_sales_1155_template": art_sales_1155_template,
        "art_edition_1155_template": art_edition_1155_template,
        "art_sales_1155_template": art_sales_1155_template}

def test_minimal_profile_creation(setup):
    """Test the most basic profile creation"""
    profile_factory_and_registry = setup["profile_factory_and_registry"]
    owner = setup["owner"]
    
    # Create a profile for the owner
    tx = profile_factory_and_registry.createProfile(owner.address, sender=setup["deployer"])
    print(f"Profile creation transaction: {tx.txn_hash}")
    
    # Verify profile was created
    assert profile_factory_and_registry.hasProfile(owner.address) is True
    profile_address = profile_factory_and_registry.getProfile(owner.address)
    print(f"Profile created at address: {profile_address}")
    
    # Access the profile
    profile = project.Profile.at(profile_address)
    assert profile.owner() == owner.address
    
    # Verify initial state
    assert profile.myArtCount() == 0
    print(f"Initial art count: {profile.myArtCount()}")
    
    # Try to get art pieces (should be empty)
    art_pieces = profile.getArtPiecesByOffset(0, 10, False)
    print(f"Initial art pieces: {art_pieces}")

def test_minimal_art_piece_creation(setup):
    """Test the most basic art piece creation"""
    # First ensure profile is created
    test_minimal_profile_creation(setup)
    
    # Get the profile directly instead of using the return value
    profile_factory_and_registry = setup["profile_factory_and_registry"]
    owner = setup["owner"]
    profile_address = profile_factory_and_registry.getProfile(owner.address)
    profile = project.Profile.at(profile_address)
    
    art_piece_template = setup["art_piece_template"]
    
    # Test data for art piece
    title = "Test Artwork"
    description = "This is a test description"
    
    print("\nCreating art piece...")
    print(f"Art piece template: {art_piece_template.address}")
    print(f"Owner: {owner.address}")
    
    # Create art piece (personal piece - owner is both artist and commissioner)
    tx_receipt = profile.createArtPiece(
        art_piece_template.address,
        TEST_TOKEN_URI_DATA,
        "avif",
        title,
        description,
        True,  # As artist (creating their own art)
        owner.address,  # Other party is also owner (personal piece)
        False,  # Not AI generated
        ZERO_ADDRESS,  # No commission hub
        False,  # Not profile art
        sender=owner
    )
    
    print(f"Art piece creation transaction: {tx_receipt.txn_hash}")
    print(f"Transaction status: {tx_receipt.status}")
    
    # Check if art piece was added
    new_count = profile.myArtCount()
    print(f"New art count: {new_count}")
    
    # This should be 1 if successful
    assert new_count == 1, f"Expected art count to be 1, got {new_count}"
    
    # Get art pieces 
    art_pieces = profile.getArtPiecesByOffset(0, 10, False)
    print(f"Art pieces list (count: {len(art_pieces)}): {art_pieces}")
    
    # Should have at least one entry if successful
    assert len(art_pieces) == 1, f"Expected 1 art piece, got {len(art_pieces)}"
    
    # Get the art piece address
    art_piece_address = art_pieces[0]
    print(f"Art piece address: {art_piece_address}")
    
    # Access the art piece contract
    art_piece = project.ArtPiece.at(art_piece_address)
    
    # Check art piece properties
    piece_owner = art_piece.getOwner()
    piece_artist = art_piece.getArtist()
    piece_title = art_piece.getTitle()
    
    print(f"Art piece owner: {piece_owner}")
    print(f"Art piece artist: {piece_artist}")
    print(f"Art piece title: {piece_title}")
    
    assert piece_owner == owner.address
    assert piece_artist == owner.address  # Personal piece, so owner is also artist
    assert piece_title == title 