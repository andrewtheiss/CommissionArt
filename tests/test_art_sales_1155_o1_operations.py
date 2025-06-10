import pytest
from ape import accounts, project
import time
import base64
import json

# Test data for creating art pieces
TEST_TOKEN_URI_DATA = b"data:application/json;base64,eyJuYW1lIjoiVGVzdCBBcnR3b3JrIiwiZGVzY3JpcHRpb24iOiJUaGlzIGlzIGEgdGVzdCBkZXNjcmlwdGlvbiBmb3IgdGhlIGFydHdvcmsiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJCTndJREFBQUFCbEJNVkVYLy8vL24vNGJsQUFBQUJYUlNUbk1BUUtKZVVtUktBQUFBQWtsRVFWUUkxMkJnQUFNRE1BQUJoVUFCQUVtQ0FVQUFBQUJKUlU1RXJrSmdnZz09In0="
TEST_TITLE = "Test Artwork"
TEST_DESCRIPTION = "This is a test description for the artwork"
TEST_TOKEN_URI_DATA_FORMAT = "avif"
TEST_AI_GENERATED = False
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

# Extract JSON metadata from the base64 data URL for tests
def get_test_token_uri_json():
    """Extract the JSON metadata from TEST_TOKEN_URI_DATA"""
    data_url = TEST_TOKEN_URI_DATA.decode('utf-8')
    return data_url

TEST_TOKEN_URI_JSON = get_test_token_uri_json()

# --- Fixture for ArtSales1155 O(1) operations tests ---
@pytest.fixture
def setup():
    deployer = accounts.test_accounts[0]
    owner = accounts.test_accounts[1]
    artist = accounts.test_accounts[2]
    user1 = accounts.test_accounts[3]
    user2 = accounts.test_accounts[4]
    user3 = accounts.test_accounts[5]
    user4 = accounts.test_accounts[6]
    user5 = accounts.test_accounts[7]
    user6 = accounts.test_accounts[8]
    user7 = accounts.test_accounts[9]

    # Deploy templates
    profile_template = project.Profile.deploy(sender=deployer)
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    art_edition_1155_template = project.ArtEdition1155.deploy(sender=deployer)
    art_sales_1155_template = project.ArtSales1155.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy ProfileFactoryAndRegistry
    profile_factory_and_registry = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address, profile_social_template.address, commission_hub_template.address, 
        art_edition_1155_template.address, art_sales_1155_template.address,
        sender=deployer
    )
    
    # Deploy ArtCommissionHubOwners
    art_commission_hub_owners = project.ArtCommissionHubOwners.deploy(
        deployer.address,
        commission_hub_template.address,
        art_piece_template.address,
        sender=deployer
    )
    
    # Link contracts
    profile_factory_and_registry.linkArtCommissionHubOwnersContract(art_commission_hub_owners.address, sender=deployer)
    art_commission_hub_owners.linkProfileFactoryAndRegistry(profile_factory_and_registry.address, sender=deployer)
    
    # Create profiles
    profile_factory_and_registry.createProfile(sender=owner)
    profile_factory_and_registry.createProfile(sender=artist)
    
    # Get profile addresses
    owner_profile_address = profile_factory_and_registry.getProfile(owner.address)
    artist_profile_address = profile_factory_and_registry.getProfile(artist.address)
    
    # Create profile objects
    owner_profile = project.Profile.at(owner_profile_address)
    artist_profile = project.Profile.at(artist_profile_address)
    
    # Set artist flag - this auto-creates ArtSales1155
    artist_profile.setIsArtist(True, sender=artist)
    
    # Deploy ArtSales1155 for owner
    owner_sales = project.ArtSales1155.deploy(sender=deployer)
    owner_sales.initialize(owner_profile_address, owner.address, profile_factory_and_registry.address, sender=deployer)
    
    # Get auto-created ArtSales1155 for artist
    artist_sales_address = artist_profile.artSales1155()
    artist_sales = project.ArtSales1155.at(artist_sales_address)
    
    # Link ArtSales1155 to owner profile
    owner_profile.setArtSales1155(owner_sales.address, sender=owner)

    return {
        "deployer": deployer,
        "owner": owner,
        "artist": artist,
        "user1": user1,
        "user2": user2,
        "user3": user3,
        "user4": user4,
        "user5": user5,
        "user6": user6,
        "user7": user7,
        "profile_factory_and_registry": profile_factory_and_registry,
        "owner_profile": owner_profile,
        "artist_profile": artist_profile,
        "owner_sales": owner_sales,
        "artist_sales": artist_sales,
        "art_piece_template": art_piece_template,
    }

def normalize_address(address):
    return address.lower()

# ================================================================================================
# ARTIST ERC1155s O(1) OPERATIONS TESTS
# ================================================================================================

def test_artist_erc1155_exists_o1(setup):
    """Test O(1) artistErc1155Exists function"""
    artist = setup["artist"]
    artist_sales = setup["artist_sales"]
    
    test_addresses = [
        "0x1111111111111111111111111111111111111111",
        "0x2222222222222222222222222222222222222222",
        "0x3333333333333333333333333333333333333333"
    ]
    
    # Initially nothing should exist
    for addr in test_addresses:
        assert not artist_sales.artistErc1155Exists(addr), f"Address {addr} should not exist initially"
    
    # Add addresses and test existence
    for i, addr in enumerate(test_addresses):
        artist_sales.addAdditionalMintErc1155(addr, sender=artist)
        
        # Test that the added address exists
        assert artist_sales.artistErc1155Exists(addr), f"Address {addr} should exist after adding"
        
        # Test that previously added addresses still exist
        for j in range(i):
            assert artist_sales.artistErc1155Exists(test_addresses[j]), f"Previously added address {test_addresses[j]} should still exist"
        
        # Test that not-yet-added addresses don't exist
        for k in range(i+1, len(test_addresses)):
            assert not artist_sales.artistErc1155Exists(test_addresses[k]), f"Not-yet-added address {test_addresses[k]} should not exist"
    
    # Remove middle address and test
    artist_sales.removeAdditionalMintErc1155(test_addresses[1], sender=artist)
    assert not artist_sales.artistErc1155Exists(test_addresses[1]), "Removed address should not exist"
    assert artist_sales.artistErc1155Exists(test_addresses[0]), "Other addresses should still exist"
    assert artist_sales.artistErc1155Exists(test_addresses[2]), "Other addresses should still exist"

def test_artist_erc1155_position_o1(setup):
    """Test O(1) getArtistErc1155Position function"""
    artist = setup["artist"]
    artist_sales = setup["artist_sales"]
    
    test_addresses = [
        "0x1111111111111111111111111111111111111111",
        "0x2222222222222222222222222222222222222222",
        "0x3333333333333333333333333333333333333333",
        "0x4444444444444444444444444444444444444444",
        "0x5555555555555555555555555555555555555555"
    ]
    
    # Test non-existent address returns max value
    non_existent = "0x9999999999999999999999999999999999999999"
    assert artist_sales.getArtistErc1155Position(non_existent) == 2**256 - 1, "Non-existent address should return max uint256"
    
    # Add addresses and test positions
    for i, addr in enumerate(test_addresses):
        artist_sales.addAdditionalMintErc1155(addr, sender=artist)
        
        # Test position of newly added address
        position = artist_sales.getArtistErc1155Position(addr)
        assert position == i, f"Address {addr} should be at position {i}, got {position}"
        
        # Test positions of all previously added addresses
        for j in range(i):
            prev_position = artist_sales.getArtistErc1155Position(test_addresses[j])
            assert prev_position == j, f"Address {test_addresses[j]} should be at position {j}, got {prev_position}"
    
    # Test position after removal (swap-and-pop behavior)
    # Remove address at position 2 (middle)
    artist_sales.removeAdditionalMintErc1155(test_addresses[2], sender=artist)
    
    # The last address should now be at position 2 (swapped)
    last_addr_position = artist_sales.getArtistErc1155Position(test_addresses[4])
    assert last_addr_position == 2, f"Last address should be swapped to position 2, got {last_addr_position}"
    
    # Removed address should return max value
    removed_position = artist_sales.getArtistErc1155Position(test_addresses[2])
    assert removed_position == 2**256 - 1, "Removed address should return max uint256"

def test_artist_erc1155_at_index_o1(setup):
    """Test O(1) getArtistErc1155AtIndex function"""
    artist = setup["artist"]
    artist_sales = setup["artist_sales"]
    
    test_addresses = [
        "0x1111111111111111111111111111111111111111",
        "0x2222222222222222222222222222222222222222",
        "0x3333333333333333333333333333333333333333"
    ]
    
    # Add addresses
    for addr in test_addresses:
        artist_sales.addAdditionalMintErc1155(addr, sender=artist)
    
    # Test accessing by index
    for i, expected_addr in enumerate(test_addresses):
        actual_addr = artist_sales.getArtistErc1155AtIndex(i)
        assert normalize_address(actual_addr) == normalize_address(expected_addr), f"Index {i} should return {expected_addr}, got {actual_addr}"

def test_artist_erc1155_by_offset_pagination(setup):
    """Test new getArtistErc1155sByOffset function with forward and reverse pagination"""
    artist = setup["artist"]
    artist_sales = setup["artist_sales"]
    
    # Create 10 test addresses
    test_addresses = [f"0x{str(i).zfill(40)}" for i in range(1, 11)]
    
    # Add all addresses
    for addr in test_addresses:
        artist_sales.addAdditionalMintErc1155(addr, sender=artist)
    
    # Test forward pagination
    # Get first 3 items (offset 0, count 3)
    forward_page1 = artist_sales.getArtistErc1155sByOffset(0, 3, False)
    assert len(forward_page1) == 3
    for i in range(3):
        assert normalize_address(forward_page1[i]) == normalize_address(test_addresses[i])
    
    # Get next 3 items (offset 3, count 3)
    forward_page2 = artist_sales.getArtistErc1155sByOffset(3, 3, False)
    assert len(forward_page2) == 3
    for i in range(3):
        assert normalize_address(forward_page2[i]) == normalize_address(test_addresses[i + 3])
    
    # Test reverse pagination
    # Get last 3 items (offset 0 from end, count 3)
    reverse_page1 = artist_sales.getArtistErc1155sByOffset(0, 3, True)
    assert len(reverse_page1) == 3
    expected_reverse = [test_addresses[9], test_addresses[8], test_addresses[7]]
    for i in range(3):
        assert normalize_address(reverse_page1[i]) == normalize_address(expected_reverse[i])
    
    # Get next 3 items in reverse (offset 3 from end, count 3)
    reverse_page2 = artist_sales.getArtistErc1155sByOffset(3, 3, True)
    assert len(reverse_page2) == 3
    expected_reverse2 = [test_addresses[6], test_addresses[5], test_addresses[4]]
    for i in range(3):
        assert normalize_address(reverse_page2[i]) == normalize_address(expected_reverse2[i])
    
    # Test edge cases
    # Empty result when offset beyond bounds
    empty_result = artist_sales.getArtistErc1155sByOffset(20, 5, False)
    assert len(empty_result) == 0
    
    # Partial result when count exceeds remaining items
    partial_result = artist_sales.getArtistErc1155sByOffset(8, 5, False)
    assert len(partial_result) == 2  # Only 2 items remaining
    assert normalize_address(partial_result[0]) == normalize_address(test_addresses[8])
    assert normalize_address(partial_result[1]) == normalize_address(test_addresses[9])

def test_artist_erc1155_o1_performance_consistency(setup):
    """Test that O(1) operations maintain performance with large datasets"""
    artist = setup["artist"]
    artist_sales = setup["artist_sales"]
    
    # Add many addresses to test O(1) behavior
    large_dataset = [f"0x{str(i).zfill(40)}" for i in range(1, 101)]  # 100 addresses
    
    # Time adding addresses (should be O(1) per add)
    for addr in large_dataset:
        artist_sales.addAdditionalMintErc1155(addr, sender=artist)
    
    # Test existence checks are O(1) regardless of dataset size
    # Check first, middle, and last addresses
    test_indices = [0, 50, 99]
    for idx in test_indices:
        addr = large_dataset[idx]
        assert artist_sales.artistErc1155Exists(addr), f"Address at index {idx} should exist"
        
        position = artist_sales.getArtistErc1155Position(addr)
        assert position == idx, f"Address at index {idx} should have position {idx}"
        
        addr_at_index = artist_sales.getArtistErc1155AtIndex(idx)
        assert normalize_address(addr_at_index) == normalize_address(addr), f"Index {idx} should return correct address"
    
    # Test removal is O(1) (remove middle element)
    middle_addr = large_dataset[50]
    artist_sales.removeAdditionalMintErc1155(middle_addr, sender=artist)
    
    # Verify removal worked correctly
    assert not artist_sales.artistErc1155Exists(middle_addr), "Removed address should not exist"
    assert artist_sales.artistErc1155sToSellCount() == 99, "Count should be reduced by 1"
    
    # Last element should have been swapped to position 50
    last_addr = large_dataset[99]
    new_position = artist_sales.getArtistErc1155Position(last_addr)
    assert new_position == 50, "Last address should be swapped to position 50"

# ================================================================================================
# COLLECTOR ERC1155s O(1) OPERATIONS TESTS
# ================================================================================================

def test_collector_erc1155_exists_o1(setup):
    """Test O(1) collectorErc1155Exists function"""
    owner = setup["owner"]
    owner_sales = setup["owner_sales"]
    
    test_addresses = [
        "0xaaaa111111111111111111111111111111111111",
        "0xbbbb222222222222222222222222222222222222",
        "0xcccc333333333333333333333333333333333333"
    ]
    
    # Initially nothing should exist
    for addr in test_addresses:
        assert not owner_sales.collectorErc1155Exists(addr), f"Address {addr} should not exist initially"
    
    # Add addresses and test existence
    for i, addr in enumerate(test_addresses):
        owner_sales.addCollectorErc1155(addr, sender=owner)
        
        # Test that the added address exists
        assert owner_sales.collectorErc1155Exists(addr), f"Address {addr} should exist after adding"
        
        # Test that previously added addresses still exist
        for j in range(i):
            assert owner_sales.collectorErc1155Exists(test_addresses[j]), f"Previously added address {test_addresses[j]} should still exist"
    
    # Remove and test
    owner_sales.removeCollectorErc1155(test_addresses[1], sender=owner)
    assert not owner_sales.collectorErc1155Exists(test_addresses[1]), "Removed address should not exist"
    assert owner_sales.collectorErc1155Exists(test_addresses[0]), "Other addresses should still exist"
    assert owner_sales.collectorErc1155Exists(test_addresses[2]), "Other addresses should still exist"

def test_collector_erc1155_position_o1(setup):
    """Test O(1) getCollectorErc1155Position function"""
    owner = setup["owner"]
    owner_sales = setup["owner_sales"]
    
    test_addresses = [
        "0xaaaa111111111111111111111111111111111111",
        "0xbbbb222222222222222222222222222222222222",
        "0xcccc333333333333333333333333333333333333",
        "0xdddd444444444444444444444444444444444444"
    ]
    
    # Test non-existent address returns max value
    non_existent = "0x9999999999999999999999999999999999999999"
    assert owner_sales.getCollectorErc1155Position(non_existent) == 2**256 - 1, "Non-existent address should return max uint256"
    
    # Add addresses and test positions
    for i, addr in enumerate(test_addresses):
        owner_sales.addCollectorErc1155(addr, sender=owner)
        
        position = owner_sales.getCollectorErc1155Position(addr)
        assert position == i, f"Address {addr} should be at position {i}, got {position}"

def test_collector_erc1155_at_index_o1(setup):
    """Test O(1) getCollectorErc1155AtIndex function"""
    owner = setup["owner"]
    owner_sales = setup["owner_sales"]
    
    test_addresses = [
        "0xaaaa111111111111111111111111111111111111",
        "0xbbbb222222222222222222222222222222222222",
        "0xcccc333333333333333333333333333333333333"
    ]
    
    # Add addresses
    for addr in test_addresses:
        owner_sales.addCollectorErc1155(addr, sender=owner)
    
    # Test accessing by index
    for i, expected_addr in enumerate(test_addresses):
        actual_addr = owner_sales.getCollectorErc1155AtIndex(i)
        assert normalize_address(actual_addr) == normalize_address(expected_addr), f"Index {i} should return {expected_addr}, got {actual_addr}"

def test_collector_erc1155_by_offset_pagination(setup):
    """Test new getCollectorErc1155sByOffset function"""
    owner = setup["owner"]
    owner_sales = setup["owner_sales"]
    
    # Create test data
    test_addresses = [f"0xaaaa{str(i).zfill(36)}" for i in range(1, 8)]
    
    # Add all addresses
    for addr in test_addresses:
        owner_sales.addCollectorErc1155(addr, sender=owner)
    
    # Test forward pagination
    forward_page1 = owner_sales.getCollectorErc1155sByOffset(0, 3, False)
    assert len(forward_page1) == 3
    for i in range(3):
        assert normalize_address(forward_page1[i]) == normalize_address(test_addresses[i])
    
    # Test reverse pagination
    reverse_page1 = owner_sales.getCollectorErc1155sByOffset(0, 3, True)
    assert len(reverse_page1) == 3
    expected_reverse = [test_addresses[6], test_addresses[5], test_addresses[4]]
    for i in range(3):
        assert normalize_address(reverse_page1[i]) == normalize_address(expected_reverse[i])

def test_collector_erc1155_original_art_piece_mapping(setup):
    """Test mapping collector ERC1155s to original art pieces"""
    owner = setup["owner"]
    owner_sales = setup["owner_sales"]
    artist = setup["artist"]
    artist_profile = setup["artist_profile"]
    art_piece_template = setup["art_piece_template"]
    
    # Create some art pieces
    art_pieces = []
    for i in range(3):
        tx = artist_profile.createArtPiece(
            art_piece_template.address,
            TEST_TOKEN_URI_DATA,
            TEST_TOKEN_URI_DATA_FORMAT,
            f"Test Art {i}",
            f"Description for test art {i}",
            True,  # as artist
            artist.address,
            TEST_AI_GENERATED,
            ZERO_ADDRESS,
            False,
            sender=artist
        )
        # Get the latest art piece from the profile
        art_pieces_list = artist_profile.getArtPiecesByOffset(0, 10, False)
        art_pieces.append(art_pieces_list[-1])
    
    # Create collector ERC1155 addresses
    collector_erc1155s = [
        "0xcccc111111111111111111111111111111111111",
        "0xcccc222222222222222222222222222222222222",
        "0xcccc333333333333333333333333333333333333"
    ]
    
    # Add collector ERC1155s with original art piece mappings
    for i, erc1155_addr in enumerate(collector_erc1155s):
        owner_sales.addCollectorErc1155(erc1155_addr, art_pieces[i], sender=owner)
        
        # Test the mapping
        mapped_art_piece = owner_sales.getCollectorErc1155OriginalArtPiece(erc1155_addr)
        assert normalize_address(mapped_art_piece) == normalize_address(art_pieces[i]), f"ERC1155 {erc1155_addr} should map to art piece {art_pieces[i]}"
    
    # Test adding without art piece mapping
    no_mapping_erc1155 = "0xcccc444444444444444444444444444444444444"
    owner_sales.addCollectorErc1155(no_mapping_erc1155, sender=owner)
    
    mapped_result = owner_sales.getCollectorErc1155OriginalArtPiece(no_mapping_erc1155)
    assert mapped_result == ZERO_ADDRESS, "ERC1155 without mapping should return zero address"
    
    # Test removal clears mapping
    owner_sales.removeCollectorErc1155(collector_erc1155s[1], sender=owner)
    cleared_mapping = owner_sales.getCollectorErc1155OriginalArtPiece(collector_erc1155s[1])
    assert cleared_mapping == ZERO_ADDRESS, "Removed ERC1155 should have cleared mapping"

def test_collector_erc1155_comprehensive_o1_operations(setup):
    """Comprehensive test of all collector ERC1155 O(1) operations together"""
    owner = setup["owner"]
    owner_sales = setup["owner_sales"]
    
    # Test data
    test_data = [
        {
            "erc1155": "0xcccc111111111111111111111111111111111111",
            "art_piece": "0xaaaa111111111111111111111111111111111111"
        },
        {
            "erc1155": "0xcccc222222222222222222222222222222222222",
            "art_piece": "0xaaaa222222222222222222222222222222222222"
        },
        {
            "erc1155": "0xcccc333333333333333333333333333333333333",
            "art_piece": "0xaaaa333333333333333333333333333333333333"
        }
    ]
    
    # Add all test data
    for i, data in enumerate(test_data):
        owner_sales.addCollectorErc1155(data["erc1155"], data["art_piece"], sender=owner)
        
        # Test all O(1) operations after each addition
        assert owner_sales.collectorErc1155Exists(data["erc1155"]), f"ERC1155 {data['erc1155']} should exist"
        assert owner_sales.getCollectorErc1155Position(data["erc1155"]) == i, f"ERC1155 should be at position {i}"
        assert normalize_address(owner_sales.getCollectorErc1155AtIndex(i)) == normalize_address(data["erc1155"]), f"Index {i} should return {data['erc1155']}"
        assert normalize_address(owner_sales.getCollectorErc1155OriginalArtPiece(data["erc1155"])) == normalize_address(data["art_piece"]), f"ERC1155 should map to {data['art_piece']}"
    
    # Test pagination operations
    all_offset = owner_sales.getCollectorErc1155sByOffset(0, 10, False)
    assert len(all_offset) == 3
    
    reverse_offset = owner_sales.getCollectorErc1155sByOffset(0, 10, True)
    assert len(reverse_offset) == 3
    # In reverse order
    for i in range(3):
        assert normalize_address(reverse_offset[i]) == normalize_address(test_data[2-i]["erc1155"])
    
    # Test removal and verify all operations still work
    middle_erc1155 = test_data[1]["erc1155"]
    owner_sales.removeCollectorErc1155(middle_erc1155, sender=owner)
    
    # Verify removal
    assert not owner_sales.collectorErc1155Exists(middle_erc1155), "Removed ERC1155 should not exist"
    assert owner_sales.getCollectorErc1155Position(middle_erc1155) == 2**256 - 1, "Removed ERC1155 should return max position"
    assert owner_sales.getCollectorErc1155OriginalArtPiece(middle_erc1155) == ZERO_ADDRESS, "Removed ERC1155 should have no mapping"
    
    # Verify swap-and-pop behavior (last element moved to middle position)
    last_erc1155 = test_data[2]["erc1155"]
    assert owner_sales.getCollectorErc1155Position(last_erc1155) == 1, "Last element should be swapped to position 1"
    assert normalize_address(owner_sales.getCollectorErc1155AtIndex(1)) == normalize_address(last_erc1155), "Position 1 should contain the last element"

# ================================================================================================
# LEGACY COMPATIBILITY TESTS
# ================================================================================================

def test_artist_erc1155_add_remove_operations(setup):
    """Test artist ERC1155 add/remove operations work with O(1) verification"""
    artist = setup["artist"]
    artist_sales = setup["artist_sales"]
    
    test_addresses = [
        "0x1111111111111111111111111111111111111111",
        "0x2222222222222222222222222222222222222222"
    ]
    
    # Add first address
    artist_sales.addAdditionalMintErc1155(test_addresses[0], sender=artist)
    
    # Test that O(1) operations work
    assert artist_sales.artistErc1155Exists(test_addresses[0]), "ERC1155 should exist"
    assert artist_sales.getArtistErc1155Position(test_addresses[0]) == 0, "ERC1155 should be at position 0"
    assert normalize_address(artist_sales.getArtistErc1155AtIndex(0)) == normalize_address(test_addresses[0]), "Index 0 should return correct address"
    
    # Add second address
    artist_sales.addAdditionalMintErc1155(test_addresses[1], sender=artist)
    
    # Test both exist and have correct positions
    assert artist_sales.artistErc1155Exists(test_addresses[1]), "Second ERC1155 should exist"
    assert artist_sales.getArtistErc1155Position(test_addresses[1]) == 1, "Second ERC1155 should be at position 1"
    
    # Remove first address
    artist_sales.removeAdditionalMintErc1155(test_addresses[0], sender=artist)
    
    # Test removal worked correctly (swap-and-pop behavior)
    assert not artist_sales.artistErc1155Exists(test_addresses[0]), "Removed ERC1155 should not exist"
    assert artist_sales.getArtistErc1155Position(test_addresses[1]) == 0, "Remaining ERC1155 should be swapped to position 0"

# ================================================================================================
# INTEGRATION TESTS
# ================================================================================================

def test_o1_operations_with_edition_creation(setup):
    """Test that O(1) operations work correctly with edition creation"""
    artist = setup["artist"]
    artist_profile = setup["artist_profile"]
    artist_sales = setup["artist_sales"]
    art_piece_template = setup["art_piece_template"]
    
    # Create an art piece
    tx = artist_profile.createArtPiece(
        art_piece_template.address,
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        "Test Art for Edition",
        "Description for test art",
        True,
        artist.address,
        TEST_AI_GENERATED,
        ZERO_ADDRESS,
        False,
        sender=artist
    )
    
    # Get the art piece address
    art_pieces = artist_profile.getArtPiecesByOffset(0, 10, False)
    art_piece_address = art_pieces[-1]
    
    # Create edition (this should automatically add to artist ERC1155s using O(1) operations)
    initial_count = artist_sales.artistErc1155sToSellCount()
    
    edition_tx = artist_sales.createEditionFromArtPiece(
        art_piece_address,
        "Test Edition",
        "TE",
        1000000000000000000,  # 1 ETH
        100,  # max supply
        250,  # 2.5% royalty
        sender=artist
    )
    
    # Get edition address using reliable fallback method 
    current_count = artist_sales.artistErc1155sToSellCount()
    if current_count > initial_count:
        edition_address = artist_sales.getArtistErc1155AtIndex(current_count - 1)
    else:
        edition_address = None
    
    # Test that the edition was added using O(1) operations
    new_count = artist_sales.artistErc1155sToSellCount()
    assert new_count == initial_count + 1, "Edition should be added to artist ERC1155s"
    
    # Test O(1) operations on the created edition
    assert artist_sales.artistErc1155Exists(edition_address), "Created edition should exist"
    
    position = artist_sales.getArtistErc1155Position(edition_address)
    assert position == initial_count, f"Created edition should be at position {initial_count}"
    
    addr_at_position = artist_sales.getArtistErc1155AtIndex(position)
    assert normalize_address(addr_at_position) == normalize_address(edition_address), "Position should return correct edition address"

def test_stress_test_o1_operations(setup):
    """Stress test O(1) operations with multiple rapid additions and removals"""
    owner = setup["owner"]
    owner_sales = setup["owner_sales"]
    
    # Create a large number of test addresses
    num_addresses = 50
    test_addresses = [f"0x{str(i).zfill(40)}" for i in range(1, num_addresses + 1)]
    
    # Rapid additions
    for addr in test_addresses:
        owner_sales.addCollectorErc1155(addr, sender=owner)
    
    # Verify all exist and have correct positions
    for i, addr in enumerate(test_addresses):
        assert owner_sales.collectorErc1155Exists(addr), f"Address {addr} should exist"
        assert owner_sales.getCollectorErc1155Position(addr) == i, f"Address {addr} should be at position {i}"
        assert normalize_address(owner_sales.getCollectorErc1155AtIndex(i)) == normalize_address(addr), f"Index {i} should return {addr}"
    
    # Rapid removals (remove every other address)
    addresses_to_remove = test_addresses[::2]  # Every other address
    for addr in addresses_to_remove:
        owner_sales.removeCollectorErc1155(addr, sender=owner)
        assert not owner_sales.collectorErc1155Exists(addr), f"Removed address {addr} should not exist"
    
    # Verify count is correct
    expected_count = num_addresses - len(addresses_to_remove)
    assert owner_sales.collectorErc1155Count() == expected_count, f"Count should be {expected_count}"
    
    # Verify remaining addresses still accessible
    remaining_count = 0
    for i in range(expected_count):
        addr_at_index = owner_sales.getCollectorErc1155AtIndex(i)
        assert owner_sales.collectorErc1155Exists(addr_at_index), f"Address at index {i} should exist"
        remaining_count += 1
    
    assert remaining_count == expected_count, "All remaining addresses should be accessible" 