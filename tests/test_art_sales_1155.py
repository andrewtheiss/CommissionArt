import pytest
from ape import accounts, project
import time

# --- Fixture for ArtSales1155 tests ---
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

    # Deploy Profile template and ProfileSocial template
    profile_template = project.Profile.deploy(sender=deployer)
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    
    # Deploy ProfileFactoryAndRegistry with both templates
    profile_factory_and_regsitry = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address, 
        profile_social_template.address, 
        sender=deployer
    )
    
    # Create profiles for owner and artist
    profile_factory_and_regsitry.createProfile(sender=owner)
    profile_factory_and_regsitry.createProfile(sender=artist)
    
    # Get the created profile addresses
    owner_profile_address = profile_factory_and_regsitry.getProfile(owner.address)
    artist_profile_address = profile_factory_and_regsitry.getProfile(artist.address)
    
    # Create profile objects
    owner_profile = project.Profile.at(owner_profile_address)
    artist_profile = project.Profile.at(artist_profile_address)
    
    # Set artist flag on artist profile
    artist_profile.setIsArtist(True, sender=artist)

    # Deploy ArtSales1155 for owner and artist
    owner_sales = project.ArtSales1155.deploy(owner_profile_address, owner.address, sender=deployer)
    artist_sales = project.ArtSales1155.deploy(artist_profile_address, artist.address, sender=deployer)
    
    # Link ArtSales1155 to profiles
    owner_profile.setArtSales1155(owner_sales.address, sender=owner)
    artist_profile.setArtSales1155(artist_sales.address, sender=artist)

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
        "profile_social_template": profile_social_template,
        "profile_factory_and_regsitry": profile_factory_and_regsitry,
        "owner_profile": owner_profile,
        "artist_profile": artist_profile,
        "owner_sales": owner_sales,
        "artist_sales": artist_sales
    }

# --- Helper function ---
def normalize_address(address):
    return address.lower()

# --- ERC1155/artist/collector tests ---

def test_collector_erc1155_basic(setup):
    """Test basic collector ERC1155 functions: add, get, check, count, remove"""
    owner = setup["owner"]
    owner_sales = setup["owner_sales"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    user3 = setup["user3"]
    user4 = setup["user4"]
    user5 = setup["user5"]

    test_erc1155s = [user1.address, user2.address, user3.address, user4.address, user5.address]
    assert owner_sales.collectorErc1155Count() == 0
    assert len(owner_sales.getCollectorErc1155s(0, 10)) == 0
    assert not owner_sales.isCollectorErc1155(test_erc1155s[0])
    for i, erc1155 in enumerate(test_erc1155s):
        owner_sales.addCollectorErc1155(erc1155, sender=owner)
        assert owner_sales.collectorErc1155Count() == i + 1
        assert owner_sales.isCollectorErc1155(erc1155)
    all_erc1155s = owner_sales.getCollectorErc1155s(0, 10)
    assert len(all_erc1155s) == 5
    for i, erc1155 in enumerate(test_erc1155s):
        assert normalize_address(all_erc1155s[i]) == normalize_address(erc1155)
    with pytest.raises(Exception):
        owner_sales.addCollectorErc1155(test_erc1155s[0], sender=owner)
    owner_sales.removeCollectorErc1155(test_erc1155s[2], sender=owner)
    assert owner_sales.collectorErc1155Count() == 4
    assert not owner_sales.isCollectorErc1155(test_erc1155s[2])
    non_existent = "0x0000000000000000000000000000000000000099"
    with pytest.raises(Exception):
        owner_sales.removeCollectorErc1155(non_existent, sender=owner)
    artist = setup["artist"]
    with pytest.raises(Exception):
        owner_sales.removeCollectorErc1155(test_erc1155s[0], sender=artist)
    updated_erc1155s = owner_sales.getCollectorErc1155s(0, 10)
    assert len(updated_erc1155s) == 4
    assert normalize_address(test_erc1155s[2]) not in [normalize_address(addr) for addr in updated_erc1155s]

def test_collector_erc1155_pagination(setup):
    """Test pagination of collector ERC1155s"""
    owner = setup["owner"]
    owner_sales = setup["owner_sales"]
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
    for erc1155 in test_erc1155s:
        owner_sales.addCollectorErc1155(erc1155, sender=owner)
    assert owner_sales.collectorErc1155Count() == 15
    page_0_size_5 = owner_sales.getCollectorErc1155s(0, 5)
    assert len(page_0_size_5) == 5
    for i in range(5):
        assert normalize_address(page_0_size_5[i]) == normalize_address(test_erc1155s[i])
    page_1_size_5 = owner_sales.getCollectorErc1155s(1, 5)
    assert len(page_1_size_5) == 5
    for i in range(5):
        assert normalize_address(page_1_size_5[i]) == normalize_address(test_erc1155s[i+5])
    page_2_size_5 = owner_sales.getCollectorErc1155s(2, 5)
    assert len(page_2_size_5) == 5
    for i in range(5):
        assert normalize_address(page_2_size_5[i]) == normalize_address(test_erc1155s[i+10])
    page_3_size_5 = owner_sales.getCollectorErc1155s(3, 5)
    assert len(page_3_size_5) == 0
    recent_page_0_size_5 = owner_sales.getRecentCollectorErc1155s(0, 5)
    assert len(recent_page_0_size_5) == 5
    for i in range(5):
        assert normalize_address(recent_page_0_size_5[i]) == normalize_address(test_erc1155s[14-i])
    recent_page_1_size_5 = owner_sales.getRecentCollectorErc1155s(1, 5)
    assert len(recent_page_1_size_5) == 5
    for i in range(5):
        assert normalize_address(recent_page_1_size_5[i]) == normalize_address(test_erc1155s[9-i])
    recent_page_2_size_5 = owner_sales.getRecentCollectorErc1155s(2, 5)
    assert len(recent_page_2_size_5) == 5
    for i in range(5):
        assert normalize_address(recent_page_2_size_5[i]) == normalize_address(test_erc1155s[4-i])

def test_get_latest_collector_erc1155s(setup):
    """Test getting latest (most recent) collector ERC1155s"""
    owner = setup["owner"]
    owner_sales = setup["owner_sales"]
    empty_latest = owner_sales.getLatestCollectorErc1155s()
    assert len(empty_latest) == 0
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
    for i in range(3):
        owner_sales.addCollectorErc1155(test_erc1155s[i], sender=owner)
    latest_3 = owner_sales.getLatestCollectorErc1155s()
    assert len(latest_3) == 3
    for i in range(3):
        assert normalize_address(latest_3[i]) == normalize_address(test_erc1155s[2-i])
    for i in range(3, 10):
        owner_sales.addCollectorErc1155(test_erc1155s[i], sender=owner)
    latest_5 = owner_sales.getLatestCollectorErc1155s()
    assert len(latest_5) == 5
    for i in range(5):
        assert normalize_address(latest_5[i]) == normalize_address(test_erc1155s[9-i])

def test_ownership_restrictions(setup):
    """Test that only the owner can manage collector ERC1155s"""
    owner = setup["owner"]
    owner_sales = setup["owner_sales"]
    artist = setup["artist"]
    user1 = setup["user1"]
    test_erc1155 = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    owner_sales.addCollectorErc1155(test_erc1155, sender=owner)
    assert owner_sales.collectorErc1155Count() == 1
    with pytest.raises(Exception):
        owner_sales.addCollectorErc1155("0xcccccccccccccccccccccccccccccccccccccccc", sender=artist)
    with pytest.raises(Exception):
        owner_sales.addCollectorErc1155("0xdddddddddddddddddddddddddddddddddddddddd", sender=user1)
    with pytest.raises(Exception):
        owner_sales.removeCollectorErc1155(test_erc1155, sender=artist)
    with pytest.raises(Exception):
        owner_sales.removeCollectorErc1155(test_erc1155, sender=user1)
    assert owner_sales.collectorErc1155Count() == 1
    assert owner_sales.isCollectorErc1155(test_erc1155)

# Add artist/commission/erc1155 mapping tests from test_profile_array_methods.py here, using artist_sales as needed

def test_my_commissions_array_methods(setup):
    """Test artist-only my commissions array methods"""
    artist = setup["artist"]
    artist_sales = setup["artist_sales"]
    owner = setup["owner"]
    owner_sales = setup["owner_sales"]
    test_commissions = [f"0x{'3' * 39}{i+1}" for i in range(5)]
    # Owner is allowed to call on owner_sales (should succeed)
    owner_sales.addMyCommission(test_commissions[0], sender=owner)
    # Negative test: non-owner should fail
    with pytest.raises(Exception):
        owner_sales.addMyCommission(test_commissions[1], sender=artist)
    # Artist is allowed to call on artist_sales (should succeed)
    for comm in test_commissions:
        artist_sales.addMyCommission(comm, sender=artist)
    # Remove a commission
    artist_sales.removeMyCommission(test_commissions[2], sender=artist)
    # No Profile-level getArtistCommissionedWorks calls here

def test_additional_mint_erc1155_array_methods(setup):
    """Test artist-only additional mint ERC1155 array methods"""
    artist = setup["artist"]
    artist_sales = setup["artist_sales"]
    owner = setup["owner"]
    owner_sales = setup["owner_sales"]
    test_erc1155s = [f"0x{'4' * 39}{i+1}" for i in range(5)]
    # Owner is allowed to call on owner_sales (should succeed)
    owner_sales.addAdditionalMintErc1155(test_erc1155s[0], sender=owner)
    # Negative test: non-owner should fail
    with pytest.raises(Exception):
        owner_sales.addAdditionalMintErc1155(test_erc1155s[1], sender=artist)
    assert artist_sales.artistErc1155sToSellCount() == 0
    for erc1155 in test_erc1155s:
        artist_sales.addAdditionalMintErc1155(erc1155, sender=artist)
    assert artist_sales.artistErc1155sToSellCount() == 5
    all_erc1155s = artist_sales.getAdditionalMintErc1155s(0, 10)
    assert len(all_erc1155s) == 5
    for i, erc1155 in enumerate(test_erc1155s):
        assert all_erc1155s[i] == erc1155
    recent = artist_sales.getRecentAdditionalMintErc1155s(0, 10)
    assert len(recent) == 5
    for i, erc1155 in enumerate(test_erc1155s):
        assert recent[4-i] == erc1155
    page_0 = artist_sales.getAdditionalMintErc1155s(0, 3)
    assert len(page_0) == 3
    page_1 = artist_sales.getAdditionalMintErc1155s(1, 3)
    assert len(page_1) == 2
    artist_sales.removeAdditionalMintErc1155(test_erc1155s[1], sender=artist)
    assert artist_sales.artistErc1155sToSellCount() == 4
    updated = artist_sales.getAdditionalMintErc1155s(0, 10)
    assert len(updated) == 4
    assert test_erc1155s[1] not in updated

def test_commission_to_mint_erc1155_mapping(setup):
    """Test artist-only commission to mint ERC1155 mapping methods"""
    artist = setup["artist"]
    artist_sales = setup["artist_sales"]
    owner = setup["owner"]
    owner_sales = setup["owner_sales"]
    commission = "0x" + "5" * 40
    erc1155 = "0x" + "6" * 40
    # Owner is allowed to call on owner_sales (should succeed)
    owner_sales.mapCommissionToMintErc1155(commission, erc1155, sender=owner)
    # Negative test: non-owner should fail
    with pytest.raises(Exception):
        owner_sales.mapCommissionToMintErc1155(commission, erc1155, sender=artist)
    artist_sales.mapCommissionToMintErc1155(commission, erc1155, sender=artist)
    mapped = artist_sales.getMapCommissionToMintErc1155(commission)
    assert mapped == erc1155
    artist_sales.removeMapCommissionToMintErc1155(commission, sender=artist)
    removed = artist_sales.getMapCommissionToMintErc1155(commission)
    assert removed == "0x" + "0" * 40
