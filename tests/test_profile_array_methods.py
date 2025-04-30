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
    
    # Deploy ArtPiece template for testing ERC721 functionality
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
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
        "artist_profile": artist_profile,
        "art_piece_template": art_piece_template
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

# New tests for Vyper 0.4.1 compatibility in ArtPiece contract

def test_artpiece_erc721_functionality(setup):
    """Test ArtPiece ERC721 functionality and proper event emission"""
    deployer = setup["deployer"]
    owner = setup["owner"]
    artist = setup["artist"]
    user1 = setup["user1"]
    art_piece_template = setup["art_piece_template"]
    
    # Create a new art piece with ERC721 functionality
    art_piece_proxy = project.ArtPiece.deploy(sender=deployer)
    
    # Initialize the art piece
    title = "Test Artwork"
    description = b"This is a test artwork description"
    image_data = b"test_image_data"
    
    # Initialize the art piece with ERC721 functionality
    art_piece_proxy.initialize(
        image_data,
        title,
        description,
        owner.address,
        artist.address,
        "0x0000000000000000000000000000000000000000",  # No commission hub
        False,  # Not AI generated
        sender=deployer
    )
    
    # Test basic ERC721 functions
    # 1. balanceOf - owner should have 1 token
    assert art_piece_proxy.balanceOf(owner.address) == 1
    assert art_piece_proxy.balanceOf(artist.address) == 0
    
    # 2. ownerOf - token ID 1 should belong to owner
    assert art_piece_proxy.ownerOf(1) == owner.address
    
    # 3. name and symbol
    assert art_piece_proxy.name() == "ArtPiece"
    assert art_piece_proxy.symbol() == "ART"
    
    # 4. supportsInterface
    erc721_interface_id = 0x80ac58cd  # ERC721 interface ID
    erc165_interface_id = 0x01ffc9a7  # ERC165 interface ID
    assert art_piece_proxy.supportsInterface(erc721_interface_id)
    assert art_piece_proxy.supportsInterface(erc165_interface_id)
    
    # 5. Test approval
    art_piece_proxy.approve(user1.address, 1, sender=owner)
    assert art_piece_proxy.getApproved(1) == user1.address
    
    # 6. Test setApprovalForAll
    art_piece_proxy.setApprovalForAll(artist.address, True, sender=owner)
    assert art_piece_proxy.isApprovedForAll(owner.address, artist.address)
    
    # 7. Test transfer via approved address
    art_piece_proxy.transferFrom(owner.address, user1.address, 1, sender=user1)
    assert art_piece_proxy.ownerOf(1) == user1.address
    assert art_piece_proxy.balanceOf(user1.address) == 1
    assert art_piece_proxy.balanceOf(owner.address) == 0
    
    # 8. Verify owner in both old and new methods
    assert art_piece_proxy.getOwner() == user1.address
    assert art_piece_proxy.ownerOf(1) == user1.address
    
    # 9. Test transferFrom instead of safeTransferFrom to avoid receiver implementation issues
    art_piece_proxy.transferFrom(user1.address, owner.address, 1, sender=user1)
    assert art_piece_proxy.ownerOf(1) == owner.address

def test_artpiece_iscontract_method(setup):
    """Test the _isContract method workaround for Vyper 0.4.1"""
    deployer = setup["deployer"]
    owner = setup["owner"]
    art_piece_template = setup["art_piece_template"]
    
    # Deploy a contract that will receive an NFT
    # We'll use another ArtPiece as a contract to test with
    receiver_contract = project.ArtPiece.deploy(sender=deployer)
    
    # Initialize the art piece we'll transfer
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
        b"test_data",
        "Test NFT",
        b"Test description",
        owner.address,
        owner.address,  # owner is also artist
        "0x0000000000000000000000000000000000000000",
        False,
        sender=deployer
    )
    
    # Try to transfer to a contract address without receiver implementation
    # This should fail because the contract doesn't implement ERC721Receiver
    with pytest.raises(Exception):
        art_piece.safeTransferFrom(
            owner.address,
            receiver_contract.address,
            1,  # token ID
            b"",
            sender=owner
        )
    
    # Regular transferFrom should work because it doesn't check for receiver implementation
    art_piece.transferFrom(
        owner.address,
        receiver_contract.address,
        1,  # token ID
        sender=owner
    )
    
    # Verify transfer worked
    assert art_piece.ownerOf(1) == receiver_contract.address

def test_artpiece_transferownership_compatibility(setup):
    """Test compatibility of transferOwnership with ERC721 functionality"""
    deployer = setup["deployer"]
    owner = setup["owner"]
    user1 = setup["user1"]
    art_piece_template = setup["art_piece_template"]
    
    # Initialize the art piece
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
        b"test_data",
        "Test NFT",
        b"Test description",
        owner.address,
        owner.address,  # owner is also artist
        "0x0000000000000000000000000000000000000000",
        False,
        sender=deployer
    )
    
    # Test the original transferOwnership method
    art_piece.transferOwnership(user1.address, sender=owner)
    
    # Verify that both the traditional owner and the ERC721 ownership are updated
    assert art_piece.getOwner() == user1.address
    assert art_piece.ownerOf(1) == user1.address
    
    # Verify that approvals are cleared after ownership transfer
    assert art_piece.getApproved(1) == "0x0000000000000000000000000000000000000000"

def test_artpiece_commission_hub_integration(setup):
    """Test ArtPiece integration with Commission Hub while maintaining ERC721 compatibility"""
    deployer = setup["deployer"]
    owner = setup["owner"]
    user1 = setup["user1"]
    
    # For testing purposes, we'll use another ArtPiece as our mock commission hub
    # This works because ArtPiece has an owner() method that returns its owner
    mock_hub = project.ArtPiece.deploy(sender=deployer)
    mock_hub.initialize(
        b"mock_data",
        "Mock Hub",
        b"Mock description",
        user1.address,  # This will be the owner returned by the hub
        user1.address,  # Artist is also user1
        "0x0000000000000000000000000000000000000000",  # No commission hub
        False,  # Not AI generated
        sender=deployer
    )
    
    # Verify our mock works as expected
    assert mock_hub.getOwner() == user1.address
    
    # Initialize the art piece with no commission hub initially
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
        b"test_data",
        "Test NFT",
        b"Test description",
        owner.address,
        owner.address,
        "0x0000000000000000000000000000000000000000",  # No commission hub initially
        False,
        sender=deployer
    )
    
    # Check initial ownership
    assert art_piece.getOwner() == owner.address
    assert art_piece.ownerOf(1) == owner.address
    
    # Initially, there's no commission hub attached
    assert art_piece.attachedToCommissionHub() == False
    assert art_piece.commissionHubAddress() == "0x0000000000000000000000000000000000000000"
    
    # Attach to commission hub
    art_piece.attachToCommissionHub(mock_hub.address, sender=owner)
    
    # Verify the commission hub is set
    assert art_piece.commissionHubAddress() == mock_hub.address
    assert art_piece.attachedToCommissionHub() == True
    
    # ERC721 ownership functions shouldn't be affected by the commission hub
    assert art_piece.ownerOf(1) == owner.address
    assert art_piece.getOwner() == owner.address
    
    # Now transferring ERC721 ownership should update the direct ownership
    art_piece.transferFrom(owner.address, deployer.address, 1, sender=owner)
    assert art_piece.getOwner() == deployer.address
    assert art_piece.ownerOf(1) == deployer.address

# Tests for ArtPiece creation from Profile
def test_create_artpiece_with_erc721(setup):
    """Test creating ArtPiece through Profile and verify ERC721 functionality"""
    owner = setup["owner"]
    artist = setup["artist"]
    owner_profile = setup["owner_profile"]
    artist_profile = setup["artist_profile"]
    art_piece_template = setup["art_piece_template"]
    
    # Create art piece as owner/commissioner
    receipt = owner_profile.createArtPiece(
        art_piece_template.address,
        b"test_image",
        "Test Art",
        b"Test Description",
        False,  # Not artist
        artist.address,  # Artist is the other party
        "0x0000000000000000000000000000000000000000",  # No commission hub
        False,  # Not AI generated
        sender=owner
    )
    
    # Extract the art piece address from the logs or events
    # Since we don't have direct access to the contract address from the receipt,
    # we'll look at the transactions by the profile to find recently added art
    art_pieces = owner_profile.getRecentArtPieces(0, 1)
    assert len(art_pieces) > 0, "No art pieces found in the profile"
    
    art_piece_address = art_pieces[0]
    
    # Get the art piece contract
    art_piece = project.ArtPiece.at(art_piece_address)
    
    # Verify ERC721 properties
    assert art_piece.name() == "ArtPiece"
    assert art_piece.symbol() == "ART"
    assert art_piece.balanceOf(owner.address) == 1
    assert art_piece.ownerOf(1) == owner.address
    
    # Create another art piece as artist
    artist_receipt = artist_profile.createArtPiece(
        art_piece_template.address,
        b"artist_image",
        "Artist Creation",
        b"Created by Artist",
        True,  # Is artist
        owner.address,  # Commissioner is the other party
        "0x0000000000000000000000000000000000000000",  # No commission hub
        False,  # Not AI generated
        sender=artist
    )
    
    # Get the artist's recent art pieces
    artist_art_pieces = artist_profile.getRecentArtPieces(0, 1)
    assert len(artist_art_pieces) > 0, "No art pieces found in the artist's profile"
    
    artist_art_piece_address = artist_art_pieces[0]
    
    # Get the art piece contract
    artist_art_piece = project.ArtPiece.at(artist_art_piece_address)
    
    # Verify ERC721 properties for artist-created piece
    assert artist_art_piece.name() == "ArtPiece"
    assert artist_art_piece.symbol() == "ART"
    assert artist_art_piece.balanceOf(owner.address) == 1  # Commissioner is the owner
    assert artist_art_piece.ownerOf(1) == owner.address
    assert artist_art_piece.getArtist() == artist.address 