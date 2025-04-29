import pytest
from ape import accounts, project

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    artist = accounts.test_accounts[1]
    owner = accounts.test_accounts[2]
    
    # Deploy CommissionHub
    commission_hub = project.CommissionHub.deploy(sender=deployer)
    print(f"Deployed CommissionHub at {commission_hub.address}")
    
    # Deploy ArtPiece template
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    print(f"Deployed ArtPiece template at {art_piece_template.address}")
    
    # Deploy Profile template
    profile_template = project.Profile.deploy(sender=deployer)
    print(f"Deployed Profile template at {profile_template.address}")
    
    # Deploy ProfileHub with the template
    profile_hub = project.ProfileHub.deploy(profile_template.address, sender=deployer)
    print(f"Deployed ProfileHub at {profile_hub.address}")
    
    return {
        "deployer": deployer,
        "artist": artist,
        "owner": owner,
        "commission_hub": commission_hub,
        "art_piece_template": art_piece_template,
        "profile_template": profile_template,
        "profile_hub": profile_hub
    }

def test_minimal_profile_creation(setup):
    """Test the most basic profile creation"""
    profile_hub = setup["profile_hub"]
    owner = setup["owner"]
    
    # Create a profile for the owner
    tx = profile_hub.createProfile(sender=owner)
    print(f"Profile creation transaction: {tx.txn_hash}")
    
    # Verify profile was created
    assert profile_hub.hasProfile(owner.address) is True
    profile_address = profile_hub.getProfile(owner.address)
    print(f"Profile created at address: {profile_address}")
    
    # Access the profile
    profile = project.Profile.at(profile_address)
    assert profile.owner() == owner.address
    
    # Verify initial state
    assert profile.myArtCount() == 0
    print(f"Initial art count: {profile.myArtCount()}")
    
    # Try to get art pieces (should be empty)
    art_pieces = profile.getArtPieces(0, 10)
    print(f"Initial art pieces: {art_pieces}")
    
    return profile

def test_minimal_art_piece_creation(setup):
    """Test the most basic art piece creation"""
    profile = test_minimal_profile_creation(setup)
    owner = setup["owner"]
    artist = setup["artist"] 
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Test data for art piece
    image_data = b"test artwork image data" * 10
    title = "Test Artwork"
    description = b"This is a test description"
    
    print("\nCreating art piece...")
    print(f"Art piece template: {art_piece_template.address}")
    print(f"Commission hub: {commission_hub.address}")
    print(f"Owner: {owner.address}")
    print(f"Artist: {artist.address}")
    
    # Create art piece
    tx_receipt = profile.createArtPiece(
        art_piece_template.address,
        image_data,
        title,
        description,
        False,  # Not as artist
        artist.address,
        commission_hub.address,
        False,  # Not AI generated
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
    art_pieces = profile.getArtPieces(0, 10)
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
    assert piece_artist == artist.address
    assert piece_title == title 