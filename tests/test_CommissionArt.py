import pytest
from ape import accounts, project

@pytest.fixture
def setup():
    # Get local accounts for testing
    deployer = accounts.test_accounts[0]
    owner = accounts.test_accounts[1]
    artist = accounts.test_accounts[2]
    
    # Sample image data (smaller size for testing)
    sample_image_data = b"sample image data" * 10  # Still well under 1000 bytes
    
    # Deploy the ArtPiece contract
    contract = project.ArtPiece.deploy(sender=deployer)
    
    # Initialize the ArtPiece contract
    contract.initialize(
        sample_image_data,
        "Test Artwork",
        b"Test Description",
        owner.address,
        artist.address,
        deployer.address,  # Commission hub address (using deployer as placeholder)
        False,  # Not AI generated
        sender=deployer
    )
    
    return contract, owner, artist

def test_art_piece_initialization(setup):
    """Test that the contract initializes with correct values"""
    contract, owner, artist = setup
    
    # Check if the owner is set correctly
    assert contract.getOwner() == owner.address
    
    # Check if the artist is set correctly
    assert contract.getArtist() == artist.address
    
    # Check if the image data is set correctly
    assert contract.getImageData() == b"sample image data" * 10

def test_art_piece_transfer_ownership(setup):
    """Test the transferOwnership method"""
    contract, owner, artist = setup
    new_owner = accounts.test_accounts[3]
    
    # Transfer ownership
    contract.transferOwnership(new_owner.address, sender=owner)
    
    # Check if ownership was transferred correctly
    assert contract.getOwner() == new_owner.address

def test_commission_hub_with_small_arrays():
    """Test CommissionHub getLatestVerifiedArt with small array sizes"""
    # Get local accounts for testing
    deployer = accounts.test_accounts[0]
    owner = accounts.test_accounts[1]
    artist = accounts.test_accounts[2]
    
    # Deploy L2Relay contract first (needed for registry)
    l2relay = project.L2Relay.deploy(sender=deployer)
    
    # Deploy CommissionHub contract to use as template
    commission_hub_template = project.CommissionHub.deploy(sender=deployer)
    
    # Deploy OwnerRegistry with the required parameters
    registry = project.OwnerRegistry.deploy(
        l2relay.address,  # Initial L2 relay
        commission_hub_template.address,  # CommissionHub template
        sender=deployer
    )
    
    # Deploy a new CommissionHub instance
    commission_hub = project.CommissionHub.deploy(sender=deployer)
    
    # Initialize CommissionHub
    commission_hub.initialize(1, "0x1111111111111111111111111111111111111111", 1, registry.address, sender=deployer)
    
    # Set owner via registry
    commission_hub.updateRegistration(1, "0x1111111111111111111111111111111111111111", 1, owner.address, sender=registry)
    
    # Deploy ArtPiece contract as implementation
    art_piece_implementation = project.ArtPiece.deploy(sender=deployer)
    
    # Whitelist ArtPiece implementation
    commission_hub.setWhitelistedArtPieceContract(art_piece_implementation.address, sender=owner)
    
    # Test with zero art pieces
    empty_result = commission_hub.getLatestVerifiedArt(3)
    assert len(empty_result) == 0
    
    # Test with small arrays of art pieces
    # Submit a commission
    commission_hub.submitCommission(art_piece_implementation.address, sender=owner)
    
    # Test with one art piece
    single_result = commission_hub.getLatestVerifiedArt(3)
    assert len(single_result) == 1
    assert single_result[0] == art_piece_implementation.address

def test_profile_with_small_arrays():
    """Test Profile getLatestArtPieces with small array sizes"""
    # Get local accounts for testing
    deployer = accounts.test_accounts[0]
    owner = accounts.test_accounts[1]
    artist = accounts.test_accounts[2]
    
    # Deploy Profile contract
    profile = project.Profile.deploy(sender=deployer)
    
    # Initialize Profile with owner
    profile.initialize(owner.address, sender=deployer)
    
    # Test with zero art pieces
    empty_result = profile.getLatestArtPieces()
    assert len(empty_result) == 0
    
    # Deploy a test art piece
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
        b"test image data",
        "Test Title",
        b"Test Description",
        owner.address,
        artist.address,
        deployer.address,  # Commission hub address
        False,  # Not AI generated
        sender=deployer
    )
    
    # Add one art piece to profile
    profile.addArtPiece(art_piece.address, sender=owner)
    
    # Test with one art piece
    single_result = profile.getLatestArtPieces()
    assert len(single_result) == 1
    assert single_result[0] == art_piece.address
    
    # Add multiple art pieces
    for i in range(6):  # Add 6 more pieces for a total of 7
        new_art = project.ArtPiece.deploy(sender=deployer)
        new_art.initialize(
            b"test image data",
            f"Test Title {i}",
            b"Test Description",
            owner.address,
            artist.address,
            deployer.address,
            False,
            sender=deployer
        )
        profile.addArtPiece(new_art.address, sender=owner)
    
    # Test with many art pieces (should return at most 5)
    multi_result = profile.getLatestArtPieces()
    assert len(multi_result) == 5  # Should be capped at 5 items 