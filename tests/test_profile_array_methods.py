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

# Tests for Commission Array Methods
def test_commission_array_methods(setup):
    """Test commission array methods: add, get, getRecent, remove"""
    owner = setup["owner"]
    owner_profile = setup["owner_profile"]
    
    # Generate test commission addresses
    test_commissions = [f"0x{'1' * 39}{i+1}" for i in range(8)]
    
    # Test empty state
    assert owner_profile.commissionCount() == 0
    empty_commissions = owner_profile.getCommissions(0, 10)
    assert len(empty_commissions) == 0
    empty_recent = owner_profile.getRecentCommissions(0, 10)
    assert len(empty_recent) == 0
    
    # Add commissions in order
    for i, comm in enumerate(test_commissions):
        owner_profile.addCommission(comm, sender=owner)
        assert owner_profile.commissionCount() == i + 1
    
    # Test getCommissions pagination
    page_0_size_3 = owner_profile.getCommissions(0, 3)
    assert len(page_0_size_3) == 3
    assert page_0_size_3[0] == test_commissions[0]
    assert page_0_size_3[1] == test_commissions[1]
    assert page_0_size_3[2] == test_commissions[2]
    
    page_1_size_3 = owner_profile.getCommissions(1, 3)
    assert len(page_1_size_3) == 3
    assert page_1_size_3[0] == test_commissions[3]
    assert page_1_size_3[1] == test_commissions[4]
    assert page_1_size_3[2] == test_commissions[5]
    
    page_2_size_3 = owner_profile.getCommissions(2, 3)
    assert len(page_2_size_3) == 2
    assert page_2_size_3[0] == test_commissions[6]
    assert page_2_size_3[1] == test_commissions[7]
    
    page_3_size_3 = owner_profile.getCommissions(3, 3)
    assert len(page_3_size_3) == 0  # Should be empty (out of bounds)
    
    # Test getRecentCommissions pagination (reverse order)
    recent_page_0_size_3 = owner_profile.getRecentCommissions(0, 3)
    assert len(recent_page_0_size_3) == 3
    assert recent_page_0_size_3[0] == test_commissions[7]  # Most recent first
    assert recent_page_0_size_3[1] == test_commissions[6]
    assert recent_page_0_size_3[2] == test_commissions[5]
    
    recent_page_1_size_3 = owner_profile.getRecentCommissions(1, 3)
    assert len(recent_page_1_size_3) == 3
    assert recent_page_1_size_3[0] == test_commissions[4]
    assert recent_page_1_size_3[1] == test_commissions[3]
    assert recent_page_1_size_3[2] == test_commissions[2]
    
    recent_page_2_size_3 = owner_profile.getRecentCommissions(2, 3)
    assert len(recent_page_2_size_3) == 2
    assert recent_page_2_size_3[0] == test_commissions[1]
    assert recent_page_2_size_3[1] == test_commissions[0]
    
    # Test remove commission
    # Remove middle element
    owner_profile.removeCommission(test_commissions[3], sender=owner)
    assert owner_profile.commissionCount() == 7
    
    # Check that the array was updated correctly (order may have changed due to swap-and-pop)
    updated_commissions = owner_profile.getCommissions(0, 10)
    assert len(updated_commissions) == 7
    assert test_commissions[3] not in updated_commissions
    
    # Remove first element
    owner_profile.removeCommission(test_commissions[0], sender=owner)
    assert owner_profile.commissionCount() == 6
    
    # Check that the array was updated correctly
    updated_commissions = owner_profile.getCommissions(0, 10)
    assert len(updated_commissions) == 6
    assert test_commissions[0] not in updated_commissions
    
    # Remove last remaining element in array
    owner_profile.removeCommission(updated_commissions[5], sender=owner)
    assert owner_profile.commissionCount() == 5
    
    # Test non-existent commission removal (should fail)
    non_existent = "0x" + "f" * 40
    with pytest.raises(Exception):
        owner_profile.removeCommission(non_existent, sender=owner)

# Tests for Unverified Commission Array Methods
def test_unverified_commission_array_methods(setup):
    """Test unverified commission array methods"""
    owner = setup["owner"]
    owner_profile = setup["owner_profile"]
    
    # Generate test commission addresses
    test_commissions = [f"0x{'2' * 39}{i+1}" for i in range(5)]
    
    # Test empty state
    assert owner_profile.unverifiedCommissionCount() == 0
    
    # Test allow/disallow unverified commissions
    assert owner_profile.allowUnverifiedCommissions() is True  # Default is True
    owner_profile.setAllowUnverifiedCommissions(False, sender=owner)
    assert owner_profile.allowUnverifiedCommissions() is False
    owner_profile.setAllowUnverifiedCommissions(True, sender=owner)
    assert owner_profile.allowUnverifiedCommissions() is True
    
    # Add unverified commissions
    for comm in test_commissions:
        owner_profile.addUnverifiedCommission(comm, sender=owner)
    
    # Test getUnverifiedCommissions
    all_commissions = owner_profile.getUnverifiedCommissions(0, 10)
    assert len(all_commissions) == 5
    for i, comm in enumerate(test_commissions):
        assert all_commissions[i] == comm
    
    # Test getRecentUnverifiedCommissions
    recent_commissions = owner_profile.getRecentUnverifiedCommissions(0, 10)
    assert len(recent_commissions) == 5
    for i, comm in enumerate(test_commissions):
        assert recent_commissions[4-i] == comm
    
    # Test pagination
    page_0 = owner_profile.getUnverifiedCommissions(0, 3)
    assert len(page_0) == 3
    page_1 = owner_profile.getUnverifiedCommissions(1, 3)
    assert len(page_1) == 2
    
    # Test reverse pagination
    recent_page_0 = owner_profile.getRecentUnverifiedCommissions(0, 3)
    assert len(recent_page_0) == 3
    assert recent_page_0[0] == test_commissions[4]  # Most recent first
    
    # Test remove unverified commission
    owner_profile.removeUnverifiedCommission(test_commissions[2], sender=owner)
    assert owner_profile.unverifiedCommissionCount() == 4
    
    # Verify it's removed
    updated_list = owner_profile.getUnverifiedCommissions(0, 10)
    assert test_commissions[2] not in updated_list

# Tests for Liked Profiles Array Methods
def test_liked_profiles_array_methods(setup):
    """Test liked profiles array methods"""
    owner = setup["owner"]
    profile_hub = setup["profile_hub"]
    owner_profile = setup["owner_profile"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    user3 = setup["user3"]
    
    # Create profiles for test users
    for user in [user1, user2, user3]:
        profile_hub.createProfile(sender=user)
    
    profiles = [
        profile_hub.getProfile(user1.address),
        profile_hub.getProfile(user2.address),
        profile_hub.getProfile(user3.address)
    ]
    
    # Test empty state
    assert owner_profile.likedProfileCount() == 0
    
    # Add liked profiles
    for profile in profiles:
        owner_profile.addLikedProfile(profile, sender=owner)
    
    # Test getLikedProfiles
    liked = owner_profile.getLikedProfiles(0, 10)
    assert len(liked) == 3
    for i, profile in enumerate(profiles):
        assert liked[i] == profile
    
    # Test getRecentLikedProfiles
    recent = owner_profile.getRecentLikedProfiles(0, 10)
    assert len(recent) == 3
    for i, profile in enumerate(profiles):
        assert recent[2-i] == profile
    
    # Test pagination
    page_0 = owner_profile.getLikedProfiles(0, 2)
    assert len(page_0) == 2
    assert page_0[0] == profiles[0]
    assert page_0[1] == profiles[1]
    
    page_1 = owner_profile.getLikedProfiles(1, 2)
    assert len(page_1) == 1
    assert page_1[0] == profiles[2]
    
    # Test remove liked profile
    owner_profile.removeLikedProfile(profiles[1], sender=owner)
    assert owner_profile.likedProfileCount() == 2
    
    updated = owner_profile.getLikedProfiles(0, 10)
    assert profiles[1] not in updated

# Tests for Linked Profiles Array Methods
def test_linked_profiles_array_methods(setup):
    """Test linked profiles array methods"""
    owner = setup["owner"]
    profile_hub = setup["profile_hub"]
    owner_profile = setup["owner_profile"]
    user4 = setup["user4"]
    user5 = setup["user5"]
    user6 = setup["user6"]
    
    # Create profiles for test users
    for user in [user4, user5, user6]:
        profile_hub.createProfile(sender=user)
    
    profiles = [
        profile_hub.getProfile(user4.address),
        profile_hub.getProfile(user5.address),
        profile_hub.getProfile(user6.address)
    ]
    
    # Test empty state
    assert owner_profile.linkedProfileCount() == 0
    
    # Add linked profiles
    for profile in profiles:
        owner_profile.linkProfile(profile, sender=owner)
        
    # Test getLinkedProfiles
    linked = owner_profile.getLinkedProfiles(0, 10)
    assert len(linked) == 3
    for i, profile in enumerate(profiles):
        assert linked[i] == profile
    
    # Test getRecentLinkedProfiles
    recent = owner_profile.getRecentLinkedProfiles(0, 10)
    assert len(recent) == 3
    for i, profile in enumerate(profiles):
        assert recent[2-i] == profile
    
    # Test remove linked profile
    owner_profile.removeLinkedProfile(profiles[0], sender=owner)
    assert owner_profile.linkedProfileCount() == 2
    
    updated = owner_profile.getLinkedProfiles(0, 10)
    assert profiles[0] not in updated
    
    # Test attempting to link already linked profile
    with pytest.raises(Exception):
        owner_profile.linkProfile(profiles[1], sender=owner)

# Tests for Artist-Only Methods (My Commissions)
def test_my_commissions_array_methods(setup):
    """Test artist-only my commissions array methods"""
    artist = setup["artist"]
    artist_profile = setup["artist_profile"]
    owner = setup["owner"]
    owner_profile = setup["owner_profile"]
    
    # Generate test commission addresses
    test_commissions = [f"0x{'3' * 39}{i+1}" for i in range(5)]
    
    # Test restrictions for non-artists
    with pytest.raises(Exception):
        owner_profile.addMyCommission(test_commissions[0], sender=owner)
    
    with pytest.raises(Exception):
        owner_profile.getArtistCommissionedWorks(0, 10)
    
    with pytest.raises(Exception):
        owner_profile.getRecentArtistCommissionedWorks(0, 10)
    
    # Test for artist profile
    assert artist_profile.artistCommissionedWorkCount() == 0
    
    # Add my commissions
    for comm in test_commissions:
        artist_profile.addMyCommission(comm, sender=artist)
    
    assert artist_profile.artistCommissionedWorkCount() == 5
    
    # Test getArtistCommissionedWorks
    my_commissions = artist_profile.getArtistCommissionedWorks(0, 10)
    assert len(my_commissions) == 5
    for i, comm in enumerate(test_commissions):
        assert my_commissions[i] == comm
    
    # Test getRecentArtistCommissionedWorks
    recent = artist_profile.getRecentArtistCommissionedWorks(0, 10)
    assert len(recent) == 5
    for i, comm in enumerate(test_commissions):
        assert recent[4-i] == comm
    
    # Test pagination
    page_0 = artist_profile.getArtistCommissionedWorks(0, 2)
    assert len(page_0) == 2
    assert page_0[0] == test_commissions[0]
    assert page_0[1] == test_commissions[1]
    
    # Test remove my commission
    artist_profile.removeMyCommission(test_commissions[2], sender=artist)
    assert artist_profile.artistCommissionedWorkCount() == 4
    
    updated = artist_profile.getArtistCommissionedWorks(0, 10)
    assert len(updated) == 4
    assert test_commissions[2] not in updated

# Tests for Artist-Only Methods (Additional Mint ERC1155s)
def test_additional_mint_erc1155_array_methods(setup):
    """Test artist-only additional mint ERC1155 array methods"""
    artist = setup["artist"]
    artist_profile = setup["artist_profile"]
    owner = setup["owner"]
    owner_profile = setup["owner_profile"]
    
    # Generate test ERC1155 addresses
    test_erc1155s = [f"0x{'4' * 39}{i+1}" for i in range(5)]
    
    # Test restrictions for non-artists
    with pytest.raises(Exception):
        owner_profile.addAdditionalMintErc1155(test_erc1155s[0], sender=owner)
    
    with pytest.raises(Exception):
        owner_profile.getAdditionalMintErc1155s(0, 10)
    
    # Test for artist profile
    assert artist_profile.artistErc1155sToSellCount() == 0
    
    # Add additional mint ERC1155s
    for erc1155 in test_erc1155s:
        artist_profile.addAdditionalMintErc1155(erc1155, sender=artist)
    
    assert artist_profile.artistErc1155sToSellCount() == 5
    
    # Test getAdditionalMintErc1155s
    all_erc1155s = artist_profile.getAdditionalMintErc1155s(0, 10)
    assert len(all_erc1155s) == 5
    for i, erc1155 in enumerate(test_erc1155s):
        assert all_erc1155s[i] == erc1155
    
    # Test getRecentAdditionalMintErc1155s
    recent = artist_profile.getRecentAdditionalMintErc1155s(0, 10)
    assert len(recent) == 5
    for i, erc1155 in enumerate(test_erc1155s):
        assert recent[4-i] == erc1155
    
    # Test pagination
    page_0 = artist_profile.getAdditionalMintErc1155s(0, 3)
    assert len(page_0) == 3
    
    page_1 = artist_profile.getAdditionalMintErc1155s(1, 3)
    assert len(page_1) == 2
    
    # Test remove additional mint ERC1155
    artist_profile.removeAdditionalMintErc1155(test_erc1155s[1], sender=artist)
    assert artist_profile.artistErc1155sToSellCount() == 4
    
    updated = artist_profile.getAdditionalMintErc1155s(0, 10)
    assert len(updated) == 4
    assert test_erc1155s[1] not in updated

# Tests for Commission to Mint ERC1155 Mapping
def test_commission_to_mint_erc1155_mapping(setup):
    """Test artist-only commission to mint ERC1155 mapping methods"""
    artist = setup["artist"]
    artist_profile = setup["artist_profile"]
    owner = setup["owner"]
    owner_profile = setup["owner_profile"]
    
    # Generate test addresses
    commission = "0x" + "5" * 40
    erc1155 = "0x" + "6" * 40
    
    # Test restrictions for non-artists
    with pytest.raises(Exception):
        owner_profile.mapCommissionToMintErc1155(commission, erc1155, sender=owner)
    
    with pytest.raises(Exception):
        owner_profile.getMapCommissionToMintErc1155(commission)
    
    # Test for artist profile
    
    # Map commission to mint ERC1155
    artist_profile.mapCommissionToMintErc1155(commission, erc1155, sender=artist)
    
    # Test getMapCommissionToMintErc1155
    mapped = artist_profile.getMapCommissionToMintErc1155(commission)
    assert mapped == erc1155
    
    # Test remove map
    artist_profile.removeMapCommissionToMintErc1155(commission, sender=artist)
    
    # Verify it's removed
    removed = artist_profile.getMapCommissionToMintErc1155(commission)
    assert removed == "0x" + "0" * 40  # Empty address

# Tests for Collector ERC1155 Array Methods
def test_collector_erc1155_array_methods(setup):
    """Test collector ERC1155 array methods"""
    owner = setup["owner"]
    owner_profile = setup["owner_profile"]
    
    # Generate test ERC1155 addresses
    test_erc1155s = [f"0x{'9' * 39}{i+1}" for i in range(6)]
    
    # Test empty state
    assert owner_profile.collectorErc1155Count() == 0
    assert len(owner_profile.getCollectorErc1155s(0, 10)) == 0
    
    # Add collector ERC1155s
    for erc1155 in test_erc1155s:
        owner_profile.addCollectorErc1155(erc1155, sender=owner)
    
    assert owner_profile.collectorErc1155Count() == 6
    
    # Test getCollectorErc1155s
    all_erc1155s = owner_profile.getCollectorErc1155s(0, 10)
    assert len(all_erc1155s) == 6
    for i, erc1155 in enumerate(test_erc1155s):
        assert all_erc1155s[i] == erc1155
    
    # Test getRecentCollectorErc1155s
    recent = owner_profile.getRecentCollectorErc1155s(0, 10)
    assert len(recent) == 6
    for i, erc1155 in enumerate(test_erc1155s):
        assert recent[5-i] == erc1155  # Most recent first
    
    # Test isCollectorErc1155
    assert owner_profile.isCollectorErc1155(test_erc1155s[0])
    assert not owner_profile.isCollectorErc1155("0x" + "f" * 40)
    
    # Test pagination
    page_0 = owner_profile.getCollectorErc1155s(0, 3)
    assert len(page_0) == 3
    assert page_0[0] == test_erc1155s[0]
    assert page_0[1] == test_erc1155s[1]
    assert page_0[2] == test_erc1155s[2]
    
    page_1 = owner_profile.getCollectorErc1155s(1, 3)
    assert len(page_1) == 3
    assert page_1[0] == test_erc1155s[3]
    assert page_1[1] == test_erc1155s[4]
    assert page_1[2] == test_erc1155s[5]
    
    # Test getLatestCollectorErc1155s
    latest = owner_profile.getLatestCollectorErc1155s()
    assert len(latest) == 5  # Should return max 5 items
    for i in range(5):
        assert latest[i] == test_erc1155s[5-i]  # Most recent first
    
    # Test remove collector ERC1155
    owner_profile.removeCollectorErc1155(test_erc1155s[1], sender=owner)
    assert owner_profile.collectorErc1155Count() == 5
    assert not owner_profile.isCollectorErc1155(test_erc1155s[1])
    
    updated = owner_profile.getCollectorErc1155s(0, 10)
    assert len(updated) == 5
    assert test_erc1155s[1] not in updated 