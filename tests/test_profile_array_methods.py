import pytest
from ape import accounts, project
import time

def empty(type_=str):
    return "0x0000000000000000000000000000000000000000"

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
    art_piece_template = setup["art_piece_template"]
    
    # Test empty state
    assert owner_profile.commissionCount() == 0
    empty_commissions = owner_profile.getCommissions(0, 10)
    assert len(empty_commissions) == 0
    empty_recent = owner_profile.getRecentCommissions(0, 10)
    assert len(empty_recent) == 0
    
    # Create test art pieces
    test_commissions = []
    for i in range(8):
        # Create a valid art piece
        token_uri_data = f"data:image/png;base64,test{i}".encode()
        token_uri_format = "png"
        
        art_piece = project.ArtPiece.deploy(sender=owner)
        art_piece.initialize(
            token_uri_data,
            token_uri_format,
            f"Test Art {i}",
            f"Test Description {i}",
            owner.address,  # Owner
            owner.address,  # Artist (same as owner for test)
            "0x0000000000000000000000000000000000000000",  # No commission hub
            False,  # Not AI generated
            sender=owner
        )
        test_commissions.append(art_piece.address)
    
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

# Tests for Unverified Commission Array Methods
def test_unverified_commission_array_methods(setup):
    """Test unverified commission array methods"""
    owner = setup["owner"]
    owner_profile = setup["owner_profile"]
    user1 = setup["user1"]
    art_piece_template = setup["art_piece_template"]
    
    # Test empty state
    assert owner_profile.unverifiedCommissionCount() == 0
    
    # Test allow/disallow unverified commissions
    assert owner_profile.allowUnverifiedCommissions() is True  # Default is True
    owner_profile.setAllowUnverifiedCommissions(False, sender=owner)
    assert owner_profile.allowUnverifiedCommissions() is False
    owner_profile.setAllowUnverifiedCommissions(True, sender=owner)
    assert owner_profile.allowUnverifiedCommissions() is True
    
    # Remove user1 from whitelist to ensure commissions go to unverified
    owner_profile.removeFromWhitelist(user1.address, sender=owner)
    
    # Create test art pieces
    test_commissions = []
    for i in range(5):
        # Create a valid art piece
        token_uri_data = f"data:image/png;base64,unverified{i}".encode()
        token_uri_format = "png"
        
        art_piece = project.ArtPiece.deploy(sender=user1)
        art_piece.initialize(
            token_uri_data,
            token_uri_format,
            f"Unverified Art {i}",
            f"Unverified Description {i}",
            user1.address,  # Owner
            user1.address,  # Artist
            "0x0000000000000000000000000000000000000000",  # No commission hub
            False,  # Not AI generated
            sender=user1
        )
        test_commissions.append(art_piece.address)
    
    # Add unverified commissions (using user1 who is not whitelisted)
    for comm in test_commissions:
        owner_profile.addCommission(comm, sender=user1)
    
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
    owner_profile.removeCommission(test_commissions[2], sender=owner)
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
    art_piece_template = setup["art_piece_template"]
    
    # Create test art pieces
    test_commissions = []
    for i in range(5):
        # Create a valid art piece
        token_uri_data = f"data:image/png;base64,artist{i}".encode()
        token_uri_format = "png"
        
        art_piece = project.ArtPiece.deploy(sender=artist)
        art_piece.initialize(
            token_uri_data,
            token_uri_format,
            f"Artist Art {i}",
            f"Artist Description {i}",
            artist.address,  # Owner
            artist.address,  # Artist
            "0x0000000000000000000000000000000000000000",  # No commission hub
            False,  # Not AI generated
            sender=artist
        )
        test_commissions.append(art_piece.address)
    
    # Test for artist profile
    # Add my commissions
    for comm in test_commissions:
        artist_profile.addCommission(comm, sender=artist)
    
    # Test getCommissions
    my_commissions = artist_profile.getCommissions(0, 10)
    assert len(my_commissions) == 5
    for i, comm in enumerate(test_commissions):
        assert my_commissions[i] == comm
    
    # Test getRecentCommissions
    recent = artist_profile.getRecentCommissions(0, 10)
    assert len(recent) == 5
    for i, comm in enumerate(test_commissions):
        assert recent[4-i] == comm
    
    # Test pagination
    page_0 = artist_profile.getCommissions(0, 2)
    assert len(page_0) == 2
    assert page_0[0] == test_commissions[0]
    assert page_0[1] == test_commissions[1]
    
    # Test remove my commission
    artist_profile.removeCommission(test_commissions[2], sender=artist)
    updated = artist_profile.getCommissions(0, 10)
    assert len(updated) == 4
    assert test_commissions[2] not in updated

# Tests for ArtPiece creation from Profile
def test_create_artpiece_with_erc721(setup):
    """Test creating ArtPiece through Profile and verify ERC721 functionality"""
    owner = setup["owner"]
    artist = setup["artist"]
    owner_profile = setup["owner_profile"]
    artist_profile = setup["artist_profile"]
    art_piece_template = setup["art_piece_template"]
    
    # Create art piece as owner/commissioner
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiVGVzdCBBcnQiLCJkZXNjcmlwdGlvbiI6IlRlc3QgRGVzY3JpcHRpb24iLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFCM1JKVFVVSDVBb1NEdUZvQ0FBQUFBMUpSRUZVZU5xVEVFRUFBQUE1VVBBRHhpVXFJVzRBQUFBQlNVVk9SSzVDWUlJPSJ9"
    token_uri_format = "avif"  # Set the format to avif
    
    receipt = owner_profile.createArtPiece(
        art_piece_template.address,
        token_uri_data,
        token_uri_format,
        "Test Art",
        "Test Description",
        False,  # Not artist
        artist.address,  # Artist is the other party
        False,  # Not AI generated
        empty(),  # No commission hub
        False,  # Not profile art
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
        b"data:application/json;base64,eyJuYW1lIjoiQXJ0aXN0IENyZWF0aW9uIiwiZGVzY3JpcHRpb24iOiJDcmVhdGVkIGJ5IEFydGlzdCIsImltYWdlIjoiZGF0YTppbWFnZS9wbmc7YmFzZTY0LGlWQk9SdzBLR2dvQUFBQU5TVWhFVWdBQUFBUUFBQUFFQ0FJQUFBQ05kQ3ZEQUFBQUJYULNU0kE6eTdid0p3QUFBQWxJUkVGVUNKbGp4QUVDVGdCSzVnRGk3QUFBQUFFbEZUa1N1UW1DQyJ9",
        "avif",  # Set the format to avif
        "Artist Creation",
        "Created by Artist",
        True,  # Is artist
        owner.address,  # Commissioner is the other party
        False,  # Not AI generated
        empty(),  # No commission hub
        False,  # Not profile art
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