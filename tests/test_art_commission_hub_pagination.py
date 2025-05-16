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
    
    # Create a commission hub template for the ArtCommissionHubOwners
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    
    # Deploy an actual ArtCommissionHubOwners contract
    # For testing, we can use deployer address as the L2RelayOwnership
    art_collection_ownership_registry = project.ArtCommissionHubOwners.deploy(deployer.address, commission_hub_template.address, sender=deployer)
    
    # Set test parameters
    chain_id = 1
    nft_contract = deployer.address  # Use deployer address as mock NFT contract
    token_id = 1
    
    # Register an NFT owner through the ArtCommissionHubOwners (acting as L2RelayOwnership)
    art_collection_ownership_registry.registerNFTOwnerFromParentChain(
        chain_id, 
        nft_contract, 
        token_id, 
        deployer.address,  # Set deployer as the owner
        sender=deployer     # Pretend to be the L2RelayOwnership
    )
    
    # Get the automatically created hub address from the registry
    commission_hub_address = art_collection_ownership_registry.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
    
    # Create a reference to the hub
    commission_hub = project.ArtCommissionHub.at(commission_hub_address)
    
    # Deploy ArtPiece template for testing
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Approve the ArtPiece template's code hash
    commission_hub.approveArtPieceCodeHash(art_piece_template.address, True, sender=deployer)
    
    return {
        "deployer": deployer,
        "user": user,
        "artist": artist,
        "commission_hub": commission_hub,
        "art_piece_template": art_piece_template,
        "art_collection_ownership_registry": art_collection_ownership_registry,
        "chain_id": chain_id,
        "nft_contract": nft_contract,
        "token_id": token_id
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

def test_code_hash_verification(setup):
    """
    Test the code hash verification functionality
    """
    # Arrange
    deployer = setup["deployer"]
    commission_hub = setup["commission_hub"]
    art_piece_template = setup["art_piece_template"]
    
    # Test that the template is approved
    assert commission_hub.isApprovedArtPieceType(art_piece_template.address), "Template should be approved"
    
    # Deploy another instance of the same contract (same bytecode)
    another_art_piece = project.ArtPiece.deploy(sender=deployer)
    
    # This new instance should also be approved since it has the same bytecode
    assert commission_hub.isApprovedArtPieceType(another_art_piece.address), "Contract with same bytecode should be approved"
    
    # Deploy a different contract type
    # For test purposes, we'll use a simple contract that's not an ArtPiece
    # Assuming there's a SimpleContract in the project
    try:
        different_contract = project.SimpleContract.deploy(sender=deployer)
        
        # This different contract should not be approved
        assert not commission_hub.isApprovedArtPieceType(different_contract.address), "Different contract type should not be approved"
    except AttributeError:
        # If SimpleContract doesn't exist, we'll use different approach
        pass
    
    # Test revoking approval
    commission_hub.approveArtPieceCodeHash(art_piece_template.address, False, sender=deployer)
    
    # Now both template and second instance should no longer be approved
    assert not commission_hub.isApprovedArtPieceType(art_piece_template.address), "Template should no longer be approved"
    assert not commission_hub.isApprovedArtPieceType(another_art_piece.address), "Contract with same bytecode should no longer be approved"
    
    # Test direct hash approval
    # Get code hash from first template
    code_hash = None
    
    # Re-approve via direct hash method
    # Note: In an actual test, we'd use the contract method to get the hash
    # For this demo, we'll re-approve via the contract address method
    commission_hub.approveArtPieceCodeHash(art_piece_template.address, True, sender=deployer)
    
    # Verify both are approved again
    assert commission_hub.isApprovedArtPieceType(art_piece_template.address), "Template should be approved again"
    assert commission_hub.isApprovedArtPieceType(another_art_piece.address), "Contract with same bytecode should be approved again" 