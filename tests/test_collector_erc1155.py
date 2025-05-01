import pytest
from ape import accounts, project
import time

@pytest.fixture
def setup():
    # Get accounts for testing
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
    
    # Deploy Profile template
    profile_template = project.Profile.deploy(sender=deployer)
    
    # Deploy ProfileHub
    profile_hub = project.ProfileHub.deploy(profile_template.address, sender=deployer)
    
    # Create profiles for testing
    profile_hub.createProfile(sender=owner)
    profile_hub.createProfile(sender=artist)
    
    owner_profile_address = profile_hub.getProfile(owner.address)
    artist_profile_address = profile_hub.getProfile(artist.address)
    
    owner_profile = project.Profile.at(owner_profile_address)
    artist_profile = project.Profile.at(artist_profile_address)
    
    # Set artist status for artist profile
    artist_profile.setIsArtist(True, sender=artist)
    
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
        "profile_template": profile_template,
        "profile_hub": profile_hub,
        "owner_profile": owner_profile,
        "artist_profile": artist_profile
    }

def normalize_address(address):
    """Helper function to normalize address format for comparison"""
    return address.lower()

def test_collector_erc1155_basic(setup):
    """Test basic collector ERC1155 functions: add, get, check, count, remove"""
    owner = setup["owner"]
    owner_profile = setup["owner_profile"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    user3 = setup["user3"]
    user4 = setup["user4"]
    user5 = setup["user5"]
    
    # Use account addresses as ERC1155 contract addresses for testing
    test_erc1155s = [
        user1.address,
        user2.address,
        user3.address,
        user4.address,
        user5.address
    ]
    
    # Test initial state
    assert owner_profile.collectorErc1155Count() == 0
    assert len(owner_profile.getCollectorErc1155s(0, 10)) == 0
    
    # Test isCollectorErc1155 with non-existent ERC1155
    assert not owner_profile.isCollectorErc1155(test_erc1155s[0])
    
    # Add collector ERC1155s
    for i, erc1155 in enumerate(test_erc1155s):
        owner_profile.addCollectorErc1155(erc1155, sender=owner)
        assert owner_profile.collectorErc1155Count() == i + 1
        assert owner_profile.isCollectorErc1155(erc1155)
    
    # Test getCollectorErc1155s
    all_erc1155s = owner_profile.getCollectorErc1155s(0, 10)
    assert len(all_erc1155s) == 5
    for i, erc1155 in enumerate(test_erc1155s):
        assert normalize_address(all_erc1155s[i]) == normalize_address(erc1155)
    
    # Test adding duplicate (should fail)
    with pytest.raises(Exception):
        owner_profile.addCollectorErc1155(test_erc1155s[0], sender=owner)
    
    # Test removing an ERC1155
    owner_profile.removeCollectorErc1155(test_erc1155s[2], sender=owner)
    assert owner_profile.collectorErc1155Count() == 4
    assert not owner_profile.isCollectorErc1155(test_erc1155s[2])
    
    # Test removing non-existent ERC1155 (should fail)
    non_existent = "0x0000000000000000000000000000000000000099"
    with pytest.raises(Exception):
        owner_profile.removeCollectorErc1155(non_existent, sender=owner)
    
    # Test unauthorized removal (should fail)
    artist = setup["artist"]
    with pytest.raises(Exception):
        owner_profile.removeCollectorErc1155(test_erc1155s[0], sender=artist)
    
    # Test all ERC1155s after removal
    updated_erc1155s = owner_profile.getCollectorErc1155s(0, 10)
    assert len(updated_erc1155s) == 4
    assert normalize_address(test_erc1155s[2]) not in [normalize_address(addr) for addr in updated_erc1155s]

def test_collector_erc1155_pagination(setup):
    """Test pagination of collector ERC1155s"""
    owner = setup["owner"]
    owner_profile = setup["owner_profile"]
    
    # Generate valid Ethereum addresses for testing
    # We'll use a set of fixed addresses that are already precomputed
    test_erc1155s = [
        "0x0000000000000000000000000000000000000001",
        "0x0000000000000000000000000000000000000002",
        "0x0000000000000000000000000000000000000003",
        "0x0000000000000000000000000000000000000004",
        "0x0000000000000000000000000000000000000005",
        "0x0000000000000000000000000000000000000006",
        "0x0000000000000000000000000000000000000007",
        "0x0000000000000000000000000000000000000008",
        "0x0000000000000000000000000000000000000009",
        "0x000000000000000000000000000000000000000a",
        "0x000000000000000000000000000000000000000b",
        "0x000000000000000000000000000000000000000c",
        "0x000000000000000000000000000000000000000d",
        "0x000000000000000000000000000000000000000e",
        "0x000000000000000000000000000000000000000f"
    ]
    
    # Add all ERC1155s
    for erc1155 in test_erc1155s:
        owner_profile.addCollectorErc1155(erc1155, sender=owner)
    
    assert owner_profile.collectorErc1155Count() == 15
    
    # Test pagination with getCollectorErc1155s
    page_0_size_5 = owner_profile.getCollectorErc1155s(0, 5)
    assert len(page_0_size_5) == 5
    for i in range(5):
        assert normalize_address(page_0_size_5[i]) == normalize_address(test_erc1155s[i])
    
    page_1_size_5 = owner_profile.getCollectorErc1155s(1, 5)
    assert len(page_1_size_5) == 5
    for i in range(5):
        assert normalize_address(page_1_size_5[i]) == normalize_address(test_erc1155s[i+5])
    
    page_2_size_5 = owner_profile.getCollectorErc1155s(2, 5)
    assert len(page_2_size_5) == 5
    for i in range(5):
        assert normalize_address(page_2_size_5[i]) == normalize_address(test_erc1155s[i+10])
    
    page_3_size_5 = owner_profile.getCollectorErc1155s(3, 5)
    assert len(page_3_size_5) == 0  # Should be empty (out of bounds)
    
    # Test pagination with getRecentCollectorErc1155s (reverse order)
    recent_page_0_size_5 = owner_profile.getRecentCollectorErc1155s(0, 5)
    assert len(recent_page_0_size_5) == 5
    for i in range(5):
        assert normalize_address(recent_page_0_size_5[i]) == normalize_address(test_erc1155s[14-i])  # Most recent first
    
    recent_page_1_size_5 = owner_profile.getRecentCollectorErc1155s(1, 5)
    assert len(recent_page_1_size_5) == 5
    for i in range(5):
        assert normalize_address(recent_page_1_size_5[i]) == normalize_address(test_erc1155s[9-i])
    
    recent_page_2_size_5 = owner_profile.getRecentCollectorErc1155s(2, 5)
    assert len(recent_page_2_size_5) == 5
    for i in range(5):
        assert normalize_address(recent_page_2_size_5[i]) == normalize_address(test_erc1155s[4-i])

def test_get_latest_collector_erc1155s(setup):
    """Test getting latest (most recent) collector ERC1155s"""
    owner = setup["owner"]
    owner_profile = setup["owner_profile"]
    
    # Test with empty collection
    empty_latest = owner_profile.getLatestCollectorErc1155s()
    assert len(empty_latest) == 0
    
    # Use valid Ethereum addresses for testing
    test_erc1155s = [
        "0x1111111111111111111111111111111111111111",
        "0x2222222222222222222222222222222222222222",
        "0x3333333333333333333333333333333333333333",
        "0x4444444444444444444444444444444444444444",
        "0x5555555555555555555555555555555555555555",
        "0x6666666666666666666666666666666666666666",
        "0x7777777777777777777777777777777777777777",
        "0x8888888888888888888888888888888888888888",
        "0x9999999999999999999999999999999999999999",
        "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    ]
    
    # Add first 3 ERC1155s
    for i in range(3):
        owner_profile.addCollectorErc1155(test_erc1155s[i], sender=owner)
    
    # Test with less than 5 ERC1155s
    latest_3 = owner_profile.getLatestCollectorErc1155s()
    assert len(latest_3) == 3
    for i in range(3):
        assert normalize_address(latest_3[i]) == normalize_address(test_erc1155s[2-i])  # Most recent first
    
    # Add more ERC1155s to go over 5
    for i in range(3, 10):
        owner_profile.addCollectorErc1155(test_erc1155s[i], sender=owner)
    
    # Test with more than 5 ERC1155s
    latest_5 = owner_profile.getLatestCollectorErc1155s()
    assert len(latest_5) == 5
    for i in range(5):
        assert normalize_address(latest_5[i]) == normalize_address(test_erc1155s[9-i])  # Most recent first

def test_ownership_restrictions(setup):
    """Test that only the owner can manage collector ERC1155s"""
    owner = setup["owner"]
    owner_profile = setup["owner_profile"]
    artist = setup["artist"]
    user1 = setup["user1"]
    
    test_erc1155 = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    
    # Add an ERC1155 as owner
    owner_profile.addCollectorErc1155(test_erc1155, sender=owner)
    assert owner_profile.collectorErc1155Count() == 1
    
    # Try to add an ERC1155 as non-owner (should fail)
    with pytest.raises(Exception):
        owner_profile.addCollectorErc1155("0xcccccccccccccccccccccccccccccccccccccccc", sender=artist)
    
    with pytest.raises(Exception):
        owner_profile.addCollectorErc1155("0xdddddddddddddddddddddddddddddddddddddddd", sender=user1)
    
    # Try to remove an ERC1155 as non-owner (should fail)
    with pytest.raises(Exception):
        owner_profile.removeCollectorErc1155(test_erc1155, sender=artist)
    
    with pytest.raises(Exception):
        owner_profile.removeCollectorErc1155(test_erc1155, sender=user1)
    
    # Verify no changes were made
    assert owner_profile.collectorErc1155Count() == 1
    assert owner_profile.isCollectorErc1155(test_erc1155) 