import pytest
from ape import accounts, project
import time
from eth_utils import to_checksum_address

# Define constant for zero address
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    user = accounts.test_accounts[1]
    artist = accounts.test_accounts[2]
    
    # Deploy ArtCommissionHub
    commission_hub = project.ArtCommissionHub.deploy(sender=deployer)
    
    # Initialize the hub
    chain_id = 1
    nft_contract = deployer.address  # Use deployer address as mock NFT contract
    token_id = 1
    commission_hub.initialize(chain_id, nft_contract, token_id, deployer.address, sender=deployer)
    
    # Deploy ArtPiece template for testing
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Set the whitelisted ArtPiece contract
    commission_hub.setWhitelistedArtPieceContract(art_piece_template.address, sender=deployer)
    
    return {
        "deployer": deployer,
        "user": user,
        "artist": artist,
        "commission_hub": commission_hub
    }

def test_pagination_functions_with_empty_arrays(setup):
    """
    Test pagination functions with empty arrays
    """
    # Arrange
    commission_hub = setup["commission_hub"]
    
    # Test verified art pieces pagination
    verified_art = commission_hub.getVerifiedArtPiecesByOffset(0, 10)
    assert len(verified_art) == 0, "Expected empty array for verified art"
    
    # Test unverified art pieces pagination
    unverified_art = commission_hub.getUnverifiedArtPiecesByOffset(0, 10)
    assert len(unverified_art) == 0, "Expected empty array for unverified art"
    
    # Test with different offsets and counts
    verified_art_large_offset = commission_hub.getVerifiedArtPiecesByOffset(100, 10)
    assert len(verified_art_large_offset) == 0, "Expected empty array for large offset"
    
    verified_art_large_count = commission_hub.getVerifiedArtPiecesByOffset(0, 100)
    assert len(verified_art_large_count) == 0, "Expected empty array for large count"
    
    unverified_art_large_offset = commission_hub.getUnverifiedArtPiecesByOffset(100, 10)
    assert len(unverified_art_large_offset) == 0, "Expected empty array for large offset"
    
    unverified_art_large_count = commission_hub.getUnverifiedArtPiecesByOffset(0, 100)
    assert len(unverified_art_large_count) == 0, "Expected empty array for large count"

def test_get_art_piece_by_index_with_empty_arrays(setup):
    """
    Test getArtPieceByIndex with empty arrays
    """
    # Arrange
    commission_hub = setup["commission_hub"]
    
    # Test index out of bounds for verified art
    with pytest.raises(Exception):
        commission_hub.getArtPieceByIndex(True, 0)
    
    # Test index out of bounds for unverified art
    with pytest.raises(Exception):
        commission_hub.getArtPieceByIndex(False, 0) 