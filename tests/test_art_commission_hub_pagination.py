import pytest
from ape import accounts, project
import time
from eth_utils import to_checksum_address
from eth_account import Account
import eth_utils
import secrets

# Define constant for zero address
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
GENERIC_ART_COMMISSION_HUB_CONTRACT = "0x1000000000000000000000000000000000000001"
GENERIC_ART_COMMISSION_HUB_CHAIN_ID = 1

# Define global test data constants
TEST_TOKEN_URI_DATA = b"data:application/json;base64,eyJuYW1lIjoiVGVzdCBBcnR3b3JrIiwiZGVzY3JpcHRpb24iOiJUaGlzIGlzIGEgdGVzdCBkZXNjcmlwdGlvbiBmb3IgdGhlIGFydHdvcmsiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTndJREFBQUFCbEJNVkVYLy8vL24vNGJsQUFBQUJYUlNUbk1BUUtKZVVtUktBQUFBQWtsRVFWUUkxMkJnQUFNRE1BQUJoVUFCQUVtQ0FVQUFBQUJKUlU1RXJrSmdnZz09In0="
TEST_TITLE = "Test Artwork"
TEST_DESCRIPTION = "This is a test description for the artwork"
TEST_TOKEN_URI_DATA_FORMAT = "avif"
TEST_AI_GENERATED = False

@pytest.fixture(scope="function")
def setup():
    """Setup function that deploys and initializes all contracts needed for testing"""
    deployer = accounts.test_accounts[0]
    user = accounts.test_accounts[1]
    artist = accounts.test_accounts[2]
    owner = accounts.test_accounts[3]
    
    # Deploy all templates
    profile_template = project.Profile.deploy(sender=deployer)
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)

    # Deploy ArtEdition1155 template
    art_edition_1155_template = project.ArtEdition1155.deploy(sender=deployer)
    
    # Deploy ArtSales1155 template
    art_sales_1155_template = project.ArtSales1155.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy factory registry
    profile_factory = project.ProfileFactoryAndRegistry.deploy(
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
    profile_factory.linkArtCommissionHubOwnersContract(art_commission_hub_owners.address, sender=deployer)
    art_commission_hub_owners.linkProfileFactoryAndRegistry(profile_factory.address, sender=deployer)
    
    # Create a generic commission hub for the owner
    art_commission_hub_owners.createGenericCommissionHub(
        owner.address,  # Owner
        sender=deployer
    )
    
    # Get the hub address
    hub_address = art_commission_hub_owners.getCommissionHubsByOwnerWithOffset(owner.address, 0, 1, False)[0]
    commission_hub = project.ArtCommissionHub.at(hub_address)
    
    # Create profiles for test accounts if they don't exist
    if not profile_factory.hasProfile(user.address):
        profile_factory.createProfile(user.address, sender=deployer)
    if not profile_factory.hasProfile(artist.address):
        profile_factory.createProfile(artist.address, sender=deployer)
    
    # Get profile addresses
    user_profile_address = profile_factory.getProfile(user.address)
    artist_profile_address = profile_factory.getProfile(artist.address)
    owner_profile_address = profile_factory.getProfile(owner.address)
    
    return {
        "deployer": deployer,
        "user": user,
        "artist": artist,
        "owner": owner,
        "profile_factory": profile_factory,
        "art_commission_hub_owners": art_commission_hub_owners,
        "commission_hub": commission_hub,
        "art_edition_1155_template": art_edition_1155_template,
        "art_sales_1155_template": art_sales_1155_template,
        "art_piece_template": art_piece_template
    }

@pytest.fixture
def many_addresses():
    """Generate many valid Ethereum addresses for testing"""
    addresses = []
    for i in range(60):
        priv_key = secrets.token_hex(32)
        account = Account.from_key(priv_key)
        addresses.append(eth_utils.to_checksum_address(account.address))
    return addresses

def create_verified_art_piece(setup, commissioner, artist, title_suffix=""):
    """Helper function to create an art piece that will go to verified list"""
    # Whitelist the artist so their commissions go directly to verified list when auto-submitted
    setup["commission_hub"].updateWhitelistOrBlacklist(artist, True, True, sender=setup["owner"])
    
    # Get the artist profile to create the art piece properly
    artist_profile_address = setup["profile_factory"].getProfile(artist)
    artist_profile = project.Profile.at(artist_profile_address)
    
    # Create art piece through the Profile (this will automatically verify the artist)
    tx_receipt = artist_profile.createArtPiece(
        setup["art_piece_template"].address,  # _art_piece_template
        TEST_TOKEN_URI_DATA,         # _token_uri_data
        TEST_TOKEN_URI_DATA_FORMAT,  # _token_uri_data_format
        f"{TEST_TITLE}{title_suffix}",  # _title
        TEST_DESCRIPTION,            # _description
        True,                        # _as_artist
        commissioner,                # _other_party (commissioner)
        TEST_AI_GENERATED,           # _ai_generated
        setup["commission_hub"].address,  # _art_commission_hub
        False,                       # _is_profile_art
        sender=artist
    )
    
    # Get the art piece address from the artist's recent art pieces
    art_pieces = artist_profile.getArtPiecesByOffset(0, 1, True)
    assert len(art_pieces) > 0, "No art pieces found in the artist's profile"
    art_piece_address = art_pieces[0]
    
    art_piece = project.ArtPiece.at(art_piece_address)
    
    # Approve the ArtPiece instance in ArtCommissionHubOwners
    setup["art_commission_hub_owners"].setApprovedArtPiece(art_piece.address, True, sender=setup["deployer"])
    
    # Complete verification by having commissioner verify (which will auto-submit to verified list)
    art_piece.verifyAsCommissioner(sender=commissioner)
    
    return art_piece

def create_unverified_art_piece(setup, commissioner, artist, title_suffix=""):
    """Helper function to create an art piece that will go to unverified list"""
    # Ensure the artist is NOT whitelisted so their commissions go to unverified list
    setup["commission_hub"].updateWhitelistOrBlacklist(artist, True, False, sender=setup["owner"])
    
    # Get the artist profile to create the art piece properly
    artist_profile_address = setup["profile_factory"].getProfile(artist)
    artist_profile = project.Profile.at(artist_profile_address)
    
    # Create art piece through the Profile (this will automatically verify the artist)
    tx_receipt = artist_profile.createArtPiece(
        setup["art_piece_template"].address,  # _art_piece_template
        TEST_TOKEN_URI_DATA,         # _token_uri_data
        TEST_TOKEN_URI_DATA_FORMAT,  # _token_uri_data_format
        f"{TEST_TITLE}{title_suffix}",  # _title
        TEST_DESCRIPTION,            # _description
        True,                        # _as_artist
        commissioner,                # _other_party (commissioner)
        TEST_AI_GENERATED,           # _ai_generated
        setup["commission_hub"].address,  # _art_commission_hub
        False,                       # _is_profile_art
        sender=artist
    )
    
    # Get the art piece address from the artist's recent art pieces
    art_pieces = artist_profile.getArtPiecesByOffset(0, 1, True)
    assert len(art_pieces) > 0, "No art pieces found in the artist's profile"
    art_piece_address = art_pieces[0]
    
    art_piece = project.ArtPiece.at(art_piece_address)
    
    # Approve the ArtPiece instance in ArtCommissionHubOwners
    setup["art_commission_hub_owners"].setApprovedArtPiece(art_piece.address, True, sender=setup["deployer"])
    
    # Complete verification by having commissioner verify (which will auto-submit to unverified list)
    art_piece.verifyAsCommissioner(sender=commissioner)
    
    return art_piece

def create_art_piece(setup, commissioner, artist, title_suffix=""):
    """Helper function to create and verify an art piece - DEPRECATED, use create_verified_art_piece or create_unverified_art_piece"""
    return create_unverified_art_piece(setup, commissioner, artist, title_suffix)

def test_empty_arrays_pagination(setup):
    """Test all pagination methods with empty arrays"""
    commission_hub = setup["commission_hub"]
    
    # Test all verified art pagination methods with empty array
    assert len(commission_hub.getVerifiedArtPiecesByOffset(0, 10)) == 0
    assert len(commission_hub.getBatchVerifiedArtPieces(0, 10)) == 0
    assert len(commission_hub.getRecentVerifiedArtPieces(10)) == 0
    assert len(commission_hub.getVerifiedArtPieces(0, 10)) == 0
    
    # Test all unverified art pagination methods with empty array
    assert len(commission_hub.getUnverifiedArtPiecesByOffset(0, 10)) == 0
    assert len(commission_hub.getBatchUnverifiedArtPieces(0, 10)) == 0
    assert len(commission_hub.getRecentUnverifiedArtPieces(10)) == 0
    assert len(commission_hub.getUnverifiedArtPieces(0, 10)) == 0
    
    # Test with large offsets and counts
    assert len(commission_hub.getVerifiedArtPiecesByOffset(100, 50)) == 0
    assert len(commission_hub.getUnverifiedArtPiecesByOffset(100, 50)) == 0
    
    # Test getArtPieceByIndex with empty arrays (should revert)
    with pytest.raises(Exception):
        commission_hub.getArtPieceByIndex(True, 0)
    
    with pytest.raises(Exception):
        commission_hub.getArtPieceByIndex(False, 0)

def test_single_verified_art_piece_pagination(setup):
    """Test pagination with a single verified art piece"""
    commission_hub = setup["commission_hub"]
    
    # Create verified art piece (auto-submits to verified list)
    art_piece = create_verified_art_piece(setup, setup["owner"], setup["artist"], " Single")
    
    # Verify counts
    assert commission_hub.countVerifiedArtCommissions() == 1
    assert commission_hub.countUnverifiedArtCommissions() == 0
    
    # Test getVerifiedArtPiecesByOffset
    result = commission_hub.getVerifiedArtPiecesByOffset(0, 1)
    assert len(result) == 1
    assert result[0] == art_piece.address
    
    result = commission_hub.getVerifiedArtPiecesByOffset(0, 10)  # Request more than available
    assert len(result) == 1
    assert result[0] == art_piece.address
    
    result = commission_hub.getVerifiedArtPiecesByOffset(1, 1)  # Offset beyond bounds
    assert len(result) == 0

def test_multiple_verified_art_pieces_pagination(setup):
    """Test pagination with multiple verified art pieces"""
    commission_hub = setup["commission_hub"]
    
    # Create and submit 5 verified art pieces
    art_pieces = []
    for i in range(5):
        art_piece = create_verified_art_piece(setup, setup["owner"], setup["artist"], f" Verified {i}")
        art_pieces.append(art_piece.address)
    
    assert commission_hub.countVerifiedArtCommissions() == 5
    
    # Test getVerifiedArtPiecesByOffset - first 3 items
    result = commission_hub.getVerifiedArtPiecesByOffset(0, 3)
    assert len(result) == 3
    assert result[0] == art_pieces[0]
    assert result[1] == art_pieces[1]
    assert result[2] == art_pieces[2]
    
    # Test getVerifiedArtPiecesByOffset - skip first 2, get next 2
    result = commission_hub.getVerifiedArtPiecesByOffset(2, 2)
    assert len(result) == 2
    assert result[0] == art_pieces[2]
    assert result[1] == art_pieces[3]
    
    # Test getVerifiedArtPiecesByOffset - start at index 4, only 1 available
    result = commission_hub.getVerifiedArtPiecesByOffset(4, 10)
    assert len(result) == 1
    assert result[0] == art_pieces[4]
    
    # Test getVerifiedArtPiecesByOffset - offset beyond bounds
    result = commission_hub.getVerifiedArtPiecesByOffset(5, 2)
    assert len(result) == 0
    
    # Test getVerifiedArtPiecesByOffset - get all items
    result = commission_hub.getVerifiedArtPiecesByOffset(0, 50)
    assert len(result) == 5
    for i in range(5):
        assert result[i] == art_pieces[i]

def test_pagination_edge_cases(setup):
    """Test edge cases for pagination"""
    commission_hub = setup["commission_hub"]
    
    # Create 3 verified art pieces
    art_pieces = []
    for i in range(3):
        art_piece = create_verified_art_piece(setup, setup["owner"], setup["artist"], f" Edge {i}")
        art_pieces.append(art_piece.address)
    
    # Test requesting 5 items when there are only 3
    result = commission_hub.getVerifiedArtPiecesByOffset(0, 5)
    assert len(result) == 3  # Should return only available items
    
    # Test accessing 2nd page when there aren't enough items
    result = commission_hub.getVerifiedArtPiecesByOffset(2, 2)  # Page size 2, page 1 (offset 2)
    assert len(result) == 1  # Should return only 1 item (the last one)
    assert result[0] == art_pieces[2]
    
    # Test accessing 3rd page when there aren't enough items  
    result = commission_hub.getVerifiedArtPiecesByOffset(4, 2)  # Page size 2, page 2 (offset 4)
    assert len(result) == 0  # Should return empty array
    
    # Test count = 0
    result = commission_hub.getVerifiedArtPiecesByOffset(0, 0)
    assert len(result) == 0

def test_unverified_art_pieces_pagination(setup):
    """Test pagination with unverified art pieces"""
    commission_hub = setup["commission_hub"]
    
    # Create and submit 4 unverified art pieces (submitted by user, not owner)
    unverified_pieces = []
    for i in range(4):
        art_piece = create_unverified_art_piece(setup, setup["user"], setup["artist"], f" Unverified {i}")
        unverified_pieces.append(art_piece.address)
    
    assert commission_hub.countUnverifiedArtCommissions() == 4
    assert commission_hub.countVerifiedArtCommissions() == 0
    
    # Test getUnverifiedArtPiecesByOffset - first 2 items
    result = commission_hub.getUnverifiedArtPiecesByOffset(0, 2)
    assert len(result) == 2
    assert result[0] == unverified_pieces[0]
    assert result[1] == unverified_pieces[1]
    
    # Test getUnverifiedArtPiecesByOffset - offset beyond bounds
    result = commission_hub.getUnverifiedArtPiecesByOffset(4, 2)
    assert len(result) == 0
    
    # Test getBatchUnverifiedArtPieces
    result = commission_hub.getBatchUnverifiedArtPieces(1, 2)
    assert len(result) == 2
    assert result[0] == unverified_pieces[1]
    assert result[1] == unverified_pieces[2]

def test_verify_unverify_commission_effects(setup):
    """Test how verifying and unverifying commissions affects pagination"""
    commission_hub = setup["commission_hub"]
    
    # Create 3 unverified art pieces
    unverified_pieces = []
    for i in range(3):
        art_piece = create_unverified_art_piece(setup, setup["user"], setup["artist"], f" Verify Test {i}")
        unverified_pieces.append(art_piece.address)
    
    # Initial state: 0 verified, 3 unverified
    assert commission_hub.countVerifiedArtCommissions() == 0
    assert commission_hub.countUnverifiedArtCommissions() == 3
    
    # Verify the middle piece
    commission_hub.verifyCommission(unverified_pieces[1], sender=setup["owner"])
    
    # Should now have 1 verified, 2 unverified
    assert commission_hub.countVerifiedArtCommissions() == 1
    assert commission_hub.countUnverifiedArtCommissions() == 2
    
    # Check verified list contains the verified piece
    verified_result = commission_hub.getVerifiedArtPiecesByOffset(0, 10)
    assert len(verified_result) == 1
    assert verified_result[0] == unverified_pieces[1]

def test_recent_methods_functionality(setup):
    """Test getRecent* methods specifically"""
    commission_hub = setup["commission_hub"]
    
    # Create 6 verified art pieces
    verified_pieces = []
    for i in range(6):
        art_piece = create_verified_art_piece(setup, setup["owner"], setup["artist"], f" Recent Verified {i}")
        verified_pieces.append(art_piece.address)
    
    # Test getRecentVerifiedArtPieces
    result = commission_hub.getRecentVerifiedArtPieces(3)
    assert len(result) == 3
    # Should return the last 3 items
    assert result[0] == verified_pieces[3]
    assert result[1] == verified_pieces[4] 
    assert result[2] == verified_pieces[5]
    
    result = commission_hub.getRecentVerifiedArtPieces(10)  # More than available
    assert len(result) == 6  # Should return all 6

def test_batch_operations_effects(setup):
    """Test how bulk verify/unverify operations affect pagination"""
    commission_hub = setup["commission_hub"]
    
    # Create 5 unverified art pieces
    unverified_pieces = []
    for i in range(5):
        art_piece = create_unverified_art_piece(setup, setup["user"], setup["artist"], f" Bulk Test {i}")
        unverified_pieces.append(art_piece.address)
    
    # Initial state: 0 verified, 5 unverified
    assert commission_hub.countVerifiedArtCommissions() == 0
    assert commission_hub.countUnverifiedArtCommissions() == 5
    
    # Bulk verify first 3 pieces
    commission_hub.bulkVerifyCommissions(unverified_pieces[:3], sender=setup["owner"])
    
    # Should now have 3 verified, 2 unverified
    assert commission_hub.countVerifiedArtCommissions() == 3
    assert commission_hub.countUnverifiedArtCommissions() == 2

def test_boundary_conditions(setup):
    """Test boundary conditions and edge cases"""
    commission_hub = setup["commission_hub"]
    
    # Create exactly 3 art pieces for precise boundary testing
    art_pieces = []
    for i in range(3):
        art_piece = create_verified_art_piece(setup, setup["owner"], setup["artist"], f" Boundary {i}")
        art_pieces.append(art_piece.address)
    
    # Test accessing exactly the last item
    result = commission_hub.getVerifiedArtPiecesByOffset(2, 1)
    assert len(result) == 1
    assert result[0] == art_pieces[2]
    
    # Test accessing exactly at the boundary (one past the end)
    result = commission_hub.getVerifiedArtPiecesByOffset(3, 1)
    assert len(result) == 0
    
    # Test accessing with count that exactly matches remaining items
    result = commission_hub.getVerifiedArtPiecesByOffset(1, 2)
    assert len(result) == 2
    assert result[0] == art_pieces[1]
    assert result[1] == art_pieces[2]

def test_large_offset_scenarios(setup):
    """Test scenarios with large offsets"""
    commission_hub = setup["commission_hub"]
    
    # Create 10 verified art pieces
    art_pieces = []
    for i in range(10):
        art_piece = create_verified_art_piece(setup, setup["owner"], setup["artist"], f" Large {i}")
        art_pieces.append(art_piece.address)
    
    # Test pagination through large array
    page_size = 3
    
    # Page 0: offset 0, count 3 -> [0, 1, 2]
    result = commission_hub.getVerifiedArtPiecesByOffset(0, page_size)
    assert len(result) == 3
    for i in range(3):
        assert result[i] == art_pieces[i]
    
    # Page 1: offset 3, count 3 -> [3, 4, 5]
    result = commission_hub.getVerifiedArtPiecesByOffset(3, page_size)
    assert len(result) == 3
    for i in range(3):
        assert result[i] == art_pieces[3 + i]
    
    # Page 2: offset 6, count 3 -> [6, 7, 8]
    result = commission_hub.getVerifiedArtPiecesByOffset(6, page_size)
    assert len(result) == 3
    for i in range(3):
        assert result[i] == art_pieces[6 + i]
    
    # Page 3: offset 9, count 3 -> [9] (only 1 available)
    result = commission_hub.getVerifiedArtPiecesByOffset(9, page_size)
    assert len(result) == 1
    assert result[0] == art_pieces[9]
    
    # Page 4: offset 12, count 3 -> [] (out of bounds)
    result = commission_hub.getVerifiedArtPiecesByOffset(12, page_size)
    assert len(result) == 0

def test_mixed_verified_unverified_scenarios(setup):
    """Test scenarios with both verified and unverified art pieces"""
    commission_hub = setup["commission_hub"]
    
    # Create 3 verified art pieces (submitted by owner)
    verified_pieces = []
    for i in range(3):
        art_piece = create_verified_art_piece(setup, setup["owner"], setup["artist"], f" Mixed Verified {i}")
        verified_pieces.append(art_piece.address)
    
    # Create 2 unverified art pieces (submitted by user)
    unverified_pieces = []
    for i in range(2):
        art_piece = create_unverified_art_piece(setup, setup["user"], setup["artist"], f" Mixed Unverified {i}")
        unverified_pieces.append(art_piece.address)
    
    # Verify counts
    assert commission_hub.countVerifiedArtCommissions() == 3
    assert commission_hub.countUnverifiedArtCommissions() == 2
    
    # Test verified pagination
    result = commission_hub.getVerifiedArtPiecesByOffset(0, 10)
    assert len(result) == 3
    for i in range(3):
        assert result[i] == verified_pieces[i]
    
    # Test unverified pagination
    result = commission_hub.getUnverifiedArtPiecesByOffset(0, 10)
    assert len(result) == 2
    for i in range(2):
        assert result[i] == unverified_pieces[i]

def test_count_zero_and_edge_values(setup):
    """Test edge cases with count values"""
    commission_hub = setup["commission_hub"]
    
    # Create a few art pieces
    for i in range(3):
        art_piece = create_verified_art_piece(setup, setup["owner"], setup["artist"], f" Count Test {i}")
    
    # Test count = 0
    result = commission_hub.getVerifiedArtPiecesByOffset(0, 0)
    assert len(result) == 0
    
    # Test count = 1
    result = commission_hub.getVerifiedArtPiecesByOffset(0, 1)
    assert len(result) == 1
    
    # Test very large count
    result = commission_hub.getVerifiedArtPiecesByOffset(0, 1000)
    assert len(result) == 3  # Should return actual count, not 1000

def test_method_consistency(setup):
    """Test that different pagination methods return consistent results"""
    commission_hub = setup["commission_hub"]
    
    # Create 5 verified art pieces
    verified_pieces = []
    for i in range(5):
        art_piece = create_verified_art_piece(setup, setup["owner"], setup["artist"], f" Consistency {i}")
        verified_pieces.append(art_piece.address)
    
    # Compare getVerifiedArtPiecesByOffset vs getBatchVerifiedArtPieces
    result1 = commission_hub.getVerifiedArtPiecesByOffset(1, 3)
    result2 = commission_hub.getBatchVerifiedArtPieces(1, 3)
    assert len(result1) == len(result2)
    for i in range(len(result1)):
        assert result1[i] == result2[i]
    
    # Test getArtPieceByIndex consistency
    for i in range(5):
        indexed_piece = commission_hub.getArtPieceByIndex(True, i)
        assert indexed_piece == verified_pieces[i] 