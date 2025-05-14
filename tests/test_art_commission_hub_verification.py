import pytest
from ape import accounts, project
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
    
    # Deploy Mock ArtPiece - To simplify testing, we'll use ArtPiece contracts
    # but in a real test would be better to use a mock that implements isOnCommissionWhitelist
    art_piece_1 = project.ArtPiece.deploy(sender=deployer)
    art_piece_2 = project.ArtPiece.deploy(sender=deployer)
    art_piece_3 = project.ArtPiece.deploy(sender=deployer)
    
    # Approve the ArtPiece template's code hash
    commission_hub.approveArtPieceCodeHash(art_piece_1.address, True, sender=deployer)
    
    return {
        "deployer": deployer,
        "user": user,
        "artist": artist,
        "commission_hub": commission_hub,
        "art_piece_1": art_piece_1,
        "art_piece_2": art_piece_2,
        "art_piece_3": art_piece_3
    }

def test_verify_commission_removes_from_unverified(setup):
    """
    Test that verifyCommission properly removes the art piece from the unverified list
    """
    # Arrange
    deployer = setup["deployer"]
    artist = setup["artist"]
    commission_hub = setup["commission_hub"]
    art_piece = setup["art_piece_1"]
    
    # Submit an unverified commission
    # NOTE: In a real test, we'd mock isOnCommissionWhitelist to return False
    # For now, we'll assume it returns False so submission goes to unverified list
    commission_hub.submitCommission(art_piece.address, sender=artist)
    
    # Check initial state
    assert commission_hub.countUnverifiedCommissions() == 1, "Should have 1 unverified commission"
    assert commission_hub.countVerifiedCommissions() == 0, "Should have 0 verified commissions"
    assert commission_hub.getUnverifiedCount(artist.address) == 1, "Artist should have 1 unverified commission"
    
    # Get the art piece from unverified list to confirm it's there
    unverified_art_pieces = commission_hub.getUnverifiedArtPieces(0, 10)
    assert len(unverified_art_pieces) == 1, "Should have 1 art piece in unverified list"
    assert unverified_art_pieces[0] == art_piece.address, "Art piece should be in unverified list"
    
    # Act: Verify the commission
    commission_hub.verifyCommission(art_piece.address, artist.address, sender=deployer)
    
    # Assert: Check state after verification
    assert commission_hub.countUnverifiedCommissions() == 0, "Should have 0 unverified commissions"
    assert commission_hub.countVerifiedCommissions() == 1, "Should have 1 verified commission"
    assert commission_hub.getUnverifiedCount(artist.address) == 0, "Artist should have 0 unverified commissions"
    
    # Check unverified list - should be empty
    unverified_art_pieces = commission_hub.getUnverifiedArtPieces(0, 10)
    assert len(unverified_art_pieces) == 0, "Unverified list should be empty"
    
    # Check verified list - should contain the art piece
    verified_art_pieces = commission_hub.getVerifiedArtPieces(0, 10)
    assert len(verified_art_pieces) == 1, "Should have 1 art piece in verified list"
    assert verified_art_pieces[0] == art_piece.address, "Art piece should be in verified list"
    
    # Check latest verified art
    latest_verified = commission_hub.getLatestVerifiedArt(1)
    assert len(latest_verified) == 1, "Should have 1 art piece in latest verified"
    assert latest_verified[0] == art_piece.address, "Art piece should be in latest verified"

def test_verify_multiple_commissions(setup):
    """
    Test verifying multiple commissions from the same submitter
    """
    # Arrange
    deployer = setup["deployer"]
    artist = setup["artist"]
    commission_hub = setup["commission_hub"]
    art_piece_1 = setup["art_piece_1"]
    art_piece_2 = setup["art_piece_2"]
    
    # Submit two unverified commissions
    commission_hub.submitCommission(art_piece_1.address, sender=artist)
    commission_hub.submitCommission(art_piece_2.address, sender=artist)
    
    # Check initial state
    assert commission_hub.countUnverifiedCommissions() == 2, "Should have 2 unverified commissions"
    assert commission_hub.getUnverifiedCount(artist.address) == 2, "Artist should have 2 unverified commissions"
    
    # Act: Verify the first commission
    commission_hub.verifyCommission(art_piece_1.address, artist.address, sender=deployer)
    
    # Assert: Check state after first verification
    assert commission_hub.countUnverifiedCommissions() == 1, "Should have 1 unverified commission"
    assert commission_hub.countVerifiedCommissions() == 1, "Should have 1 verified commission"
    assert commission_hub.getUnverifiedCount(artist.address) == 1, "Artist should have 1 unverified commission"
    
    # Check unverified list - should contain second art piece only
    unverified_art_pieces = commission_hub.getUnverifiedArtPieces(0, 10)
    assert len(unverified_art_pieces) == 1, "Should have 1 art piece in unverified list"
    assert unverified_art_pieces[0] == art_piece_2.address, "Art piece 2 should be in unverified list"
    
    # Act: Verify the second commission
    commission_hub.verifyCommission(art_piece_2.address, artist.address, sender=deployer)
    
    # Assert: Check state after second verification
    assert commission_hub.countUnverifiedCommissions() == 0, "Should have 0 unverified commissions"
    assert commission_hub.countVerifiedCommissions() == 2, "Should have 2 verified commissions"
    assert commission_hub.getUnverifiedCount(artist.address) == 0, "Artist should have 0 unverified commissions"

def test_unverify_commission(setup):
    """
    Test the new unverifyCommission function
    """
    # Arrange
    deployer = setup["deployer"]
    artist = setup["artist"]
    commission_hub = setup["commission_hub"]
    art_piece = setup["art_piece_1"]
    
    # First get the art piece into the verified list
    # Option 1: Submit as verified directly (assumes isOnCommissionWhitelist returns True)
    # Option 2: Submit as unverified then verify
    # We'll use option 2 as it's more robust for testing
    
    commission_hub.submitCommission(art_piece.address, sender=artist)
    commission_hub.verifyCommission(art_piece.address, artist.address, sender=deployer)
    
    # Check initial state
    assert commission_hub.countUnverifiedCommissions() == 0, "Should have 0 unverified commissions"
    assert commission_hub.countVerifiedCommissions() == 1, "Should have 1 verified commission"
    assert commission_hub.getUnverifiedCount(artist.address) == 0, "Artist should have 0 unverified commissions"
    
    # Act: Unverify the commission
    commission_hub.unverifyCommission(art_piece.address, artist.address, sender=deployer)
    
    # Assert: Check state after unverification
    assert commission_hub.countUnverifiedCommissions() == 1, "Should have 1 unverified commission"
    assert commission_hub.countVerifiedCommissions() == 0, "Should have 0 verified commissions"
    assert commission_hub.getUnverifiedCount(artist.address) == 1, "Artist should have 1 unverified commission"
    
    # Check unverified list - should contain the art piece
    unverified_art_pieces = commission_hub.getUnverifiedArtPieces(0, 10)
    assert len(unverified_art_pieces) == 1, "Should have 1 art piece in unverified list"
    assert unverified_art_pieces[0] == art_piece.address, "Art piece should be in unverified list"
    
    # Check verified list - should be empty
    verified_art_pieces = commission_hub.getVerifiedArtPieces(0, 10)
    assert len(verified_art_pieces) == 0, "Verified list should be empty"

def test_unverify_commission_permissions(setup):
    """
    Test that only the owner can unverify commissions
    """
    # Arrange
    deployer = setup["deployer"]
    user = setup["user"]
    artist = setup["artist"]
    commission_hub = setup["commission_hub"]
    art_piece = setup["art_piece_1"]
    
    # First get the art piece into the verified list
    commission_hub.submitCommission(art_piece.address, sender=artist)
    commission_hub.verifyCommission(art_piece.address, artist.address, sender=deployer)
    
    # Act & Assert: Non-owner (user) should not be able to unverify
    with pytest.raises(Exception) as excinfo:
        commission_hub.unverifyCommission(art_piece.address, artist.address, sender=user)
    
    # Check error message
    error_message = str(excinfo.value).lower()
    assert "not authorized" in error_message or "auth" in error_message, "Error should mention authorization"
    
    # State should remain unchanged
    assert commission_hub.countVerifiedCommissions() == 1, "Should still have 1 verified commission"
    assert commission_hub.countUnverifiedCommissions() == 0, "Should still have 0 unverified commissions"

def test_unverify_nonexistent_commission(setup):
    """
    Test that unverifying a nonexistent commission fails appropriately
    """
    # Arrange
    deployer = setup["deployer"]
    artist = setup["artist"]
    commission_hub = setup["commission_hub"]
    art_piece = setup["art_piece_1"]
    nonexistent_art_piece = setup["art_piece_3"]  # Not submitted yet
    
    # Submit and verify one commission to have some state
    commission_hub.submitCommission(art_piece.address, sender=artist)
    commission_hub.verifyCommission(art_piece.address, artist.address, sender=deployer)
    
    # Act & Assert: Trying to unverify a piece that's not in verified list should fail
    with pytest.raises(Exception) as excinfo:
        commission_hub.unverifyCommission(nonexistent_art_piece.address, artist.address, sender=deployer)
    
    # Check error message
    error_message = str(excinfo.value).lower()
    assert "not found" in error_message, "Error should mention the art piece not being found"
    
    # State should remain unchanged
    assert commission_hub.countVerifiedCommissions() == 1, "Should still have 1 verified commission"
    assert commission_hub.countUnverifiedCommissions() == 0, "Should still have 0 unverified commissions"

def test_verify_unverify_cycle(setup):
    """
    Test a full cycle of verify -> unverify -> verify again
    """
    # Arrange
    deployer = setup["deployer"]
    artist = setup["artist"]
    commission_hub = setup["commission_hub"]
    art_piece = setup["art_piece_1"]
    
    # Submit as unverified
    commission_hub.submitCommission(art_piece.address, sender=artist)
    
    # Initial state
    assert commission_hub.countUnverifiedCommissions() == 1, "Should have 1 unverified commission"
    assert commission_hub.countVerifiedCommissions() == 0, "Should have 0 verified commissions"
    
    # Step 1: Verify the commission
    commission_hub.verifyCommission(art_piece.address, artist.address, sender=deployer)
    
    # Check state after verification
    assert commission_hub.countUnverifiedCommissions() == 0, "Should have 0 unverified commissions"
    assert commission_hub.countVerifiedCommissions() == 1, "Should have 1 verified commission"
    
    # Step 2: Unverify the commission
    commission_hub.unverifyCommission(art_piece.address, artist.address, sender=deployer)
    
    # Check state after unverification
    assert commission_hub.countUnverifiedCommissions() == 1, "Should have 1 unverified commission"
    assert commission_hub.countVerifiedCommissions() == 0, "Should have 0 verified commissions"
    
    # Step 3: Verify the commission again
    commission_hub.verifyCommission(art_piece.address, artist.address, sender=deployer)
    
    # Check final state
    assert commission_hub.countUnverifiedCommissions() == 0, "Should have 0 unverified commissions"
    assert commission_hub.countVerifiedCommissions() == 1, "Should have 1 verified commission"
    
    # Get the art piece from verified list
    verified_art_pieces = commission_hub.getVerifiedArtPieces(0, 10)
    assert len(verified_art_pieces) == 1, "Should have 1 art piece in verified list"
    assert verified_art_pieces[0] == art_piece.address, "Art piece should be in verified list" 